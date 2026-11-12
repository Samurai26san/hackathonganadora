"""OIDC authorization-code flow with PKCE S256, state, nonce and JWKS validation."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import token_hash
from app.models import OIDCTransaction, User
from app.models.user import now


class AuthService:
    def __init__(self, db: AsyncSession, http: httpx.AsyncClient) -> None:
        self.db, self.http, self.settings = db, http, get_settings()

    async def discovery(self) -> dict[str, Any]:
        if not self.settings.oidc_provider_url:
            raise AppException(
                "Configura el proveedor institucional OIDC para iniciar sesión.",
                503,
                "oidc_not_configured",
            )
        response = await self.http.get(
            f"{self.settings.oidc_provider_url.rstrip('/')}/.well-known/openid-configuration"
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        if data.get("issuer", "").rstrip("/") != self.settings.oidc_provider_url.rstrip(
            "/"
        ):
            raise AppException(
                "El emisor OIDC no corresponde al proveedor configurado.", 401
            )
        return data

    async def login_url(self) -> tuple[str, str]:
        config = await self.discovery()
        state, nonce, verifier = (secrets.token_urlsafe(48) for _ in range(3))
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        self.db.add(
            OIDCTransaction(
                state_hash=token_hash(state),
                verifier=verifier,
                nonce=nonce,
                expires_at=now() + timedelta(minutes=5),
            )
        )
        await self.db.flush()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.settings.oidc_client_id,
                "redirect_uri": self.settings.oidc_redirect_uri,
                "scope": self.settings.oidc_scopes,
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{config['authorization_endpoint']}?{query}", state

    async def callback(self, code: str, state: str, browser_state: str) -> User:
        if not secrets.compare_digest(state, browser_state):
            raise AppException(
                "No se pudo verificar el estado del inicio de sesión.", 401
            )
        transaction = await self.db.get(
            OIDCTransaction, token_hash(state), with_for_update=True
        )
        if (
            transaction is None
            or transaction.expires_at.replace(tzinfo=timezone.utc) <= now()
        ):
            raise AppException("El inicio de sesión expiró. Inténtalo nuevamente.", 401)
        await self.db.delete(transaction)
        await self.db.flush()
        config = await self.discovery()
        response = await self.http.post(
            config["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.settings.oidc_client_id,
                "client_secret": self.settings.oidc_client_secret,
                "redirect_uri": self.settings.oidc_redirect_uri,
                "code_verifier": transaction.verifier,
            },
        )
        response.raise_for_status()
        token = str(response.json()["id_token"])
        jwks_response = await self.http.get(config["jwks_uri"])
        jwks_response.raise_for_status()
        keys = jwt.PyJWKSet.from_dict(jwks_response.json())
        key_id = jwt.get_unverified_header(token).get("kid")
        key = next((key for key in keys.keys if key.key_id == key_id), None)
        if key is None:
            raise AppException("La firma institucional no tiene una clave válida.", 401)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256", "ES256"],
            audience=self.settings.oidc_client_id,
            issuer=str(config["issuer"]),
            options={"require": ["exp", "iat", "sub", "nonce", "iss", "aud"]},
        )
        if (
            claims.get("nonce") != transaction.nonce
            or claims.get("email_verified") is not True
        ):
            raise AppException(
                "El proveedor no confirmó la identidad institucional.", 401
            )
        if (
            isinstance(claims["aud"], list)
            and len(claims["aud"]) > 1
            and claims.get("azp") != self.settings.oidc_client_id
        ):
            raise AppException("Cliente OIDC no autorizado.", 401)
        subject = f"{config['issuer']}|{claims['sub']}"
        user = await self.db.scalar(select(User).where(User.oidc_subject == subject))
        if user is None:
            # Accounts are provisioned by an administrator; an OIDC email alone
            # never grants a role or unrestricted access to financial data.
            user = await self.db.scalar(
                select(User).where(User.email == str(claims.get("email", "")).lower())
            )
            if user is None or user.oidc_subject is not None:
                raise AppException(
                    "Solicita a administración que habilite tu cuenta institucional.",
                    403,
                )
            user.oidc_subject = subject
        if not user.is_active:
            raise AppException("La cuenta no está activa.", 403)
        await self.db.flush()
        return user

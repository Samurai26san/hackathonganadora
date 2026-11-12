"""Session revocation, scopes, RBAC, CSRF origins and OIDC transaction binding."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import hash_password
from app.main import app
from app.models import OIDCTransaction, User
from app.models.user import now
from app.services.auth_service import AuthService


@pytest.fixture
async def client(
    db: AsyncSession, sample: User, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[httpx.AsyncClient]:
    # Unit checks for the explicit demo path must not depend on local OIDC setup.
    monkeypatch.setattr(get_settings(), "auth_mode", "demo")
    monkeypatch.setattr(get_settings(), "cookie_secure", False)
    sample.password_hash = hash_password("Demo2026!")

    async def override_db() -> AsyncIterator[AsyncSession]:
        yield db
        await db.flush()

    app.dependency_overrides[get_db] = override_db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8080",
        headers={"Origin": "http://localhost:8080"},
    ) as client:
        yield client
    app.dependency_overrides.clear()


async def test_login_rbac_scope_and_revoke(
    client: httpx.AsyncClient, sample: User
) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/login", json={"email": sample.email, "password": "wrong"}
        )
    ).status_code == 401
    response = await client.post(
        "/api/v1/auth/login", json={"email": sample.email, "password": "Demo2026!"}
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert (await client.get("/api/v1/users")).status_code == 403
    sample.region_ids = [1]
    data = (await client.get("/api/v1/budget/execution/summary?years=2026")).json()
    assert data["summary"]["executed"] == "0.30"
    catalogs = (await client.get("/api/v1/catalogs")).json()
    assert catalogs["region"] == [{"id": 1, "name": "LP"}]
    exported = await client.post(
        "/api/v1/reports/export",
        json={
            "report": "movements",
            "format": "csv",
            "filters": {
                "years": [2026],
                "date_from": "2026-03-01",
                "date_to": "2026-03-02",
            },
        },
    )
    assert exported.status_code == 200
    assert (
        "0.10" in exported.text
        and "0.20" in exported.text
        and "Pasaje 3" not in exported.text
    )
    assert (
        await client.post(
            "/api/v1/auth/logout", headers={"Origin": "https://evil.example"}
        )
    ).status_code == 403
    assert (await client.post("/api/v1/auth/logout")).status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_oidc_state_expired_and_cross_browser(db: AsyncSession) -> None:
    async with httpx.AsyncClient() as http:
        service = AuthService(db, http)
        with pytest.raises(AppException):
            await service.callback("code", "attacker", "victim")
        from app.core.security import token_hash

        db.add(
            OIDCTransaction(
                state_hash=token_hash("expired"),
                verifier="v",
                nonce="n",
                expires_at=now() - timedelta(minutes=1),
            )
        )
        await db.flush()
        with pytest.raises(AppException):
            await service.callback("code", "expired", "expired")


async def test_oidc_validates_signed_identity_and_pkce(
    db: AsyncSession, sample: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.core.config import get_settings
    from app.core.security import token_hash

    settings = get_settings()
    monkeypatch.setattr(settings, "oidc_provider_url", "https://idp.example")
    monkeypatch.setattr(settings, "oidc_client_id", "exb-client")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk["kid"] = "test-key"
    token = jwt.encode(
        {
            "iss": "https://idp.example",
            "aud": "exb-client",
            "sub": "subject-1",
            "exp": now() + timedelta(minutes=5),
            "iat": now(),
            "nonce": "test-nonce",
            "email_verified": True,
            "email": sample.email,
        },
        key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": "https://idp.example",
                    "token_endpoint": "https://idp.example/token",
                    "jwks_uri": "https://idp.example/jwks",
                    "authorization_endpoint": "https://idp.example/authorize",
                },
            )
        if request.url.path == "/token":
            assert b"code_verifier=test-verifier" in request.content
            return httpx.Response(200, json={"id_token": token})
        return httpx.Response(200, json={"keys": [jwk]})

    db.add(
        OIDCTransaction(
            state_hash=token_hash("valid-state"),
            verifier="test-verifier",
            nonce="test-nonce",
            expires_at=now() + timedelta(minutes=5),
        )
    )
    await db.flush()
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as http:
        user = await AuthService(db, http).callback(
            "authorization-code", "valid-state", "valid-state"
        )
        assert user.id == sample.id
        assert user.oidc_subject == "https://idp.example|subject-1"
        assert await db.get(OIDCTransaction, token_hash("valid-state")) is None
        with pytest.raises(AppException):
            await AuthService(db, http).callback(
                "authorization-code", "valid-state", "valid-state"
            )

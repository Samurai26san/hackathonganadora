"""Revocable HttpOnly sessions and role dependencies. No tokens in localStorage."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta, timezone
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AppException, ForbiddenException
from app.models import AuthSession, User
from app.models.user import now

COOKIE = "exb_session"
DB = Annotated[AsyncSession, Depends(get_db)]


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 600_000
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    return hmac.compare_digest(
        hash_password(password, encoded.split("$", 1)[0]), encoded
    )


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_session(db: AsyncSession, user: User, response: Response) -> None:
    settings = get_settings()
    token = secrets.token_urlsafe(48)
    db.add(
        AuthSession(
            token_hash=token_hash(token),
            user_id=user.id,
            expires_at=now() + timedelta(hours=settings.session_hours),
        )
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    await db.flush()


async def get_current_user(request: Request, db: DB) -> User:
    token = request.cookies.get(COOKIE)
    session = await db.get(AuthSession, token_hash(token)) if token else None
    if session is None or session.expires_at.replace(tzinfo=timezone.utc) <= now():
        raise AppException("Inicia sesión para continuar.", 401, "unauthenticated")
    user = await db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise AppException("La cuenta no está activa.", 401, "unauthenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise ForbiddenException("Esta acción está reservada a administración.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def user_out(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "scopes": {
            "region_ids": user.region_ids,
            "area_ids": user.area_ids,
            "financier_ids": user.financier_ids,
        },
    }

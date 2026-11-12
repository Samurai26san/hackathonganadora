"""Institutional authentication and explicitly local demonstration login."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import (
    COOKIE,
    DB,
    CurrentUser,
    create_session,
    token_hash,
    user_out,
    verify_password,
)
from app.models import AuditLog, AuthSession, User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Identidad"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(default="", max_length=255)
    password: str = Field(default="", max_length=256)


@router.post(
    "/login",
    summary="Iniciar sesión institucional",
    description="OIDC con PKCE; contraseña solo en modo demo explícito.",
)
async def login(
    body: LoginRequest, request: Request, response: Response, db: DB
) -> dict[str, object]:
    if get_settings().auth_mode == "oidc":
        url, state = await AuthService(db, request.app.state.http).login_url()
        response.set_cookie(
            "exb_oidc_state",
            state,
            max_age=300,
            httponly=True,
            secure=get_settings().cookie_secure,
            samesite="lax",
            path="/",
        )
        return {"authorization_url": url}
    user = await db.scalar(
        select(User).where(
            User.email == body.email.strip().lower(), User.is_active.is_(True)
        )
    )
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        db.add(AuditLog(user_id=None, action="auth.login", status="denied"))
        await db.commit()
        raise AppException("Correo o contraseña de demostración incorrectos.", 401)
    await create_session(db, user, response)
    db.add(AuditLog(user_id=user.id, action="auth.login"))
    return user_out(user)


@router.get(
    "/callback",
    summary="Retorno del proveedor OIDC",
    description="Valida state, PKCE, firma, emisor, audiencia y nonce del ID token.",
)
async def callback(code: str, state: str, request: Request, db: DB) -> RedirectResponse:
    user = await AuthService(db, request.app.state.http).callback(
        code, state, request.cookies.get("exb_oidc_state", "")
    )
    response = RedirectResponse("/", status_code=303)
    await create_session(db, user, response)
    response.delete_cookie("exb_oidc_state", path="/")
    db.add(AuditLog(user_id=user.id, action="auth.oidc_callback"))
    return response


@router.get(
    "/me",
    summary="Cuenta autenticada",
    description="Devuelve rol y alcances definidos en el servidor.",
)
async def me(user: CurrentUser) -> dict[str, object]:
    return user_out(user)


@router.post(
    "/refresh",
    summary="Rotar sesión",
    description="Invalida la cookie previa y emite una nueva sesión revocable.",
)
async def refresh(
    request: Request, response: Response, user: CurrentUser, db: DB
) -> dict[str, object]:
    old = await db.get(AuthSession, token_hash(request.cookies[COOKIE]))
    if old:
        await db.delete(old)
    await create_session(db, user, response)
    return user_out(user)


@router.post(
    "/logout",
    summary="Cerrar sesión",
    description="Revoca la sesión del servidor y elimina la cookie HttpOnly.",
)
async def logout(
    request: Request, response: Response, user: CurrentUser, db: DB
) -> dict[str, bool]:
    session = await db.get(AuthSession, token_hash(request.cookies[COOKIE]))
    if session:
        await db.delete(session)
    response.delete_cookie(COOKIE, path="/")
    db.add(AuditLog(user_id=user.id, action="auth.logout"))
    return {"ok": True}

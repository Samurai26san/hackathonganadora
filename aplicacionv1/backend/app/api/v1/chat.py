"""SSE POST owns its database lifetime, independently of request dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.database import SessionFactory
from app.core.exceptions import AppException
from app.core.security import DB, CurrentUser
from app.models import ChatMessage, ChatSession
from app.schemas.chat import ChatEvent, ChatRequest
from app.services.chat_service import ChatService
from app.services.context_manager import ContextManager
from app.services.llm_client import LLMClient

router = APIRouter(tags=["Juku"])


@router.post(
    "/chat/stream",
    summary="Conversación con Juku por SSE",
    description="Emite delta, tool_call, tool_result, context_update, done o error; herramientas estrictamente permitidas.",
)
async def stream(
    body: ChatRequest, request: Request, db: DB, user: CurrentUser
) -> StreamingResponse:
    if body.session_id:
        await ContextManager(db).owned_session(user, body.session_id)

    async def events() -> AsyncIterator[str]:
        async with SessionFactory() as session:
            service = ChatService(
                session, LLMClient(request.app.state.http), request.app.state.http
            )
            try:
                async for event in service.process_message(
                    user, body.session_id, body.message, body.filters
                ):
                    if await request.is_disconnected():
                        break
                    yield event.sse()
            except AppException as error:
                yield ChatEvent(
                    event="error", data=error.detail, session_id=body.session_id or ""
                ).sse()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/sessions",
    summary="Conversaciones del usuario",
    description="El historial nunca incluye conversaciones de otros usuarios.",
)
async def sessions(db: DB, user: CurrentUser) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        {"id": row.id, "title": row.title, "created_at": row.created_at.isoformat()}
        for row in rows
    ]


@router.post(
    "/sessions",
    summary="Crear conversación",
    description="Crea una conversación vacía perteneciente al usuario autenticado.",
)
async def create_session(db: DB, user: CurrentUser) -> dict[str, str]:
    row = ChatSession(user_id=user.id)
    db.add(row)
    await db.flush()
    return {"id": row.id, "title": row.title}


@router.get(
    "/sessions/{session_id}/messages",
    summary="Historial de conversación",
    description="Mensajes y resultados persistidos, después de verificar propiedad.",
)
async def messages(session_id: str, db: DB, user: CurrentUser) -> list[dict[str, Any]]:
    await ContextManager(db).owned_session(user, session_id)
    rows = (
        await db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sequence)
        )
    ).all()
    return [{"role": row.role, **row.content_json} for row in rows]


@router.get(
    "/sessions/{session_id}/context",
    summary="Filtros conversacionales activos",
    description="Devuelve contexto estructurado persistido y reporte base.",
)
async def context(session_id: str, db: DB, user: CurrentUser) -> dict[str, Any]:
    manager = ContextManager(db)
    await manager.owned_session(user, session_id)
    value = await manager.get_context(session_id)
    return {
        "active_filters": value.active_filters_json,
        "current_report": value.current_report,
    }


@router.post(
    "/sessions/{session_id}/context/reset",
    summary="Limpiar contexto",
    description="Reinicia filtros de la conversación propia; conserva el historial.",
)
async def reset(session_id: str, db: DB, user: CurrentUser) -> dict[str, bool]:
    manager = ContextManager(db)
    await manager.owned_session(user, session_id)
    await manager.reset_context(session_id)
    return {"ok": True}

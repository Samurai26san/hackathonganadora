"""Session ownership and explicit structured-filter persistence."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models import ChatSession, ConversationContext, User
from app.schemas.budget import BudgetFilterParams


class ContextManager:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def owned_session(self, user: User, session_id: str) -> ChatSession:
        session = await self.db.get(ChatSession, session_id)
        if session is None or session.user_id != user.id:
            raise NotFoundException("La conversación no está disponible.")
        return session

    async def get_context(self, session_id: str) -> ConversationContext:
        context = await self.db.get(ConversationContext, session_id)
        if context is None:
            context = ConversationContext(session_id=session_id, active_filters_json={})
            self.db.add(context)
            await self.db.flush()
        return context

    async def update_context(
        self, session_id: str, filters: BudgetFilterParams, report: str | None
    ) -> ConversationContext:
        context = await self.get_context(session_id)
        context.active_filters_json = filters.model_dump(mode="json")
        context.current_report = report
        await self.db.flush()
        return context

    async def reset_context(self, session_id: str) -> ConversationContext:
        context = await self.get_context(session_id)
        context.active_filters_json, context.current_report = {}, None
        await self.db.flush()
        return context

"""Read the active dictionary on every turn so updates are not cached in prompts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataDictionary


class DictionaryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_system_prompt_context(self) -> str:
        entries = (
            await self.db.scalars(
                select(DataDictionary).where(DataDictionary.activo.is_(True))
            )
        ).all()
        return "\n".join(
            f"- {entry.termino_usuario}: {entry.descripcion}; sinónimos: {', '.join(entry.sinonimos_json)}"
            for entry in entries
        )

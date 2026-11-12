"""Real chunk persistence and retrieval; deterministic HTTP TEI fixture only."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models import KnowledgeChunk
from app.services.rag_service import RAGService


async def test_ingestion_search_threshold_and_idempotence(db: AsyncSession) -> None:
    def tei(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[[1.0] + [0.0] * 1023])

    async with httpx.AsyncClient(transport=httpx.MockTransport(tei)) as http:
        rag = RAGService(db, http)
        created = await rag.ingest_text(
            "El procedimiento institucional requiere validación documentada de ampliaciones presupuestarias.",
            "manual",
            "test-manual",
            "Manual de prueba",
        )
        assert created[0].content_tokens > 0
        result = await rag.search("ampliaciones", source_types=["manual"])
        assert len(result) == 1 and result[0]["similarity"] == pytest.approx(1)
        assert "[Fuente 1: Manual de prueba]" in rag.format_context_for_prompt(result)
        assert await rag.search("ampliaciones", source_types=["law"]) == []
        await rag.ingest_text(
            "Documento revisado para la misma fuente institucional.",
            "manual",
            "test-manual",
            "Manual de prueba",
        )
        assert len((await db.scalars(select(KnowledgeChunk))).all()) == 1
        (await db.scalars(select(KnowledgeChunk))).one().embedding = [0.0, 1.0] + [
            0.0
        ] * 1022
        await db.flush()
        assert await rag.search("ampliaciones") == []
        assert "No se encontró" in rag.format_context_for_prompt([])


async def test_invalid_embedding_and_chunk_boundaries(db: AsyncSession) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[[0.1]]))
    ) as http:
        rag = RAGService(db, http)
        with pytest.raises(AppException):
            await rag._get_embedding("test")
        with pytest.raises(AppException):
            await rag.ingest_text("test", "manual", "bad", "bad", chunk_overlap=512)

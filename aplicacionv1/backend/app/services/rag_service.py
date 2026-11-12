"""TEI BGE-m3 ingestion and dense/BM25 reciprocal-rank retrieval with citations."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Any

import httpx
import tiktoken
from rank_bm25 import BM25Okapi
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models import KnowledgeChunk


class RAGService:
    def __init__(self, db: AsyncSession, http: httpx.AsyncClient) -> None:
        self.db, self.http, self.settings = db, http, get_settings()

    async def _get_embedding(self, text: str) -> list[float]:
        response = await self.http.post(
            f"{self.settings.embeddings_server_url.rstrip('/')}/embed",
            json={"inputs": [text], "truncate": True},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list) or not data or not isinstance(data[0], list):
            raise AppException(
                "El servicio de embeddings devolvió un formato inválido.", 502
            )
        vector = [float(value) for value in data[0]]
        if (
            len(vector) != self.settings.embedding_dim
            or not all(math.isfinite(v) for v in vector)
            or not any(vector)
        ):
            raise AppException(
                "El embedding no tiene la dimensión BGE-m3 esperada (1024) o contiene valores inválidos.",
                502,
            )
        return vector

    async def ingest_text(
        self,
        content: str,
        source_type: str,
        source_id: str,
        source_title: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> list[KnowledgeChunk]:
        if source_type not in {"manual", "regulation", "law", "classifier", "faq"}:
            raise AppException("Tipo de fuente no permitido.")
        if (
            not 0 <= chunk_overlap < chunk_size
            or chunk_size > 2048
            or not content.strip()
        ):
            raise AppException("Texto o parámetros de fragmentación inválidos.")
        encoder = tiktoken.get_encoding("cl100k_base")
        tokens = encoder.encode(content)
        chunks: list[KnowledgeChunk] = []
        for start in range(0, len(tokens), chunk_size - chunk_overlap):
            part = tokens[start : start + chunk_size]
            text = encoder.decode(part)
            chunks.append(
                KnowledgeChunk(
                    content=text,
                    content_tokens=len(part),
                    embedding=await self._get_embedding(text),
                    source_type=source_type,
                    source_id=source_id,
                    source_title=source_title,
                    chunk_index=len(chunks),
                    tags=tags or [],
                    metadata_json=metadata or {},
                )
            )
            if start + chunk_size >= len(tokens):
                break
        # All embeddings must succeed before replacing an ingested source.
        await self.db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)
        )
        self.db.add_all(chunks)
        await self.db.flush()
        return chunks

    async def search(
        self, query: str, top_k: int = 5, source_types: Sequence[str] | None = None
    ) -> list[dict[str, Any]]:
        vector = await self._get_embedding(query)
        base = select(KnowledgeChunk)
        if source_types is not None:
            base = base.where(KnowledgeChunk.source_type.in_(source_types))
        sqlite = self.db.get_bind().dialect.name == "sqlite"
        if sqlite:
            candidates = list((await self.db.scalars(base.limit(100))).all())
        else:
            distance = KnowledgeChunk.embedding.cosine_distance(vector)
            dense = list(
                (await self.db.scalars(base.order_by(distance).limit(50))).all()
            )
            lexical = func.ts_rank_cd(
                func.to_tsvector("spanish", KnowledgeChunk.content),
                func.plainto_tsquery("spanish", query),
            )
            sparse = list(
                (
                    await self.db.scalars(
                        base.where(lexical > 0).order_by(lexical.desc()).limit(50)
                    )
                ).all()
            )
            candidates = list({chunk.id: chunk for chunk in [*dense, *sparse]}.values())
        if not candidates:
            return []

        def cosine(chunk: KnowledgeChunk) -> float:
            denominator = math.sqrt(sum(v * v for v in vector)) * math.sqrt(
                sum(v * v for v in chunk.embedding)
            )
            # pgvector loads numpy.float32 values; convert the similarity score
            # to a JSON-native float before persisting tool results.
            return (
                float(sum(a * b for a, b in zip(vector, chunk.embedding)) / denominator)
                if denominator
                else 0.0
            )

        similarities = {chunk.id: cosine(chunk) for chunk in candidates}

        def tokenize(text: str) -> list[str]:
            return re.findall(r"\w+", text.lower())

        bm25 = BM25Okapi([tokenize(chunk.content) for chunk in candidates])
        lexical_scores = bm25.get_scores(tokenize(query))
        dense_order = sorted(
            range(len(candidates)),
            key=lambda i: similarities[candidates[i].id],
            reverse=True,
        )
        sparse_order = sorted(
            range(len(candidates)), key=lambda i: float(lexical_scores[i]), reverse=True
        )
        scores: dict[int, float] = {}
        for order in [dense_order, sparse_order]:
            for rank, index in enumerate(order, 1):
                scores[index] = scores.get(index, 0) + 1 / (60 + rank)
        results = []
        for index in sorted(scores, key=lambda i: scores[i], reverse=True):
            chunk = candidates[index]
            if similarities[chunk.id] < self.settings.rag_similarity_threshold:
                continue
            results.append(
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "source_id": chunk.source_id,
                    "source_title": chunk.source_title,
                    "source_type": chunk.source_type,
                    "chunk_index": chunk.chunk_index,
                    "similarity": similarities[chunk.id],
                    "metadata": chunk.metadata_json,
                }
            )
            if len(results) == top_k:
                break
        return results

    @staticmethod
    def format_context_for_prompt(results: list[dict[str, Any]]) -> str:
        if not results:
            return "No se encontró información institucional relevante. No inventes normativa ni citas."
        return "\n\n".join(
            f"[Fuente {i}: {r['source_title']}]\n{str(r['content'])[:2000]}"
            for i, r in enumerate(results, 1)
        )

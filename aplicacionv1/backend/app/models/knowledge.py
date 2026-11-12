"""Institutional document chunks; embeddings never contain financial measures."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import now, uid


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("source_id", "chunk_index"),
        Index(
            "ix_knowledge_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    content: Mapped[str] = mapped_column(Text)
    content_tokens: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1024).with_variant(JSON(), "sqlite")
    )
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str] = mapped_column(String(255), index=True)
    source_title: Mapped[str] = mapped_column(String(500))
    chunk_index: Mapped[int] = mapped_column(Integer)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

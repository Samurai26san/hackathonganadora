"""Validated tool arguments and server-sent event envelopes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.budget import BudgetFilterParams


class SearchKnowledgeParams(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    query: str = Field(min_length=2, max_length=2000)
    source_types: (
        list[Literal["regulation", "manual", "faq", "classifier", "law"]] | None
    ) = None
    top_k: int = Field(default=5, ge=1, le=10)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    filters: BudgetFilterParams | None = None


class ChatEvent(BaseModel):
    event: Literal[
        "delta", "tool_call", "tool_result", "context_update", "done", "error"
    ]
    data: Any
    session_id: str

    def sse(self) -> str:
        return f"event: {self.event}\ndata: {self.model_dump_json()}\n\n"

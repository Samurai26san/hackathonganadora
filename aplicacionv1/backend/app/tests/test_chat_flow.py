"""Strict tool execution, persisted context and SSE envelopes."""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models import ChatMessage, ConversationContext, User
from app.schemas.budget import BudgetFilterParams
from app.services.chat_service import ChatService
from app.services.context_manager import ContextManager
from app.services.llm_client import LLMClient


async def test_strict_dispatch_rejects_sql_and_context_persists(
    db: AsyncSession, sample: User
) -> None:
    def llm(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["messages"][-1]["role"] == "tool":
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Consulta completada."}}]},
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "get_execution_by_financier",
                                        "arguments": '{"years":[2026],"group_by":"financier"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(llm)) as http:
        service = ChatService(db, LLMClient(http), http)
        with pytest.raises(AppException):
            await service.execute_tool(sample, "__dict__", "{}", {"years": [2026]})
        with pytest.raises(ValidationError):
            await service.execute_tool(
                sample,
                "get_general_summary",
                '{"sql":"DROP TABLE budgets"}',
                {"years": [2026]},
            )
        with pytest.raises(ValidationError):
            await service.execute_tool(
                sample, "get_general_summary", '{"years":["2026"]}', {}
            )
        events = [
            event
            async for event in service.process_message(
                sample, None, "por financiador", BudgetFilterParams(years=[2026])
            )
        ]
        assert [event.event for event in events][-1] == "done"
        assert any(
            event.event == "tool_result" and not event.data["is_error"]
            for event in events
        )
        assert "event: done\ndata:" in events[-1].sse()
        context = await db.get(ConversationContext, events[-1].session_id)
        assert context and context.active_filters_json["years"] == [2026]
        assert context.active_filters_json["group_by"] == "financier"
        assert (await db.scalars(select(ChatMessage))).all()
        other = User(
            id="other", email="other@test.exb", full_name="Otro", role="viewer"
        )
        with pytest.raises(AppException):
            await ContextManager(db).owned_session(other, events[-1].session_id)


async def test_three_turns_merge_filters_and_compare_existing_years(
    db: AsyncSession, sample: User
) -> None:
    def llm(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["messages"][-1]["role"] == "tool":
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Resultado verificado."}}]},
            )
        question = body["messages"][-1]["content"]
        if "2025" in question:
            name, arguments = "compare_budget_periods", '{"years":[2025,2026]}'
        elif "financiador" in question:
            name, arguments = "get_execution_by_financier", '{"group_by":"financier"}'
        else:
            name, arguments = "get_general_summary", '{"years":[2026]}'
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "turn-tool",
                                    "type": "function",
                                    "function": {"name": name, "arguments": arguments},
                                }
                            ],
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(llm)) as http:
        service = ChatService(db, LLMClient(http), http)
        session_id = None
        for message in ["Muéstrame 2026", "Ahora por financiador", "Compara con 2025"]:
            events = [
                event
                async for event in service.process_message(sample, session_id, message)
            ]
            assert events[-1].event == "done"
            assert all(
                not event.data.get("is_error", False)
                for event in events
                if event.event == "tool_result"
            )
            session_id = events[-1].session_id
        context = await db.get(ConversationContext, session_id)
        assert context is not None
        assert context.active_filters_json["years"] == [2025, 2026]
        assert context.active_filters_json["group_by"] == "financier"
        assert context.current_report == "compare"


async def test_rag_tool_returns_verifiable_citation(
    db: AsyncSession, sample: User
) -> None:
    from app.models import KnowledgeChunk

    db.add(
        KnowledgeChunk(
            content="Documento institucional de prueba: la revisión se registra antes de aprobar.",
            content_tokens=18,
            embedding=[1.0] + [0.0] * 1023,
            source_type="manual",
            source_id="test-only",
            source_title="Manual de prueba",
            chunk_index=0,
        )
    )
    await db.flush()

    def services(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/embed":
            return httpx.Response(200, json=[[1.0] + [0.0] * 1023])
        body = json.loads(request.content)
        if body["messages"][-1]["role"] == "tool":
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "El documento recuperado exige registrar la revisión."
                            }
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "knowledge-1",
                                    "type": "function",
                                    "function": {
                                        "name": "search_institutional_knowledge",
                                        "arguments": '{"query":"revisión institucional","top_k":3}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(services)) as http:
        events = [
            event
            async for event in ChatService(db, LLMClient(http), http).process_message(
                sample, None, "¿Qué dice el manual?"
            )
        ]
        assert events[-1].event == "done"
        assert "[Fuente 1: Manual de prueba]" in events[-1].data["content"]
        results = [
            event.data["result"] for event in events if event.event == "tool_result"
        ]
        assert results[0]["citations"][0]["source_id"] == "test-only"

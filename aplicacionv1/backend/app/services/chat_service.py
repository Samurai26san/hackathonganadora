"""Bounded, allowlisted tool-calling with durable context and financial evidence."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.prompts import build_system_prompt
from app.models import AuditLog, Budget, ChatMessage, ChatSession, Movement, User
from app.schemas.budget import BudgetFilterParams
from app.schemas.chat import ChatEvent, SearchKnowledgeParams
from app.services.catalog_service import catalogs
from app.services.context_manager import ContextManager
from app.services.financial_engine import FinancialEngine
from app.services.juku_assistant import (
    FALLBACK_TEXT,
    HELP_TEXT,
    Intent,
    JukuAssistant,
    latest_movement,
    parse_intent,
    summarize_report,
)
from app.services.llm_client import LLMClient
from app.services.rag_service import RAGService

TOOL_REPORTS = {
    "get_execution_by_account": "account",
    "get_execution_by_financier": "financier",
    "get_execution_by_area": "area",
    "get_execution_by_region": "region",
    "get_monthly_execution": "monthly",
    "get_transaction_details": "movements",
    "get_general_summary": "summary",
    "compare_budget_periods": "compare",
}
DESCRIPTIONS = {
    "get_execution_by_account": "Montos reales de presupuesto y ejecución por rubro y cuenta.",
    "get_execution_by_financier": "Montos y saldos por financiador o fuente de financiamiento.",
    "get_execution_by_area": "Montos de ejecución agrupados por área y financiador.",
    "get_execution_by_region": "Montos y porcentajes por región institucional.",
    "get_monthly_execution": "Evolución mensual de presupuesto y ejecución. PTTO es mes cero.",
    "get_transaction_details": "Movimientos reales con fecha, comprobante y glosa; permite búsqueda.",
    "get_general_summary": "Resumen consolidado: presupuesto inicial, vigente, ejecutado y saldo disponible.",
    "compare_budget_periods": "Comparación entre dos gestiones reales con diferencias absolutas y porcentuales.",
}


def tool_parameters(model: type[BaseModel]) -> dict[str, Any]:
    # Schema annotations consume context without changing validation. Keep all
    # constraints and required fields; execution still validates the full model.
    schema = model.model_json_schema()
    schema.pop("title", None)
    for definition in schema["properties"].values():
        definition.pop("title", None)
        definition.pop("default", None)
    return schema


AVAILABLE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": tool_parameters(BudgetFilterParams),
        },
    }
    for name, description in DESCRIPTIONS.items()
] + [
    {
        "type": "function",
        "function": {
            "name": "search_institutional_knowledge",
            "description": "Consulta normativa, leyes, manuales, clasificadores y procedimientos con fuentes; NO calcula montos.",
            "parameters": tool_parameters(SearchKnowledgeParams),
        },
    }
]
logger = structlog.get_logger()


class ChatService:
    def __init__(
        self, db: AsyncSession, llm_client: LLMClient, http: httpx.AsyncClient
    ) -> None:
        self.db, self.llm, self.rag = db, llm_client, RAGService(db, http)
        self.contexts = ContextManager(db)

    async def _append(
        self, session_id: str, role: str, content: dict[str, Any]
    ) -> None:
        maximum = await self.db.scalar(
            select(func.max(ChatMessage.sequence)).where(
                ChatMessage.session_id == session_id
            )
        )
        self.db.add(
            ChatMessage(
                session_id=session_id,
                role=role,
                content_json=content,
                sequence=int(maximum or 0) + 1,
            )
        )
        await self.db.flush()

    async def execute_tool(
        self, user: User, name: str, arguments: str, filters: dict[str, Any]
    ) -> tuple[dict[str, Any], BudgetFilterParams | None]:
        if len(arguments) > 20_000:
            raise AppException("Los argumentos de la herramienta exceden el límite.")
        raw = json.loads(arguments)
        if not isinstance(raw, dict):
            raise AppException("La herramienta requiere un objeto de parámetros.")
        if name in TOOL_REPORTS:
            params = BudgetFilterParams.model_validate_json(
                json.dumps({**filters, **raw})
            )
            engine = FinancialEngine(self.db, user)
            report = TOOL_REPORTS[name]
            result = (
                await engine.compare_budget_periods(params)
                if report == "compare"
                else await engine.report(report, params)
            )
            return result.model_dump(mode="json"), params
        if name == "search_institutional_knowledge":
            params_knowledge = SearchKnowledgeParams.model_validate_json(arguments)
            hits = await self.rag.search(
                params_knowledge.query,
                params_knowledge.top_k,
                params_knowledge.source_types,
            )
            return {
                "context": self.rag.format_context_for_prompt(hits),
                "citations": hits,
                "results_count": len(hits),
            }, None
        raise AppException("El modelo solicitó una herramienta no permitida.")

    async def _cutoff(self, user: User) -> date | None:
        return await latest_movement(self.db, user)

    async def _deterministic(
        self,
        user: User,
        session_id: str,
        intent: Intent | None,
        filters: dict[str, Any],
        cutoff: date | None,
    ) -> AsyncIterator[ChatEvent]:
        """Answer with the financial engine only: reports, help and fallback."""
        reports: list[tuple[str, Any]] = []
        citations: list[dict[str, Any]] = []
        if intent is None:
            text = FALLBACK_TEXT
        elif intent.kind == "help":
            text = HELP_TEXT
        elif intent.kind == "knowledge":
            try:
                citations = await self.rag.search(intent_query(intent), 5, None)
            except (httpx.HTTPError, AppException, ValueError):
                citations = []
            text = (
                "Encontré estos fragmentos en los documentos institucionales:\n"
                + "\n".join(
                    f"[Fuente {i}: {c['source_title']}]"
                    for i, c in enumerate(citations, 1)
                )
                if citations
                else "La búsqueda en documentos institucionales no está disponible "
                "en este momento. Mientras tanto puedo darte reportes y cifras del "
                'presupuesto: escribe "ayuda" para ver las opciones.'
            )
        else:
            answer = await JukuAssistant(self.db, user).answer(intent, filters, cutoff)
            text, reports = answer.text, answer.reports
        content: dict[str, Any] = {"content": text}
        if intent is not None and reports:
            # Lets the UI rebuild this answer as a shareable PDF later on.
            content["pdf_request"] = {
                "message": intent.query_text,
                "filters": {
                    k: v
                    for k, v in filters.items()
                    if k not in {"date_from", "date_to", "months", "page"}
                },
            }
        await self._append(session_id, "assistant", content)
        await self.db.commit()
        yield ChatEvent(event="delta", data=text, session_id=session_id)
        if citations:
            payload = {
                "call_id": "juku-knowledge",
                "result": {"citations": citations, "results_count": len(citations)},
                "is_error": False,
            }
            await self._append(
                session_id,
                "tool",
                {"name": "search_institutional_knowledge", **payload},
            )
            yield ChatEvent(event="tool_result", data=payload, session_id=session_id)
        for index, (name, result) in enumerate(reports):
            call_id = f"juku-{index + 1}"
            payload = {
                "call_id": call_id,
                "result": result.model_dump(mode="json"),
                "is_error": False,
            }
            yield ChatEvent(
                event="tool_call",
                data={"name": name, "call_id": call_id},
                session_id=session_id,
            )
            await self._append(session_id, "tool", {"name": name, **payload})
            self.db.add(
                AuditLog(
                    user_id=user.id,
                    action="chat.report",
                    resource_type=name,
                    resource_id=session_id,
                    payload_json={"parameters": result.metadata.get("filters")},
                )
            )
            yield ChatEvent(event="tool_result", data=payload, session_id=session_id)
        if intent is not None and reports:
            # Keep years and named entities; report periods stay in each result.
            active = BudgetFilterParams.model_validate(
                {
                    **{
                        k: v
                        for k, v in filters.items()
                        if k not in {"date_from", "date_to", "months"}
                    },
                    **intent.entity_filters,
                },
                strict=False,
            )
            report_type = str(reports[0][1].report_type)
            await self.contexts.update_context(session_id, active, report_type)
            yield ChatEvent(
                event="context_update",
                data={
                    "active_filters": active.model_dump(mode="json"),
                    "current_report": report_type,
                },
                session_id=session_id,
            )
        await self.db.commit()
        yield ChatEvent(event="done", data=content, session_id=session_id)

    async def process_message(
        self,
        user: User,
        session_id: str | None,
        user_message: str,
        ui_filters: BudgetFilterParams | None = None,
    ) -> AsyncIterator[ChatEvent]:
        if session_id:
            session = await self.contexts.owned_session(user, session_id)
        else:
            session = ChatSession(user_id=user.id, title=user_message[:90])
            self.db.add(session)
            await self.db.flush()
        context = await self.contexts.get_context(session.id)
        filters = dict(context.active_filters_json)
        if ui_filters is not None:
            filters.update(ui_filters.model_dump(mode="json"))
        if not filters.get("years"):
            # Only use years for which scoped financial facts exist.
            scoped = FinancialEngine(self.db, user)._apply_permissions(
                select(func.max(Budget.year)), Budget
            )
            budget_year = await self.db.scalar(scoped)
            movement_year = await self.db.scalar(
                FinancialEngine(self.db, user)._apply_permissions(
                    select(func.max(Movement.year)), Movement
                )
            )
            year = max(budget_year or 0, movement_year or 0)
            if year:
                filters["years"] = [year]
        if not filters.get("years"):
            raise AppException(
                "No hay datos presupuestarios autorizados para iniciar la consulta."
            )
        recent = (
            await self.db.scalars(
                select(ChatMessage)
                .where(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.sequence.desc())
                .limit(12)
            )
        ).all()
        history = [
            {"role": m.role, **m.content_json}
            for m in reversed(recent)
            if m.role in {"user", "assistant"}
            and "content" in m.content_json
            and not m.content_json.get("tool_calls")
        ]
        # Supply catalog IDs only through the same scope boundary as reports.
        allowed_catalog = await catalogs(self.db, user)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": await build_system_prompt(self.db)},
            {
                "role": "system",
                "content": f"CONTEXTO ACTIVO: {json.dumps(filters)}\nCATÁLOGO AUTORIZADO: {json.dumps(allowed_catalog, ensure_ascii=False)}",
            },
            *history,
            {"role": "user", "content": user_message},
        ]
        await self._append(session.id, "user", {"content": user_message})
        await self.contexts.update_context(
            session.id,
            BudgetFilterParams.model_validate_json(json.dumps(filters)),
            context.current_report,
        )
        await self.db.commit()
        yield ChatEvent(event="delta", data="", session_id=session.id)
        cutoff = await self._cutoff(user)
        intent = parse_intent(
            user_message,
            list(allowed_catalog.get("years", [])),
            cutoff,
            allowed_catalog,
        )
        # Periodic reports combine several engine queries; they never need Qwen.
        if intent is not None and intent.kind in {"report", "help"}:
            async for event in self._deterministic(
                user, session.id, intent, filters, cutoff
            ):
                yield event
            return
        evidence: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        try:
            for _ in range(3):
                answer = await self.llm.chat_completion(messages, AVAILABLE_TOOLS)
                calls = answer.get("tool_calls") or []
                if not calls:
                    text = str(answer.get("content") or "")
                    if evidence:
                        # Figures only come from the engine; model prose without
                        # digits is kept as a conversational introduction.
                        verified = summarize_report(evidence[-1])
                        keep = text.strip() and not any(c.isdigit() for c in text)
                        text = f"{text.strip()}\n\n{verified}" if keep else verified
                    elif citations:
                        text += "\n\n" + "\n".join(
                            f"[Fuente {i}: {c['source_title']}]"
                            for i, c in enumerate(citations, 1)
                        )
                    else:
                        text = "No se obtuvo evidencia verificable para esa consulta. Puedes seleccionar un informe financiero o consultar un documento institucional que esté cargado."
                    await self._append(session.id, "assistant", {"content": text})
                    await self.db.commit()
                    yield ChatEvent(event="delta", data=text, session_id=session.id)
                    yield ChatEvent(
                        event="done", data={"content": text}, session_id=session.id
                    )
                    return
                if len(calls) > 4:
                    raise AppException(
                        "El modelo excedió el límite de herramientas por turno."
                    )
                messages.append(
                    {
                        "role": "assistant",
                        "content": answer.get("content"),
                        "tool_calls": calls,
                    }
                )
                for call in calls:
                    name, arguments = str(call["function"]["name"]), str(
                        call["function"]["arguments"]
                    )
                    call_id = str(call["id"])
                    yield ChatEvent(
                        event="tool_call",
                        data={"name": name, "call_id": call_id},
                        session_id=session.id,
                    )
                    try:
                        result, new_filters = await self.execute_tool(
                            user, name, arguments, filters
                        )
                        payload = {
                            "call_id": call_id,
                            "result": result,
                            "is_error": False,
                        }
                        if new_filters:
                            filters = new_filters.model_dump(mode="json")
                            await self.contexts.update_context(
                                session.id, new_filters, TOOL_REPORTS[name]
                            )
                            evidence.append(result)
                            yield ChatEvent(
                                event="context_update",
                                data={
                                    "active_filters": filters,
                                    "current_report": TOOL_REPORTS[name],
                                },
                                session_id=session.id,
                            )
                        else:
                            citations = result["citations"]
                    except (
                        AppException,
                        ValidationError,
                        ValueError,
                        httpx.HTTPError,
                    ) as error:
                        detail = (
                            error.detail
                            if isinstance(error, AppException)
                            else "Los parámetros o el servicio de la herramienta no son válidos."
                        )
                        payload = {
                            "call_id": call_id,
                            "result": {"error": detail},
                            "is_error": True,
                        }
                    self.db.add(
                        AuditLog(
                            user_id=user.id,
                            action="chat.tool",
                            resource_type=name,
                            resource_id=session.id,
                            payload_json={"parameters": filters},
                            status="error" if payload["is_error"] else "ok",
                        )
                    )
                    await self._append(session.id, "tool", {"name": name, **payload})
                    await self.db.commit()
                    yield ChatEvent(
                        event="tool_result", data=payload, session_id=session.id
                    )
                    # Avoid sending a whole transaction listing into the model.
                    compact = payload.copy()
                    if not payload["is_error"] and "summary" in result:
                        compact = {
                            **payload,
                            "result": {
                                "summary": result["summary"],
                                "rows_count": len(result["rows"]),
                                "metadata": result["metadata"],
                            },
                        }
                    elif not payload["is_error"] and "context" in result:
                        # Full citations stay in SSE/history; send their text
                        # once to Qwen, within the formatted source context.
                        compact = {
                            **payload,
                            "result": {
                                "context": result["context"],
                                "results_count": result["results_count"],
                            },
                        }
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps(compact, ensure_ascii=False),
                        }
                    )
            raise AppException(
                "Se alcanzó el límite de consultas por turno. Reformula la pregunta."
            )
        except (
            AppException,
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            unavailable = isinstance(error, httpx.HTTPError) or (
                isinstance(error, AppException)
                and error.code in {"llm_not_ready", "llm_loading"}
            )
            if unavailable and not evidence and not citations:
                # Qwen is optional: answer with the engine instead of failing.
                logger.info("chat_offline_fallback", session_id=session.id)
                async for event in self._deterministic(
                    user, session.id, intent, filters, cutoff
                ):
                    yield event
                return
            logger.warning(
                "chat_failed",
                user_id=user.id,
                session_id=session.id,
                error_type=type(error).__name__,
            )
            detail = (
                error.detail
                if isinstance(error, AppException)
                else "Juku no pudo conectarse al servicio de IA. Los informes siguen disponibles; no se generaron cifras ni citas."
            )
            await self._append(
                session.id, "assistant", {"content": detail, "error": True}
            )
            self.db.add(
                AuditLog(
                    user_id=user.id,
                    action="chat.error",
                    resource_type="chat",
                    resource_id=session.id,
                    status="error",
                )
            )
            await self.db.commit()
            yield ChatEvent(event="error", data=detail, session_id=session.id)


def intent_query(intent: Intent) -> str:
    return intent.query_text or "procedimiento institucional"

"""Periodic reports and the engine-only fallback while Qwen is unavailable."""

from __future__ import annotations

from datetime import date

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.budget import BudgetFilterParams
from app.services.chat_service import ChatService
from app.services.juku_assistant import bs, parse_intent
from app.services.llm_client import LLMClient

CUTOFF = date(2026, 9, 30)
CATALOG = {"region": [{"id": 3, "name": "Cochabamba"}], "rubro": []}


def test_parse_periodic_reports_and_queries() -> None:
    monthly = parse_intent("Hazme el reporte mensual de marzo", [2026], CUTOFF)
    assert monthly and monthly.kind == "report" and monthly.period
    assert (monthly.period.start, monthly.period.end) == (
        date(2026, 3, 1),
        date(2026, 3, 31),
    )
    latest = parse_intent("informe del último mes", [2026], CUTOFF)
    assert latest and latest.period and latest.period.months == [9]
    quarter = parse_intent("Reporte del segundo trimestre", [2026], CUTOFF)
    assert quarter and quarter.period and quarter.period.months == [4, 5, 6]
    annual = parse_intent("Reporte anual 2026", [2026], CUTOFF)
    assert annual and annual.period and annual.period.kind == "annual"
    missing = parse_intent("reporte anual 2024", [2026], CUTOFF)
    assert missing and missing.missing_year == 2024 and missing.year == 2026
    region = parse_intent("¿Cuánto saldo queda en Cochabamba?", [2026], CUTOFF, CATALOG)
    assert region and region.report == "summary"
    assert region.entity_filters == {"region_ids": [3]}
    by_area = parse_intent("ejecución por área", [2026], CUTOFF)
    assert by_area and by_area.report == "area"
    assert parse_intent("mis tareas pendientes", [2026], CUTOFF) is None
    help_intent = parse_intent("hola", [2026], CUTOFF)
    assert help_intent and help_intent.kind == "help"
    assert bs("3163379.01") == "Bs 3.163.379,01"


def _unavailable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("Qwen apagado", request=request)


async def test_monthly_report_needs_no_llm(db: AsyncSession, sample: User) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(_unavailable)) as http:
        service = ChatService(db, LLMClient(http), http)
        events = [
            event
            async for event in service.process_message(
                sample, None, "Reporte mensual de marzo 2026"
            )
        ]
    assert events[-1].event == "done"
    text = events[-1].data["content"]
    assert "Reporte mensual · Marzo 2026" in text
    assert "Bs 100,30" in text  # three March movements from the fixture
    results = [e.data["result"] for e in events if e.event == "tool_result"]
    assert results and all(r["summary"] for r in results)
    assert any(r["report_type"] == "movements" for r in results)


async def test_offline_fallback_answers_with_engine(
    db: AsyncSession, sample: User
) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(_unavailable)) as http:
        service = ChatService(db, LLMClient(http), http)
        events = [
            event
            async for event in service.process_message(
                sample,
                None,
                "¿Cuánto saldo queda disponible?",
                BudgetFilterParams(years=[2026]),
            )
        ]
        assert events[-1].event == "done"
        assert "Saldo disponible: Bs 215,00" in events[-1].data["content"]
        unknown = [
            event
            async for event in service.process_message(
                sample, events[-1].session_id, "cuéntame un chiste"
            )
        ]
    assert unknown[-1].event == "done"
    assert "ayuda" in unknown[-1].data["content"]


async def test_quarter_breakdown_only_lists_its_months(
    db: AsyncSession, sample: User
) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(_unavailable)) as http:
        service = ChatService(db, LLMClient(http), http)
        events = [
            event
            async for event in service.process_message(
                sample, None, "Reporte del primer trimestre 2026"
            )
        ]
    monthly = next(
        e.data["result"]
        for e in events
        if e.event == "tool_result" and e.data["result"]["report_type"] == "monthly"
    )
    months = {row["labels"]["month"] for row in monthly["rows"]}
    assert months and months <= {"Enero", "Febrero", "Marzo"}
    assert "Bs 100,30" in events[-1].data["content"]


async def test_report_answer_links_a_shareable_pdf(
    db: AsyncSession, sample: User
) -> None:
    import io

    from pypdf import PdfReader

    from app.api.v1.budget import JukuPdfRequest, juku_pdf

    async with httpx.AsyncClient(transport=httpx.MockTransport(_unavailable)) as http:
        service = ChatService(db, LLMClient(http), http)
        events = [
            event
            async for event in service.process_message(
                sample, None, "Reporte mensual de marzo 2026"
            )
        ]
    request = events[-1].data["pdf_request"]
    assert request["message"] == "Reporte mensual de marzo 2026"
    response = await juku_pdf(JukuPdfRequest.model_validate(request), db, sample)
    assert response.media_type == "application/pdf"
    assert (
        "exb-reporte-mensual-marzo-2026.pdf" in response.headers["content-disposition"]
    )
    text = " ".join(
        " ".join(page.extract_text().split())
        for page in PdfReader(io.BytesIO(response.body)).pages
    )
    assert "Reporte mensual · Marzo 2026" in text
    assert "Bs 100,30" in text

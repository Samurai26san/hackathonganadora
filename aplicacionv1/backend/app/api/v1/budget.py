"""Exactly seven base reports plus comparisons and identical-scope exports."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.exceptions import AppException
from app.core.security import DB, CurrentUser
from app.models import AuditLog
from app.schemas.budget import BudgetFilterParams, ExportRequest, FinancialReportResult
from app.services.catalog_service import catalogs
from app.services.export_service import export_report
from app.services.financial_engine import FinancialEngine
from app.services.juku_assistant import (
    JukuAssistant,
    latest_movement,
    normalize,
    parse_intent,
)
from app.services.report_pdf import render_juku_pdf

router = APIRouter(tags=["Finanzas"])


def filters_query(request: Request) -> BudgetFilterParams:
    data: dict[str, Any] = {}
    for key in BudgetFilterParams.model_fields:
        if key not in request.query_params:
            continue
        value = request.query_params[key]
        try:
            if key in {"years", "months"} or key.endswith("_ids"):
                data[key] = [int(item) for item in value.split(",") if item.strip()]
            elif key in {"page", "page_size"}:
                data[key] = int(value)
            else:
                data[key] = value
        except ValueError as error:
            raise AppException(f"Filtro inválido: {key}.", 422) from error
    if "years" not in data:
        raise AppException("Selecciona al menos una gestión (years).", 422)
    try:
        return BudgetFilterParams.model_validate_json(json.dumps(data))
    except ValidationError as error:
        raise AppException(
            "Revisa el período y los filtros de la consulta.", 422
        ) from error


Params = Annotated[BudgetFilterParams, Depends(filters_query)]


@router.get(
    "/catalogs",
    summary="Catálogos autorizados",
    description="Gestiones y dimensiones derivadas del alcance del usuario.",
)
async def get_catalogs(db: DB, user: CurrentUser) -> dict[str, Any]:
    return await catalogs(db, user)


@router.get(
    "/budget/execution/{report_type}",
    response_model=FinancialReportResult,
    summary="Informe financiero determinista",
    description="account, financier, area, region, monthly, movements o summary. Todos aplican RBAC y alcances en SQL.",
)
async def execution(
    report_type: str, params: Params, db: DB, user: CurrentUser
) -> FinancialReportResult:
    result = await FinancialEngine(db, user).report(report_type, params)
    db.add(
        AuditLog(
            user_id=user.id,
            action="budget.query",
            resource_type=report_type,
            payload_json=params.model_dump(mode="json"),
        )
    )
    return result


@router.get(
    "/budget/compare",
    response_model=FinancialReportResult,
    summary="Comparar gestiones",
    description="Rechaza gestiones ausentes o sin datos autorizados; no simula períodos.",
)
async def compare(params: Params, db: DB, user: CurrentUser) -> FinancialReportResult:
    result = await FinancialEngine(db, user).compare_budget_periods(params)
    db.add(
        AuditLog(
            user_id=user.id,
            action="budget.compare",
            payload_json=params.model_dump(mode="json"),
        )
    )
    return result


@router.post(
    "/reports/export",
    summary="Exportar consulta autorizada",
    description="Excel, PDF o CSV calculados con idénticos filtros, sin paginación y sin volver a consultar un LLM.",
)
async def export(body: ExportRequest, db: DB, user: CurrentUser) -> Response:
    engine = FinancialEngine(db, user)
    if body.format in {"pdf", "csv"}:
        report = await engine.export_detail(body.report, body.filters)
    elif body.report == "compare":
        report = await engine.compare_budget_periods(body.filters)
    else:
        report = await engine.report(body.report, body.filters, all_rows=True)
    content, mime, extension = export_report(report, body.format)
    db.add(
        AuditLog(
            user_id=user.id,
            action="budget.export",
            resource_type=body.report,
            payload_json=body.filters.model_dump(mode="json"),
        )
    )
    return Response(
        content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="exb-{body.report}.{extension}"'
        },
    )


class JukuPdfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=500)
    filters: BudgetFilterParams | None = None


@router.post(
    "/reports/juku-pdf",
    summary="PDF compartible de un reporte de Juku",
    description="Recalcula con el motor el reporte pedido a Juku (sin LLM) y lo entrega como PDF resumido.",
)
async def juku_pdf(body: JukuPdfRequest, db: DB, user: CurrentUser) -> Response:
    catalog = await catalogs(db, user)
    years = list(catalog.get("years", []))
    if not years:
        raise AppException("No hay datos presupuestarios autorizados.", 422)
    cutoff = await latest_movement(db, user)
    intent = parse_intent(body.message, years, cutoff, catalog)
    if intent is None or intent.kind not in {"report", "query"}:
        raise AppException("Esta consulta no genera un reporte en PDF.", 422)
    filters = (
        body.filters.model_dump(mode="json")
        if body.filters
        else {"years": [intent.year or years[0]]}
    )
    answer = await JukuAssistant(db, user).answer(intent, filters, cutoff)
    if not answer.reports:
        raise AppException("Esta consulta no genera un reporte en PDF.", 422)
    content = render_juku_pdf(
        answer, user.full_name, datetime.now(ZoneInfo("America/La_Paz"))
    )
    db.add(
        AuditLog(
            user_id=user.id,
            action="budget.export",
            resource_type="juku_pdf",
            payload_json={"message": body.message, "filters": filters},
        )
    )
    title = answer.text.split("\n")[0].replace("*", "")
    slug = re.sub(r"[^a-z0-9]+", "-", normalize(title)).strip("-")[:60] or "reporte"
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="exb-{slug}.pdf"'},
    )

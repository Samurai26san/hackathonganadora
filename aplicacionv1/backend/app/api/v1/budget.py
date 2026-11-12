"""Exactly seven base reports plus comparisons and identical-scope exports."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import ValidationError

from app.core.exceptions import AppException
from app.core.security import DB, CurrentUser
from app.models import AuditLog
from app.schemas.budget import BudgetFilterParams, ExportRequest, FinancialReportResult
from app.services.catalog_service import catalogs
from app.services.export_service import export_report
from app.services.financial_engine import FinancialEngine

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

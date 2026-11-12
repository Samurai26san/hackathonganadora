"""Deterministic monthly/annual technical dossiers with explicit evidence gaps."""

from __future__ import annotations

import calendar
import io
from datetime import date
from decimal import Decimal
from typing import Any, Literal
from xml.sax.saxutils import escape

from fastapi import APIRouter, Response
from openpyxl import Workbook
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select

from app.api.v1.accounting import full_scope
from app.api.v1.data_changes import lock
from app.core.database import money
from app.core.security import DB, CurrentUser
from app.models import AuditLog, Gestion
from app.models.accounting import CurationRow
from app.schemas.budget import BudgetFilterParams
from app.services.accounting_service import statements
from app.services.export_service import safe_text
from app.services.financial_engine import FinancialEngine

router = APIRouter(prefix="/technical-reports", tags=["Informes técnicos"])


class ReportInput(BaseModel):
    periodicity: Literal["monthly", "annual"]
    year: int = Field(ge=1900, le=2200)
    month: int = Field(default=12, ge=1, le=12)
    validated_only: bool = True
    iue_base: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=2, allow_inf_nan=False
    )
    iue_rate: Decimal | None = Field(
        default=None, ge=0, le=100, decimal_places=4, allow_inf_nan=False
    )
    format: Literal["json", "pdf", "excel"] = "json"


async def dossier(body: ReportInput, db: Any, user: Any) -> dict[str, Any]:
    full_scope(user)
    await lock(db)
    month = body.month if body.periodicity == "monthly" else 12
    cutoff = date(body.year, month, calendar.monthrange(body.year, month)[1])
    status = "validated" if body.validated_only else None
    params = BudgetFilterParams(
        years=[body.year],
        months=[0, *range(1, month + 1)],
        date_to=cutoff,
        validation_status=status,
    )
    engine = FinancialEngine(db, user)
    budget = await engine.report("summary", params, all_rows=True)
    breakdown = {}
    for name in ("financier", "region"):
        result = await engine.report(name, params, all_rows=True)
        breakdown[name] = [r.model_dump(mode="json") for r in result.rows]
    previous = None
    if await db.get(Gestion, body.year - 1):
        prev_cut = date(
            body.year - 1, month, calendar.monthrange(body.year - 1, month)[1]
        )
        prev = await engine.report(
            "summary",
            params.model_copy(update={"years": [body.year - 1], "date_to": prev_cut}),
            all_rows=True,
        )
        previous = {
            "year": body.year - 1,
            "summary": prev.summary.model_dump(mode="json"),
            "execution_delta": str(
                money(budget.summary.executed - prev.summary.executed)
            ),
        }
    accounting = await statements(db, cutoff, date(body.year, 1, 1))
    quality_query = select(CurationRow).where(CurationRow.data.is_not(None))
    staged = (await db.scalars(quality_query)).all()
    staged = [r for r in staged if str(r.data.get("year")) == str(body.year)]
    quality = {
        "rows": len(staged),
        "pending": sum(r.status == "pending" for r in staged),
        "predicted": sum(bool(r.prediction.get("labels")) for r in staged),
        "manually_validated": sum(r.validated_by is not None for r in staged),
        "consolidated": sum(r.status == "consolidated" for r in staged),
        "cleaned": sum(r.data != r.original for r in staged),
        "with_issues": sum(bool(r.issues) for r in staged),
    }
    risks = [
        n
        for n in accounting["auditor"] + accounting["notes"]
        if n["risk"] in {"medium", "high"}
    ]
    alerts = [f'{n["risk"]}: {n["title"]}' for n in risks]
    if not accounting["balance"]["balanced"]:
        alerts.append("No se dispone de balance contable completo y cuadrado.")
    if not accounting["cash_flow"]["reconciled"]:
        alerts.append("El flujo de efectivo requiere conciliación.")
    if not accounting["auditor"]:
        alerts.append("No se ha incorporado dictamen de auditor independiente.")
    if not accounting["notes"]:
        alerts.append("No se han incorporado notas a los estados financieros.")
    if body.validated_only and not quality["consolidated"]:
        alerts.append(
            "No existen filas curadas consolidadas para esta gestión. El Excel original no se considera validación manual."
        )
    estimate = (
        money(body.iue_base * body.iue_rate / 100)
        if body.iue_base is not None and body.iue_rate is not None
        else None
    )
    return {
        "title": "Informe técnico presupuestario y contable · Enseña por Bolivia",
        "scope": {
            "periodicity": body.periodicity,
            "year": body.year,
            "cutoff": cutoff.isoformat(),
            "filters": params.model_dump(mode="json"),
            "currency": "BOB",
            "budget_basis": "Presupuesto anual completo (mes PTTO=0) más asignaciones hasta el corte; no prorrateado.",
        },
        "executive_summary": f"Al {cutoff.isoformat()}, la ejecución presupuestaria asciende a Bs {budget.summary.executed}, con saldo Bs {budget.summary.balance} y avance {budget.summary.execution_percentage} %. Se identifican {len(alerts)} asuntos que requieren revisión. Documento borrador generado con datos registrados, sin opinión de auditoría automática.",
        "risks": alerts,
        "budget_execution": {
            "summary": budget.summary.model_dump(mode="json"),
            "breakdown": breakdown,
            "previous_year": previous,
            "comparison_status": (
                "available"
                if previous
                else "Sin gestión anterior registrada; no se estiman datos históricos."
            ),
        },
        "financial_statements": accounting,
        "iue_estimate": {
            "base": str(body.iue_base) if body.iue_base is not None else None,
            "rate_percent": str(body.iue_rate) if body.iue_rate is not None else None,
            "estimate": str(estimate) if estimate is not None else None,
            "status": "Simulación con base y tasa proporcionadas; no sustituye IUE registrado ni liquidación tributaria.",
        },
        "data_quality": quality,
        "limitations": [
            accounting["regulatory_status"],
            "Los hechos presupuestarios no se convierten automáticamente en activos, pasivos o flujos de efectivo.",
            "Predicción de etiquetas: similitud supervisada, confianza no calibrada y aprobación manual obligatoria.",
            "El anexo de calidad describe el estado actual de preparación; los importes incluyen únicamente hechos consolidados con los filtros indicados.",
        ],
    }


def flatten(value: Any, prefix: str = "") -> list[list[Any]]:
    if isinstance(value, dict):
        return [
            row
            for k, v in value.items()
            for row in flatten(v, (prefix + " / " if prefix else "") + str(k))
        ]
    if isinstance(value, list):
        return [
            row for i, v in enumerate(value, 1) for row in flatten(v, f"{prefix} [{i}]")
        ] or [[prefix, "Sin datos"]]
    return [[prefix, "Sin datos" if value is None else str(value)]]


def render(report: dict[str, Any], format_: str) -> tuple[bytes, str, str]:
    target = io.BytesIO()
    if format_ == "excel":
        wb = Workbook()
        wb.remove(wb.active)
        sheets = {
            "Alcance": report["scope"],
            "Resumen y riesgos": {
                "summary": report["executive_summary"],
                "risks": report["risks"],
                "limitations": report["limitations"],
            },
            "Presupuesto": report["budget_execution"],
            "Calidad": report["data_quality"],
            "IUE estimado": report["iue_estimate"],
        }
        for name, key in [
            ("Dictamen", "auditor"),
            ("Balance", "balance"),
            ("Resultados", "income_statement"),
            ("Patrimonio", "equity_changes"),
            ("Flujo", "cash_flow"),
            ("Notas", "notes"),
            ("Libro diario", "ledger"),
        ]:
            sheets[name] = report["financial_statements"][key]
        for name, data in sheets.items():
            sheet = wb.create_sheet(name)
            sheet.append(["Concepto", "Valor"])
            for row in flatten(data):
                sheet.append([safe_text(cell) for cell in row])
            sheet.column_dimensions["A"].width = 65
            sheet.column_dimensions["B"].width = 85
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
        sheet = wb.create_sheet("Fórmulas")
        sheet.append(["Concepto", "BOB"])
        b = report["financial_statements"]["balance"]
        inc = report["financial_statements"]["income_statement"]
        for name, value in [
            ("Activo", b["asset"]),
            ("Pasivo", b["liability"]),
            ("Patrimonio contable", b["equity_booked"]),
            ("Resultado no cerrado", b["unclosed_result"]),
            ("Diferencia de balance", "=B2-B3-B4-B5"),
            ("Resultado bruto", inc["gross_result"]),
            ("Resultado operativo", inc["operating_result"]),
            ("Antes de IUE", inc["before_tax"]),
            ("IUE registrado", inc["iue_recorded"]),
            ("Utilidad neta", "=B9-B10"),
        ]:
            sheet.append(
                [name, value if str(value).startswith("=") else Decimal(value)]
            )
        sheet.column_dimensions["A"].width = 36
        for cells in sheet.iter_rows(min_row=2, min_col=2):
            cells[0].number_format = "#,##0.00"
        wb.save(target)
        return (
            target.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        )
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 8
    styles["BodyText"].leading = 11
    doc = SimpleDocTemplate(target, pagesize=A4, leftMargin=30, rightMargin=30)
    story: list[Any] = [
        Paragraph(escape(report["title"]), styles["Title"]),
        Paragraph("BORRADOR TÉCNICO · Moneda BOB", styles["Heading2"]),
    ]
    for title, data in [
        ("Alcance y corte", report["scope"]),
        (
            "Resumen ejecutivo y riesgos",
            {"summary": report["executive_summary"], "alerts": report["risks"]},
        ),
        ("Ejecución presupuestaria", report["budget_execution"]),
        ("1. Dictamen de auditores", report["financial_statements"]["auditor"]),
        ("2. Situación patrimonial", report["financial_statements"]["balance"]),
        ("3. Estado de resultados", report["financial_statements"]["income_statement"]),
        ("4. Cambios en patrimonio", report["financial_statements"]["equity_changes"]),
        ("5. Flujos de efectivo", report["financial_statements"]["cash_flow"]),
        ("6. Notas", report["financial_statements"]["notes"]),
        ("Estimación parametrizada de IUE", report["iue_estimate"]),
        ("Anexo de calidad de datos", report["data_quality"]),
        ("Alcance y limitaciones", report["limitations"]),
    ]:
        story.extend([Spacer(1, 10), Paragraph(escape(title), styles["Heading2"])])
        rows = [
            [
                Paragraph(escape(str(v)).replace("\n", "<br/>"), styles["BodyText"])
                for v in row
            ]
            for row in flatten(data)
        ]
        table = Table(
            rows, colWidths=[doc.width * 0.43, doc.width * 0.57], splitInRow=1
        )
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9EDAA")),
                ]
            )
        )
        story.append(table)
    doc.build(story)
    return target.getvalue(), "application/pdf", "pdf"


@router.post("/generate")
async def generate(body: ReportInput, db: DB, user: CurrentUser) -> Any:
    report = await dossier(body, db, user)
    db.add(
        AuditLog(
            user_id=user.id,
            action="technical_report.generate",
            payload_json=body.model_dump(mode="json"),
        )
    )
    if body.format == "json":
        return report
    content, mime, extension = render(report, body.format)
    return Response(
        content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="exb-informe-{body.year}.{extension}"'
        },
    )

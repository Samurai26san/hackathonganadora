"""Server-side exports of the exact authorized result, without pagination."""

from __future__ import annotations

import csv
import io
import json
from typing import Any
from xml.sax.saxutils import escape

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.budget import FinancialReportResult


def safe_text(value: object) -> str:
    text = str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


def export_report(
    result: FinancialReportResult, format_: str
) -> tuple[bytes, str, str]:
    labels = list(dict.fromkeys(key for row in result.rows for key in row.labels)) or [
        "Detalle"
    ]
    values = list(dict.fromkeys(key for row in result.rows for key in row.values)) or [
        "executed"
    ]
    headings = labels + values
    rows: list[list[Any]] = [
        [safe_text(row.labels.get(key, "")) for key in labels]
        + [row.values.get(key, "") for key in values]
        for row in result.rows
    ]
    if format_ == "csv":
        text = io.StringIO()
        writer = csv.writer(text)
        writer.writerow(["Gestión", "Filtros", *headings])
        scope = safe_text(
            json.dumps(
                result.metadata.get("filters", {}), ensure_ascii=False, sort_keys=True
            )
        )
        years = ", ".join(map(str, result.metadata.get("filters", {}).get("years", [])))
        writer.writerows([[years, scope, *row] for row in rows])
        return text.getvalue().encode("utf-8-sig"), "text/csv", "csv"
    target = io.BytesIO()
    if format_ == "excel":
        workbook = Workbook()
        sheet = workbook.active
        assert sheet is not None
        sheet.title = "Reporte ExB"
        sheet.append([result.title])
        sheet.append(
            ["Moneda", "BOB", "Filtros", str(result.metadata.get("filters", {}))]
        )
        sheet.append(headings)
        for row in rows:
            sheet.append(row)
        for cells in sheet.iter_rows(min_row=4, min_col=len(labels) + 1):
            for cell in cells:
                cell.number_format = "#,##0.00"
        sheet.freeze_panes = "A4"
        sheet.auto_filter.ref = sheet.dimensions
        workbook.save(target)
        return (
            target.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        )
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        target, pagesize=landscape(A4), leftMargin=20, rightMargin=20
    )
    styles["BodyText"].fontSize = 7
    styles["BodyText"].leading = 9
    scope = json.dumps(
        result.metadata.get("filters", {}), ensure_ascii=False, sort_keys=True
    )
    story = [
        Paragraph(escape(result.title), styles["Title"]),
        Paragraph("Enseña por Bolivia · Moneda: BOB", styles["BodyText"]),
        Paragraph("Gestión y filtros: " + escape(scope), styles["BodyText"]),
        Paragraph(
            "No sumar grupos, cuentas y movimientos entre sí. Son distintos niveles del mismo informe.",
            styles["BodyText"],
        ),
        Spacer(1, 12),
    ]
    sections = list(
        dict.fromkeys(row.labels.get("Sección", "Detalle") for row in result.rows)
    ) or ["Detalle"]
    for section in sections:
        selected = [
            row
            for row in result.rows
            if row.labels.get("Sección", "Detalle") == section
        ]
        keys = list(
            dict.fromkeys(k for row in selected for k in row.labels if k != "Sección")
        ) or ["Detalle"]
        metrics = (
            ["current_budget", "executed", "balance"]
            if result.metadata.get("detailed_export") and section == "Rubros y cuentas"
            else list(dict.fromkeys(k for row in selected for k in row.values))
        )
        names = {
            "current_budget": "Presupuesto vigente",
            "executed": "Ejecución",
            "balance": "Saldo",
            "cuenta": "Cuenta",
            "rubro": "Rubro",
            "date": "Fecha",
            "reference": "Comprobante",
            "description": "Descripción",
            "region": "Región",
            "area": "Área",
            "financier": "Financiador",
        }
        heading = [names.get(k, k) for k in keys + metrics]
        content = [[*heading]] + [
            [
                *[row.labels.get(k, "") for k in keys],
                *[row.values.get(k, "") for k in metrics],
            ]
            for row in selected
        ]
        display = [
            [Paragraph(escape(str(value)), styles["BodyText"]) for value in row]
            for row in content
        ]
        table = Table(
            display,
            repeatRows=1,
            colWidths=[doc.width / len(heading)] * len(heading),
            splitInRow=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EDAA")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E7DA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.extend(
            [Paragraph(escape(section), styles["Heading2"]), table, Spacer(1, 12)]
        )
    doc.build(story)
    return target.getvalue(), "application/pdf", "pdf"

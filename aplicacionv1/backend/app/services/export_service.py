"""Server-side exports of the exact authorized result, without pagination."""

from __future__ import annotations

import csv
import io
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
    labels = list(result.rows[0].labels) if result.rows else ["Detalle"]
    values = list(result.rows[0].values) if result.rows else ["executed"]
    headings = labels + values
    rows: list[list[Any]] = [
        [safe_text(row.labels.get(key, "")) for key in labels]
        + [row.values.get(key, "") for key in values]
        for row in result.rows
    ]
    if format_ == "csv":
        text = io.StringIO()
        writer = csv.writer(text)
        writer.writerow(headings)
        writer.writerows(rows)
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
    display = [
        [Paragraph(escape(str(value)), styles["BodyText"]) for value in row]
        for row in [headings, *rows]
    ]
    table = Table(display, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EDAA")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E7DA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    doc.build(
        [
            Paragraph(escape(result.title), styles["Title"]),
            Paragraph(
                "Enseña por Bolivia · Moneda: BOB · Consulta autorizada",
                styles["BodyText"],
            ),
            Spacer(1, 12),
            table,
        ]
    )
    return target.getvalue(), "application/pdf", "pdf"

"""Shareable PDF of a Juku answer: narrative, KPIs and compact tables.

Unlike the detailed export, this document is meant to be sent to someone: it
keeps Juku's summary and the top rows of each block, recomputed by the engine.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.budget import FinancialReportResult
from app.services.juku_assistant import SHARE_HINT, Answer, bs, pct

ASSETS = Path(__file__).resolve().parent.parent / "assets"
GREEN = colors.HexColor("#245741")
LIME = colors.HexColor("#D9EDAA")
LINE = colors.HexColor("#E0E7DA")
MUTED = colors.HexColor("#566958")
LABELS = {
    "rubro": "Rubro",
    "cuenta": "Cuenta",
    "financier": "Financiador",
    "region": "Región",
    "area": "Área",
    "month": "Mes",
    "year": "Gestión",
}
MAX_ROWS = 20


def _inline(text: str) -> str:
    """Escape, then map the **bold** subset Juku writes to ReportLab markup."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(text))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = ParagraphStyle("JukuBody", parent=base["BodyText"], fontSize=10, leading=14)
    return {
        "title": ParagraphStyle(
            "JukuTitle", parent=base["Title"], textColor=GREEN, alignment=0
        ),
        "h2": ParagraphStyle(
            "JukuH2", parent=base["Heading2"], textColor=GREEN, fontSize=12
        ),
        "body": body,
        "bullet": ParagraphStyle(
            "JukuBullet", parent=body, leftIndent=14, bulletIndent=4
        ),
        "note": ParagraphStyle(
            "JukuNote", parent=body, fontSize=8, leading=11, textColor=MUTED
        ),
        "cell": ParagraphStyle("JukuCell", parent=body, fontSize=8, leading=10),
    }


def _narrative(text: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    flow: list[Any] = []
    for raw in text.strip().split("\n")[1:]:  # first line is the title
        line = raw.strip()
        if not line:
            flow.append(Spacer(1, 4))
        elif line.startswith("- "):
            flow.append(Paragraph(_inline(line[2:]), styles["bullet"], bulletText="•"))
        elif line.startswith("_") and line.endswith("_") and len(line) > 2:
            flow.append(Paragraph(_inline(line[1:-1]), styles["note"]))
        elif line == SHARE_HINT:
            continue  # UI hint, meaningless on paper
        else:
            flow.append(Paragraph(_inline(line), styles["body"]))
    return flow


def _day(raw: str) -> str:
    return f"{raw[8:10]}/{raw[5:7]}/{raw[:4]}" if len(raw) == 10 else raw


def _money(value: Any) -> str:
    return bs(Decimal(str(value)))


def _table(
    result: FinancialReportResult, styles: dict[str, ParagraphStyle]
) -> list[Any]:
    s = result.summary
    kpis = Table(
        [
            ["Presupuesto vigente", "Ejecutado", "Saldo", "% Ejecución"],
            [
                _money(s.current_budget),
                _money(s.executed),
                _money(s.balance),
                pct(s.execution_percentage),
            ],
        ],
        colWidths=[4.2 * cm] * 4,
    )
    kpis.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 10),
                ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7F1")),
            ]
        )
    )
    rows = result.rows[:MAX_ROWS]
    if result.report_type == "movements":
        header = ["Fecha", "Descripción", "Rubro", "Monto"]
        body = [
            [
                Paragraph(escape(_day(r.labels.get("date", ""))), styles["cell"]),
                Paragraph(escape(r.labels.get("description", "")), styles["cell"]),
                Paragraph(escape(r.labels.get("rubro", "")), styles["cell"]),
                _money(r.values.get("executed", 0)),
            ]
            for r in rows
        ]
        widths = [2.2 * cm, 8.4 * cm, 3.6 * cm, 2.6 * cm]
    else:
        levels = list(rows[0].labels) if rows else []
        header = [LABELS.get(k, k.title()) for k in levels] + [
            "Vigente",
            "Ejecutado",
            "%",
        ]
        body = [
            [Paragraph(escape(r.labels[k]), styles["cell"]) for k in levels]
            + [
                _money(r.values.get("current_budget", 0)),
                _money(r.values.get("executed", 0)),
                pct(r.values.get("execution_percentage", 0)),
            ]
            for r in rows
        ]
        label_width = (16.8 - 8.4) / max(len(levels), 1)
        widths = [label_width * cm] * len(levels) + [3.2 * cm, 3.2 * cm, 2 * cm]
    flow: list[Any] = [Paragraph(escape(result.title), styles["h2"]), kpis]
    if body:
        detail = Table([header, *body], colWidths=widths, repeatRows=1)
        detail.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), LIME),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.3, LINE),
                    ("ALIGN", (-3, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#FAFBF8")],
                    ),
                ]
            )
        )
        flow += [Spacer(1, 6), detail]
        total = int(result.metadata.get("total_count", len(result.rows)))
        if total > len(rows):
            flow.append(
                Paragraph(
                    f"Se muestran {len(rows)} de {total} filas. El detalle completo "
                    "está disponible en Excel desde la aplicación.",
                    styles["note"],
                )
            )
    # Short tables travel with their heading; long ones may break across pages.
    if len(rows) <= 12:
        return [KeepTogether(flow), Spacer(1, 12)]
    return [KeepTogether(flow[:2]), *flow[2:], Spacer(1, 12)]


def render_juku_pdf(answer: Answer, author: str, now: datetime) -> bytes:
    styles = _styles()
    title = re.sub(r"\*", "", answer.text.strip().split("\n")[0]) or "Reporte"
    stamp = now.strftime("%d/%m/%Y %H:%M")

    def footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            2 * cm,
            1.2 * cm,
            f"ExB Finanzas · Generado por {author} el {stamp} · "
            "Fuente: Excel institucional (hoja BD) · Cifras del motor financiero",
        )
        canvas.drawRightString(19 * cm, 1.2 * cm, f"Página {document.page}")
        canvas.restoreState()

    header_cells: list[Any] = []
    if (ASSETS / "logo.png").is_file():
        header_cells.append(Image(str(ASSETS / "logo.png"), 4.2 * cm, 2.35 * cm))
    header_cells.append(
        [
            Paragraph(escape(title), styles["title"]),
            Paragraph(
                "Reporte preparado por Juku, asistente financiero de Enseña por "
                "Bolivia. Importes en bolivianos (Bs).",
                styles["note"],
            ),
        ]
    )
    if (ASSETS / "juku-pdf.png").is_file():
        header_cells.append(Image(str(ASSETS / "juku-pdf.png"), 2.4 * cm, 2.4 * cm))
    widths = [4.6 * cm, None, 2.8 * cm][-len(header_cells) :]
    header = Table([header_cells], colWidths=widths)
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, GREEN),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story: list[Any] = [header, Spacer(1, 12), *_narrative(answer.text, styles)]
    story.append(Spacer(1, 12))
    for _, result in answer.reports:
        story += _table(result, styles)
    target = io.BytesIO()
    SimpleDocTemplate(
        target,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
        title=title,
        author=author,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return target.getvalue()

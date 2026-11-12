"""Deterministic Juku: Spanish intents and periodic reports without an LLM.

Every amount comes from FinancialEngine. The text only describes engine results,
so periodic reports and the fallback used while Qwen is unavailable never
invent figures. Unrecognized questions return guidance instead of a guess.
"""

from __future__ import annotations

import calendar
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Movement, User
from app.schemas.budget import BudgetFilterParams, DataRow, FinancialReportResult
from app.services.financial_engine import MONTHS, FinancialEngine

MONTH_NAMES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
ORDINALS = {
    "primer": 1,
    "primero": 1,
    "1er": 1,
    "segundo": 2,
    "2do": 2,
    "tercer": 3,
    "tercero": 3,
    "3er": 3,
    "cuarto": 4,
    "4to": 4,
}
# Ordered: the first matching keyword group decides a simple query.
QUERY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("compare", ("compar*", "versus", "vs")),
    ("movements", ("movimiento", "transacc*", "comprobante", "pago", "gastos en")),
    ("financier", ("financiador", "fuente", "donante", "financiamiento")),
    ("region", ("region", "departament*", "regional")),
    ("area", ("area",)),
    ("monthly", ("por mes", "mes a mes", "mensual*", "evolucion", "tendencia")),
    ("account", ("rubro", "cuenta", "partida", "categoria")),
    (
        "summary",
        (
            "saldo",
            "disponible",
            "queda",
            "cuanto",
            "presupuesto",
            "ejecut*",
            "gastado",
            "resumen",
            "como vamos",
            "estado",
            "avance",
        ),
    ),
]
KNOWLEDGE_KEYWORDS = (
    "manual",
    "norma*",
    "ley",
    "reglamento",
    "procedimiento",
    "politica",
    "documento",
    "que dice",
)
REPORT_WORDS = ("reporte", "informe", "balance", "cierre")
GREETINGS = ("hola", "buenas", "buenos dias", "buen dia", "hey", "saludos")
HELP_WORDS = ("ayuda", "que puedes", "que sabes", "como funciona", "opciones")
ZERO = Decimal("0")
SHARE_HINT = (
    "Usa «Descargar PDF» o «Compartir» para enviar este reporte; cada bloque "
    "también se exporta a Excel o CSV."
)


def normalize(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.lower())
    return " ".join("".join(c for c in plain if not unicodedata.combining(c)).split())


def bs(value: Decimal | str | int | float) -> str:
    """Bolivian notation: Bs 3.163.379,01."""
    amount = Decimal(str(value))
    text = f"{abs(amount):,.2f}".replace(",", "_").replace(".", ",")
    return f"{'-' if amount < 0 else ''}Bs {text.replace('_', '.')}"


def pct(value: Decimal | str | int) -> str:
    return f"{Decimal(str(value)):.2f}".replace(".", ",") + " %"


def short_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


@dataclass
class Period:
    kind: str  # monthly | quarterly | semester | annual
    year: int
    start: date
    end: date
    label: str
    months: list[int] = field(default_factory=list)


@dataclass
class Intent:
    kind: str  # report | query | knowledge | help
    report: str | None = None
    period: Period | None = None
    year: int | None = None
    years: list[int] = field(default_factory=list)
    month: int | None = None
    entity_filters: dict[str, list[int]] = field(default_factory=dict)
    entity_labels: list[str] = field(default_factory=list)
    missing_year: int | None = None
    query_text: str = ""


@dataclass
class Answer:
    text: str
    reports: list[tuple[str, FinancialReportResult]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)


def _month_in(text: str) -> int | None:
    for name, number in MONTH_NAMES.items():
        if re.search(rf"\b{name}\b", text):
            return number
    return None


def _quarter_in(text: str) -> int | None:
    match = re.search(r"\b(?:q|t)([1-4])\b", text) or re.search(
        r"\b([1-4])\s*(?:er|do|ro|to|°|º)?\s*trimestre", text
    )
    if match:
        return int(match.group(1))
    for word, number in ORDINALS.items():
        if re.search(rf"\b{word}\s+trimestre", text):
            return number
    return None


def _semester_in(text: str) -> int | None:
    if re.search(r"\b(primer|1er|primero|1)\s*semestre", text):
        return 1
    if re.search(r"\b(segundo|2do|2)\s*semestre", text):
        return 2
    return None


def _period(kind: str, year: int, first: int, last: int, label: str) -> Period:
    end_day = calendar.monthrange(year, last)[1]
    return Period(
        kind=kind,
        year=year,
        start=date(year, first, 1),
        end=date(year, last, end_day),
        label=label,
        months=list(range(first, last + 1)),
    )


def parse_intent(
    message: str,
    years: list[int],
    cutoff: date | None,
    catalog: dict[str, Any] | None = None,
) -> Intent | None:
    """Recognize periodic reports and simple financial questions in Spanish."""
    text = normalize(message)
    available = sorted(years)
    mentioned = [int(y) for y in re.findall(r"\b(20\d\d)\b", text)]
    missing = next((y for y in mentioned if y not in available), None)
    valid = [y for y in mentioned if y in available]
    default_year = cutoff.year if cutoff and cutoff.year in available else None
    year = (
        valid[0] if valid else (default_year or (available[-1] if available else None))
    )
    intent = Intent(
        kind="query", year=year, missing_year=missing, query_text=message[:500]
    )
    _match_entities(text, catalog or {}, intent)

    words = text.strip(" ¡!¿?.,").split()
    if any(re.search(rf"\b{word}\b", text) for word in HELP_WORDS) or (
        len(words) <= 3 and any(" ".join(words).startswith(g) for g in GREETINGS)
    ):
        intent.kind = "help"
        return intent
    if year is None:
        return intent if missing else None

    month = _month_in(text)
    quarter = _quarter_in(text)
    semester = _semester_in(text)
    wants_report = any(word in text for word in REPORT_WORDS)
    last_month = cutoff.month if cutoff and cutoff.year == year else 12
    if "trimestr" in text or quarter:
        quarter = quarter or (last_month - 1) // 3 + 1
        first = (quarter - 1) * 3 + 1
        intent.period = _period(
            "quarterly", year, first, first + 2, f"{quarter}.º trimestre {year}"
        )
    elif "semestr" in text or semester:
        semester = semester or (1 if last_month <= 6 else 2)
        first = 1 if semester == 1 else 7
        intent.period = _period(
            "semester", year, first, first + 5, f"{semester}.º semestre {year}"
        )
    elif wants_report and (
        month or re.search(r"\b(mensual|del mes|este mes|ultimo mes)\b", text)
    ):
        month = month or last_month
        intent.period = _period(
            "monthly", year, month, month, f"{MONTHS[month]} {year}"
        )
    elif wants_report and re.search(r"\b(anual|ano|gestion|completo)\b", text):
        intent.period = _period("annual", year, 1, 12, f"Gestión {year}")
    elif wants_report:
        # "Genera un reporte" without period: the most useful default is annual.
        intent.period = _period("annual", year, 1, 12, f"Gestión {year}")
    if intent.period:
        intent.kind = "report"
        return intent

    intent.month = month
    if any(_has(text, word) for word in KNOWLEDGE_KEYWORDS):
        intent.kind = "knowledge"
        return intent
    for report, keywords in QUERY_KEYWORDS:
        if any(_has(text, word) for word in keywords):
            intent.report = report
            intent.years = sorted(set(valid)) if report == "compare" else []
            return intent
    if month or intent.entity_filters or missing:
        intent.report = "summary"
        return intent
    return None


def _has(text: str, word: str) -> bool:
    """Whole word (or plural); a trailing "*" marks a stem such as "ejecut*".

    Avoids "area" in "tareas" or "cuenta" in "cuentame".
    """
    stem = word.endswith("*")
    pattern = re.escape(word.rstrip("*"))
    suffix = "" if stem else r"(?:s|es)?(?![a-z0-9])"
    return re.search(rf"(?<![a-z0-9]){pattern}{suffix}", text) is not None


def _match_entities(text: str, catalog: dict[str, Any], intent: Intent) -> None:
    labels = {
        "region": "Región",
        "financier": "Financiador",
        "area": "Área",
        "rubro": "Rubro",
    }
    for key, label in labels.items():
        for item in catalog.get(key, []):
            # Catalog names such as "5. Viajes" are matched without numbering.
            name = re.sub(r"^[\d.\s]+", "", normalize(str(item["name"])))
            if len(name) >= 3 and re.search(rf"\b{re.escape(name)}\b", text):
                intent.entity_filters.setdefault(f"{key}_ids", []).append(
                    int(item["id"])
                )
                intent.entity_labels.append(f"{label}: {item['name']}")


def _ranked(rows: list[DataRow], key: str = "executed") -> list[DataRow]:
    return sorted(rows, key=lambda r: r.values.get(key, ZERO), reverse=True)


def _day(row: DataRow) -> str:
    raw = row.labels.get("date", "")
    return short_date(date.fromisoformat(raw)) if len(raw) == 10 else raw


def _first_level(rows: list[DataRow]) -> list[DataRow]:
    """Totals per first grouping level, e.g. region instead of region·area."""
    grouped: dict[str, DataRow] = {}
    for row in rows:
        key, name = next(iter(row.labels.items()), ("", ""))
        current = grouped.setdefault(
            name,
            DataRow(
                labels={key: name},
                values={"executed": ZERO, "current_budget": ZERO},
            ),
        )
        for field_name in ("executed", "current_budget"):
            current.values[field_name] += row.values.get(field_name, ZERO)
    for row in grouped.values():
        budget = row.values["current_budget"]
        row.values["execution_percentage"] = (
            row.values["executed"] * 100 / budget if budget else ZERO
        )
    return list(grouped.values())


def _row_name(row: DataRow) -> str:
    return " · ".join(row.labels.values()) or "Sin nombre"


def _change(current: Decimal, previous: Decimal) -> str:
    if not previous:
        return "sin ejecución en el período anterior"
    delta = (current - previous) * 100 / previous
    trend = "más" if delta >= 0 else "menos"
    return f"{pct(abs(delta))} {trend} que el período anterior ({bs(previous)})"


def summarize_report(result: dict[str, Any]) -> str:
    """Verified text for a serialized engine result used in the LLM path."""
    summary = result["summary"]
    lines = [
        f"**{result.get('title', 'Consulta')}**",
        f"- Presupuesto vigente: {bs(summary['current_budget'])}",
        f"- Ejecutado: {bs(summary['executed'])} "
        f"({pct(summary['execution_percentage'])})",
        f"- Saldo disponible: {bs(summary['balance'])}",
    ]
    rows = [
        row
        for row in result.get("rows", [])
        if Decimal(str(row["values"].get("executed", 0)))
        and row["labels"].get("month") != "PTTO"
    ]
    rows.sort(key=lambda row: Decimal(str(row["values"]["executed"])), reverse=True)
    if rows and result.get("report_type") != "movements":
        lines.append("\nMayor ejecución:")
        lines += [
            f"{i}. {' · '.join(row['labels'].values())}: "
            f"{bs(row['values']['executed'])}"
            for i, row in enumerate(rows[:3], 1)
        ]
    return "\n".join(lines)


async def latest_movement(db: AsyncSession, user: User) -> date | None:
    """Last movement date within the user's scope: the data cutoff."""
    query = FinancialEngine(db, user)._apply_permissions(
        select(func.max(Movement.date)), Movement
    )
    value = await db.scalar(query)
    return value if isinstance(value, date) else None


class JukuAssistant:
    def __init__(self, db: AsyncSession, user: User) -> None:
        self.engine = FinancialEngine(db, user)

    def _params(self, base: dict[str, Any], **update: Any) -> BudgetFilterParams:
        data = {
            key: value
            for key, value in base.items()
            if key not in {"page", "date_from", "date_to", "months", "group_by"}
        }
        data.update(update)
        return BudgetFilterParams.model_validate({**data, "page": 1}, strict=False)

    async def answer(
        self, intent: Intent, filters: dict[str, Any], cutoff: date | None
    ) -> Answer:
        base = {**filters, **intent.entity_filters}
        scope = (
            f"\nFiltros aplicados: {', '.join(intent.entity_labels)}."
            if intent.entity_labels
            else ""
        )
        if intent.missing_year:
            years = ", ".join(str(y) for y in filters.get("years", []))
            note = (
                f"No hay datos cargados para la gestión {intent.missing_year}; "
                f"uso la gestión disponible ({years}).\n\n"
            )
        else:
            note = ""
        if intent.kind == "report" and intent.period:
            answer = await self._periodic(intent.period, base, cutoff)
        else:
            answer = await self._query(intent, base, cutoff)
        answer.text = note + answer.text + scope
        return answer

    async def _query(
        self, intent: Intent, base: dict[str, Any], cutoff: date | None
    ) -> Answer:
        report = intent.report or "summary"
        year = intent.year or base["years"][0]
        extra: dict[str, Any] = {"years": [year]}
        label = f"gestión {year}"
        if intent.month:
            start = date(year, intent.month, 1)
            end = date(year, intent.month, calendar.monthrange(year, intent.month)[1])
            extra.update(date_from=start.isoformat(), date_to=end.isoformat())
            label = f"{MONTHS[intent.month].lower()} {year}"
        if report == "compare":
            years = intent.years
            if len(years) < 2:
                return Answer(
                    "Para comparar necesito dos gestiones con datos. Por ahora solo "
                    f"está cargada la gestión {year}, así que no puedo comparar sin "
                    "inventar cifras. Puedo darte el reporte anual de "
                    f"{year} o compararlo mes a mes."
                )
            params = self._params(base, years=years)
            result = await self.engine.compare_budget_periods(params)
            return Answer(
                f"Comparé las gestiones {years[0]} y {years[-1]}. "
                "El detalle muestra diferencias absolutas y porcentuales.",
                [("compare_budget_periods", result)],
            )
        if report == "movements":
            params = self._params(base, **extra, page_size=100)
            result = await self.engine.report("movements", params)
            total = result.metadata.get("total_count", 0)
            top = _ranked(result.rows)[:3]
            lines = [
                f"Encontré **{total} movimientos** en {label}, por un total de "
                f"**{bs(result.summary.executed)}**."
            ]
            if top:
                lines.append("\nLos de mayor monto en esta página:")
                lines += [
                    f"- {_day(r)} · {r.labels.get('description', '')[:60]}: "
                    f"{bs(r.values['executed'])}"
                    for r in top
                ]
            return Answer("\n".join(lines), [("get_transaction_details", result)])
        names = {
            "financier": ("get_execution_by_financier", "financiador"),
            "region": ("get_execution_by_region", "región"),
            "area": ("get_execution_by_area", "área"),
            "account": ("get_execution_by_account", "rubro y cuenta"),
            "monthly": ("get_monthly_execution", "mes"),
            "summary": ("get_general_summary", "rubro"),
        }
        tool, dimension = names[report]
        params = self._params(base, **extra)
        result = await self.engine.report(report, params)
        s = result.summary
        lines = [
            f"**{result.title} · {label}**",
            f"- Presupuesto vigente: {bs(s.current_budget)}",
            f"- Ejecutado: {bs(s.executed)} ({pct(s.execution_percentage)})",
            f"- Saldo disponible: {bs(s.balance)}",
        ]
        rows = [r for r in result.rows if r.labels.get("month") != "PTTO"]
        if report == "monthly":
            ranked = [r for r in _ranked(rows) if r.values.get("executed")]
            if ranked:
                lines.append(
                    f"\nEl mes de mayor ejecución fue **{_row_name(ranked[0])}** "
                    f"con {bs(ranked[0].values['executed'])}."
                )
        elif rows:
            top = [r for r in _ranked(_first_level(rows))[:3] if r.values["executed"]]
            if top:
                lines.append(f"\nMayor ejecución por {dimension}:")
                lines += [
                    f"{i}. {_row_name(r)}: {bs(r.values['executed'])} "
                    f"({pct(r.values['execution_percentage'])} de su presupuesto)"
                    for i, r in enumerate(top, 1)
                ]
        if cutoff:
            lines.append(f"\n_Datos al {short_date(cutoff)} (último movimiento)._")
        return Answer("\n".join(lines), [(tool, result)])

    async def _periodic(
        self, period: Period, base: dict[str, Any], cutoff: date | None
    ) -> Answer:
        year = period.year
        span = {
            "years": [year],
            "date_from": period.start.isoformat(),
            "date_to": period.end.isoformat(),
        }
        annual = period.kind == "annual"
        in_period = await self.engine.report(
            "summary", self._params(base, **({"years": [year]} if annual else span))
        )
        s = in_period.summary
        title = {
            "monthly": "Reporte mensual",
            "quarterly": "Reporte trimestral",
            "semester": "Reporte semestral",
            "annual": "Reporte anual",
        }[period.kind]
        lines = [f"**{title} · {period.label}**"]
        if cutoff and period.start > cutoff:
            lines.append(
                f"\nTodavía no hay movimientos en este período: el último registro "
                f"es del {short_date(cutoff)}. El presupuesto anual vigente es "
                f"{bs(s.current_budget)}."
            )
            return Answer("\n".join(lines), [("get_general_summary", in_period)])
        if cutoff and period.start <= cutoff < period.end:
            lines.append(f"_Período en curso: datos al {short_date(cutoff)}._")

        reports: list[tuple[str, FinancialReportResult]] = []
        if annual:
            lines += [
                "",
                f"- Presupuesto inicial: {bs(s.initial_budget)}",
                f"- Modificaciones: {bs(s.modifications)}",
                f"- **Presupuesto vigente: {bs(s.current_budget)}**",
                f"- **Ejecutado: {bs(s.executed)} ({pct(s.execution_percentage)})**",
                f"- Saldo disponible: {bs(s.balance)}",
            ]
            monthly = await self.engine.report(
                "monthly", self._params(base, years=[year])
            )
            active = [
                r
                for r in monthly.rows
                if r.labels.get("month") != "PTTO" and r.values.get("executed")
            ]
            if active:
                best = _ranked(active)[0]
                average = s.executed / len(active)
                lines += [
                    "",
                    f"**Ritmo mensual:** {len(active)} meses con ejecución, promedio "
                    f"{bs(average)} por mes. Mes más alto: {_row_name(best)} "
                    f"({bs(best.values['executed'])}).",
                ]
                if s.balance > 0 and cutoff and cutoff.year == year:
                    remaining = 12 - cutoff.month
                    if remaining > 0:
                        lines.append(
                            f"Para ejecutar el saldo en los {remaining} meses restantes "
                            f"se necesitarían {bs(s.balance / remaining)} por mes."
                        )
            monthly.rows = [r for r in monthly.rows if r.labels.get("month") != "PTTO"]
            reports.append(("get_general_summary", in_period))
            reports.append(("get_monthly_execution", monthly))
        else:
            months_in = len(period.months)
            lines += [
                "",
                f"- **Ejecutado en el período: {bs(s.executed)}**",
                f"- Representa {pct(s.executed * 100 / s.current_budget if s.current_budget else 0)} "
                f"del presupuesto vigente anual ({bs(s.current_budget)})",
            ]
            accumulated = await self.engine.report(
                "summary",
                self._params(
                    base,
                    years=[year],
                    date_from=date(year, 1, 1).isoformat(),
                    date_to=period.end.isoformat(),
                ),
            )
            a = accumulated.summary
            lines.append(
                f"- Acumulado al cierre del período: {bs(a.executed)} "
                f"({pct(a.execution_percentage)}); saldo {bs(a.balance)}"
            )
            first = period.months[0]
            if first > months_in:
                prev_start = date(year, first - months_in, 1)
                prev_end = date(
                    year, first - 1, calendar.monthrange(year, first - 1)[1]
                )
                previous = await self.engine.report(
                    "summary",
                    self._params(
                        base,
                        years=[year],
                        date_from=prev_start.isoformat(),
                        date_to=prev_end.isoformat(),
                    ),
                )
                lines.append(
                    f"- Variación: {_change(s.executed, previous.summary.executed)}"
                )
            movements = await self.engine.report(
                "movements", self._params(base, **span), all_rows=True
            )
            count = int(movements.metadata.get("total_count", 0))
            lines.append(f"- Movimientos registrados: {count}")
            if count:
                biggest = _ranked(movements.rows)[:3]
                lines.append("\n**Movimientos de mayor monto:**")
                lines += [
                    f"{i}. {_day(r)} · "
                    f"{r.labels.get('description', '')[:60]} "
                    f"({r.labels.get('rubro', '')}): {bs(r.values['executed'])}"
                    for i, r in enumerate(biggest, 1)
                ]
                movements.rows = _ranked(movements.rows)[:20]
                movements.title = "Movimientos de mayor monto del período"
            reports.append(("get_general_summary", in_period))
            if months_in > 1:
                # Month filter (not dates): budget rows only carry a BD month.
                monthly = await self.engine.report(
                    "monthly",
                    self._params(base, years=[year], months=period.months),
                )
                reports.append(("get_monthly_execution", monthly))
            if count:
                reports.append(("get_transaction_details", movements))

        executed_rows = [r for r in in_period.rows if r.values.get("executed")]
        if executed_rows:
            lines.append("\n**Rubros con mayor ejecución:**")
            lines += [
                f"{i}. {_row_name(r)}: {bs(r.values['executed'])}"
                for i, r in enumerate(_ranked(executed_rows)[:3], 1)
            ]
        alerts = [
            f"- {_row_name(r)} supera su presupuesto vigente ({bs(r.values['balance'])})."
            for r in in_period.rows
            if r.values.get("balance", ZERO) < 0
        ]
        if annual:
            alerts += [
                f"- {_row_name(r)} sin ejecución pese a contar con {bs(r.values['current_budget'])}."
                for r in in_period.rows
                if r.values.get("current_budget", ZERO) > 0
                and not r.values.get("executed")
            ]
        if alerts:
            lines.append("\n**Alertas:**")
            lines += alerts[:5]
        lines.append(f"\n{SHARE_HINT}")
        return Answer("\n".join(lines), reports)


HELP_TEXT = """¡Hola! Soy Juku. Puedo ayudarte con:

**Reportes por período**
- "Reporte anual 2026"
- "Reporte mensual de marzo"
- "Reporte del segundo trimestre" o "Reporte del primer semestre"

**Consultas rápidas**
- "¿Cuánto saldo queda disponible?"
- "Ejecución por financiador", "por región" o "por rubro"
- "Evolución mes a mes"
- "Movimientos de agosto"

Todas las cifras salen directamente del motor financiero."""

FALLBACK_TEXT = """No entendí bien la consulta. Prueba con algo como:
- "Reporte mensual de agosto" o "Reporte anual"
- "¿Cuánto saldo queda?"
- "Ejecución por región" o "por financiador"
Escribe "ayuda" para ver todas las opciones."""

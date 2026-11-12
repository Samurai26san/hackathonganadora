"""Deterministic reports with independent aggregates, Decimal and scoped SQL.

Hierarchy definitions follow backend/hackaton/backend/app/reports.py. Budget,
modifications and execution are aggregated separately to prevent fan-out joins.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Money, money
from app.core.exceptions import AppException
from app.models import (
    Area,
    Budget,
    BudgetModification,
    Cuenta,
    Financier,
    Gestion,
    Movement,
    Region,
    Rubro,
    User,
)
from app.schemas.budget import (
    BudgetFilterParams,
    DataRow,
    FinancialReportResult,
    KPISummary,
)

REPORTS: dict[str, tuple[str, list[str]]] = {
    "account": ("Ejecución por rubro y cuenta", ["rubro", "cuenta"]),
    "financier": ("Ejecución por financiador", ["financier", "rubro", "cuenta"]),
    "area": ("Ejecución por área y financiador", ["area", "financier"]),
    "region": ("Ejecución por región", ["region", "area"]),
    "monthly": ("Ejecución por mes", ["month"]),
    "movements": ("Detalle de movimientos", []),
    "summary": ("Resumen general consolidado", ["rubro"]),
}
DIMENSIONS: dict[
    str, type[Region] | type[Area] | type[Financier] | type[Rubro] | type[Cuenta]
] = {
    "region": Region,
    "area": Area,
    "financier": Financier,
    "rubro": Rubro,
    "cuenta": Cuenta,
}
MONTHS = [
    "PTTO",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]
ZERO = Decimal("0.00")


class FinancialEngine:
    def __init__(self, db: AsyncSession, current_user: User) -> None:
        self.db, self.user = db, current_user

    @staticmethod
    def _calculate_kpis(
        initial: Decimal, modifications: Decimal, executed: Decimal
    ) -> KPISummary:
        current = initial + modifications
        return KPISummary(
            initial_budget=money(initial),
            modifications=money(modifications),
            current_budget=money(current),
            executed=money(executed),
            balance=money(current - executed),
            execution_percentage=money(executed * 100 / current) if current else ZERO,
        )

    def _apply_permissions(
        self, query: Select[Any], model: type[Budget] | type[Movement]
    ) -> Select[Any]:
        for dimension in ["region", "area", "financier"]:
            allowed: list[int] | None = getattr(self.user, f"{dimension}_ids")
            if allowed is not None:
                query = query.where(getattr(model, f"{dimension}_id").in_(allowed))
        return query

    def _build_base_query(
        self,
        query: Select[Any],
        model: type[Budget] | type[Movement],
        params: BudgetFilterParams,
    ) -> Select[Any]:
        query = query.where(model.year.in_(params.years))
        for key in ["region", "area", "financier", "cuenta"]:
            ids: list[int] | None = getattr(params, f"{key}_ids")
            if ids is not None:
                query = query.where(getattr(model, f"{key}_id").in_(ids))
        if params.rubro_ids is not None:
            query = query.where(Cuenta.rubro_id.in_(params.rubro_ids))
        if params.months is not None:
            query = query.where(model.month.in_(params.months))
        if model is Movement:
            if params.date_from:
                query = query.where(Movement.date >= params.date_from)
            if params.date_to:
                query = query.where(Movement.date <= params.date_to)
            if params.search:
                pattern = f"%{params.search}%"
                query = query.where(
                    or_(
                        Movement.description.ilike(pattern),
                        Movement.reference.ilike(pattern),
                        Movement.accounting_code.ilike(pattern),
                    )
                )
        return self._apply_permissions(query, model)

    @staticmethod
    def _column(model: type[Budget] | type[Movement], key: str) -> Any:
        if key == "rubro":
            return Cuenta.rubro_id
        if key == "month":
            return model.month
        return getattr(model, f"{key}_id")

    async def _aggregates(
        self, params: BudgetFilterParams, levels: list[str]
    ) -> dict[tuple[int, ...], list[Decimal]]:
        combined: dict[tuple[int, ...], list[Decimal]] = defaultdict(
            lambda: [ZERO, ZERO, ZERO]
        )
        models: list[type[Budget] | type[Movement]] = [Budget, Budget, Movement]
        for index, model in enumerate(models):
            columns = [self._column(model, key) for key in levels]
            amount = (
                Budget.initial_amount
                if index == 0
                else (BudgetModification.amount if index == 1 else Movement.amount)
            )
            query = (
                select(*columns, func.sum(amount, type_=Money()))
                .select_from(model)
                .join(Cuenta, Cuenta.id == model.cuenta_id)
            )
            if index == 1:
                query = query.join(
                    BudgetModification, BudgetModification.budget_id == Budget.id
                )
                if params.date_from:
                    query = query.where(BudgetModification.date >= params.date_from)
                if params.date_to:
                    query = query.where(BudgetModification.date <= params.date_to)
            query = self._build_base_query(query, model, params)
            if columns:
                query = query.group_by(*columns)
            for row in await self.db.execute(query):
                combined[tuple(int(item) for item in row[:-1])][index] = money(row[-1])
        return combined

    async def report(
        self, report_type: str, params: BudgetFilterParams, *, all_rows: bool = False
    ) -> FinancialReportResult:
        if report_type not in REPORTS:
            raise AppException("Informe no permitido.")
        title, levels = REPORTS[report_type]
        totals = await self._aggregates(params, [])
        summary = self._calculate_kpis(*totals.get((), [ZERO, ZERO, ZERO]))
        sources = (
            await self.db.scalars(select(Gestion).where(Gestion.year.in_(params.years)))
        ).all()
        cutoff = await self.db.scalar(
            self._build_base_query(
                select(func.max(Movement.date))
                .select_from(Movement)
                .join(Cuenta, Cuenta.id == Movement.cuenta_id),
                Movement,
                params,
            )
        )
        metadata: dict[str, Any] = {
            "filters": params.model_dump(mode="json"),
            "currency": "BOB",
            "cutoff_date": cutoff.isoformat() if cutoff else None,
            "source": "Excel institucional · hoja BD",
            "sources": [
                {"year": s.year, "file": s.source_name, "sha256": s.source_sha256}
                for s in sources
            ],
            "user_id": self.user.id,
            "levels": levels,
            "date_filter_basis": "Fechas limitan ejecución y modificaciones; el presupuesto se filtra por gestión y mes BD.",
        }
        if report_type == "movements":
            rows, count = await self._movement_rows(params, all_rows=all_rows)
            metadata.update(
                total_count=count, page=params.page, page_size=params.page_size
            )
        else:
            values = await self._aggregates(params, levels)
            labels: dict[str, dict[int, str]] = {"month": dict(enumerate(MONTHS))}
            for key in levels:
                if key != "month":
                    table = DIMENSIONS[key]
                    labels[key] = {}
                    for item in (await self.db.scalars(select(table))).all():
                        assert isinstance(
                            item, (Region, Area, Financier, Rubro, Cuenta)
                        )
                        labels[key][item.id] = item.name
            rows = []
            for ids, amounts in sorted(values.items()):
                row_kpi = self._calculate_kpis(*amounts)
                rows.append(
                    DataRow(
                        labels={
                            key: labels[key].get(id_, str(id_))
                            for key, id_ in zip(levels, ids)
                        },
                        dimensions=dict(zip(levels, ids)),
                        values=row_kpi.model_dump(),
                    )
                )
            metadata["total_count"] = len(rows)
        return FinancialReportResult(
            report_type=report_type,
            title=title,
            metadata=metadata,
            summary=summary,
            rows=rows,
            chart_spec={
                "type": "books",
                "x": levels[0] if levels else "date",
                "yKeys": ["current_budget", "executed"],
            },
        )

    async def _movement_rows(
        self, params: BudgetFilterParams, *, all_rows: bool
    ) -> tuple[list[DataRow], int]:
        query = (
            select(
                Movement,
                Cuenta.name,
                Rubro.name,
                Financier.name,
                Region.name,
                Area.name,
            )
            .join(Cuenta, Cuenta.id == Movement.cuenta_id)
            .join(Rubro, Rubro.id == Cuenta.rubro_id)
            .join(Financier, Financier.id == Movement.financier_id)
            .join(Region, Region.id == Movement.region_id)
            .join(Area, Area.id == Movement.area_id)
        )
        query = self._build_base_query(query, Movement, params)
        count = int(
            (await self.db.scalar(select(func.count()).select_from(query.subquery())))
            or 0
        )
        query = query.order_by(Movement.date, Movement.id)
        if not all_rows:
            query = query.offset((params.page - 1) * params.page_size).limit(
                params.page_size
            )
        rows = []
        for mov, cuenta, rubro, financier, region, area in await self.db.execute(query):
            rows.append(
                DataRow(
                    labels={
                        "date": mov.date.isoformat(),
                        "reference": mov.reference,
                        "description": mov.description,
                        "cuenta": cuenta,
                        "rubro": rubro,
                        "financier": financier,
                        "region": region,
                        "area": area,
                    },
                    values={"executed": mov.amount},
                    dimensions={"cuenta": mov.cuenta_id},
                    details={
                        "id": mov.id,
                        "source_row": mov.source_row,
                        "original": mov.original_data,
                    },
                )
            )
        return rows, count

    async def compare_budget_periods(
        self, params: BudgetFilterParams
    ) -> FinancialReportResult:
        years = sorted(set(params.years))
        if len(years) < 2:
            raise AppException("Selecciona dos gestiones diferentes para comparar.")
        # Check scoped facts, not only the global fiscal-year catalog.
        for year in years:
            scoped = self._build_base_query(
                select(func.count()).select_from(Budget).join(Cuenta),
                Budget,
                params.model_copy(update={"years": [year]}),
            )
            if not await self.db.scalar(scoped):
                raise AppException(f"No hay datos autorizados para la gestión {year}.")
        rows: list[DataRow] = []
        base_values: dict[str, Decimal] = {}
        group = params.group_by if params.group_by in DIMENSIONS else None
        names: dict[int, str] = {}
        if group:
            for entity in (await self.db.scalars(select(DIMENSIONS[group]))).all():
                assert isinstance(entity, (Region, Area, Financier, Rubro, Cuenta))
                names[entity.id] = entity.name
        for year in years:
            groups = await self._aggregates(
                params.model_copy(update={"years": [year]}), [group] if group else []
            )
            for ids, amounts in groups.items():
                kpis = self._calculate_kpis(*amounts)
                key = str(ids)
                if year == years[0]:
                    base_values[key] = kpis.model_dump()[params.metric]
                base = base_values.get(key, ZERO)
                values = kpis.model_dump()
                selected_value = values[params.metric]
                values["difference"] = money(selected_value - base)
                if base:
                    values["difference_percentage"] = money(
                        (selected_value - base) * 100 / base
                    )
                labels = {"year": str(year)}
                if group:
                    labels[group] = names[ids[0]]
                rows.append(DataRow(labels=labels, values=values))
        summary = (await self.get_general_summary(params)).summary
        return FinancialReportResult(
            report_type="compare",
            title="Comparación entre gestiones",
            summary=summary,
            metadata={
                "filters": params.model_dump(mode="json"),
                "currency": "BOB",
                "total_count": len(rows),
            },
            rows=rows,
            chart_spec={
                "type": "books",
                "x": "year",
                "yKeys": ["current_budget", "executed"],
            },
        )

    async def get_execution_by_account(
        self, params: BudgetFilterParams
    ) -> FinancialReportResult:
        return await self.report("account", params)

    async def get_execution_by_financier(
        self, params: BudgetFilterParams
    ) -> FinancialReportResult:
        return await self.report("financier", params)

    async def get_execution_by_area(
        self, params: BudgetFilterParams
    ) -> FinancialReportResult:
        return await self.report("area", params)

    async def get_execution_by_region(
        self, params: BudgetFilterParams
    ) -> FinancialReportResult:
        return await self.report("region", params)

    async def get_monthly_execution(
        self, params: BudgetFilterParams
    ) -> FinancialReportResult:
        return await self.report("monthly", params)

    async def get_transaction_details(
        self, params: BudgetFilterParams
    ) -> FinancialReportResult:
        return await self.report("movements", params)

    async def get_general_summary(
        self, params: BudgetFilterParams
    ) -> FinancialReportResult:
        return await self.report("summary", params)

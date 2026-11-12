"""Catalogs derived only from financial rows visible to the requesting user."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Area, Budget, Cuenta, Financier, Movement, Region, Rubro, User
from app.services.financial_engine import DIMENSIONS, MONTHS, REPORTS, FinancialEngine


async def catalogs(db: AsyncSession, user: User) -> dict[str, Any]:
    engine = FinancialEngine(db, user)
    # Both fact tables matter after an administrator deletes a budget while
    # retaining its execution, or adds a movement without a budget amount.
    facts: list[Any] = []
    fact_models: list[type[Budget] | type[Movement]] = [Budget, Movement]
    for model in fact_models:
        query = (
            select(
                model.year,
                model.month,
                model.region_id,
                model.area_id,
                model.financier_id,
                model.cuenta_id,
                Cuenta.rubro_id,
            )
            .join(Cuenta, Cuenta.id == model.cuenta_id)
            .distinct()
        )
        facts.extend((await db.execute(engine._apply_permissions(query, model))).all())
    result: dict[str, Any] = {
        "years": sorted({row[0] for row in facts}, reverse=True),
        "reports": [{"id": key, "title": value[0]} for key, value in REPORTS.items()],
    }
    indexes = {"region": 2, "area": 3, "financier": 4, "cuenta": 5, "rubro": 6}
    for key, model_table in DIMENSIONS.items():
        ids = {row[indexes[key]] for row in facts}
        entries = (
            await db.scalars(
                select(model_table)
                .where(model_table.id.in_(ids))
                .order_by(model_table.name)
            )
        ).all()
        result[key] = []
        for item in entries:
            assert isinstance(item, (Region, Area, Financier, Rubro, Cuenta))
            result[key].append(
                {
                    "id": item.id,
                    "name": item.name,
                    **({"rubro_id": item.rubro_id} if isinstance(item, Cuenta) else {}),
                }
            )
    months = sorted({row[1] for row in facts})
    result["months"] = [{"id": month, "name": MONTHS[month]} for month in months]
    return result

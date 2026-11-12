"""Catalogs derived only from financial rows visible to the requesting user."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Budget, Cuenta, User
from app.services.financial_engine import DIMENSIONS, MONTHS, REPORTS, FinancialEngine


async def catalogs(db: AsyncSession, user: User) -> dict[str, Any]:
    engine = FinancialEngine(db, user)
    years = (
        await db.scalars(
            engine._apply_permissions(
                select(Budget.year).distinct().order_by(Budget.year.desc()), Budget
            )
        )
    ).all()
    result: dict[str, Any] = {
        "years": list(years),
        "reports": [{"id": key, "title": value[0]} for key, value in REPORTS.items()],
    }
    for key, table in DIMENSIONS.items():
        query = (
            select(table.id, table.name)
            .distinct()
            .select_from(Budget)
            .join(Cuenta, Cuenta.id == Budget.cuenta_id)
        )
        if key != "cuenta":
            query = query.join(
                table,
                table.id
                == (
                    Cuenta.rubro_id if key == "rubro" else getattr(Budget, f"{key}_id")
                ),
            )
        rows = await db.execute(
            engine._apply_permissions(query.order_by(table.name), Budget)
        )
        result[key] = [{"id": id_, "name": name} for id_, name in rows]
    accounts = (
        await db.execute(
            engine._apply_permissions(
                select(Cuenta.id, Cuenta.rubro_id)
                .distinct()
                .join(Budget, Budget.cuenta_id == Cuenta.id),
                Budget,
            )
        )
    ).all()
    parents: dict[int, int] = {id_: parent for id_, parent in accounts}
    for account in result["cuenta"]:
        account["rubro_id"] = parents[account["id"]]
    months = (
        await db.scalars(
            engine._apply_permissions(
                select(Budget.month).distinct().order_by(Budget.month), Budget
            )
        )
    ).all()
    result["months"] = [{"id": month, "name": MONTHS[month]} for month in months]
    return result

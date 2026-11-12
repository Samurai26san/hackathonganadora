"""Exact monetary arithmetic and row-level authorization of every report."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import money
from app.core.exceptions import AppException
from app.models import User
from app.schemas.budget import BudgetFilterParams
from app.services.financial_engine import REPORTS, FinancialEngine


def test_money_rejects_nonfinite_values() -> None:
    for invalid in ["NaN", "Infinity", "-Infinity"]:
        with pytest.raises(ValueError):
            money(invalid)


@pytest.mark.parametrize("report", list(REPORTS))
async def test_reports_exact_and_no_join_fanout(
    db: AsyncSession, sample: User, report: str
) -> None:
    result = await FinancialEngine(db, sample).report(
        report, BudgetFilterParams(years=[2026])
    )
    assert result.summary.initial_budget == Decimal("300.30")
    assert result.summary.modifications == Decimal("15.00")
    assert result.summary.current_budget == Decimal("315.30")
    assert result.summary.executed == Decimal("100.30")
    assert result.summary.balance == Decimal("215.00")
    assert result.metadata["cutoff_date"] == "2026-03-03"
    assert '"315.30"' in result.model_dump_json()


async def test_scopes_cannot_be_widened_by_request(
    db: AsyncSession, sample: User
) -> None:
    sample.region_ids = [1]
    engine = FinancialEngine(db, sample)
    result = await engine.get_general_summary(BudgetFilterParams(years=[2026]))
    assert result.summary.executed == Decimal("0.30")
    hidden = await engine.get_transaction_details(
        BudgetFilterParams(years=[2026], region_ids=[2])
    )
    assert hidden.rows == [] and hidden.summary.executed == 0
    sample.region_ids = []
    assert (
        await engine.get_general_summary(BudgetFilterParams(years=[2026]))
    ).summary.current_budget == 0


async def test_compare_missing_period_and_zero_denominator(
    db: AsyncSession, sample: User
) -> None:
    engine = FinancialEngine(db, sample)
    result = await engine.compare_budget_periods(BudgetFilterParams(years=[2025, 2026]))
    assert len(result.rows) == 2
    assert result.rows[1].values["difference"] == Decimal("100.30")
    budget_compare = await engine.compare_budget_periods(
        BudgetFilterParams(years=[2025, 2026], metric="current_budget")
    )
    assert budget_compare.rows[1].values["difference"] == Decimal("265.30")
    assert "difference_percentage" not in result.rows[1].values
    with pytest.raises(AppException):
        await engine.compare_budget_periods(BudgetFilterParams(years=[2024, 2026]))
    assert (
        engine._calculate_kpis(Decimal(0), Decimal(0), Decimal(1)).execution_percentage
        == 0
    )


async def test_combined_filters_and_pagination(db: AsyncSession, sample: User) -> None:
    result = await FinancialEngine(db, sample).get_transaction_details(
        BudgetFilterParams(
            years=[2026],
            region_ids=[1],
            months=[3],
            search="Pasaje",
            page_size=1,
            page=2,
        )
    )
    assert result.metadata["total_count"] == 2
    assert len(result.rows) == 1
    assert result.rows[0].values["executed"] == Decimal("0.20")

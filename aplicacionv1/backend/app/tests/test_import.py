"""Reconcile the supplied workbook instead of approximate or synthetic totals."""

from decimal import Decimal
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.budget import BudgetFilterParams
from app.services.financial_engine import REPORTS, FinancialEngine
from app.services.import_service import ingest_bd, preview

SOURCE = next(
    (Path(__file__).resolve().parents[2] / "hackaton").glob("Prueba ExB Nov*.xlsx")
)


def test_workbook_reconciles_reference_exactly() -> None:
    result = preview(SOURCE.read_bytes())
    assert result["source_rows"] == 3574
    assert result["movement_rows"] == 1478
    assert result["budget"] == "3163379.01"
    assert result["executed"] == "528694.16"
    assert result["year"] == 2026


async def test_ingestion_and_all_reports_reconcile(db: AsyncSession) -> None:
    await ingest_bd(db, SOURCE)
    assert (await ingest_bd(db, SOURCE))["status"] == "already_imported"
    user = User(
        id="real-reader",
        email="real@test.exb",
        full_name="Lector",
        role="viewer",
        region_ids=None,
    )
    db.add(user)
    await db.flush()
    for report in REPORTS:
        result = await FinancialEngine(db, user).report(
            report, BudgetFilterParams(years=[2026])
        )
        assert result.summary.current_budget == Decimal("3163379.01")
        assert result.summary.executed == Decimal("528694.16")
        assert result.summary.balance == Decimal("2634684.85")

"""Focused checks for financial edits, immutable history and complete exports."""

from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import Budget, BudgetModification, Cuenta, Rubro, User
from app.schemas.budget import BudgetFilterParams
from app.services.export_service import export_report
from app.services.financial_engine import FinancialEngine


@pytest.fixture
async def change_client(
    db: AsyncSession, sample: User, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setattr(get_settings(), "auth_mode", "demo")
    monkeypatch.setattr(get_settings(), "cookie_secure", False)
    if db.get_bind().dialect.name == "postgresql":
        # The shared fixture assigns IDs explicitly; initialize its sequences.
        await db.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('budgets','id'), (SELECT max(id) FROM budgets))"
            )
        )
        await db.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('movements','id'), (SELECT max(id) FROM movements))"
            )
        )
    sample.role = "admin"
    sample.password_hash = hash_password("Demo2026!")

    async def override() -> AsyncIterator[AsyncSession]:
        yield db
        await db.flush()

    app.dependency_overrides[get_db] = override
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost:8080"
        ) as client:
            assert (
                await client.post(
                    "/api/v1/auth/login",
                    json={"email": sample.email, "password": "Demo2026!"},
                )
            ).status_code == 200
            yield client
    finally:
        app.dependency_overrides.clear()


def body(**extra: Any) -> dict[str, Any]:
    return {
        "year": 2026,
        "month": 0,
        "region_id": 1,
        "area_id": 1,
        "financier_id": 1,
        "rubro_id": 1,
        "cuenta_id": 1,
        "amount": "32.15",
        "reason": "Corrección verificada del presupuesto",
        **extra,
    }


async def test_crud_restore_preserves_original_and_history(
    change_client: httpx.AsyncClient, db: AsyncSession
) -> None:
    c = change_client
    original = (await c.get("/api/v1/data/records?years=2026&kind=budget")).json()[
        "rows"
    ][0]
    original_amount = original["amount"]
    created = await c.post("/api/v1/data/records/budget", json=body())
    assert created.status_code == 200, created.text
    created_id = created.json()["id"]
    edited = await c.put(
        f'/api/v1/data/records/budget/{original["id"]}',
        json=body(amount="222.22", expected_version=original["version"]),
    )
    assert edited.status_code == 200, edited.text
    stale = await c.put(
        f'/api/v1/data/records/budget/{original["id"]}',
        json=body(expected_version=original["version"]),
    )
    assert stale.status_code == 409
    denied = await c.post(
        f'/api/v1/data/records/budget/{original["id"]}/delete',
        json={
            "confirm": False,
            "reason": "Eliminación controlada",
            "expected_version": edited.json()["version"],
        },
    )
    assert denied.status_code == 422
    removed = await c.post(
        f'/api/v1/data/records/budget/{original["id"]}/delete',
        json={
            "confirm": True,
            "reason": "Eliminación controlada",
            "expected_version": edited.json()["version"],
        },
    )
    assert removed.status_code == 200, removed.text
    history = (await c.get("/api/v1/data/history")).json()
    assert history["total"] == 3
    assert history["rows"][0]["before"]["initial_amount"] == "222.22"
    restored = await c.post(
        "/api/v1/data/restore",
        json={
            "confirm": True,
            "reason": "Restauración solicitada del original",
            "expected_revision": history["revision"],
        },
    )
    assert restored.status_code == 200, restored.text
    row = await db.get(Budget, original["id"])
    assert row is not None
    assert row.initial_amount == Decimal(original_amount)
    modifications = (
        await db.scalars(
            select(BudgetModification).where(BudgetModification.budget_id == row.id)
        )
    ).all()
    assert sum((item.amount for item in modifications), Decimal("0.00")) == Decimal(
        "15.00"
    )
    assert await db.get(Budget, created_id) is None
    log = await c.get("/api/v1/data/history/export")
    assert log.status_code == 200 and len(log.json()) == 4
    assert log.json()[0]["action"] == "restore"
    assert (
        len((await c.get("/api/v1/data/records?years=2026&kind=budget")).json()["rows"])
        == 2
    )


async def test_technical_role_and_account_parent(
    change_client: httpx.AsyncClient, sample: User
) -> None:
    c = change_client
    assert (
        await c.post("/api/v1/data/records/budget", json=body(rubro_id=999))
    ).status_code == 422
    assert (
        await c.post("/api/v1/data/records/movement", json=body())
    ).status_code == 422
    sample.role = "analyst"
    assert (await c.post("/api/v1/data/records/budget", json=body())).status_code == 403
    assert (await c.get("/api/v1/data/history")).status_code == 403
    assert (await c.get("/api/v1/data/catalogs")).status_code == 403


async def test_detailed_exports_include_unexpanded_empty_accounts_and_all_movements(
    db: AsyncSession, sample: User
) -> None:
    db.add(Rubro(id=2, name="Sin ejecución", code="2"))
    await db.flush()
    db.add(Cuenta(id=2, name="Cuenta sin movimientos", code="2.1", rubro_id=2))
    await db.flush()
    db.add(
        Budget(
            id=10,
            year=2026,
            month=0,
            region_id=1,
            area_id=1,
            financier_id=1,
            cuenta_id=2,
            source_row=10,
            initial_amount=Decimal("99.99"),
        )
    )
    await db.flush()
    report = await FinancialEngine(db, sample).export_detail(
        "summary", BudgetFilterParams(years=[2026], page_size=1)
    )
    movements = [r for r in report.rows if r.labels["Nivel"] == "Movimiento"]
    accounts = [r for r in report.rows if r.labels["Nivel"] == "Cuenta"]
    assert len(movements) == 3
    assert any(
        r.labels["cuenta"] == "Cuenta sin movimientos"
        and r.values["current_budget"] == Decimal("99.99")
        for r in accounts
    )
    content, _, _ = export_report(report, "csv")
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    assert sum(r["Nivel"] == "Movimiento" for r in rows) == 3
    assert all(r["Gestión"] == "2026" and "years" in r["Filtros"] for r in rows)
    pdf, _, _ = export_report(report, "pdf")
    assert pdf.startswith(b"%PDF")


async def test_movement_changes_update_execution_and_enforce_admin_scope(
    change_client: httpx.AsyncClient, sample: User
) -> None:
    c = change_client
    movement = body(
        month=3, date="2026-03-04", amount="12.34", description="Ajuste manual"
    )
    created = await c.post("/api/v1/data/records/movement", json=movement)
    assert created.status_code == 200, created.text
    id_ = created.json()["id"]
    report = (await c.get("/api/v1/budget/execution/summary?years=2026")).json()
    assert report["summary"]["executed"] == "112.64"
    edited = await c.put(
        f"/api/v1/data/records/movement/{id_}",
        json={
            **movement,
            "amount": "2.22",
            "expected_version": created.json()["version"],
        },
    )
    assert edited.status_code == 200, edited.text
    assert (await c.get("/api/v1/budget/execution/summary?years=2026")).json()[
        "summary"
    ]["executed"] == "102.52"
    assert (
        await c.post(
            f"/api/v1/data/records/movement/{id_}/delete",
            json={
                "confirm": True,
                "reason": "Eliminar movimiento creado",
                "expected_version": edited.json()["version"],
            },
        )
    ).status_code == 200
    history = (await c.get("/api/v1/data/history")).json()
    assert (
        await c.post(
            "/api/v1/data/restore",
            json={
                "confirm": True,
                "reason": "Restaurar estado inicial",
                "expected_revision": history["revision"],
            },
        )
    ).status_code == 200
    assert (await c.get("/api/v1/budget/execution/summary?years=2026")).json()[
        "summary"
    ]["executed"] == "100.30"
    sample.region_ids = [1]
    assert (
        await c.post("/api/v1/data/records/budget", json=body(region_id=2))
    ).status_code == 403
    assert (
        await c.put(
            "/api/v1/data/records/budget/2", json=body(expected_version="0" * 64)
        )
    ).status_code == 404

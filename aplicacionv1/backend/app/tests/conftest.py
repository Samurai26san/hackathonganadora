"""Isolated async database fixtures; TEST_DATABASE_URI enables PostgreSQL checks."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.database import Base
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


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        os.getenv("TEST_DATABASE_URI", "sqlite+aiosqlite:///:memory:")
    )
    async with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            from sqlalchemy import text

            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    async with engine.connect() as conn:
        tx = await conn.begin()
        async with AsyncSession(conn, expire_on_commit=False) as session:
            yield session
        await tx.rollback()
    await engine.dispose()


@pytest.fixture
async def sample(db: AsyncSession) -> User:
    db.add_all(
        [
            Region(id=1, code="LP", name="LP"),
            Region(id=2, code="SC", name="SC"),
            Area(id=1, code="EDU", name="Educación"),
            Financier(id=1, code="CAT", name="Catalyst"),
            Rubro(id=1, code="1", name="1. Viajes"),
            Gestion(year=2026, source_name="prueba", source_sha256="test"),
            Gestion(year=2025, source_name="prueba", source_sha256="test2"),
        ]
    )
    await db.flush()
    db.add(Cuenta(id=1, code="1.1", name="1.1 Pasajes", rubro_id=1))
    await db.flush()
    for row, region, amount, year in [
        (1, 1, "100.10", 2026),
        (2, 2, "200.20", 2026),
        (3, 1, "50.00", 2025),
    ]:
        db.add(
            Budget(
                id=row,
                year=year,
                month=0,
                region_id=region,
                area_id=1,
                financier_id=1,
                cuenta_id=1,
                source_row=row,
                initial_amount=Decimal(amount),
            )
        )
    await db.flush()
    db.add_all(
        [
            BudgetModification(
                budget_id=1, amount=Decimal("10.00"), date=date(2026, 1, 1)
            ),
            BudgetModification(
                budget_id=1, amount=Decimal("5.00"), date=date(2026, 1, 1)
            ),
        ]
    )
    for row, region, amount in [(1, 1, "0.10"), (2, 1, "0.20"), (3, 2, "100.00")]:
        db.add(
            Movement(
                year=2026,
                month=3,
                region_id=region,
                area_id=1,
                financier_id=1,
                cuenta_id=1,
                source_row=row,
                date=date(2026, 3, row),
                amount=Decimal(amount),
                description=f"Pasaje {row}",
                reference=f"LP-{row}",
            )
        )
    user = User(
        id="reader",
        email="test@exb.test",
        full_name="Lector",
        role="analyst",
        region_ids=None,
    )
    db.add(user)
    await db.flush()
    return user

"""Async SQLAlchemy unit of work and exact monetary storage."""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import BigInteger, Numeric
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator, TypeEngine

from app.core.config import get_settings

CENT = Decimal("0.01")


def money(value: object) -> Decimal:
    exact = Decimal(str(value or 0))
    if not exact.is_finite():
        raise ValueError("El importe debe ser finito.")
    return exact.quantize(CENT, rounding=ROUND_HALF_UP)


class Money(TypeDecorator[Decimal]):
    """NUMERIC in PostgreSQL; integer cents in the isolated SQLite test harness."""

    impl = Numeric(20, 2)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        return dialect.type_descriptor(
            BigInteger() if dialect.name == "sqlite" else Numeric(20, 2)
        )

    def process_bind_param(
        self, value: Decimal | None, dialect: Dialect
    ) -> Decimal | int | None:
        if value is None:
            return None
        exact = money(value)
        return int(exact * 100) if dialect.name == "sqlite" else exact

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        return (
            money(Decimal(str(value)) / 100)
            if dialect.name == "sqlite"
            else money(value)
        )


class Base(DeclarativeBase):
    pass


engine = create_async_engine(get_settings().database_uri, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

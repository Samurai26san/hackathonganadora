"""Budget dimensions and facts adapted from the supplied ExB backend."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Money
from app.models.user import now


class Gestion(Base):
    __tablename__ = "gestiones"
    year: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(255))
    source_sha256: Mapped[str] = mapped_column(String(64))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Dimension:
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), unique=True)


class Region(Dimension, Base):
    __tablename__ = "regiones"


class Area(Dimension, Base):
    __tablename__ = "areas"


class Financier(Dimension, Base):
    __tablename__ = "financiadores"


class Rubro(Dimension, Base):
    __tablename__ = "rubros"


class Cuenta(Base):
    __tablename__ = "cuentas"
    __table_args__ = (UniqueConstraint("name", "rubro_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    rubro_id: Mapped[int] = mapped_column(ForeignKey("rubros.id"))


class FinancialDimensions:
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(ForeignKey("gestiones.year"), index=True)
    month: Mapped[int] = mapped_column(Integer, index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regiones.id"), index=True)
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"), index=True)
    financier_id: Mapped[int] = mapped_column(
        ForeignKey("financiadores.id"), index=True
    )
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"), index=True)
    source_row: Mapped[int] = mapped_column(Integer)


class Budget(FinancialDimensions, Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("year", "source_row"),)
    initial_amount: Mapped[Decimal] = mapped_column(Money())


class BudgetModification(Base):
    __tablename__ = "budget_modifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Money())
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text, default="")


class Movement(FinancialDimensions, Base):
    __tablename__ = "movements"
    __table_args__ = (UniqueConstraint("year", "source_row"),)
    date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Money())
    reference: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    accounting_code: Mapped[str] = mapped_column(String(255), default="")
    movement_type: Mapped[str] = mapped_column(String(40), default="")
    original_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    rate: Mapped[Decimal] = mapped_column(Money())


class ImportLog(Base):
    __tablename__ = "import_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    source_name: Mapped[str] = mapped_column(String(255))
    rows: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

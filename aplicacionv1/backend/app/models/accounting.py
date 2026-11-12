"""Staging, double-entry ledger and qualitative financial disclosures."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Money
from app.models.user import now


class CurationBatch(Base):
    __tablename__ = "curation_batches"
    __table_args__ = (UniqueConstraint("owner_id", "sha256"),)
    sha256: Mapped[str] = mapped_column(String(64))
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CurationRow(Base):
    __tablename__ = "curation_rows"
    __table_args__ = (UniqueConstraint("batch_id", "source_row"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("curation_batches.id"), index=True)
    source_row: Mapped[int]
    original: Mapped[dict[str, Any]] = mapped_column(JSON)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    issues: Mapped[list[str]] = mapped_column(JSON, default=list)
    prediction: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    version: Mapped[int] = mapped_column(default=1)
    validated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_kind: Mapped[str | None] = mapped_column(String(20))
    target_id: Mapped[int | None] = mapped_column(index=True)


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_accounts.id"))
    kind: Mapped[str] = mapped_column(String(30))
    section: Mapped[str] = mapped_column(String(100))
    liquidity_order: Mapped[int] = mapped_column(default=0)
    is_cash: Mapped[bool] = mapped_column(default=False)


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(Text)
    reference: Mapped[str] = mapped_column(String(100), unique=True)
    entry_type: Mapped[str] = mapped_column(String(30), default="normal")
    equity_event: Mapped[str] = mapped_column(String(40), default="other")
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class JournalLine(Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint(
            "debit >= 0 AND credit >= 0 AND (debit = 0 OR credit = 0)",
            name="ck_journal_one_side",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("ledger_accounts.id"), index=True
    )
    debit: Mapped[Decimal] = mapped_column(Money())
    credit: Mapped[Decimal] = mapped_column(Money())
    cash_activity: Mapped[str | None] = mapped_column(String(20))


class FinancialDisclosure(Base):
    __tablename__ = "financial_disclosures"
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(20))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_accounts.id"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    risk: Mapped[str] = mapped_column(String(20), default="none")
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

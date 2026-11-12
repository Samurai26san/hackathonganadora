"""Accounting configuration and immutable balanced postings, independent of budget facts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from app.api.v1.data_changes import lock
from app.core.exceptions import AppException
from app.core.security import DB, AdminUser, CurrentUser
from app.models import AuditLog, User
from app.models.accounting import (
    FinancialDisclosure,
    JournalEntry,
    JournalLine,
    LedgerAccount,
)
from app.services.accounting_service import statements

router = APIRouter(prefix="/accounting", tags=["Contabilidad"])
Kind = Literal[
    "asset", "liability", "equity", "income", "expense", "contingent", "order"
]
SECTIONS = {
    "asset": {
        "cash",
        "temporary_investment",
        "portfolio",
        "realizable_assets",
        "fixed_assets",
        "other_assets",
    },
    "liability": {
        "public",
        "banks",
        "fiscal",
        "public_companies",
        "provisions",
        "other_liabilities",
    },
    "equity": {
        "capital",
        "legal_reserves",
        "uncapitalized_contributions",
        "retained_results",
    },
    "income": {"financial_income", "operating_income", "other_income"},
    "expense": {
        "financial_cost",
        "operating_expense",
        "provision",
        "other_expense",
        "iue",
    },
    "contingent": {"guarantees", "unused_credit", "other_contingent"},
    "order": {"order_debit", "order_credit"},
}


def full_scope(user: User) -> None:
    if any(
        getattr(user, k + "_ids") is not None for k in ("region", "area", "financier")
    ):
        raise AppException(
            "Los estados consolidados requieren alcance institucional completo.", 403
        )


class AccountInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=2, max_length=255)
    parent_id: int | None = None
    kind: Kind
    section: str = Field(max_length=100)
    liquidity_order: int = Field(default=0, ge=0)
    is_cash: bool = False

    @model_validator(mode="after")
    def valid(self) -> AccountInput:
        if self.section not in SECTIONS[self.kind]:
            raise ValueError("Sección incompatible con el tipo de cuenta")
        if self.is_cash and (self.kind != "asset" or self.section != "cash"):
            raise ValueError("Las disponibilidades deben ser activo/cash")
        return self


class LineInput(BaseModel):
    account_id: int = Field(gt=0)
    debit: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=20,
        decimal_places=2,
        allow_inf_nan=False,
    )
    credit: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=20,
        decimal_places=2,
        allow_inf_nan=False,
    )
    cash_activity: Literal["operation", "investment", "financing"] | None = None


class EntryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    date: date
    description: str = Field(min_length=5, max_length=4000)
    reference: str = Field(min_length=1, max_length=100)
    entry_type: Literal["normal", "opening", "closing", "reversal"] = "normal"
    equity_event: Literal[
        "opening", "reinvestment", "reserve", "dividend", "contribution", "other"
    ] = "other"
    reason: str = Field(min_length=5, max_length=1000)
    lines: list[LineInput] = Field(min_length=2, max_length=200)

    @model_validator(mode="after")
    def balanced(self) -> EntryInput:
        if self.entry_type == "opening" and (self.date.month, self.date.day) != (1, 1):
            raise ValueError("Los saldos de apertura se registran al 1 de enero.")
        if any((line.debit > 0) == (line.credit > 0) for line in self.lines):
            raise ValueError(
                "Cada línea requiere exactamente un debe o un haber positivo"
            )
        if sum(line.debit for line in self.lines) != sum(
            line.credit for line in self.lines
        ):
            raise ValueError("El asiento debe cuadrar: suma del debe = suma del haber")
        return self


class DisclosureInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    year: int = Field(ge=1900, le=2200)
    kind: Literal["auditor", "note"]
    account_id: int | None = None
    title: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=10, max_length=50000)
    risk: Literal["none", "low", "medium", "high"] = "none"


@router.get("/catalogs")
async def catalogs(db: DB, user: CurrentUser) -> dict[str, Any]:
    full_scope(user)
    return {
        "sections": {key: sorted(values) for key, values in SECTIONS.items()},
        "accounts": [
            {
                "id": a.id,
                "code": a.code,
                "name": a.name,
                "kind": a.kind,
                "section": a.section,
                "parent_id": a.parent_id,
                "is_cash": a.is_cash,
            }
            for a in (
                await db.scalars(select(LedgerAccount).order_by(LedgerAccount.code))
            ).all()
        ],
    }


@router.post("/accounts")
async def add_account(body: AccountInput, db: DB, user: AdminUser) -> dict[str, int]:
    full_scope(user)
    await lock(db)
    if await db.scalar(select(LedgerAccount.id).where(LedgerAccount.code == body.code)):
        raise AppException("El código de cuenta ya existe.", 409)
    if body.parent_id:
        parent = await db.get(LedgerAccount, body.parent_id)
        if parent is None or parent.kind != body.kind or parent.section != body.section:
            raise AppException(
                "La subcuenta debe mantener tipo y sección de su cuenta superior.", 422
            )
        if await db.scalar(
            select(JournalLine.id).where(JournalLine.account_id == parent.id).limit(1)
        ):
            raise AppException(
                "La cuenta superior ya tiene asientos: no se puede convertir en agrupador.",
                409,
            )
    row = LedgerAccount(**body.model_dump())
    db.add(row)
    await db.flush()
    db.add(
        AuditLog(
            user_id=user.id,
            action="accounting.account",
            resource_id=str(row.id),
            payload_json=body.model_dump(mode="json"),
        )
    )
    await db.commit()
    return {"id": row.id}


@router.post("/entries")
async def post_entry(body: EntryInput, db: DB, user: AdminUser) -> dict[str, int]:
    full_scope(user)
    await lock(db)
    if await db.scalar(
        select(JournalEntry.id).where(JournalEntry.reference == body.reference)
    ):
        raise AppException("El comprobante ya fue registrado.", 409)
    off_balance: list[bool] = []
    for line in body.lines:
        account = await db.get(LedgerAccount, line.account_id)
        if account is None:
            raise AppException("Cuenta contable inexistente.", 422)
        if await db.scalar(
            select(LedgerAccount.id)
            .where(LedgerAccount.parent_id == account.id)
            .limit(1)
        ):
            raise AppException("Registra el movimiento en una subcuenta final.", 422)
        off_balance.append(account.kind in {"contingent", "order"})
        if body.entry_type == "closing" and account.kind not in {
            "income",
            "expense",
            "equity",
        }:
            raise AppException(
                "El cierre de resultados solo admite ingresos, gastos y patrimonio.",
                422,
            )
        if (
            account.is_cash
            and body.entry_type != "opening"
            and line.cash_activity is None
        ):
            raise AppException(
                "Cada movimiento de efectivo requiere actividad: operación, inversión o financiamiento.",
                422,
            )
        if not account.is_cash and line.cash_activity:
            raise AppException(
                "La clasificación de flujo corresponde únicamente a cuentas de efectivo.",
                422,
            )
        if body.entry_type == "opening" and account.kind in {"income", "expense"}:
            raise AppException(
                "Los saldos iniciales de resultados deben incorporarse al patrimonio.",
                422,
            )
    if any(off_balance) and not all(off_balance):
        raise AppException(
            "Las cuentas contingentes/de orden se registran en asientos separados del balance.",
            422,
        )
    entry = JournalEntry(**body.model_dump(exclude={"lines"}), author_id=user.id)
    db.add(entry)
    await db.flush()
    for line in body.lines:
        db.add(JournalLine(entry_id=entry.id, **line.model_dump()))
    db.add(
        AuditLog(
            user_id=user.id,
            action="accounting.post",
            resource_type="journal",
            resource_id=str(entry.id),
            payload_json=body.model_dump(mode="json"),
        )
    )
    await db.commit()
    return {"id": entry.id}


@router.post("/disclosures")
async def add_disclosure(
    body: DisclosureInput, db: DB, user: AdminUser
) -> dict[str, int]:
    full_scope(user)
    if body.account_id and await db.get(LedgerAccount, body.account_id) is None:
        raise AppException("Cuenta contable inexistente.", 422)
    row = FinancialDisclosure(**body.model_dump(), author_id=user.id)
    db.add(row)
    await db.flush()
    db.add(
        AuditLog(
            user_id=user.id,
            action="accounting.disclosure",
            resource_id=str(row.id),
            payload_json=body.model_dump(mode="json"),
        )
    )
    await db.commit()
    return {"id": row.id}


@router.get("/statements")
async def financial_statements(
    cutoff: date, db: DB, user: CurrentUser, start: date | None = None
) -> dict[str, Any]:
    full_scope(user)
    start = start or date(cutoff.year, 1, 1)
    if start > cutoff or start.year != cutoff.year:
        raise AppException(
            "El inicio debe pertenecer a la gestión y preceder al corte.", 422
        )
    await lock(db)
    return await statements(db, cutoff, start)


@router.get("/alerts")
async def risk_alerts(year: int, db: DB, user: CurrentUser) -> list[dict[str, Any]]:
    # Consolidated disclosures cannot be disclosed through a scoped budget account.
    if any(
        getattr(user, k + "_ids") is not None for k in ("region", "area", "financier")
    ):
        return []
    rows = (
        await db.scalars(
            select(FinancialDisclosure)
            .where(
                FinancialDisclosure.year == year,
                FinancialDisclosure.risk.in_(["medium", "high"]),
            )
            .order_by(FinancialDisclosure.id.desc())
            .limit(30)
        )
    ).all()
    return [
        {"id": row.id, "title": row.title, "risk": row.risk, "kind": row.kind}
        for row in rows
    ]

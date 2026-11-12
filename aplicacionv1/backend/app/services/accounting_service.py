"""Exact, cutoff-aware statements from an independent double-entry ledger."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import money
from app.models.accounting import (
    FinancialDisclosure,
    JournalEntry,
    JournalLine,
    LedgerAccount,
)

ZERO = Decimal("0.00")


async def statements(db: AsyncSession, cutoff: date, start: date) -> dict[str, Any]:
    records = (
        await db.execute(
            select(JournalLine, JournalEntry, LedgerAccount)
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .join(LedgerAccount, LedgerAccount.id == JournalLine.account_id)
            .where(JournalEntry.date <= cutoff)
            .order_by(
                LedgerAccount.liquidity_order,
                LedgerAccount.code,
                JournalEntry.date,
                JournalLine.id,
            )
        )
    ).all()
    balances: dict[int, Decimal] = defaultdict(lambda: ZERO)
    initial: dict[int, Decimal] = defaultdict(lambda: ZERO)
    accounts: dict[int, LedgerAccount] = {
        a.id: a
        for a in (
            await db.scalars(
                select(LedgerAccount).order_by(
                    LedgerAccount.liquidity_order, LedgerAccount.code
                )
            )
        ).all()
    }
    income: dict[str, Decimal] = defaultdict(lambda: ZERO)
    cash: dict[str, Decimal] = defaultdict(lambda: ZERO)
    equity: dict[int, dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: ZERO)
    )
    cash_initial = ZERO
    lines = []
    for line, entry, account in records:
        accounts[account.id] = account
        debit_net = line.debit - line.credit
        normal_net = (
            debit_net
            if account.kind in {"asset", "expense", "contingent", "order"}
            else -debit_net
        )
        balances[account.id] += normal_net
        if entry.date < start:
            initial[account.id] += normal_net
        in_period = start <= entry.date <= cutoff and entry.entry_type not in {
            "opening",
            "closing",
        }
        if in_period and account.kind in {"income", "expense"}:
            income[account.section] += normal_net
        if account.is_cash:
            if entry.date < start or (
                entry.date == start and entry.entry_type == "opening"
            ):
                cash_initial += debit_net
            elif entry.date >= start:
                cash[line.cash_activity or "unclassified"] += debit_net
        if account.kind == "equity" and entry.date >= start:
            equity[account.id][entry.equity_event] += normal_net
        lines.append(
            {
                "date": entry.date.isoformat(),
                "reference": entry.reference,
                "account": account.code,
                "name": account.name,
                "debit": str(line.debit),
                "credit": str(line.credit),
                "cash_activity": line.cash_activity or "",
                "type": entry.entry_type,
            }
        )

    def total(kind: str) -> Decimal:
        return money(
            sum((v for k, v in balances.items() if accounts[k].kind == kind), ZERO)
        )

    asset, liability, capital = total("asset"), total("liability"), total("equity")
    unclosed = total("income") - total("expense")
    difference = money(asset - liability - capital - unclosed)
    gross = income["financial_income"] - income["financial_cost"]
    operating = (
        gross
        + income["operating_income"]
        - income["operating_expense"]
        - income["provision"]
    )
    before_tax = operating + income["other_income"] - income["other_expense"]
    net = before_tax - income["iue"]
    disclosures = (
        await db.scalars(
            select(FinancialDisclosure)
            .where(FinancialDisclosure.year == cutoff.year)
            .order_by(FinancialDisclosure.id)
        )
    ).all()
    notes = [
        {
            "id": d.id,
            "kind": d.kind,
            "title": d.title,
            "body": d.body,
            "risk": d.risk,
            "account_id": d.account_id,
            "created_at": d.created_at.isoformat(),
        }
        for d in disclosures
    ]
    closing_cash = money(
        sum((v for k, v in balances.items() if accounts[k].is_cash), ZERO)
    )
    cash_delta = money(sum(cash.values(), ZERO))
    children: dict[int | None, list[LedgerAccount]] = defaultdict(list)
    for account in accounts.values():
        children[account.parent_id].append(account)

    def node(account: LedgerAccount) -> dict[str, Any]:
        nested = [node(child) for child in children[account.id]]
        return {
            "code": account.code,
            "name": account.name,
            "kind": account.kind,
            "balance": str(
                money(
                    balances[account.id]
                    + sum((Decimal(child["balance"]) for child in nested), ZERO)
                )
            ),
            "children": nested,
            "movements": [line for line in lines if line["account"] == account.code],
        }

    hierarchy = [node(account) for account in children[None]]
    opening_unclosed = sum(
        (
            value if accounts[id_].kind == "income" else -value
            for id_, value in initial.items()
            if accounts[id_].kind in {"income", "expense"}
        ),
        ZERO,
    )
    equity_matrix = [
        {
            "code": accounts[id_].code,
            "account": accounts[id_].name,
            "opening": str(money(initial[id_])),
            "events": {k: str(money(v)) for k, v in equity[id_].items()},
            "closing": str(money(balance)),
        }
        for id_, balance in balances.items()
        if accounts[id_].kind == "equity"
    ]
    equity_matrix.append(
        {
            "code": "RESULTADOS_NO_CERRADOS",
            "account": "Resultados pendientes de cierre patrimonial",
            "opening": str(money(opening_unclosed)),
            "events": {"result_and_closing": str(money(unclosed - opening_unclosed))},
            "closing": str(money(unclosed)),
        }
    )
    return {
        "hierarchy": hierarchy,
        "cutoff": cutoff.isoformat(),
        "period_start": start.isoformat(),
        "currency": "BOB",
        "status": "draft" if records else "missing_accounting_data",
        "regulatory_status": "Borrador técnico. Requiere plan de cuentas, revisión contable y confirmación de aplicabilidad del MCEF; no acredita cumplimiento ASFI.",
        "auditor": [n for n in notes if n["kind"] == "auditor"],
        "balance": {
            "asset": str(asset),
            "liability": str(liability),
            "equity_booked": str(capital),
            "unclosed_result": str(money(unclosed)),
            "equity_total": str(money(capital + unclosed)),
            "difference": str(difference),
            "balanced": bool(records) and difference == ZERO,
            "accounts": [
                {
                    "code": a.code,
                    "name": a.name,
                    "parent_id": a.parent_id,
                    "kind": a.kind,
                    "section": a.section,
                    "balance": str(money(balances[id_])),
                }
                for id_, a in accounts.items()
                if a.kind not in {"income", "expense"}
            ],
        },
        "income_statement": {
            "sections": {k: str(money(v)) for k, v in income.items()},
            "gross_result": str(money(gross)),
            "operating_result": str(money(operating)),
            "before_tax": str(money(before_tax)),
            "iue_recorded": str(money(income["iue"])),
            "net_result": str(money(net)),
            "operating_margin_percentage": (
                str(
                    money(
                        operating
                        * 100
                        / (income["financial_income"] + income["operating_income"])
                    )
                )
                if income["financial_income"] + income["operating_income"]
                else None
            ),
        },
        "equity_changes": equity_matrix,
        "cash_flow": {
            "opening": str(money(cash_initial)),
            "operation": str(money(cash["operation"])),
            "investment": str(money(cash["investment"])),
            "financing": str(money(cash["financing"])),
            "unclassified": str(money(cash["unclassified"])),
            "net": str(cash_delta),
            "closing": str(closing_cash),
            "difference": str(money(cash_initial + cash_delta - closing_cash)),
            "reconciled": bool(records)
            and cash_initial + cash_delta == closing_cash
            and not cash["unclassified"],
        },
        "notes": [n for n in notes if n["kind"] == "note"],
        "ledger": lines,
    }

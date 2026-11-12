"""Administrator financial changes with exact money, version checks and durable audit."""

from __future__ import annotations

import hashlib
import json
from datetime import date as Date
from decimal import Decimal
from typing import Any, Literal, cast

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, func, inspect, select, text

from app.api.v1.budget import Params
from app.core.exceptions import AppException
from app.core.security import DB, AdminUser, CurrentUser
from app.models import (
    Area,
    AuditLog,
    Budget,
    BudgetModification,
    Cuenta,
    Financier,
    Gestion,
    Movement,
    Region,
    Rubro,
)
from app.services.financial_engine import FinancialEngine

router = APIRouter(prefix="/data", tags=["Control de cambios"])
Kind = Literal["budget", "movement"]
MODELS: dict[str, type[Budget] | type[Movement]] = {
    "budget": Budget,
    "movement": Movement,
}


class RecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: int = Field(ge=1900, le=2200)
    month: int = Field(ge=0, le=12)
    region_id: int = Field(gt=0)
    area_id: int = Field(gt=0)
    financier_id: int = Field(gt=0)
    rubro_id: int = Field(gt=0)
    cuenta_id: int = Field(gt=0)
    amount: Decimal = Field(max_digits=20, decimal_places=2, allow_inf_nan=False)
    date: Date | None = None
    reference: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=4000)
    reason: str = Field(min_length=5, max_length=1000)
    expected_version: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def meaningful_reason(self) -> RecordInput:
        self.reason = self.reason.strip()
        if len(self.reason) < 5:
            raise ValueError("Indica un motivo de al menos cinco caracteres.")
        if self.date and self.date.year != self.year:
            raise ValueError("La fecha debe pertenecer a la gestión.")
        return self


class ConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=5, max_length=1000)
    confirm: Literal[True]
    expected_version: str = Field(min_length=64, max_length=64)


class RestoreInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=5, max_length=1000)
    confirm: Literal[True]
    expected_revision: int = Field(ge=0)


def snapshot(row: Any) -> dict[str, Any]:
    data = {
        column.key: getattr(row, column.key) for column in inspect(type(row)).columns
    }
    return cast(
        dict[str, Any], json.loads(json.dumps(data, default=str))
    )  # Decimal/date stay exact strings.


def version(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def allowed(user: Any, data: dict[str, Any]) -> bool:
    return all(
        getattr(user, key + "_ids") is None
        or data.get(key + "_id") in getattr(user, key + "_ids")
        for key in ("region", "area", "financier")
    )


async def lock(db: Any) -> None:
    if db.get_bind().dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(20261112)"))


async def revision(db: Any) -> int:
    return int(
        await db.scalar(
            select(func.max(AuditLog.id)).where(
                AuditLog.action.in_(["data.change", "data.restore"])
            )
        )
        or 0
    )


async def captured(db: Any, row: Any) -> dict[str, Any]:
    value = snapshot(row)
    if isinstance(row, Budget):
        value["modifications"] = [
            snapshot(m)
            for m in (
                await db.scalars(
                    select(BudgetModification).where(
                        BudgetModification.budget_id == row.id
                    )
                )
            ).all()
        ]
    return value


def audit(
    db: Any,
    user: Any,
    kind: str,
    id_: int | None,
    action: str,
    reason: str,
    before: Any,
    after: Any,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id,
            action="data.change",
            resource_type=kind,
            resource_id=str(id_),
            payload_json={
                "actor_name": user.full_name,
                "actor_email": user.email,
                "action": action,
                "reason": reason.strip(),
                "before": before,
                "after": after,
            },
        )
    )


async def existing(db: Any, user: Any, kind: Kind, id_: int) -> Any:
    model = MODELS[kind]
    row = await db.scalar(
        FinancialEngine(db, user)._apply_permissions(
            select(model).where(model.id == id_).with_for_update(), model
        )
    )
    if row is None:
        raise AppException("Registro no disponible en tu alcance.", 404)
    return row


async def validated(
    db: Any, user: Any, kind: Kind, body: RecordInput
) -> dict[str, Any]:
    if not allowed(user, body.model_dump()):
        raise AppException("Categorías fuera de tu alcance.", 403)
    for model, id_ in [
        (Gestion, body.year),
        (Region, body.region_id),
        (Area, body.area_id),
        (Financier, body.financier_id),
    ]:
        if await db.get(model, id_) is None:
            raise AppException(
                "Selecciona categorías y gestión existentes del Excel.", 422
            )
    account = await db.get(Cuenta, body.cuenta_id)
    if account is None or account.rubro_id != body.rubro_id:
        raise AppException("La cuenta no corresponde al rubro seleccionado.", 422)
    values = {
        key: getattr(body, key)
        for key in (
            "year",
            "month",
            "region_id",
            "area_id",
            "financier_id",
            "cuenta_id",
        )
    }
    if kind == "budget":
        values["initial_amount"] = body.amount
    else:
        if body.date is None:
            raise AppException("Los movimientos requieren una fecha.", 422)
        values.update(
            amount=body.amount,
            date=body.date,
            reference=body.reference,
            description=body.description,
            original_data={"origin": "administrator_change"},
        )
    return values


@router.get("/revision", summary="Versión de datos financieros")
async def get_revision(db: DB, user: CurrentUser) -> dict[str, int]:
    return {"revision": await revision(db)}


@router.get("/catalogs", summary="Categorías para cambios administrativos")
async def get_catalogs(db: DB, user: AdminUser) -> dict[str, Any]:
    result: dict[str, Any] = {
        "years": list(
            (await db.scalars(select(Gestion.year).order_by(Gestion.year.desc()))).all()
        )
    }
    categories: list[tuple[str, Any]] = [
        ("region", Region),
        ("area", Area),
        ("financier", Financier),
        ("rubro", Rubro),
        ("cuenta", Cuenta),
    ]
    for key, model in categories:
        query = select(model).order_by(model.name)
        if (
            key in {"region", "area", "financier"}
            and getattr(user, key + "_ids") is not None
        ):
            query = query.where(model.id.in_(getattr(user, key + "_ids")))
        result[key] = [
            {
                "id": item.id,
                "name": item.name,
                **({"rubro_id": item.rubro_id} if isinstance(item, Cuenta) else {}),
            }
            for item in (await db.scalars(query)).all()
        ]
    return result


@router.get(
    "/records", summary="Registros financieros editables con filtros y paginación"
)
async def records(
    params: Params, db: DB, user: AdminUser, kind: Kind = "budget"
) -> dict[str, Any]:
    model = MODELS[kind]
    engine = FinancialEngine(db, user)
    query = select(model).join(Cuenta, Cuenta.id == model.cuenta_id)
    query = engine._build_base_query(query, model, params)
    count = int(
        await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    )
    rows = (
        await db.scalars(
            query.order_by(model.id)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
    ).all()
    result = []
    for candidate in rows:
        assert isinstance(candidate, (Budget, Movement))
        row = candidate
        data = await captured(db, row)
        account = await db.get(Cuenta, row.cuenta_id)
        assert account is not None
        result.append(
            {
                **data,
                "rubro_id": account.rubro_id,
                "account_name": account.name,
                "amount": str(
                    row.initial_amount if isinstance(row, Budget) else row.amount
                ),
                "version": version(data),
            }
        )
    return {
        "rows": result,
        "total": count,
        "page": params.page,
        "revision": await revision(db),
    }


@router.post(
    "/records/{kind}", summary="Crear registro financiero con motivo obligatorio"
)
async def create(
    kind: Kind, body: RecordInput, db: DB, user: AdminUser
) -> dict[str, Any]:
    await lock(db)
    values = await validated(db, user, kind, body)
    model = MODELS[kind]
    lowest = await db.scalar(
        select(func.min(model.source_row)).where(model.year == body.year)
    )
    values["source_row"] = min(int(lowest or 0), 0) - 1
    row = model(**values)
    db.add(row)
    await db.flush()
    after = await captured(db, row)
    audit(db, user, kind, row.id, "create", body.reason, None, after)
    await db.commit()
    return {"id": row.id, "version": version(after)}


@router.put("/records/{kind}/{id_}", summary="Editar registro comprobando su versión")
async def edit(
    kind: Kind, id_: int, body: RecordInput, db: DB, user: AdminUser
) -> dict[str, Any]:
    await lock(db)
    row = await existing(db, user, kind, id_)
    before = await captured(db, row)
    if body.expected_version != version(before):
        raise AppException(
            "El registro cambió. Actualiza la lista antes de editar.", 409
        )
    for key, value in (await validated(db, user, kind, body)).items():
        setattr(row, key, value)
    await db.flush()
    after = await captured(db, row)
    audit(db, user, kind, id_, "edit", body.reason, before, after)
    await db.commit()
    return {"id": row.id, "version": version(after)}


@router.post(
    "/records/{kind}/{id_}/delete",
    summary="Eliminar con confirmación, motivo y versión",
)
async def remove(
    kind: Kind, id_: int, body: ConfirmInput, db: DB, user: AdminUser
) -> dict[str, bool]:
    if len(body.reason.strip()) < 5:
        raise AppException("Escribe un motivo válido.", 422)
    await lock(db)
    row = await existing(db, user, kind, id_)
    before = await captured(db, row)
    if body.expected_version != version(before):
        raise AppException("El registro cambió. Actualiza la lista.", 409)
    if kind == "budget":
        await db.execute(
            delete(BudgetModification).where(BudgetModification.budget_id == id_)
        )
    await db.delete(row)
    audit(db, user, kind, id_, "delete", body.reason, before, None)
    await db.commit()
    return {"ok": True}


async def history_rows(db: Any, user: Any) -> list[dict[str, Any]]:
    events = (
        await db.scalars(
            select(AuditLog)
            .where(AuditLog.action.in_(["data.change", "data.restore"]))
            .order_by(AuditLog.id.desc())
        )
    ).all()
    result = []
    for event in events:
        payload = event.payload_json
        if any(
            not allowed(user, value)
            for value in (payload.get("before"), payload.get("after"))
            if value
        ):
            continue
        if event.action == "data.restore" and any(
            getattr(user, k + "_ids") is not None
            for k in ("region", "area", "financier")
        ):
            continue
        result.append(
            {
                "id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "administrator": payload.get("actor_name"),
                "email": payload.get("actor_email"),
                "kind": event.resource_type,
                "record_id": event.resource_id,
                **payload,
            }
        )
    return result


@router.get("/history", summary="Historial de datos con valores anteriores y nuevos")
async def history(db: DB, user: AdminUser, page: int = 1) -> dict[str, Any]:
    if page < 1:
        raise AppException("Página inválida.", 422)
    items = await history_rows(db, user)
    return {
        "rows": items[(page - 1) * 30 : page * 30],
        "total": len(items),
        "revision": await revision(db),
    }


@router.get("/history/export", summary="Descargar historial completo en JSON")
async def history_export(db: DB, user: AdminUser) -> Response:
    return Response(
        json.dumps(await history_rows(db, user), ensure_ascii=False, indent=2).encode(),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="exb-historial-datos.json"'
        },
    )


async def restore_snapshot(db: Any, model: Any, data: dict[str, Any]) -> None:
    values = {key: value for key, value in data.items() if key != "modifications"}
    for key in ("initial_amount", "amount"):
        if key in values:
            values[key] = Decimal(values[key])
    if "date" in values:
        values["date"] = Date.fromisoformat(values["date"])
    row = await db.get(model, values["id"])
    if row is None:
        db.add(model(**values))
    else:
        for key, value in values.items():
            setattr(row, key, value)
    await db.flush()
    if model is Budget:
        await db.execute(
            delete(BudgetModification).where(
                BudgetModification.budget_id == values["id"]
            )
        )
        for item in data.get("modifications", []):
            await restore_snapshot(db, BudgetModification, item)


@router.post(
    "/restore", summary="Restaurar estado original conservando todo el historial"
)
async def restore(body: RestoreInput, db: DB, user: AdminUser) -> dict[str, int]:
    if any(
        getattr(user, k + "_ids") is not None for k in ("region", "area", "financier")
    ):
        raise AppException(
            "La restauración global requiere un administrador sin restricciones.", 403
        )
    if len(body.reason.strip()) < 5:
        raise AppException("Escribe un motivo válido.", 422)
    await lock(db)
    if body.expected_revision != await revision(db):
        raise AppException("Los datos cambiaron. Actualiza antes de restaurar.", 409)
    last = int(
        await db.scalar(
            select(func.max(AuditLog.id)).where(AuditLog.action == "data.restore")
        )
        or 0
    )
    events = (
        await db.scalars(
            select(AuditLog)
            .where(AuditLog.action == "data.change", AuditLog.id > last)
            .order_by(AuditLog.id.desc())
        )
    ).all()
    for event in events:
        model = MODELS[event.resource_type]
        before = event.payload_json.get("before")
        if before is not None:
            await restore_snapshot(db, model, before)
        else:
            row = await db.get(model, int(event.resource_id or "0"))
            if row is not None:
                assert isinstance(row, (Budget, Movement))
                if model is Budget:
                    await db.execute(
                        delete(BudgetModification).where(
                            BudgetModification.budget_id == row.id
                        )
                    )
                await db.delete(row)
                await db.flush()
    db.add(
        AuditLog(
            user_id=user.id,
            action="data.restore",
            resource_type="financial",
            payload_json={
                "actor_name": user.full_name,
                "actor_email": user.email,
                "action": "restore",
                "reason": body.reason.strip(),
                "restored_events": [event.id for event in events],
            },
        )
    )
    await db.commit()
    return {"restored_changes": len(events)}

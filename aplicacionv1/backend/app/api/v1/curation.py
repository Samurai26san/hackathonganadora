"""Private technical staging; predictions never validate or post financial data."""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from openpyxl import load_workbook
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.v1.data_changes import (
    MODELS,
    RecordInput,
    allowed,
    audit,
    captured,
    lock,
    validated,
)
from app.core.exceptions import AppException
from app.core.security import DB, CurrentUser
from app.models import Area, AuditLog, Cuenta, Financier, Gestion, Region, Rubro, User
from app.models.accounting import CurationBatch, CurationRow
from app.models.user import now

router = APIRouter(prefix="/curation", tags=["Curaduría técnica"])


def technical(user: CurrentUser) -> User:
    if user.role not in {"admin", "analyst", "technician"}:
        raise AppException("Se requiere rol técnico o administrador.", 403)
    return user


TechnicalUser = Annotated[User, Depends(technical)]


class BatchInput(BaseModel):
    filename: str = Field(max_length=255)
    reason: str = Field(
        default="Carga de lote en preparación", min_length=5, max_length=1000
    )
    rows: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)
    xlsx_base64: str | None = Field(default=None, max_length=14_000_000)


class RowInput(BaseModel):
    data: dict[str, Any]
    version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000, pattern=r".*\S.*")


class ActionInput(BaseModel):
    version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000, pattern=r".*\S.*")


FIELDS = {
    "kind",
    "year",
    "month",
    "date",
    "region_id",
    "area_id",
    "financier_id",
    "rubro_id",
    "cuenta_id",
    "amount",
    "reference",
    "description",
}


def normalize(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    result = {
        str(k).strip().lower(): (v.strip() if isinstance(v, str) else v)
        for k, v in data.items()
        if str(k).strip().lower() in FIELDS
    }
    issues: list[str] = []
    for key in [
        "year",
        "month",
        "region_id",
        "area_id",
        "financier_id",
        "rubro_id",
        "cuenta_id",
    ]:
        value = result.get(key)
        if value is not None and str(value).strip():
            try:
                exact = Decimal(str(value))
                if not exact.is_finite() or exact != int(exact):
                    raise ValueError()
                result[key] = int(exact)
            except (ValueError, InvalidOperation, OverflowError):
                issues.append(f"{key}: requiere un entero")
    value = result.get("date")
    if value:
        if isinstance(value, (date, datetime)):
            result["date"] = value.strftime("%Y-%m-%d")
        else:
            try:
                result["date"] = date.fromisoformat(str(value)).isoformat()
            except ValueError:
                try:
                    result["date"] = (
                        datetime.strptime(str(value), "%d/%m/%Y").date().isoformat()
                    )
                except ValueError:
                    issues.append("date: utiliza AAAA-MM-DD o DD/MM/AAAA")
    value = result.get("amount")
    if value is not None:
        cleaned = (
            re.sub(r"(?i)\b(?:BOB|Bs)\.?", "", str(value)).strip().replace(" ", "")
        )
        # A single decimal comma is unambiguous. Mixed separators require manual correction.
        if "," in cleaned and "." in cleaned:
            issues.append("amount: separadores ambiguos; usa 1234.56")
        else:
            try:
                amount = Decimal(cleaned.replace(",", "."))
                if not amount.is_finite() or amount.as_tuple().exponent < -2:
                    raise ValueError()
                result["amount"] = format(amount, ".2f")
            except (ValueError, InvalidOperation):
                issues.append("amount: importe finito con hasta dos decimales")
    required = [
        "kind",
        "year",
        "month",
        "region_id",
        "area_id",
        "financier_id",
        "rubro_id",
        "cuenta_id",
        "amount",
    ]
    if result.get("kind") == "movement":
        required.append("date")
    for key in required:
        if result.get(key) is None or result.get(key) == "":
            issues.append(f"{key}: nulo o vacío")
    if result.get("kind") not in {"budget", "movement"}:
        issues.append("kind: budget o movement")
    return result, issues


def fingerprint(data: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def out(row: CurationRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "source_row": row.source_row,
        "data": row.data,
        "original": row.original,
        "issues": row.issues,
        "prediction": row.prediction,
        "status": row.status,
        "version": row.version,
        "validated_by": row.validated_by,
        "validated_at": row.validated_at.isoformat() if row.validated_at else None,
        "target_id": row.target_id,
    }


async def get_row(db: Any, user: User, id_: int, version: int) -> CurationRow:
    row = await db.scalar(
        select(CurationRow)
        .join(CurationBatch)
        .where(CurationRow.id == id_, CurationBatch.owner_id == user.id)
        .with_for_update()
    )
    if row is None:
        raise AppException("Fila no disponible en tu espacio de trabajo.", 404)
    if row.version != version:
        raise AppException("La fila cambió. Recarga antes de continuar.", 409)
    if row.target_id is not None:
        raise AppException(
            "Fila consolidada: utiliza Control de cambios para corregirla.", 409
        )
    return row


def event(
    db: Any, user: User, row: CurationRow, action: str, reason: str, before: Any
) -> None:
    db.add(
        AuditLog(
            user_id=user.id,
            action="curation." + action,
            resource_type="curation_row",
            resource_id=str(row.id),
            payload_json={
                "actor": user.email,
                "reason": reason.strip(),
                "before": before,
                "after": out(row)
                | {"validated_at": str(row.validated_at) if row.validated_at else None},
            },
        )
    )


async def inspect_row(
    db: Any, user: User, data: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    cleaned, issues = normalize(data)
    if not issues:
        try:
            body = RecordInput.model_validate(
                {k: v for k, v in cleaned.items() if k != "kind"}
                | {"reason": "Validación técnica"}
            )
            await validated(db, user, cleaned["kind"], body)
        except (ValueError, AppException) as error:
            issues.append(getattr(error, "detail", str(error)))
    return cleaned, issues


@router.get("/catalogs")
async def categories(db: DB, user: TechnicalUser) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, model in [
        ("regiones", Region),
        ("areas", Area),
        ("financiadores", Financier),
        ("rubros", Rubro),
        ("cuentas", Cuenta),
    ]:
        query = select(model)
        dimension = {
            "regiones": "region",
            "areas": "area",
            "financiadores": "financier",
        }.get(key)
        ids = getattr(user, dimension + "_ids") if dimension else None
        if ids is not None:
            query = query.where(model.id.in_(ids))
        result[key] = [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                **({"rubro_id": r.rubro_id} if isinstance(r, Cuenta) else {}),
            }
            for r in (await db.scalars(query)).all()
        ]
    result["years"] = list(
        (await db.scalars(select(Gestion.year).order_by(Gestion.year.desc()))).all()
    )
    return result


@router.post("/batches")
async def upload(body: BatchInput, db: DB, user: TechnicalUser) -> dict[str, Any]:
    rows = body.rows
    if body.xlsx_base64:
        import zipfile

        try:
            binary = base64.b64decode(body.xlsx_base64, validate=True)
            with zipfile.ZipFile(io.BytesIO(binary)) as archive:
                if sum(z.file_size for z in archive.infolist()) > 60_000_000:
                    raise ValueError("Libro demasiado grande descomprimido")
            wb = load_workbook(io.BytesIO(binary), read_only=True, data_only=True)
            sheet = wb.active
            if sheet is None or sheet.max_column > 40:
                raise ValueError("Usa la plantilla de hasta 40 columnas")
            iterator = sheet.iter_rows(values_only=True)
            headers = [str(v or "").strip().lower() for v in next(iterator)]
            if len(set(headers)) != len(headers) or not set(headers).issubset(FIELDS):
                raise ValueError(
                    "Encabezados inválidos o repetidos; utiliza la plantilla de curaduría"
                )
            rows = []
            for cells in iterator:
                if any(v is not None for v in cells):
                    rows.append(dict(zip(headers, cells)))
                if len(rows) > 5000:
                    raise ValueError("Máximo 5000 filas por lote")
            wb.close()
        except (
            ValueError,
            binascii.Error,
            zipfile.BadZipFile,
            StopIteration,
            KeyError,
            OSError,
        ) as error:
            raise AppException(f"No se pudo leer el Excel: {error}", 422) from error
    if not rows:
        raise AppException("El lote está vacío.", 422)
    digest = fingerprint({"rows": rows})
    if await db.scalar(
        select(CurationBatch.id).where(
            CurationBatch.owner_id == user.id, CurationBatch.sha256 == digest
        )
    ):
        raise AppException(
            "Este lote ya está en tu espacio de trabajo. Abre el lote existente.", 409
        )
    batch = CurationBatch(owner_id=user.id, filename=body.filename, sha256=digest)
    db.add(batch)
    await db.flush()
    seen: set[str] = set()
    for index, source in enumerate(rows, 2):
        cleaned, issues = await inspect_row(db, user, source)
        digest = fingerprint(cleaned)
        if digest in seen:
            issues.append("Duplicado dentro del lote")
        seen.add(digest)
        original = json.loads(json.dumps(source, default=str))
        db.add(
            CurationRow(
                batch_id=batch.id,
                source_row=index,
                original=original,
                data=cleaned,
                issues=issues,
            )
        )
    db.add(
        AuditLog(
            user_id=user.id,
            action="curation.upload",
            resource_type="batch",
            resource_id=str(batch.id),
            payload_json={
                "filename": body.filename,
                "rows": len(rows),
                "reason": body.reason.strip(),
            },
        )
    )
    await db.commit()
    return {"id": batch.id, "rows": len(rows)}


@router.get("/batches")
async def batches(db: DB, user: TechnicalUser) -> list[dict[str, Any]]:
    return [
        {"id": b.id, "filename": b.filename, "created_at": b.created_at}
        for b in (
            await db.scalars(
                select(CurationBatch)
                .where(CurationBatch.owner_id == user.id)
                .order_by(CurationBatch.id.desc())
                .limit(100)
            )
        ).all()
    ]


@router.get("/batches/{batch_id}")
async def batch_rows(
    batch_id: int, db: DB, user: TechnicalUser, page: int = 1, status: str | None = None
) -> dict[str, Any]:
    if page < 1:
        raise AppException("Página inválida.", 422)
    query = (
        select(CurationRow)
        .join(CurationBatch)
        .where(CurationBatch.id == batch_id, CurationBatch.owner_id == user.id)
    )
    if status:
        query = query.where(CurationRow.status == status)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (
        await db.scalars(
            query.order_by(CurationRow.id).offset((page - 1) * 25).limit(25)
        )
    ).all()
    return {"rows": [out(r) for r in rows], "total": total, "page": page}


@router.put("/rows/{id_}")
async def edit_row(
    id_: int, body: RowInput, db: DB, user: TechnicalUser
) -> dict[str, Any]:
    if len(body.reason.strip()) < 5:
        raise AppException("Escribe un motivo de al menos cinco caracteres.", 422)
    row = await get_row(db, user, id_, body.version)
    before = out(row)
    row.data, row.issues = await inspect_row(db, user, body.data)
    row.status, row.prediction, row.validated_by, row.validated_at = (
        "pending",
        {},
        None,
        None,
    )
    row.version += 1
    event(db, user, row, "edit", body.reason, before)
    await db.commit()
    return out(row)


@router.post("/rows/{id_}/validate")
async def validate_row(
    id_: int, body: ActionInput, db: DB, user: TechnicalUser
) -> dict[str, Any]:
    if len(body.reason.strip()) < 5:
        raise AppException("Escribe un motivo de al menos cinco caracteres.", 422)
    row = await get_row(db, user, id_, body.version)
    before = out(row)
    row.data, row.issues = await inspect_row(db, user, row.data)
    siblings = (
        await db.scalars(
            select(CurationRow).where(
                CurationRow.batch_id == row.batch_id, CurationRow.id != row.id
            )
        )
    ).all()
    if any(fingerprint(s.data) == fingerprint(row.data) for s in siblings):
        row.issues = row.issues + [
            "Duplicado dentro del lote: corrige los datos antes de validar"
        ]
    if row.issues:
        raise AppException("; ".join(map(str, row.issues)), 422)
    row.status, row.validated_by, row.validated_at = "validated", user.id, now()
    row.version += 1
    event(db, user, row, "validate", body.reason, before)
    await db.commit()
    return out(row)


def tokens(data: dict[str, Any]) -> set[str]:
    return set(
        re.findall(
            r"\w+",
            (
                str(data.get("description", "")) + " " + str(data.get("reference", ""))
            ).casefold(),
        )
    )


@router.post("/rows/{id_}/predict")
async def predict_row(
    id_: int, body: ActionInput, db: DB, user: TechnicalUser
) -> dict[str, Any]:
    if len(body.reason.strip()) < 5:
        raise AppException("Escribe un motivo de al menos cinco caracteres.", 422)
    row = await get_row(db, user, id_, body.version)
    before = out(row)
    # Supervised nearest-neighbor classifier, trained only on this technician's manual labels.
    samples = (
        await db.scalars(
            select(CurationRow)
            .join(CurationBatch)
            .where(
                CurationBatch.owner_id == user.id,
                CurationRow.validated_by.is_not(None),
                CurationRow.id != id_,
            )
            .order_by(CurationRow.id.desc())
            .limit(2000)
        )
    ).all()
    source = tokens(row.data)
    candidates = [
        (len(source & tokens(s.data)) / max(1, len(source | tokens(s.data))), s)
        for s in samples
        if allowed(user, s.data)
    ]
    best = max(candidates, key=lambda pair: pair[0]) if candidates else (0.0, None)
    labels = (
        {
            k: best[1].data[k]
            for k in ("rubro_id", "cuenta_id", "region_id", "area_id", "financier_id")
            if best[1] is not None and k in best[1].data
        }
        if best[0] >= 0.25
        else {}
    )
    row.prediction = {
        "labels": labels,
        "confidence": round(best[0] * 100, 1) if labels else 0,
        "calibrated": False,
        "model": "nearest-neighbor-jaccard-v1",
        "training_rows": len(samples),
        "message": (
            "Similitud orientativa; requiere revisión y validación manual."
            if labels
            else "Sin ejemplos manuales suficientemente similares. Completa las etiquetas manualmente."
        ),
    }
    row.status, row.validated_by, row.validated_at = (
        ("predicted" if labels else "pending"),
        None,
        None,
    )
    row.version += 1
    event(db, user, row, "predict", body.reason, before)
    await db.commit()
    return out(row)


@router.post("/rows/{id_}/consolidate")
async def consolidate(
    id_: int, body: ActionInput, db: DB, user: TechnicalUser
) -> dict[str, Any]:
    await lock(db)
    if len(body.reason.strip()) < 5:
        raise AppException("Escribe un motivo de al menos cinco caracteres.", 422)
    row = await get_row(db, user, id_, body.version)
    if row.status != "validated":
        raise AppException("Valida manualmente la fila antes de consolidarla.", 422)
    kind: Literal["budget", "movement"] = row.data["kind"]
    record = RecordInput.model_validate(
        {k: v for k, v in row.data.items() if k != "kind"} | {"reason": body.reason}
    )
    values = await validated(db, user, kind, record)
    model = MODELS[kind]
    minimum = await db.scalar(
        select(func.min(model.source_row)).where(model.year == record.year)
    )
    values["source_row"] = min(int(minimum or 0), 0) - 1
    fact = model(**values)
    db.add(fact)
    await db.flush()
    audit(
        db, user, kind, fact.id, "create", body.reason, None, await captured(db, fact)
    )
    before = out(row)
    row.status, row.target_kind, row.target_id = "consolidated", kind, fact.id
    row.version += 1
    event(db, user, row, "consolidate", body.reason, before)
    await db.commit()
    return out(row)


@router.post("/template")
async def template(db: DB, user: TechnicalUser) -> Any:
    from fastapi import Response
    from openpyxl import Workbook

    wb = Workbook()
    sheet = wb.active
    assert sheet is not None
    sheet.title = "Preparación"
    columns = [
        "kind",
        "year",
        "month",
        "date",
        "region_id",
        "area_id",
        "financier_id",
        "rubro_id",
        "cuenta_id",
        "amount",
        "reference",
        "description",
    ]
    sheet.append(columns)
    help_ = wb.create_sheet("Instrucciones")
    for line in [
        "Completa Preparación con IDs del catálogo visible en Curaduría.",
        "kind: budget para presupuesto; movement para movimientos.",
        "year: gestión existente; month: 0=presupuesto anual, 1..12=mes.",
        "date: obligatorio para movimiento, AAAA-MM-DD.",
        "amount: número exacto en BOB, hasta 2 decimales; sin separadores de miles.",
        "No cambies encabezados. Máximo 5000 filas. No se consolidan filas automáticamente.",
    ]:
        help_.append([line])
    cat = await categories(db, user)
    for name in ("regiones", "areas", "financiadores", "rubros", "cuentas"):
        s = wb.create_sheet(name)
        s.append(["ID", "Código", "Nombre", "Rubro ID"])
        for item in cat[name]:
            from app.services.export_service import safe_text

            s.append(
                [
                    item["id"],
                    safe_text(item["code"]),
                    safe_text(item["name"]),
                    item.get("rubro_id", ""),
                ]
            )
    stream = io.BytesIO()
    wb.save(stream)
    return Response(
        stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="plantilla-curaduria.xlsx"'
        },
    )


@router.get("/rows/{id_}/history")
async def row_history(id_: int, db: DB, user: TechnicalUser) -> list[dict[str, Any]]:
    row = await db.scalar(
        select(CurationRow)
        .join(CurationBatch)
        .where(CurationRow.id == id_, CurationBatch.owner_id == user.id)
    )
    if row is None:
        raise AppException("Fila no disponible en tu espacio de trabajo.", 404)
    events = (
        await db.scalars(
            select(AuditLog)
            .where(
                AuditLog.resource_type == "curation_row",
                AuditLog.resource_id == str(id_),
                AuditLog.user_id == user.id,
            )
            .order_by(AuditLog.id.desc())
        )
    ).all()
    return [
        {"action": e.action, "date": e.timestamp.isoformat(), **e.payload_json}
        for e in events
    ]

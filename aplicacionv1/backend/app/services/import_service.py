"""Reconciled BD reader. Never deletes or silently replaces an existing year."""

from __future__ import annotations

import hashlib
import io
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import money
from app.core.exceptions import AppException
from app.models import (
    Area,
    Budget,
    Cuenta,
    Financier,
    Gestion,
    ImportLog,
    Movement,
    Region,
    Rubro,
)

MONTHS = {
    name: index
    for index, name in enumerate(
        [
            "PTTO",
            "ENERO",
            "FEBRERO",
            "MARZO",
            "ABRIL",
            "MAYO",
            "JUNIO",
            "JULIO",
            "AGOSTO",
            "SEPTIEMBRE",
            "OCTUBRE",
            "NOVIEMBRE",
            "DICIEMBRE",
        ]
    )
}
MONTHS["SETIEMBRE"] = 9


def read_bd(content: bytes) -> tuple[list[dict[str, Any]], int]:
    book = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    try:
        if "BD" not in book.sheetnames:
            raise AppException("El archivo debe contener la hoja BD.")
        rows = book["BD"].iter_rows(values_only=True)
        headers: list[str] | None = None
        data: list[dict[str, Any]] = []
        for number, values in enumerate(rows, 1):
            if headers is None:
                candidate = [str(value or "").strip() for value in values]
                if "presupuesto Bs" in candidate and "Ejecución" in candidate:
                    headers = candidate
                elif number > 10:
                    raise AppException("No se encontraron los encabezados de BD.")
                continue
            if not any(value is not None for value in values):
                continue
            row: dict[str, Any] = dict(zip(headers, values))
            row["source_row"] = number
            for key in ["region", "area", "fondo", "rubro", "Cuenta"]:
                if not str(row.get(key) or "").strip():
                    raise AppException(
                        f"Fila BD {number}: falta {key}; requiere validación humana."
                    )
            try:
                row["budget"] = money(row.get("presupuesto Bs"))
                row["executed"] = money(row.get("Ejecución"))
            except (InvalidOperation, ValueError, TypeError) as error:
                raise AppException(
                    f"Fila BD {number}: importe inválido; revisa la fuente."
                ) from error
            raw_month = str(row.get("mes") or "").strip().upper()
            month = MONTHS.get(raw_month)
            if month is None and raw_month.isdigit() and 0 <= int(raw_month) <= 12:
                month = int(raw_month)
            if month is None:
                raise AppException(
                    f"Fila BD {number}: mes no reconocido ({raw_month})."
                )
            row["month"] = month
            when = row.get("cfecha")
            if isinstance(when, datetime):
                row["date"] = when.date()
            elif isinstance(when, date):
                row["date"] = when
            elif when:
                raw_date = str(when).strip()
                row["date"] = (
                    datetime.strptime(raw_date, "%d/%m/%Y").date()
                    if "/" in raw_date
                    else date.fromisoformat(raw_date[:10])
                )
            else:
                row["date"] = None
            if row["executed"] and not row["date"]:
                raise AppException(
                    f"Fila BD {number}: ejecución sin fecha, no se ingiere."
                )
            data.append(row)
        years: Counter[int] = Counter(row["date"].year for row in data if row["date"])
        if len(years) != 1:
            raise AppException(
                "BD debe identificar exactamente una gestión mediante sus fechas."
            )
        return data, next(iter(years))
    finally:
        book.close()


def preview(content: bytes) -> dict[str, Any]:
    rows, year = read_bd(content)
    return {
        "year": year,
        "source_rows": len(rows),
        "movement_rows": sum(bool(r["date"]) for r in rows),
        "budget": str(sum((r["budget"] for r in rows), Decimal("0.00"))),
        "executed": str(sum((r["executed"] for r in rows), Decimal("0.00"))),
        "sha256": hashlib.sha256(content).hexdigest(),
        "status": "preview_only",
    }


async def ingest_bd(db: AsyncSession, path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    report = preview(content)
    if await db.scalar(select(ImportLog).where(ImportLog.sha256 == report["sha256"])):
        return {**report, "status": "already_imported"}
    rows, year = read_bd(content)
    if await db.get(Gestion, year):
        raise AppException(
            "La gestión ya existe. No se reemplaza información financiera automáticamente."
        )
    db.add(Gestion(year=year, source_name=path.name, source_sha256=report["sha256"]))
    await db.flush()
    catalogs: dict[tuple[str, str, int], int] = {}
    for row in rows:
        ids: dict[str, int] = {}
        mappings: list[
            tuple[
                str,
                str,
                type[Region]
                | type[Area]
                | type[Financier]
                | type[Rubro]
                | type[Cuenta],
            ]
        ] = [
            ("region", "region", Region),
            ("area", "area", Area),
            ("financier", "fondo", Financier),
            ("rubro", "rubro", Rubro),
            ("cuenta", "Cuenta", Cuenta),
        ]
        for name, field, table in mappings:
            value = str(row[field]).strip()
            parent = ids.get("rubro", 0) if name == "cuenta" else 0
            key = (name, value, parent)
            if key not in catalogs:
                query = select(table).where(table.name == value)
                if table is Cuenta:
                    query = query.where(Cuenta.rubro_id == parent)
                item = await db.scalar(query)
                if item is None:
                    args: dict[str, Any] = {
                        "code": value.split(" ", 1)[0],
                        "name": value,
                    }
                    if table is Cuenta:
                        args["rubro_id"] = parent
                    item = table(**args)
                    db.add(item)
                    await db.flush()
                assert isinstance(item, (Region, Area, Financier, Rubro, Cuenta))
                catalogs[key] = item.id
            ids[name] = catalogs[key]
        dimensions = dict(
            year=year,
            month=row["month"],
            region_id=ids["region"],
            area_id=ids["area"],
            financier_id=ids["financier"],
            cuenta_id=ids["cuenta"],
            source_row=row["source_row"],
        )
        db.add(Budget(**dimensions, initial_amount=row["budget"]))
        if row["date"]:
            original = {
                str(k): str(v) if v is not None else None for k, v in row.items()
            }
            db.add(
                Movement(
                    **dimensions,
                    date=row["date"],
                    amount=row["executed"],
                    reference=str(row.get("numero") or ""),
                    description=str(row.get("ref") or ""),
                    accounting_code=str(row.get("codigo") or ""),
                    movement_type=str(row.get("tipo") or ""),
                    original_data=original,
                )
            )
    db.add(ImportLog(sha256=report["sha256"], source_name=path.name, rows=len(rows)))
    await db.flush()
    return report

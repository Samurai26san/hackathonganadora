"""Bootstrap users/dictionary and ingest the supplied real workbook idempotently."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionFactory
from app.core.security import hash_password
from app.models import DataDictionary, User
from app.services.import_service import ingest_bd


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", type=Path)
    parser.add_argument("--admin-email", default="admin@exb.demo")
    args = parser.parse_args()
    async with SessionFactory() as db:
        demo = get_settings().auth_mode == "demo"
        accounts = (
            [
                (args.admin_email, "Administración ExB", "admin"),
                ("tecnico@exb.demo", "Técnico ExB", "analyst"),
            ]
            if demo
            else [(args.admin_email, "Administración ExB", "admin")]
        )
        if not demo and args.admin_email.endswith(".demo"):
            raise SystemExit(
                "Para OIDC indica --admin-email con la cuenta institucional real."
            )
        for email, name, role in accounts:
            if not await db.scalar(select(User).where(User.email == email)):
                db.add(
                    User(
                        email=email,
                        full_name=name,
                        role=role,
                        password_hash=hash_password("Demo2026!") if demo else None,
                        region_ids=None,
                        area_ids=None,
                        financier_ids=None,
                    )
                )
        definitions = [
            (
                "presupuesto vigente",
                "initial_amount",
                "budgets",
                "Suma de presupuesto Bs de BD más modificaciones autorizadas.",
                ["presupuesto", "vigente"],
            ),
            (
                "ejecutado",
                "amount",
                "movements",
                "Columna Ejecución de BD sin restar haber nuevamente.",
                ["ejecución", "gasto"],
            ),
            (
                "saldo",
                "balance",
                "derived",
                "Vigente menos ejecutado; calculado exclusivamente por el motor financiero.",
                ["restante", "disponible"],
            ),
            (
                "financiador",
                "financier_id",
                "budgets",
                "Etiqueta original fondo de BD.",
                ["fuente", "fondo"],
            ),
            (
                "PTTO",
                "month",
                "budgets",
                "Mes cero: presupuesto sin programación mensual; nunca se distribuye artificialmente.",
                ["sin programar"],
            ),
        ]
        for term, column, table, description, synonyms in definitions:
            if not await db.scalar(
                select(DataDictionary).where(DataDictionary.termino_usuario == term)
            ):
                db.add(
                    DataDictionary(
                        termino_usuario=term,
                        columna_canonica=column,
                        tabla_origen=table,
                        descripcion=description,
                        sinonimos_json=synonyms,
                    )
                )
        await db.flush()
        if args.excel:
            print(await ingest_bd(db, args.excel))
        await db.commit()
        print("Cuentas y diccionario inicializados. No se crearon gestiones ficticias.")


if __name__ == "__main__":
    asyncio.run(main())

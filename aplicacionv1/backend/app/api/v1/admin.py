"""Audited administration; no financial write operations are exposed."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.exceptions import AppException, NotFoundException
from app.core.security import DB, AdminUser, CurrentUser, user_out
from app.models import AuditLog, DataDictionary, User
from app.schemas.chat import SearchKnowledgeParams
from app.services.import_service import preview
from app.services.rag_service import RAGService

router = APIRouter(tags=["Administración"])


class DictionaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    termino_usuario: str = Field(min_length=1, max_length=150)
    columna_canonica: str = Field(min_length=1, max_length=150)
    tabla_origen: str = Field(min_length=1, max_length=150)
    descripcion: str = Field(min_length=1, max_length=2000)
    sinonimos_json: list[str] = Field(default_factory=list)
    activo: bool = True


class KnowledgeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=10, max_length=200_000)
    source_type: Literal["manual", "regulation", "law", "classifier", "faq"]
    source_id: str = Field(min_length=1, max_length=255)
    source_title: str = Field(min_length=1, max_length=500)
    tags: list[str] = Field(default_factory=list)


class UserInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=1, max_length=180)
    role: Literal["viewer", "analyst", "admin"] = "viewer"
    region_ids: list[int] | None = Field(default_factory=lambda: [])
    area_ids: list[int] | None = None
    financier_ids: list[int] | None = None
    is_active: bool = True


def dictionary_out(row: DataDictionary) -> dict[str, Any]:
    return {
        "id": row.id,
        "version": row.version,
        **{key: getattr(row, key) for key in DictionaryInput.model_fields},
    }


@router.get(
    "/dictionary",
    summary="Diccionario institucional",
    description="Lista las definiciones institucionales para revisión administrativa.",
)
async def dictionary(db: DB, user: AdminUser) -> list[dict[str, Any]]:
    return [
        dictionary_out(row) for row in (await db.scalars(select(DataDictionary))).all()
    ]


@router.post(
    "/dictionary",
    summary="Agregar término",
    description="Solo administración; se incluye dinámicamente en el prompt de Juku.",
)
async def add_dictionary(
    body: DictionaryInput, db: DB, user: AdminUser
) -> dict[str, Any]:
    if await db.scalar(
        select(DataDictionary).where(
            DataDictionary.termino_usuario == body.termino_usuario
        )
    ):
        raise AppException("El término ya existe.", 409)
    row = DataDictionary(**body.model_dump())
    db.add(row)
    await db.flush()
    db.add(
        AuditLog(user_id=user.id, action="dictionary.create", resource_id=str(row.id))
    )
    return dictionary_out(row)


@router.put(
    "/dictionary/{id_}",
    summary="Actualizar término",
    description="Incrementa la versión y registra la modificación.",
)
async def edit_dictionary(
    id_: int, body: DictionaryInput, db: DB, user: AdminUser
) -> dict[str, Any]:
    row = await db.get(DataDictionary, id_)
    if row is None:
        raise NotFoundException()
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.version += 1
    db.add(AuditLog(user_id=user.id, action="dictionary.update", resource_id=str(id_)))
    return dictionary_out(row)


@router.delete(
    "/dictionary/{id_}",
    summary="Desactivar término",
    description="Borrado lógico que conserva trazabilidad y versiones.",
)
async def delete_dictionary(id_: int, db: DB, user: AdminUser) -> dict[str, bool]:
    row = await db.get(DataDictionary, id_)
    if row is None:
        raise NotFoundException()
    row.activo = False
    row.version += 1
    db.add(
        AuditLog(user_id=user.id, action="dictionary.deactivate", resource_id=str(id_))
    )
    return {"ok": True}


@router.post(
    "/knowledge/ingest",
    summary="Ingerir documento normativo",
    description="Fragmenta, obtiene embeddings BGE-m3 y registra su fuente; no acepta cambios financieros.",
)
async def ingest(
    body: KnowledgeInput, request: Request, db: DB, user: AdminUser
) -> dict[str, int]:
    chunks = await RAGService(db, request.app.state.http).ingest_text(
        **body.model_dump()
    )
    db.add(
        AuditLog(user_id=user.id, action="knowledge.ingest", resource_id=body.source_id)
    )
    return {"chunks": len(chunks)}


@router.post(
    "/knowledge/search",
    summary="Buscar evidencia institucional",
    description="Búsqueda híbrida con fuentes, tipos y umbral de similitud.",
)
async def search(
    body: SearchKnowledgeParams, request: Request, db: DB, user: CurrentUser
) -> dict[str, Any]:
    hits = await RAGService(db, request.app.state.http).search(
        body.query, body.top_k, body.source_types
    )
    db.add(
        AuditLog(
            user_id=user.id,
            action="knowledge.search",
            payload_json={"source_types": body.source_types},
        )
    )
    return {"results": hits}


@router.post(
    "/imports/preview",
    summary="Validar Excel BD sin aplicarlo",
    description="Fase 1 es de lectura financiera; valida hasta 20 MB y muestra totales sin escribir presupuestos.",
)
async def import_preview(
    db: DB, user: AdminUser, file: UploadFile = File(...)
) -> dict[str, Any]:
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise AppException("El archivo supera 20 MB.", 413)
    result = preview(content)
    db.add(AuditLog(user_id=user.id, action="imports.preview", payload_json=result))
    return result


@router.get(
    "/users",
    summary="Usuarios y alcances",
    description="Solo administración puede inspeccionar las cuentas institucionales.",
)
async def users(db: DB, user: AdminUser) -> list[dict[str, object]]:
    return [
        {**user_out(row), "is_active": row.is_active}
        for row in (await db.scalars(select(User))).all()
    ]


@router.post(
    "/users",
    summary="Habilitar cuenta institucional",
    description="Provisiona una cuenta para acceso OIDC con rol y alcance explícitos.",
)
async def add_user(body: UserInput, db: DB, user: AdminUser) -> dict[str, object]:
    if await db.scalar(select(User).where(User.email == body.email.lower())):
        raise AppException("La cuenta ya existe.", 409)
    row = User(**{**body.model_dump(), "email": body.email.lower()})
    db.add(row)
    await db.flush()
    db.add(AuditLog(user_id=user.id, action="users.create", resource_id=row.id))
    return user_out(row)


@router.put(
    "/users/{user_id}",
    summary="Actualizar permisos",
    description="No permite desactivar ni quitar el rol a la propia cuenta administradora.",
)
async def edit_user(
    user_id: str, body: UserInput, db: DB, user: AdminUser
) -> dict[str, object]:
    row = await db.get(User, user_id)
    if row is None:
        raise NotFoundException()
    if row.id == user.id and (body.role != "admin" or not body.is_active):
        raise AppException("No puedes quitar tu propio acceso administrativo.")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.add(AuditLog(user_id=user.id, action="users.update", resource_id=row.id))
    return user_out(row)


@router.get(
    "/audit/logs",
    summary="Auditoría",
    description="Últimas 200 acciones, sin contraseñas, tokens ni contenido completo del chat.",
)
async def audit(db: DB, user: AdminUser) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(200))
    ).all()
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "action": row.action,
            "resource": row.resource_type,
            "status": row.status,
            "timestamp": row.timestamp.isoformat(),
        }
        for row in rows
    ]

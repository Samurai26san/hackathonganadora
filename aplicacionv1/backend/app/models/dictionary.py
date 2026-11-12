"""Institution-owned dictionary injected at each conversation turn."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataDictionary(Base):
    __tablename__ = "data_dictionary"
    id: Mapped[int] = mapped_column(primary_key=True)
    termino_usuario: Mapped[str] = mapped_column(String(150), unique=True)
    columna_canonica: Mapped[str] = mapped_column(String(150))
    tabla_origen: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str] = mapped_column(Text)
    sinonimos_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

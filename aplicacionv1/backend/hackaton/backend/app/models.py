"""Modelo de datos normalizado del sistema de control presupuestario.

Catálogos: financiadores, regiones, areas, rubros, cuentas.
Hechos:    presupuestos (asignación anual), modificaciones, movimientos (ejecución).
Soporte:   usuarios, tipos_cambio, importaciones, auditoria.
"""
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

Monto = Numeric(18, 2)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(200))
    # admin: usuarios y auditoría | validador: carga y validación de datos | consulta: dashboard y reportes
    rol: Mapped[str] = mapped_column(String(20), default="consulta")
    activo: Mapped[bool] = mapped_column(default=True)


# ---------- Catálogos ----------
class Financiador(Base):
    __tablename__ = "financiadores"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(80), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))


class Region(Base):
    __tablename__ = "regiones"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(80), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))


class Area(Base):
    __tablename__ = "areas"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(80), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))


class Rubro(Base):
    __tablename__ = "rubros"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(80), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))
    cuentas: Mapped[list["Cuenta"]] = relationship(back_populates="rubro")


class Cuenta(Base):
    __tablename__ = "cuentas"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(80), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    rubro_id: Mapped[int] = mapped_column(ForeignKey("rubros.id"))
    rubro: Mapped[Rubro] = relationship(back_populates="cuentas")


# ---------- Hechos ----------
class Presupuesto(Base):
    """Presupuesto asignado a una combinación cuenta/financiador/área/región en una gestión.

    mes = 0 corresponde al presupuesto aún no programado por mes (filas PTTO del archivo
    contable); 1..12 al presupuesto programado para ese mes.
    """
    __tablename__ = "presupuestos"
    __table_args__ = (UniqueConstraint("gestion", "mes", "cuenta_id", "financiador_id", "area_id", "region_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    gestion: Mapped[int] = mapped_column(index=True)
    mes: Mapped[int] = mapped_column(default=0, index=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"))
    financiador_id: Mapped[int] = mapped_column(ForeignKey("financiadores.id"))
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"))
    region_id: Mapped[int] = mapped_column(ForeignKey("regiones.id"))
    monto_inicial: Mapped[float] = mapped_column(Monto, default=0)
    modificaciones: Mapped[list["Modificacion"]] = relationship(back_populates="presupuesto")


class Modificacion(Base):
    """Incrementos (+) o reducciones (-) al presupuesto inicial."""
    __tablename__ = "modificaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuestos.id"))
    fecha: Mapped[date] = mapped_column(Date)
    monto: Mapped[float] = mapped_column(Monto)
    tipo: Mapped[str] = mapped_column(String(30), default="traspaso")
    resolucion: Mapped[str | None] = mapped_column(String(80))
    presupuesto: Mapped[Presupuesto] = relationship(back_populates="modificaciones")


class Movimiento(Base):
    """Registro de ejecución tomado del sistema contable."""
    __tablename__ = "movimientos"
    id: Mapped[int] = mapped_column(primary_key=True)
    gestion: Mapped[int] = mapped_column(index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    mes: Mapped[int] = mapped_column(index=True)
    comprobante: Mapped[str | None] = mapped_column(String(40))
    descripcion: Mapped[str | None] = mapped_column(Text)
    cuenta_contable: Mapped[str | None] = mapped_column(String(150))  # código y nombre del plan de cuentas
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"), index=True)
    financiador_id: Mapped[int] = mapped_column(ForeignKey("financiadores.id"), index=True)
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"), index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regiones.id"), index=True)
    moneda: Mapped[str] = mapped_column(String(3), default="BOB")
    monto_original: Mapped[float] = mapped_column(Monto)
    tipo_cambio: Mapped[float] = mapped_column(Numeric(10, 4), default=1)
    monto_bs: Mapped[float] = mapped_column(Monto)
    monto_usd: Mapped[float | None] = mapped_column(Monto)
    importacion_id: Mapped[int | None] = mapped_column(ForeignKey("importaciones.id"))


class TipoCambio(Base):
    __tablename__ = "tipos_cambio"
    __table_args__ = (UniqueConstraint("fecha", "moneda"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(3))
    valor: Mapped[float] = mapped_column(Numeric(10, 4))


class Importacion(Base):
    __tablename__ = "importaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    archivo: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(20))  # movimientos | presupuestos
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    filas_ok: Mapped[int] = mapped_column(default=0)
    filas_error: Mapped[int] = mapped_column(default=0)
    errores: Mapped[list | None] = mapped_column(JSON)
    resumen: Mapped[dict | None] = mapped_column(JSON)  # gestión, totales de control y advertencias


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    usuario: Mapped[str | None] = mapped_column(String(50))
    accion: Mapped[str] = mapped_column(String(50))
    detalle: Mapped[dict | None] = mapped_column(JSON)


class FilaPendiente(Base):
    """Fila importada con etiquetas faltantes: queda en revisión hasta que el admin la valide.

    etiquetas: valores de la fila (None en los faltantes) para fondo/rubro/cuenta/area/region.
    prediccion: {campo: {"valor", "confianza", "alternativas"}} propuesta por el modelo.
    valores: etiquetas finales con que se validó (originales + predichas o corregidas).
    """
    __tablename__ = "filas_pendientes"
    id: Mapped[int] = mapped_column(primary_key=True)
    importacion_id: Mapped[int | None] = mapped_column(ForeignKey("importaciones.id"))
    gestion: Mapped[int] = mapped_column(index=True)
    fila: Mapped[int]  # número de fila en el Excel
    mes: Mapped[int]
    fecha: Mapped[date | None] = mapped_column(Date)
    comprobante: Mapped[str | None] = mapped_column(String(40))
    descripcion: Mapped[str | None] = mapped_column(Text)
    cuenta_contable: Mapped[str | None] = mapped_column(String(150))
    presupuesto: Mapped[float] = mapped_column(Monto, default=0)
    ejecucion: Mapped[float] = mapped_column(Monto, default=0)
    tipo_cambio: Mapped[float] = mapped_column(Numeric(10, 4), default=1)
    monto_usd: Mapped[float | None] = mapped_column(Monto)
    etiquetas: Mapped[dict] = mapped_column(JSON)
    faltantes: Mapped[list] = mapped_column(JSON)
    prediccion: Mapped[dict | None] = mapped_column(JSON)
    valores: Mapped[dict | None] = mapped_column(JSON)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", index=True)  # pendiente | validada | descartada
    origen: Mapped[str | None] = mapped_column(String(20))  # prediccion | manual | mixto
    validado_por: Mapped[str | None] = mapped_column(String(50))
    validado_en: Mapped[datetime | None] = mapped_column(DateTime)

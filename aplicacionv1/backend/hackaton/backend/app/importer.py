"""Importación de archivos Excel exportados del sistema contable.

Los encabezados se normalizan (minúsculas, sin tildes) y se aceptan sinónimos,
de modo que se puede adaptar a la hoja original sin tocar el código: basta con
agregar el nombre de columna a SINONIMOS.
"""
import unicodedata
from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

from .models import Area, Cuenta, Financiador, Importacion, Movimiento, Presupuesto, Region, Rubro, TipoCambio

SINONIMOS = {
    "gestion": ["gestion", "anio", "ano", "year"],
    "fecha": ["fecha", "fecha comprobante", "fecha_registro"],
    "comprobante": ["comprobante", "nro comprobante", "cbte", "n comprobante"],
    "descripcion": ["descripcion", "glosa", "detalle", "concepto"],
    "rubro_codigo": ["rubro_codigo", "cod rubro", "codigo rubro"],
    "rubro": ["rubro", "nombre rubro"],
    "cuenta_codigo": ["cuenta_codigo", "cod cuenta", "codigo cuenta", "partida"],
    "cuenta": ["cuenta", "nombre cuenta", "descripcion cuenta"],
    "financiador_codigo": ["financiador_codigo", "cod financiador", "fuente", "codigo fuente"],
    "financiador": ["financiador", "nombre financiador", "fuente de financiamiento", "organismo"],
    "area_codigo": ["area_codigo", "cod area"],
    "area": ["area", "unidad", "nombre area"],
    "region_codigo": ["region_codigo", "cod region"],
    "region": ["region", "regional", "departamento"],
    "moneda": ["moneda"],
    "monto": ["monto", "importe", "debe", "ejecutado", "monto_inicial", "presupuesto", "monto bs"],
}
TC_DEFECTO = {"BOB": 1.0, "USD": 6.96}

OBLIG_MOV = ["fecha", "cuenta_codigo", "financiador", "area", "region", "monto"]
OBLIG_PPTO = ["gestion", "cuenta_codigo", "financiador", "area", "region", "monto"]


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
    return " ".join(s.replace("_", " ").replace(".", " ").split())


def _mapear_encabezados(fila) -> dict[str, int]:
    norm = [_norm(c) for c in fila]
    out = {}
    for campo, sinos in SINONIMOS.items():
        for s in sinos:
            s = _norm(s)
            if s in norm:
                out[campo] = norm.index(s)
                break
    return out


class Catalogos:
    """Cache de catálogos con alta automática de valores nuevos."""

    def __init__(self, db: Session):
        self.db = db
        self.cache: dict[type, dict[str, object]] = {}

    def obtener(self, modelo, codigo, nombre, **extra):
        codigo = str(codigo or nombre).strip()[:80]
        if modelo not in self.cache:
            self.cache[modelo] = {o.codigo: o for o in self.db.query(modelo).all()}
        cache = self.cache[modelo]
        obj = cache.get(codigo)
        if obj is None:
            obj = modelo(codigo=codigo, nombre=str(nombre or codigo).strip(), **extra)
            self.db.add(obj)
            self.db.flush()
            cache[codigo] = obj
        return obj


def _fecha(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Fecha inválida: {v}")


def _tipo_cambio(db: Session, fecha: date, moneda: str) -> float:
    if moneda == "BOB":
        return 1.0
    tc = (
        db.query(TipoCambio).filter(TipoCambio.moneda == moneda, TipoCambio.fecha <= fecha)
        .order_by(TipoCambio.fecha.desc()).first()
    )
    return float(tc.valor) if tc else TC_DEFECTO.get(moneda, 1.0)


def importar(db: Session, contenido: bytes, archivo: str, tipo: str, usuario_id: int | None,
             gestion: int | None = None) -> Importacion:
    wb = load_workbook(BytesIO(contenido), read_only=True, data_only=True)
    # Si el libro trae la base del sistema contable (hoja BD) se usa ese formato
    encontrado = _buscar_hoja_contable(wb)
    if encontrado:
        from .importer_contable import importar_contable
        return importar_contable(db, *encontrado, archivo=archivo, usuario_id=usuario_id, gestion=gestion)

    ws = wb.active
    filas = ws.iter_rows(values_only=True)

    # Busca la fila de encabezados dentro de las primeras 15 filas
    oblig = OBLIG_MOV if tipo == "movimientos" else OBLIG_PPTO
    mapa, encabezado_ok = {}, False
    for _ in range(15):
        fila = next(filas, None)
        if fila is None:
            break
        mapa = _mapear_encabezados(fila)
        if all(c in mapa for c in oblig):
            encabezado_ok = True
            break
    if not encabezado_ok:
        faltan = [c for c in oblig if c not in mapa]
        raise ValueError(f"No se encontraron las columnas requeridas: {', '.join(faltan)}")

    imp = Importacion(archivo=archivo, tipo=tipo, usuario_id=usuario_id)
    db.add(imp)
    db.flush()
    cat = Catalogos(db)
    ok, errores = 0, []

    for n, fila in enumerate(filas, start=2):
        if not fila or all(v is None for v in fila):
            continue
        g = lambda campo: fila[mapa[campo]] if campo in mapa and mapa[campo] < len(fila) else None
        try:
            rubro = cat.obtener(Rubro, g("rubro_codigo") or str(g("cuenta_codigo"))[:1], g("rubro") or f"Rubro {str(g('cuenta_codigo'))[:1]}")
            cuenta = cat.obtener(Cuenta, g("cuenta_codigo"), g("cuenta"), rubro_id=rubro.id)
            fin = cat.obtener(Financiador, g("financiador_codigo"), g("financiador"))
            area = cat.obtener(Area, g("area_codigo"), g("area"))
            reg = cat.obtener(Region, g("region_codigo"), g("region"))
            monto = float(g("monto"))
            if tipo == "movimientos":
                f = _fecha(g("fecha"))
                moneda = (str(g("moneda") or "BOB").strip().upper()[:3]).replace("BS", "BOB")
                tc = _tipo_cambio(db, f, moneda)
                db.add(Movimiento(
                    gestion=int(g("gestion") or f.year), fecha=f, mes=f.month, comprobante=g("comprobante"),
                    descripcion=g("descripcion"), cuenta_id=cuenta.id, financiador_id=fin.id, area_id=area.id,
                    region_id=reg.id, moneda=moneda, monto_original=monto, tipo_cambio=tc,
                    monto_bs=round(monto * tc, 2), importacion_id=imp.id,
                ))
            else:
                clave = dict(gestion=int(g("gestion")), cuenta_id=cuenta.id, financiador_id=fin.id, area_id=area.id, region_id=reg.id)
                p = db.query(Presupuesto).filter_by(**clave).first()
                if p:
                    p.monto_inicial = monto
                else:
                    db.add(Presupuesto(**clave, monto_inicial=monto))
                db.flush()
            ok += 1
        except Exception as e:  # una fila mala no detiene la importación
            errores.append({"fila": n, "error": str(e)})

    imp.filas_ok, imp.filas_error, imp.errores = ok, len(errores), errores[:200]
    db.commit()
    return imp


COLUMNAS_CONTABLE = {"mes", "fondo", "rubro", "cuenta", "area", "region", "ejecucion", "presupuesto bs"}


def _buscar_hoja_contable(wb):
    """Devuelve (filas, mapa_columnas) si alguna hoja tiene el formato de la base contable."""
    hojas = sorted(wb.worksheets, key=lambda w: w.title.strip().upper() != "BD")
    for ws in hojas:
        filas = ws.iter_rows(values_only=True)
        for _ in range(15):
            fila = next(filas, None)
            if fila is None:
                break
            norm = [_norm(c) for c in fila]
            if COLUMNAS_CONTABLE <= set(norm):
                return filas, {n: i for i, n in enumerate(norm) if n}
    return None


def plantilla(tipo: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    if tipo == "movimientos":
        ws.append(["fecha", "comprobante", "descripcion", "rubro_codigo", "rubro", "cuenta_codigo", "cuenta",
                   "financiador_codigo", "financiador", "area_codigo", "area", "region_codigo", "region", "moneda", "monto"])
        ws.append(["15/03/2026", "CBT-0001", "Compra de material", "20000", "Servicios no personales", "21100",
                   "Comunicaciones", "F01", "Tesoro General", "A01", "Administración", "R01", "La Paz", "BOB", 1500.50])
    else:
        ws.append(["gestion", "rubro_codigo", "rubro", "cuenta_codigo", "cuenta", "financiador_codigo", "financiador",
                   "area_codigo", "area", "region_codigo", "region", "monto_inicial"])
        ws.append([2026, "20000", "Servicios no personales", "21100", "Comunicaciones", "F01", "Tesoro General",
                   "A01", "Administración", "R01", "La Paz", 50000])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()

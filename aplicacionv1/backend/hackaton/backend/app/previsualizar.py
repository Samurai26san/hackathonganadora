"""Vista previa de un Excel antes de importarlo ("cuaderno" con una pestaña por hoja).

No guarda nada: lee el libro, identifica qué es cada hoja (base contable, tabla dinámica,
plantilla…) y, para la base contable, calcula lo que pasaría al importarla: gestión,
totales, filas incompletas por campo y si reemplazaría datos ya cargados.
"""
from collections import Counter
from datetime import date, datetime
from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from .importer import COLUMNAS_CONTABLE, OBLIG_MOV, OBLIG_PPTO, _mapear_encabezados, _norm
from .importer_contable import _leer_fila
from .models import FilaPendiente, Movimiento, Presupuesto

MUESTRA = 100        # filas que se envían por hoja
MAX_COLUMNAS = 30
MAX_INCOMPLETAS = 300

# Columna de la base contable -> significado en el sistema
SIGNIFICADO = {
    "mes": "Mes", "codigo": "Cuenta contable (código)", "nombre": "Cuenta contable (nombre)", "cfecha": "Fecha",
    "tipo": "Tipo de comprobante", "numero": "N° comprobante", "region": "Región", "ref": "Glosa",
    "ejecucion": "Ejecución (Bs)", "haber": "Haber (resta)", "dsus": "Ejecución (USD)", "hsus": "Haber (USD)",
    "tasa": "Tipo de cambio", "fondo": "Financiador", "rubro": "Rubro", "cuenta": "Cuenta", "area": "Área",
    "presupuesto bs": "Presupuesto (Bs)",
}
ETIQUETAS = {"fondo": "Financiador", "rubro": "Rubro", "cuenta": "Cuenta", "area": "Área", "region": "Región"}


def _valor(v):
    if isinstance(v, datetime):
        return v.date().isoformat() if v.time() == datetime.min.time() else v.isoformat(sep=" ")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float):
        return round(v, 2)
    return v


def _recortar(fila, n):
    return [_valor(v) for v in list(fila)[:n]]


def _clasificar(encabezado_norm: list[str], titulo: str) -> tuple[str, str]:
    conjunto = set(encabezado_norm)
    if COLUMNAS_CONTABLE <= conjunto:
        return "base", "Base contable"
    if "etiquetas de fila" in conjunto:
        return "pivot", "Tabla dinámica (referencia)"
    if titulo.startswith("_"):
        return "auxiliar", "Hoja auxiliar"
    mapa = _mapear_encabezados(encabezado_norm)
    if all(c in mapa for c in OBLIG_MOV):
        return "plantilla", "Plantilla de movimientos"
    if all(c in mapa for c in OBLIG_PPTO):
        return "plantilla", "Plantilla de presupuesto"
    return "otra", "No reconocida"


def previsualizar(db: Session, contenido: bytes, archivo: str, gestion: int | None = None) -> dict:
    try:
        wb = load_workbook(BytesIO(contenido), read_only=True, data_only=True)
    except Exception:
        raise ValueError("El archivo no es un Excel .xlsx válido")

    hojas, base = [], None
    for ws in wb.worksheets:
        filas = [f for f in ws.iter_rows(values_only=True)]
        # Encabezado: la fila con más textos entre las primeras 15
        candidatas = [(sum(isinstance(c, str) and c.strip() != "" for c in f), i) for i, f in enumerate(filas[:15])]
        idx_enc = max(candidatas, default=(0, 0))[1]
        encabezado = list(filas[idx_enc]) if filas else []
        norm = [_norm(c) for c in encabezado]
        tipo, tipo_texto = _clasificar(norm, ws.title)
        if tipo == "base":
            idx_enc = next(i for i, f in enumerate(filas[:15]) if COLUMNAS_CONTABLE <= {_norm(c) for c in f})
            encabezado = list(filas[idx_enc])
            norm = [_norm(c) for c in encabezado]
        # Columnas con datos (descarta columnas vacías del final)
        ancho = max((max((i + 1 for i, c in enumerate(f) if c is not None), default=0) for f in filas), default=0)
        ancho = min(ancho, MAX_COLUMNAS)
        datos = [(idx_enc + 2 + i, f) for i, f in enumerate(filas[idx_enc + 1:]) if any(c is not None for c in f)]
        hoja = {
            "nombre": ws.title,
            "tipo": tipo,
            "tipo_texto": tipo_texto,
            "importable": tipo == "base",
            "fila_encabezado": idx_enc + 1,
            "total_filas": len(datos),
            "columnas": [
                {"nombre": "" if c is None else str(c), "significado": SIGNIFICADO.get(norm[i]) if tipo == "base" else None}
                for i, c in enumerate(encabezado[:ancho])
            ] + [{"nombre": "", "significado": None}] * max(0, ancho - len(encabezado)),
            "muestra": [{"fila": n, "valores": _recortar(f, ancho)} for n, f in datos[:MUESTRA]],
        }
        if tipo == "base" and base is None:
            base = (hoja, datos, {n: i for i, n in enumerate(norm) if n})
        hojas.append(hoja)

    resultado = {"archivo": archivo, "hojas": hojas, "hoja_importable": None, "analisis": None}
    if base is None:
        resultado["mensaje"] = ("No se encontró una hoja con el formato de la base contable "
                                f"(columnas: {', '.join(sorted(COLUMNAS_CONTABLE))}).")
        return resultado

    hoja, datos, col = base
    resultado["hoja_importable"] = hoja["nombre"]
    resultado["analisis"] = _analizar(db, datos, col, gestion)
    # Marca en la muestra las celdas faltantes, y añade las filas incompletas que no entraron en la muestra
    inc = {d["fila"]: d["faltantes"] for d in resultado["analisis"].pop("_incompletas")}
    posicion = {c: col[c] for c in ETIQUETAS if c in col}
    for m in hoja["muestra"]:
        m["faltantes"] = [posicion[c] for c in inc.get(m["fila"], [])]
    en_muestra = {m["fila"] for m in hoja["muestra"]}
    ancho = len(hoja["columnas"])
    hoja["incompletas"] = [
        {"fila": n, "valores": _recortar(f, ancho), "faltantes": [posicion[c] for c in inc[n]]}
        for n, f in datos if n in inc
    ][:MAX_INCOMPLETAS]
    hoja["incompletas_fuera_de_muestra"] = sum(1 for n in inc if n not in en_muestra)
    return resultado


def _analizar(db: Session, datos, col: dict[str, int], gestion: int | None) -> dict:
    g = lambda fila, campo: fila[col[campo]] if campo in col and col[campo] < len(fila) else None

    if gestion is None:
        from .importer import _fecha
        anios = Counter()
        for _, f in datos:
            try:
                anios[_fecha(g(f, "cfecha")).year] += 1
            except Exception:
                pass
        gestion = anios.most_common(1)[0][0] if anios else None

    leidas, errores = [], []
    for n, f in datos:
        try:
            d = _leer_fila(f, g, gestion or date.today().year)
            d["fila"] = n
            leidas.append(d)
        except Exception as e:
            errores.append({"fila": n, "error": str(e)})

    completas = [d for d in leidas if not d["faltantes"]]
    incompletas = [d for d in leidas if d["faltantes"]]
    por_campo = Counter(c for d in incompletas for c in d["faltantes"])
    meses = Counter(d["mes"] for d in leidas)

    existentes = None
    if gestion:
        existentes = {
            "movimientos": db.query(Movimiento).filter_by(gestion=gestion).count(),
            "lineas_presupuesto": db.query(Presupuesto).filter_by(gestion=gestion).count(),
            "pendientes": db.query(FilaPendiente).filter_by(gestion=gestion, estado="pendiente").count(),
        }

    return {
        "gestion": gestion,
        "filas": len(datos),
        "filas_completas": len(completas),
        "filas_incompletas": len(incompletas),
        "filas_con_error": len(errores),
        "errores": errores[:50],
        "movimientos": sum(1 for d in completas if d["ejecucion"]),
        "total_presupuesto": round(sum(d["presupuesto"] for d in leidas), 2),
        "total_ejecucion": round(sum(d["ejecucion"] for d in leidas), 2),
        "presupuesto_pendiente": round(sum(d["presupuesto"] for d in incompletas), 2),
        "ejecucion_pendiente": round(sum(d["ejecucion"] for d in incompletas), 2),
        "faltantes_por_campo": [{"campo": ETIQUETAS[c], "filas": por_campo[c]} for c in ETIQUETAS if por_campo[c]],
        "filas_por_mes": [{"mes": m, "filas": meses[m]} for m in sorted(meses)],
        "financiadores": sorted({d["etiquetas"]["fondo"] for d in leidas if d["etiquetas"]["fondo"]}),
        "regiones": sorted({d["etiquetas"]["region"] for d in leidas if d["etiquetas"]["region"]}),
        "reemplaza": existentes if existentes and (existentes["movimientos"] or existentes["lineas_presupuesto"]) else None,
        "_incompletas": [{"fila": d["fila"], "faltantes": d["faltantes"]} for d in incompletas],
    }

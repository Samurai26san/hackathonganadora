"""Importación de la base del sistema contable institucional (hoja BD).

Cada fila de la base aporta:
  - "presupuesto Bs": presupuesto. Las filas con mes PTTO son presupuesto aún no
    programado (mes 0); el resto queda programado en su mes.
  - "Ejecución" (menos "haber"): ejecución real, solo en filas con comprobante.

El archivo es acumulado al día, por lo que cada importación REEMPLAZA los datos de
esa gestión; las demás gestiones se conservan (histórico para comparativos).
"""
import re
from collections import Counter, defaultdict
from datetime import date, datetime

from sqlalchemy.orm import Session

from . import prediccion
from .importer import Catalogos, _fecha
from .models import FilaPendiente, Area, Cuenta, Financiador, Importacion, Modificacion, Movimiento, Presupuesto, Region, Rubro

MESES = {m: i for i, m in enumerate(
    ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"], start=1)}
MESES["SETIEMBRE"] = 9
REGIONES = {"LP": "La Paz", "SC": "Santa Cruz", "CB": "Cochabamba", "OR": "Oruro", "PT": "Potosí", "CH": "Chuquisaca",
            "TJ": "Tarija", "BE": "Beni", "PD": "Pando", "NAL": "Nacional"}


def _prefijo(texto: str) -> str:
    """'4.1 Videos' -> '4'; '9. Otros Gastos' -> '9'."""
    m = re.match(r"\s*(\d+)", texto or "")
    return m.group(1) if m else ""


def _num(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return float(str(v).replace(",", ""))


def _limpiar(v) -> str:
    return " ".join(str(v or "").split())


def importar_contable(db: Session, filas, col: dict[str, int], archivo: str, usuario_id: int | None,
                      gestion: int | None = None) -> Importacion:
    g = lambda fila, campo: fila[col[campo]] if campo in col and col[campo] < len(fila) else None
    filas = [f for f in filas if f and any(v is not None for v in f)]

    # Gestión: la indicada o el año más frecuente en las fechas de los comprobantes
    if gestion is None:
        anios = Counter()
        for f in filas:
            try:
                anios[_fecha(g(f, "cfecha")).year] += 1
            except Exception:
                pass
        if not anios:
            raise ValueError("No se pudo determinar la gestión: indíquela al importar")
        gestion = anios.most_common(1)[0][0]

    # Reemplaza la gestión completa (el archivo contable es acumulado)
    previos = db.query(Movimiento).filter_by(gestion=gestion).count()
    ids_ppto = [i for (i,) in db.query(Presupuesto.id).filter_by(gestion=gestion)]
    if ids_ppto:
        db.query(Modificacion).filter(Modificacion.presupuesto_id.in_(ids_ppto)).delete(synchronize_session=False)
    db.query(Presupuesto).filter_by(gestion=gestion).delete(synchronize_session=False)
    db.query(Movimiento).filter_by(gestion=gestion).delete(synchronize_session=False)
    db.query(FilaPendiente).filter_by(gestion=gestion).delete(synchronize_session=False)

    imp = Importacion(archivo=archivo, tipo="base contable", usuario_id=usuario_id)
    db.add(imp)
    db.flush()

    cat = Catalogos(db)
    presupuesto = defaultdict(float)
    cruces = defaultdict(float)  # cuentas registradas bajo un rubro que no les corresponde
    errores, pendientes, n_mov, total_ppto, total_ejec = [], [], 0, 0.0, 0.0

    for n, f in enumerate(filas, start=3):
        try:
            datos = _leer_fila(f, g, gestion)
            datos["fila"] = n
            if datos["faltantes"]:
                pendientes.append(datos)  # se revisa y valida antes de entrar a los reportes
                continue
            ids, cruce = resolver(cat, datos["etiquetas"])
            presupuesto[(datos["mes"], *ids)] += datos["presupuesto"]
            total_ppto += datos["presupuesto"]
            if cruce:
                cruces[cruce] += datos["presupuesto"]
            if datos["ejecucion"]:
                db.add(_movimiento(datos, gestion, ids, imp.id))
                n_mov += 1
                total_ejec += datos["ejecucion"]
        except Exception as e:  # una fila mala no detiene la importación
            errores.append({"fila": n, "error": str(e)})

    for (mes, cuenta_id, fin_id, area_id, reg_id), monto in presupuesto.items():
        db.add(Presupuesto(gestion=gestion, mes=mes, cuenta_id=cuenta_id, financiador_id=fin_id, area_id=area_id,
                           region_id=reg_id, monto_inicial=round(monto, 2)))
    db.flush()

    # Filas con etiquetas faltantes: se predicen con el modelo entrenado en las filas completas
    if pendientes:
        modelos = prediccion.entrenar(prediccion.filas_entrenamiento(db))
        for d in pendientes:
            db.add(FilaPendiente(
                importacion_id=imp.id, gestion=gestion, fila=d["fila"], mes=d["mes"], fecha=d["fecha"],
                comprobante=d["comprobante"], descripcion=d["descripcion"], cuenta_contable=d["cuenta_contable"],
                presupuesto=d["presupuesto"], ejecucion=d["ejecucion"], tipo_cambio=d["tasa"], monto_usd=d["usd"],
                etiquetas=d["etiquetas"], faltantes=d["faltantes"],
                prediccion=prediccion.predecir(modelos, d, d["faltantes"]),
            ))

    advertencias = [
        f"La cuenta '{c}' está registrada bajo el rubro '{r}' (Bs {m:,.2f} de presupuesto); se reporta separada."
        for (c, r), m in sorted(cruces.items())
    ]
    if pendientes:
        advertencias.insert(0, f"{len(pendientes)} filas tienen etiquetas faltantes: quedan pendientes de validación "
                               f"(Bs {sum(d['presupuesto'] for d in pendientes):,.2f} de presupuesto y "
                               f"Bs {sum(d['ejecucion'] for d in pendientes):,.2f} de ejecución).")
    if previos:
        advertencias.insert(0, f"Se reemplazaron los {previos} movimientos anteriores de la gestión {gestion}.")

    imp.filas_ok = len(filas) - len(errores) - len(pendientes)
    imp.filas_error = len(errores)
    imp.errores = errores[:200]
    imp.resumen = {
        "gestion": gestion,
        "movimientos": n_mov,
        "lineas_presupuesto": len(presupuesto),
        "pendientes": len(pendientes),
        "total_presupuesto": round(total_ppto, 2),
        "total_ejecucion": round(total_ejec, 2),
        "advertencias": advertencias,
        "importado": datetime.utcnow().isoformat(),
    }
    db.commit()
    return imp


def _leer_fila(f, g, gestion: int) -> dict:
    mes_txt = _limpiar(g(f, "mes")).upper()
    mes = 0 if mes_txt == "PTTO" else MESES.get(mes_txt)
    fecha = None
    try:
        fecha = _fecha(g(f, "cfecha"))
    except Exception:
        pass
    if mes is None:
        if not fecha:
            raise ValueError(f"Mes no reconocido: '{mes_txt}'")
        mes = fecha.month
    etiquetas = {
        "fondo": _limpiar(g(f, "fondo")) or None,
        "rubro": _limpiar(g(f, "rubro")) or None,
        "cuenta": _limpiar(g(f, "cuenta")) or None,
        "area": _limpiar(g(f, "area")) or None,
        "region": _limpiar(g(f, "region")).upper() or None,
    }
    tipo, numero, codigo = g(f, "tipo"), g(f, "numero"), _limpiar(g(f, "codigo"))
    ejec = _num(g(f, "ejecucion")) - _num(g(f, "haber"))
    return {
        "mes": mes, "fecha": fecha or (date(gestion, max(mes, 1), 1) if ejec else None),
        "tipo": "ejec" if ejec else "ppto",
        "comprobante": f"T{tipo}-{numero}" if tipo is not None else None,
        "descripcion": _limpiar(g(f, "ref")) or None,
        "cuenta_contable": f"{codigo} {_limpiar(g(f, 'nombre'))}".strip()[:150] or None,
        "presupuesto": _num(g(f, "presupuesto bs")), "ejecucion": ejec,
        "tasa": _num(g(f, "tasa")) or 1, "usd": (_num(g(f, "dsus")) - _num(g(f, "hsus"))) or None,
        "etiquetas": etiquetas, "faltantes": [c for c, v in etiquetas.items() if not v],
    }


def resolver(cat: Catalogos, et: dict) -> tuple[tuple[int, int, int, int, int], tuple | None]:
    """Convierte las etiquetas de texto en ids de catálogo (los crea si son nuevos).

    Devuelve (cuenta_id, financiador_id, area_id, region_id) y el cruce cuenta/rubro si la
    cuenta pertenece por numeración a otro rubro (se mantiene separada, como en la tabla dinámica).
    """
    rubro_txt, cuenta_txt = et["rubro"], et["cuenta"]
    if re.fullmatch(r"[\d.]+", cuenta_txt):
        cuenta_txt += " (sin nombre)"
    rubro = cat.obtener(Rubro, rubro_txt, rubro_txt)
    codigo_cuenta, cruce = cuenta_txt, None
    if _prefijo(cuenta_txt) != _prefijo(rubro_txt):
        codigo_cuenta, cruce = f"{cuenta_txt} [{rubro_txt}]", (cuenta_txt, rubro_txt)
    cuenta = cat.obtener(Cuenta, codigo_cuenta, cuenta_txt, rubro_id=rubro.id)
    fin = cat.obtener(Financiador, et["fondo"], et["fondo"])
    area = cat.obtener(Area, et["area"], et["area"])
    reg = cat.obtener(Region, et["region"].upper(), REGIONES.get(et["region"].upper(), et["region"]))
    return (cuenta.id, fin.id, area.id, reg.id), cruce


def _movimiento(d: dict, gestion: int, ids, importacion_id: int | None) -> Movimiento:
    cuenta_id, fin_id, area_id, reg_id = ids
    return Movimiento(
        gestion=gestion, fecha=d["fecha"], mes=d["mes"] or d["fecha"].month, comprobante=d["comprobante"],
        descripcion=d["descripcion"], cuenta_contable=d["cuenta_contable"],
        cuenta_id=cuenta_id, financiador_id=fin_id, area_id=area_id, region_id=reg_id,
        moneda="BOB", monto_original=d["ejecucion"], tipo_cambio=d["tasa"], monto_bs=d["ejecucion"],
        monto_usd=d["usd"], importacion_id=importacion_id,
    )


def registrar_validada(db: Session, cat: Catalogos, p: FilaPendiente, valores: dict) -> None:
    """Incorpora una fila pendiente ya validada al presupuesto y la ejecución."""
    ids, _ = resolver(cat, valores)
    cuenta_id, fin_id, area_id, reg_id = ids
    clave = dict(gestion=p.gestion, mes=p.mes, cuenta_id=cuenta_id, financiador_id=fin_id, area_id=area_id, region_id=reg_id)
    ppto = db.query(Presupuesto).filter_by(**clave).first()
    if ppto:
        ppto.monto_inicial = float(ppto.monto_inicial) + float(p.presupuesto)
    else:
        db.add(Presupuesto(**clave, monto_inicial=float(p.presupuesto)))
        db.flush()  # visible para la siguiente fila del mismo lote con la misma combinación
    if float(p.ejecucion):
        d = {"fecha": p.fecha, "mes": p.mes, "comprobante": p.comprobante, "descripcion": p.descripcion,
             "cuenta_contable": p.cuenta_contable, "ejecucion": float(p.ejecucion), "tasa": float(p.tipo_cambio),
             "usd": float(p.monto_usd) if p.monto_usd is not None else None}
        db.add(_movimiento(d, p.gestion, ids, p.importacion_id))

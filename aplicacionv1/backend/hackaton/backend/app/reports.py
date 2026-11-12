"""Motor genérico de reportes de ejecución presupuestaria.

Cada reporte se define como una lista de niveles (dimensiones). El motor agrega
presupuesto, modificaciones y ejecución por esos niveles y devuelve un árbol
desplegable (drill-down) con totales en cada nodo.

El presupuesto tiene dimensión mes (0 = no programado / PTTO), igual que la base
contable, por lo que todos los reportes y filtros se comportan como las tablas
dinámicas del archivo original.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Area, Cuenta, Financiador, Modificacion, Movimiento, Presupuesto, Region, Rubro

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MES_PTTO = "PTTO (sin programar)"


@dataclass
class Dim:
    key: str
    label: str
    tabla: type | None  # catálogo para nombres; None = dimensión calculada


DIMS = {
    "rubro": Dim("rubro", "Rubro", Rubro),
    "cuenta": Dim("cuenta", "Cuenta", Cuenta),
    "financiador": Dim("financiador", "Financiador", Financiador),
    "area": Dim("area", "Área", Area),
    "region": Dim("region", "Región", Region),
    "mes": Dim("mes", "Mes", None),
}

# Mismos niveles que las tablas dinámicas del archivo contable original
REPORTES = {
    "rubro-cuenta": {"titulo": "Ejecución por rubro y cuenta", "niveles": ["rubro", "cuenta"]},
    "financiador": {"titulo": "Ejecución por financiador", "niveles": ["financiador", "rubro", "cuenta"]},
    "area-financiador": {"titulo": "Ejecución por área y financiador", "niveles": ["area", "financiador", "rubro", "cuenta"]},
    "region": {"titulo": "Ejecución por región", "niveles": ["region", "area", "financiador", "rubro", "cuenta"]},
    "mes": {"titulo": "Ejecución por mes", "niveles": ["mes", "rubro", "cuenta"]},
    "movimientos": {"titulo": "Detalle de movimientos", "niveles": []},
    "resumen": {"titulo": "Resumen general consolidado", "niveles": ["rubro"]},
}

FILTROS = ["rubro", "cuenta", "financiador", "area", "region", "mes"]


def nombre_mes(m: int) -> str:
    return MES_PTTO if m == 0 else MESES[m - 1]


def _col(model, dim: str):
    """Columna de agrupación para una dimensión en Presupuesto o Movimiento."""
    if dim == "rubro":
        return Cuenta.rubro_id
    if dim == "mes":
        return model.mes
    return getattr(model, f"{dim}_id")


def _aplicar_filtros(q, model, filtros: dict):
    for dim, valores in filtros.items():
        if valores:
            q = q.where(_col(model, dim).in_(valores))
    return q


def _etiqueta(codigo: str, nombre: str) -> str:
    # Si el código ya forma parte del nombre (p. ej. "4.1 Videos") no se repite
    if codigo.startswith(nombre.strip()) or nombre.startswith(codigo):
        return nombre
    return f"{codigo} - {nombre}"


def _nombres(db: Session) -> dict[str, dict[int, str]]:
    out = {"mes": {i: nombre_mes(i) for i in range(13)}}
    for key, d in DIMS.items():
        if d.tabla is not None:
            out[key] = {r.id: _etiqueta(r.codigo, r.nombre) for r in db.query(d.tabla).all()}
    return out


def _agregados(db: Session, gestion: int, niveles: list[str], filtros: dict):
    """Devuelve dicts {tupla_dims: monto} para presupuesto, modificaciones y ejecutado."""

    def consulta(model, valor, join_mod=False):
        cols = [_col(model, n) for n in niveles]
        q = select(*cols, func.sum(valor)).select_from(model).join(Cuenta, Cuenta.id == model.cuenta_id)
        if join_mod:
            q = q.join(Modificacion, Modificacion.presupuesto_id == Presupuesto.id)
        q = _aplicar_filtros(q.where(model.gestion == gestion), model, filtros)
        if cols:
            q = q.group_by(*cols)
        return {tuple(r[:-1]): float(r[-1] or 0) for r in db.execute(q)}

    return (
        consulta(Presupuesto, Presupuesto.monto_inicial),
        consulta(Presupuesto, Modificacion.monto, join_mod=True),
        consulta(Movimiento, Movimiento.monto_bs),
    )


def _acumular(niveles, *dicts):
    """Suma cada dict en todos los prefijos de su clave: {prefijo: [v0, v1, ...]}."""
    acum = defaultdict(lambda: [0.0] * len(dicts))
    for i, d in enumerate(dicts):
        for clave, v in d.items():
            for k in range(len(niveles) + 1):
                acum[clave[:k]][i] += v
    return acum


def _metricas(inicial=0.0, modif=0.0, ejec=0.0):
    vigente = inicial + modif
    return {
        "inicial": round(inicial, 2),
        "modificaciones": round(modif, 2),
        "vigente": round(vigente, 2),
        "ejecutado": round(ejec, 2),
        "saldo": round(vigente - ejec, 2),
        "porcentaje": round(ejec / vigente * 100, 2) if vigente else None,
    }


def generar(db: Session, reporte: str, gestion: int, filtros: dict, comparar: int | None = None) -> dict:
    cfg = REPORTES[reporte]
    niveles = cfg["niveles"]
    acum = _acumular(niveles, *_agregados(db, gestion, niveles, filtros))
    nombres = _nombres(db)

    # Comparativo con otra gestión (mismos niveles y filtros)
    comp = _acumular(niveles, *_agregados(db, comparar, niveles, filtros)) if comparar else None

    def nodo(pref):
        m = _metricas(*acum[pref])
        if comp is not None:
            ci, cm, ce = comp.get(pref, [0.0, 0.0, 0.0])
            m["comparativo"] = {
                "gestion": comparar,
                "vigente": round(ci + cm, 2),
                "ejecutado": round(ce, 2),
                "variacion": round(m["ejecutado"] - ce, 2),
                "variacion_pct": round((m["ejecutado"] - ce) / ce * 100, 2) if ce else None,
            }
        return m

    def construir(pref):
        k = len(pref)
        if k == len(niveles):
            return []
        dim = niveles[k]
        hijos = {p[k] for p in acum if len(p) == k + 1 and p[:k] == pref}
        orden = sorted(hijos) if dim == "mes" else sorted(hijos, key=lambda h: nombres[dim].get(h, ""))
        return [
            {"nivel": dim, "id": h, "nombre": nombres[dim].get(h, str(h)), **nodo(pref + (h,)), "hijos": construir(pref + (h,))}
            for h in orden
        ]

    return {
        "reporte": reporte,
        "titulo": cfg["titulo"],
        "gestion": gestion,
        "niveles": [{"key": n, "label": DIMS[n].label} for n in niveles],
        "filtros": filtros,
        "total": nodo(()),
        "filas": construir(()),
    }


def movimientos(db: Session, gestion: int, filtros: dict, limite: int = 500, offset: int = 0) -> dict:
    q = (
        select(
            Movimiento.id, Movimiento.fecha, Movimiento.comprobante, Movimiento.descripcion, Movimiento.cuenta_contable,
            Rubro.nombre.label("rubro"), Cuenta.codigo.label("cuenta_codigo"), Cuenta.nombre.label("cuenta"),
            Financiador.nombre.label("financiador"), Area.nombre.label("area"), Region.nombre.label("region"),
            Movimiento.moneda, Movimiento.monto_original, Movimiento.tipo_cambio, Movimiento.monto_bs, Movimiento.monto_usd,
        )
        .select_from(Movimiento)
        .join(Cuenta, Cuenta.id == Movimiento.cuenta_id)
        .join(Rubro, Rubro.id == Cuenta.rubro_id)
        .join(Financiador, Financiador.id == Movimiento.financiador_id)
        .join(Area, Area.id == Movimiento.area_id)
        .join(Region, Region.id == Movimiento.region_id)
        .where(Movimiento.gestion == gestion)
    )
    q = _aplicar_filtros(q, Movimiento, filtros)
    sub = q.subquery()
    total = db.execute(select(func.count(), func.coalesce(func.sum(sub.c.monto_bs), 0)).select_from(sub)).one()
    rows = db.execute(q.order_by(Movimiento.fecha.desc(), Movimiento.id.desc()).limit(limite).offset(offset)).mappings().all()
    num = lambda v: float(v) if v is not None else None
    return {
        "reporte": "movimientos",
        "titulo": REPORTES["movimientos"]["titulo"],
        "gestion": gestion,
        "filtros": filtros,
        "total_registros": total[0],
        "total_monto": float(total[1] or 0),
        "filas": [
            {**r, "fecha": r["fecha"].isoformat(), "monto_original": num(r["monto_original"]), "tipo_cambio": num(r["tipo_cambio"]),
             "monto_bs": num(r["monto_bs"]), "monto_usd": num(r["monto_usd"])}
            for r in rows
        ],
    }


def serie_mensual(db: Session, gestion: int, filtros: dict) -> list[dict]:
    """Presupuesto programado y ejecución por mes (1..12) con acumulados."""
    ppto, modif, ejec = _agregados(db, gestion, ["mes"], filtros)
    # La ejecución se corta en el último mes con movimientos (los datos llegan con rezago)
    hoy = date.today()
    ultimo = max((m for (m,), v in ejec.items() if v), default=0)
    acum_e, acum_p, out = 0.0, 0.0, []
    for i, nombre in enumerate(MESES, start=1):
        p = ppto.get((i,), 0.0) + modif.get((i,), 0.0)
        e = ejec.get((i,), 0.0)
        acum_p += p
        acum_e += e
        futuro = gestion >= hoy.year and i > ultimo
        out.append({
            "mes": i, "nombre": nombre, "presupuesto": round(p, 2), "presupuesto_acumulado": round(acum_p, 2),
            "ejecutado": None if futuro else round(e, 2), "acumulado": None if futuro else round(acum_e, 2),
        })
    return out

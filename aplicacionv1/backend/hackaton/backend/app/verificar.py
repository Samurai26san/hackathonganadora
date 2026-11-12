"""Compara los reportes del sistema contra las tablas dinámicas del Excel original.

Uso: python -m app.verificar archivo.xlsx [gestion]
"""
import sys
from collections import Counter

from openpyxl import load_workbook

from . import reports
from .db import SessionLocal

# hoja del Excel -> (reporte del sistema, profundidad de la tabla dinámica)
HOJAS = {
    "Rubro": ("resumen", 1),
    "Financiador": ("financiador", 2),
    "por cuenta": ("rubro-cuenta", 2),
    "Por Area y Fin": ("area-financiador", 3),
    "Por region y Area": ("region", 5),
    "Por mes": ("mes", 1),
}


def _filas_pivot(ws):
    """Filas (presupuesto, ejecución) de la tabla dinámica y su total general."""
    filas, total, dentro = [], None, False
    for fila in ws.iter_rows(values_only=True):
        celdas = [c for c in fila]
        if "Etiquetas de fila" in celdas:
            i = celdas.index("Etiquetas de fila")
            dentro = True
            continue
        if not dentro or celdas[i] is None:
            continue
        par = (round(float(celdas[i + 1] or 0), 2), round(float(celdas[i + 2] or 0), 2))
        if celdas[i] == "Total general":
            total = par
            break
        filas.append(par)
    return filas, total


def _filas_sistema(rep, profundidad):
    out = []

    def rec(nodos, d):
        for n in nodos:
            out.append((round(n["vigente"], 2), round(n["ejecutado"], 2)))
            if d < profundidad:
                rec(n["hijos"], d + 1)

    rec(rep["filas"], 1)
    return out, (round(rep["total"]["vigente"], 2), round(rep["total"]["ejecutado"], 2))


def verificar(ruta: str, gestion: int) -> bool:
    wb = load_workbook(ruta, read_only=True, data_only=True)
    db = SessionLocal()
    todo_ok = True
    for hoja, (rep_id, prof) in HOJAS.items():
        if hoja not in wb.sheetnames:
            continue
        p_filas, p_total = _filas_pivot(wb[hoja])
        s_filas, s_total = _filas_sistema(reports.generar(db, rep_id, gestion, {}), prof)
        diferencias = sum((Counter(p_filas) - Counter(s_filas)).values()) + sum((Counter(s_filas) - Counter(p_filas)).values())
        ok = p_total == s_total and diferencias == 0
        todo_ok &= ok
        print(f"{'OK ' if ok else 'DIF'} {hoja:<18} -> {rep_id:<17} filas excel={len(p_filas):>4} sistema={len(s_filas):>4} "
              f"total excel={p_total} sistema={s_total} diferencias={diferencias}")
    db.close()
    return todo_ok


if __name__ == "__main__":
    ok = verificar(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2026)
    sys.exit(0 if ok else 1)

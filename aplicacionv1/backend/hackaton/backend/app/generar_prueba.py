"""Genera una copia de la base contable con etiquetas borradas, para demostrar la predicción.

Uso: python -m app.generar_prueba origen.xlsx destino.xlsx [n_filas]

Toma la hoja BD, borra al azar 1 o 2 etiquetas (financiador, rubro, cuenta, área o región)
en n filas y guarda el resultado. Las respuestas reales quedan en una hoja aparte
("_respuestas") que el importador ignora, para medir los aciertos del modelo.
"""
import random
import sys

from openpyxl import Workbook, load_workbook

COLUMNAS = {"fondo": "fondo", "rubro": "rubro", "cuenta": "Cuenta", "area": "area", "region": "region"}
PESOS = {"fondo": 3, "cuenta": 3, "rubro": 2, "area": 2, "region": 2}


def generar(origen: str, destino: str, n: int = 60, semilla: int = 7) -> dict[int, dict[str, str]]:
    ws = load_workbook(origen, read_only=True, data_only=True)["BD"]
    filas = [list(f) for f in ws.iter_rows(values_only=True)]
    encabezado = filas[1]
    ix = {c: encabezado.index(col) for c, col in COLUMNAS.items()}
    ref = encabezado.index("ref")

    rnd = random.Random(semilla)
    datos = list(range(2, len(filas)))
    # Mayoría de movimientos ejecutados (tienen glosa) y algunas líneas de presupuesto
    ejec = [i for i in datos if filas[i][ref] != "PRESUPUESTO"]
    ppto = [i for i in datos if filas[i][ref] == "PRESUPUESTO"]
    elegidas = rnd.sample(ejec, int(n * 0.7)) + rnd.sample(ppto, n - int(n * 0.7))

    respuestas = {}
    campos, pesos = list(PESOS), list(PESOS.values())
    for i in elegidas:
        borrar = set(rnd.choices(campos, pesos, k=1 if rnd.random() < 0.7 else 2))
        respuestas[i + 1] = {c: filas[i][ix[c]] for c in borrar}  # número de fila en Excel
        for c in borrar:
            filas[i][ix[c]] = None

    wb = Workbook()
    bd = wb.active
    bd.title = "BD"
    for f in filas:
        bd.append(f)
    hoja = wb.create_sheet("_respuestas")
    hoja.append(["fila", "campo", "valor_real"])
    for fila, vals in sorted(respuestas.items()):
        for c, v in vals.items():
            hoja.append([fila, c, v])
    wb.save(destino)
    return respuestas


if __name__ == "__main__":
    r = generar(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 60)
    print(f"Generado {sys.argv[2]}: {len(r)} filas con etiquetas borradas")

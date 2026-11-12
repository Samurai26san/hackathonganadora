"""Exportación de reportes a Excel y PDF."""
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COLS_EJEC = [
    ("inicial", "Ppto. inicial"), ("modificaciones", "Modificaciones"), ("vigente", "Ppto. vigente"),
    ("ejecutado", "Ejecutado"), ("saldo", "Saldo"), ("porcentaje", "% Ejec."),
]
COLS_MOV = [
    ("fecha", "Fecha"), ("comprobante", "Comprobante"), ("descripcion", "Descripción"), ("cuenta_contable", "Cuenta contable"),
    ("rubro", "Rubro"), ("cuenta", "Cuenta"), ("financiador", "Financiador"), ("area", "Área"), ("region", "Región"),
    ("moneda", "Mon."), ("monto_original", "Monto orig."), ("tipo_cambio", "T/C"), ("monto_bs", "Ejecución Bs"), ("monto_usd", "Ejecución USD"),
]


def _tabla(rep: dict) -> tuple[list[str], list[list], list[int]]:
    """Aplana el reporte en encabezados, filas y nivel de sangría por fila."""
    if rep["reporte"] == "movimientos":
        heads = [h for _, h in COLS_MOV]
        filas = [[f.get(k) for k, _ in COLS_MOV] for f in rep["filas"]]
        filas.append(["TOTAL"] + [""] * (len(COLS_MOV) - 3) + [rep["total_monto"], ""])
        return heads, filas, [0] * len(filas)

    comparar = "comparativo" in rep["total"]
    heads = [" / ".join(n["label"] for n in rep["niveles"])] + [h for _, h in COLS_EJEC]
    if comparar:
        g = rep["total"]["comparativo"]["gestion"]
        heads += [f"Ejecutado {g}", "Variación", "Var. %"]
    filas, niveles = [], []

    def valores(n):
        v = [n[k] for k, _ in COLS_EJEC]
        if comparar:
            c = n["comparativo"]
            v += [c["ejecutado"], c["variacion"], c["variacion_pct"]]
        return v

    def recorrer(nodos, prof):
        for n in nodos:
            filas.append([n["nombre"]] + valores(n))
            niveles.append(prof)
            recorrer(n["hijos"], prof + 1)

    recorrer(rep["filas"], 0)
    filas.append(["TOTAL"] + valores(rep["total"]))
    niveles.append(0)
    return heads, filas, niveles


def _subtitulo(rep: dict) -> str:
    f = {k: v for k, v in (rep.get("filtros") or {}).items() if v}
    txt = f"Gestión {rep['gestion']}"
    if f:
        txt += " | Filtros: " + ", ".join(f"{k}={v}" for k, v in f.items())
    return txt + f" | Generado {datetime.now():%d/%m/%Y %H:%M}"


def excel(rep: dict) -> bytes:
    heads, filas, niveles = _tabla(rep)
    wb = Workbook()
    ws = wb.active
    ws.title = rep["reporte"][:30]
    ws.append([rep["titulo"]])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([_subtitulo(rep)])
    ws.append([])
    ws.append(heads)
    fill = PatternFill("solid", fgColor="1F3A5F")
    for c in ws[4]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = fill
        c.alignment = Alignment(horizontal="center", wrap_text=True)
    for fila, nivel in zip(filas, niveles):
        ws.append(fila)
        r = ws.max_row
        ws.cell(r, 1).alignment = Alignment(indent=nivel * 2)
        if nivel == 0:
            for c in ws[r]:
                c.font = Font(bold=True)
        for c in ws[r][1:]:
            if isinstance(c.value, (int, float)):
                c.number_format = "#,##0.00"
    ws.column_dimensions["A"].width = 45
    for col in "BCDEFGHIJKL":
        ws.column_dimensions[col].width = 16
    ws.freeze_panes = "B5"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fmt(v):
    if isinstance(v, float):
        return f"{v:,.2f}"
    return "" if v is None else str(v)


def pdf(rep: dict) -> bytes:
    heads, filas, niveles = _tabla(rep)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=25, bottomMargin=25)
    st = getSampleStyleSheet()
    data = [heads] + [
        [(" " * 4 * nivel) + _fmt(f[0])[:60]] + [_fmt(v)[:40] for v in f[1:]]
        for f, nivel in zip(filas, niveles)
    ]
    t = Table(data, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]
    for i, nivel in enumerate(niveles, start=1):
        if nivel == 0 and rep["reporte"] != "movimientos":
            estilo.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#E8EEF5")))
    t.setStyle(TableStyle(estilo))
    doc.build([Paragraph(rep["titulo"], st["Title"]), Paragraph(_subtitulo(rep), st["Normal"]), Spacer(1, 8), t])
    return buf.getvalue()

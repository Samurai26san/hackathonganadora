"""Inicializa la base de datos.

Uso:
  python -m app.seed archivo.xlsx   # usuarios + importa la base contable real
  python -m app.seed --demo         # usuarios + datos ficticios de 2 gestiones
"""
import sys
import random
from datetime import date, timedelta

from .auth import hash_password
from .db import Base, SessionLocal, engine
from .models import Area, Cuenta, Financiador, Modificacion, Movimiento, Presupuesto, Region, Rubro, TipoCambio, Usuario

RUBROS = {
    ("10000", "Servicios personales"): [("11100", "Haberes básicos"), ("11700", "Sueldos"), ("13100", "Aportes patronales")],
    ("20000", "Servicios no personales"): [("21100", "Comunicaciones"), ("22100", "Pasajes"), ("22200", "Viáticos"), ("25200", "Consultorías")],
    ("30000", "Materiales y suministros"): [("31100", "Alimentos"), ("32100", "Papel"), ("34100", "Combustibles")],
    ("40000", "Activos reales"): [("43100", "Equipo de oficina"), ("43700", "Equipo de computación")],
}
FINANCIADORES = [("F01", "Tesoro General de la Nación", "BOB"), ("F02", "Recursos propios", "BOB"),
                 ("F03", "Cooperación BID", "USD"), ("F04", "Unión Europea", "USD")]
AREAS = [("A01", "Administración"), ("A02", "Operaciones"), ("A03", "Proyectos"), ("A04", "Planificación")]
REGIONES = [("R01", "La Paz"), ("R02", "Cochabamba"), ("R03", "Santa Cruz"), ("R04", "Oruro")]


# Credenciales de demostración, una por rol (los demás usuarios se registran desde la web)
USUARIOS_DEMO = [
    ("admin", "Administrador de usuarios", "admin", "1234"),
    ("validador", "Técnico validador", "validador", "1234"),
    ("consulta", "Usuario de consulta", "consulta", "1234"),
]


def usuarios(db):
    for u, n, r, pw in USUARIOS_DEMO:
        db.add(Usuario(username=u, nombre=n, rol=r, password_hash=hash_password(pw)))


def reiniciar():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    usuarios(db)
    db.commit()
    db.close()


def cargar_excel(ruta: str):
    from .importer import importar
    db = SessionLocal()
    with open(ruta, "rb") as fh:
        imp = importar(db, fh.read(), ruta.split("/")[-1], "movimientos", None)
    print(f"Importado {ruta}: {imp.filas_ok} filas, {imp.filas_error} errores")
    for k, v in (imp.resumen or {}).items():
        print(f"  {k}: {v}")
    db.close()


def run(reset: bool = True):
    """Datos ficticios de demostración (también usados por las pruebas)."""
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    random.seed(42)
    db = SessionLocal()
    usuarios(db)

    cuentas = []
    for (rc, rn), cs in RUBROS.items():
        rubro = Rubro(codigo=rc, nombre=rn)
        db.add(rubro)
        db.flush()
        for cc, cn in cs:
            c = Cuenta(codigo=cc, nombre=cn, rubro_id=rubro.id)
            db.add(c)
            cuentas.append(c)
    fins = [Financiador(codigo=c, nombre=n) for c, n, _ in FINANCIADORES]
    monedas = {c: m for c, _, m in FINANCIADORES}
    areas = [Area(codigo=c, nombre=n) for c, n in AREAS]
    regs = [Region(codigo=c, nombre=n) for c, n in REGIONES]
    db.add_all(fins + areas + regs)
    db.flush()

    hoy = date.today()
    for gestion in (hoy.year - 1, hoy.year):
        d = date(gestion, 1, 1)
        while d.year == gestion:
            db.add(TipoCambio(fecha=d, moneda="USD", valor=6.96))
            d += timedelta(days=7)

        fin_mes = 12 if gestion < hoy.year else hoy.month
        n_comp = 0
        for c in cuentas:
            for f in fins:
                for a in random.sample(areas, 2):
                    reg = random.choice(regs)
                    inicial = random.randrange(20, 400) * 1000
                    p = Presupuesto(gestion=gestion, cuenta_id=c.id, financiador_id=f.id, area_id=a.id, region_id=reg.id, monto_inicial=inicial)
                    db.add(p)
                    db.flush()
                    if random.random() < 0.3:
                        db.add(Modificacion(presupuesto_id=p.id, fecha=date(gestion, random.randint(3, 9), 1),
                                            monto=random.choice([-1, 1]) * random.randrange(5, 50) * 1000, tipo="traspaso",
                                            resolucion=f"RA-{random.randint(100, 999)}/{gestion}"))
                    # Ejecución: tasa distinta por combinación para que los reportes sean interesantes
                    tasa = random.uniform(0.45, 1.0) if gestion < hoy.year else random.uniform(0.3, 0.9) * fin_mes / 12
                    objetivo = inicial * tasa
                    k = random.randint(2, 6)
                    for _ in range(k):
                        mes = random.randint(1, fin_mes)
                        dia = random.randint(1, 28)
                        fecha = date(gestion, mes, dia)
                        if fecha > hoy:
                            fecha = hoy
                        moneda = monedas[f.codigo]
                        tc = 6.96 if moneda == "USD" else 1.0
                        bs = round(objetivo / k * random.uniform(0.6, 1.4), 2)
                        n_comp += 1
                        db.add(Movimiento(gestion=gestion, fecha=fecha, mes=fecha.month, comprobante=f"CBT-{gestion}-{n_comp:05d}",
                                          descripcion=f"{c.nombre} - {a.nombre}", cuenta_id=c.id, financiador_id=f.id, area_id=a.id,
                                          region_id=reg.id, moneda=moneda, monto_original=round(bs / tc, 2), tipo_cambio=tc, monto_bs=bs))
    db.commit()
    db.close()
    print("Datos de demostración cargados. Usuarios: admin, validador, consulta (contraseña 1234)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--demo" in args:
        run()
    else:
        reiniciar()
        for ruta in args:
            cargar_excel(ruta)
        print("Usuarios (contraseña 1234): admin (usuarios), validador (carga y validación), consulta (lectura)")

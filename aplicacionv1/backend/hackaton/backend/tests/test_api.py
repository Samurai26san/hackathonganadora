import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

import pytest
from fastapi.testclient import TestClient

from app import seed
from app.main import app

REPORTES = ["rubro-cuenta", "financiador", "area-financiador", "region", "mes", "resumen", "movimientos"]


@pytest.fixture(scope="module")
def client():
    seed.run()
    return TestClient(app)


def token(client, user):
    r = client.post("/api/auth/login", data={"username": user, "password": "1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def gestion(client):
    return client.get("/api/catalogos", headers=token(client, "validador")).json()["gestiones"][0]


@pytest.mark.parametrize("rep", REPORTES)
def test_reportes_cuadran_con_movimientos(client, gestion, rep):
    h = token(client, "validador")
    total_mov = client.get(f"/api/reportes/movimientos?gestion={gestion}", headers=h).json()["total_monto"]
    r = client.get(f"/api/reportes/{rep}?gestion={gestion}", headers=h).json()
    ejecutado = r["total_monto"] if rep == "movimientos" else r["total"]["ejecutado"]
    assert ejecutado == pytest.approx(total_mov, abs=0.01)


def test_hijos_suman_al_padre(client, gestion):
    r = client.get(f"/api/reportes/rubro-cuenta?gestion={gestion}", headers=token(client, "validador")).json()
    for rubro in r["filas"]:
        assert sum(c["vigente"] for c in rubro["hijos"]) == pytest.approx(rubro["vigente"], abs=0.01)
        assert sum(c["ejecutado"] for c in rubro["hijos"]) == pytest.approx(rubro["ejecutado"], abs=0.01)


def test_filtros_combinados_reducen_total(client, gestion):
    h = token(client, "validador")
    todo = client.get(f"/api/reportes/financiador?gestion={gestion}", headers=h).json()["total"]["ejecutado"]
    parcial = client.get(f"/api/reportes/financiador?gestion={gestion}&region=1&rubro=1,2", headers=h).json()["total"]["ejecutado"]
    assert 0 < parcial < todo


@pytest.mark.parametrize("formato", ["xlsx", "pdf"])
def test_exportacion(client, gestion, formato):
    r = client.get(f"/api/reportes/area-financiador/export?gestion={gestion}&formato={formato}&comparar={gestion - 1}", headers=token(client, "consulta"))
    assert r.status_code == 200 and len(r.content) > 1000


def test_separacion_de_funciones(client):
    admin, validador, consulta = (token(client, u) for u in ("admin", "validador", "consulta"))
    archivo = {"archivo": ("x.xlsx", b"x")}

    # Administrador: solo usuarios y auditoría, sin acceso a datos financieros
    assert client.get("/api/usuarios", headers=admin).status_code == 200
    assert client.get("/api/auditoria", headers=admin).status_code == 200
    assert client.get("/api/catalogos", headers=admin).status_code == 403
    assert client.get("/api/pendientes", headers=admin).status_code == 403
    assert client.post("/api/importar", data={"tipo": "movimientos"}, files=archivo, headers=admin).status_code == 403

    # Validador: carga, validación y consulta, pero no administra usuarios
    assert client.get("/api/catalogos", headers=validador).status_code == 200
    assert client.get("/api/pendientes", headers=validador).status_code == 200
    assert client.get("/api/usuarios", headers=validador).status_code == 403
    assert client.get("/api/auditoria", headers=validador).status_code == 403

    # Consulta: solo lectura
    assert client.get("/api/catalogos", headers=consulta).status_code == 200
    assert client.get("/api/pendientes", headers=consulta).status_code == 403
    assert client.post("/api/pendientes/validar", json={"ids": [1]}, headers=consulta).status_code == 403
    assert client.post("/api/importar", data={"tipo": "movimientos"}, files=archivo, headers=consulta).status_code == 403
    assert client.get("/api/usuarios", headers=consulta).status_code == 403
    assert client.get("/api/catalogos").status_code == 401


def test_admin_asigna_roles(client):
    admin = token(client, "admin")
    r = client.post("/api/auth/registro", json={"username": "tecnica", "nombre": "Técnica", "password": "clave1"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/pendientes", headers=h).status_code == 403
    uid = next(u["id"] for u in client.get("/api/usuarios", headers=admin).json() if u["username"] == "tecnica")
    assert client.patch(f"/api/usuarios/{uid}", json={"rol": "validador"}, headers=admin).status_code == 200
    assert client.get("/api/pendientes", headers=h).status_code == 200
    assert client.patch(f"/api/usuarios/{uid}", json={"rol": "jefe"}, headers=admin).status_code == 400
    yo = next(u["id"] for u in client.get("/api/usuarios", headers=admin).json() if u["username"] == "admin")
    assert client.patch(f"/api/usuarios/{yo}", json={"rol": "consulta"}, headers=admin).status_code == 400


def test_registro_crea_usuario_de_consulta(client):
    r = client.post("/api/auth/registro", json={"username": "Nuevo", "nombre": "Nuevo Usuario", "password": "clave1"})
    assert r.status_code == 200 and r.json()["usuario"]["rol"] == "consulta"
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/catalogos", headers=h).status_code == 200
    assert client.get("/api/pendientes", headers=h).status_code == 403
    assert client.post("/api/auth/registro", json={"username": "nuevo", "nombre": "x", "password": "clave1"}).status_code == 400


def test_importacion_con_plantilla(client):
    h = token(client, "validador")
    plantilla = client.get("/api/plantilla/movimientos", headers=h).content
    r = client.post("/api/importar", data={"tipo": "movimientos"}, files={"archivo": ("m.xlsx", plantilla)}, headers=h).json()
    assert r["filas_ok"] == 1 and r["filas_error"] == 0


EXCEL_REAL = Path(__file__).resolve().parents[2] / "Prueba ExB Nov 2026 (1) (1).xlsx"


@pytest.mark.skipif(not EXCEL_REAL.exists(), reason="Excel institucional no disponible")
def test_excel_real_cuadra_con_tablas_dinamicas(client):
    from app.verificar import verificar

    h = token(client, "validador")
    r = client.post("/api/importar", data={"tipo": "movimientos"}, files={"archivo": ("bd.xlsx", EXCEL_REAL.read_bytes())}, headers=h).json()
    assert r["filas_error"] == 0 and r["resumen"]["gestion"] == 2026
    assert verificar(str(EXCEL_REAL), 2026)
    # Reimportar reemplaza la gestión en lugar de duplicarla
    r2 = client.post("/api/importar", data={"tipo": "movimientos"}, files={"archivo": ("bd.xlsx", EXCEL_REAL.read_bytes())}, headers=h).json()
    assert r2["resumen"]["movimientos"] == r["resumen"]["movimientos"]
    assert verificar(str(EXCEL_REAL), 2026)


@pytest.mark.skipif(not EXCEL_REAL.exists(), reason="Excel institucional no disponible")
def test_filas_incompletas_prediccion_y_validacion(client, tmp_path):
    from app.generar_prueba import generar
    from app.verificar import verificar

    h = token(client, "validador")
    incompleto = tmp_path / "incompleto.xlsx"
    respuestas = generar(str(EXCEL_REAL), str(incompleto), n=40)
    r = client.post("/api/importar", data={"tipo": "movimientos"}, files={"archivo": ("inc.xlsx", incompleto.read_bytes())}, headers=h).json()
    assert r["resumen"]["pendientes"] == 40
    assert not verificar(str(EXCEL_REAL), 2026)  # sin validar, los totales no cuadran

    pend = client.get("/api/pendientes?gestion=2026", headers=h).json()["filas"]
    assert len(pend) == 40 and all(p["prediccion"] for p in pend)
    aciertos = sum(p["prediccion"][c]["valor"] == " ".join(str(v).split()) for p in pend for c, v in respuestas[p["fila"]].items())
    assert aciertos / sum(len(v) for v in respuestas.values()) >= 0.7

    # Una fila validada por el admin completando a mano las etiquetas reales
    primera = pend[0]
    manual = {c: str(v) for c, v in respuestas[primera["fila"]].items()}
    ok = client.post("/api/pendientes/validar", json={"ids": [primera["id"]], "valores": {primera["id"]: manual}}, headers=h).json()
    assert ok["validadas"] == 1

    # El resto: se corrigen con los valores reales y se validan juntas → los reportes vuelven a cuadrar
    resto = pend[1:]
    valores = {p["id"]: {c: str(v) for c, v in respuestas[p["fila"]].items()} for p in resto}
    ok = client.post("/api/pendientes/validar", json={"ids": [p["id"] for p in resto], "valores": valores}, headers=h).json()
    assert ok["validadas"] == 39 and not ok["incompletas"]
    assert verificar(str(EXCEL_REAL), 2026)
    conteo = client.get("/api/pendientes?gestion=2026", headers=h).json()["conteo"]
    assert conteo == {"pendiente": 0, "validada": 40, "descartada": 0}


@pytest.mark.skipif(not EXCEL_REAL.exists(), reason="Excel institucional no disponible")
def test_validacion_en_bloque_por_confianza(client, tmp_path):
    from app.generar_prueba import generar

    h = token(client, "validador")
    incompleto = tmp_path / "incompleto.xlsx"
    generar(str(EXCEL_REAL), str(incompleto), n=30, semilla=3)
    client.post("/api/importar", data={"tipo": "movimientos"}, files={"archivo": ("inc.xlsx", incompleto.read_bytes())}, headers=h)
    pend = client.get("/api/pendientes?gestion=2026", headers=h).json()["filas"]
    altas = [p for p in pend if p["confianza_min"] is not None and p["confianza_min"] >= 0.8]
    r = client.post("/api/pendientes/validar", json={"umbral": 0.8, "gestion": 2026}, headers=h).json()
    assert r["validadas"] == len(altas) > 0
    quedan = client.get("/api/pendientes?gestion=2026", headers=h).json()
    assert quedan["conteo"]["pendiente"] == len(pend) - len(altas)
    d = client.post("/api/pendientes/descartar", json={"ids": [quedan["filas"][0]["id"]]}, headers=h).json()
    assert d["descartadas"] == 1
    assert client.post("/api/pendientes/predecir", headers=h).json()["filas"] == len(pend) - len(altas) - 1
    ev = client.get("/api/prediccion/evaluacion", headers=h).json()
    assert ev["precision_global"] > 0.7


@pytest.mark.skipif(not EXCEL_REAL.exists(), reason="Excel institucional no disponible")
def test_vista_previa_no_guarda_y_describe_hojas(client, tmp_path):
    from app.generar_prueba import generar

    h = token(client, "validador")
    antes = client.get("/api/importaciones", headers=h).json()
    r = client.post("/api/importar/previsualizar", files={"archivo": ("bd.xlsx", EXCEL_REAL.read_bytes())}, headers=h).json()
    tipos = {x["nombre"]: x["tipo"] for x in r["hojas"]}
    assert r["hoja_importable"] == "BD" and tipos["BD"] == "base" and tipos["Rubro"] == "pivot"
    a = r["analisis"]
    assert (a["gestion"], a["filas"], a["filas_incompletas"]) == (2026, 3574, 0)
    assert (a["total_presupuesto"], a["total_ejecucion"]) == (3163379.01, 528694.16)
    assert client.get("/api/importaciones", headers=h).json() == antes  # no importó nada

    incompleto = tmp_path / "inc.xlsx"
    generar(str(EXCEL_REAL), str(incompleto), n=25)
    r = client.post("/api/importar/previsualizar", files={"archivo": ("inc.xlsx", incompleto.read_bytes())}, headers=h).json()
    bd = next(x for x in r["hojas"] if x["importable"])
    assert r["analisis"]["filas_incompletas"] == 25 and len(bd["incompletas"]) == 25
    assert all(f["faltantes"] for f in bd["incompletas"])
    assert client.post("/api/importar/previsualizar", files={"archivo": ("x.xlsx", b"no")}, headers=h).status_code == 400
    assert client.post("/api/importar/previsualizar", files={"archivo": ("x.xlsx", b"no")}, headers=token(client, "admin")).status_code == 403

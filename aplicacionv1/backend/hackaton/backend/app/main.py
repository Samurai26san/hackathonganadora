from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import exports, importer, prediccion, previsualizar, reports
from .importer_contable import registrar_validada
from .auth import ROLES, auditar, create_token, current_user, hash_password, requiere, verify_password
from .db import Base, engine, get_db
from .models import FilaPendiente, Area, Auditoria, Cuenta, Financiador, Importacion, Movimiento, Presupuesto, Region, Rubro, TipoCambio, Usuario

Base.metadata.create_all(engine)

app = FastAPI(title="Sistema de Control Presupuestario y Ejecución Financiera", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition"])


def filtros_query(request: Request) -> dict:
    """Lee filtros combinados desde la URL: ?financiador=1,2&region=3&mes=1,2,3"""
    out = {}
    for f in reports.FILTROS:
        v = request.query_params.get(f)
        if v:
            out[f] = [int(x) for x in v.split(",") if x.strip()]
    return out


# ---------- Autenticación ----------
@app.post("/api/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter_by(username=form.username, activo=True).first()
    if not user or not verify_password(form.password, user.password_hash):
        auditar(db, form.username, "login_fallido")
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    auditar(db, user.username, "login")
    return {"access_token": create_token(user), "token_type": "bearer", "usuario": {"username": user.username, "nombre": user.nombre, "rol": user.rol}}


class RegistroIn(BaseModel):
    username: str
    nombre: str
    password: str


@app.post("/api/auth/registro")
def registro(body: RegistroIn, db: Session = Depends(get_db)):
    """Autoregistro: siempre crea un usuario de consulta; solo el admin puede asignar otro rol."""
    username = body.username.strip().lower()
    if len(username) < 3 or len(body.password) < 4:
        raise HTTPException(400, "Usuario de al menos 3 caracteres y contraseña de al menos 4")
    if db.query(Usuario).filter_by(username=username).first():
        raise HTTPException(400, "Ese nombre de usuario ya existe")
    user = Usuario(username=username, nombre=body.nombre.strip() or username, rol="consulta", password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    auditar(db, username, "registro")
    return {"access_token": create_token(user), "token_type": "bearer", "usuario": {"username": user.username, "nombre": user.nombre, "rol": user.rol}}


@app.get("/api/auth/me")
def me(user: Usuario = Depends(current_user)):
    return {"username": user.username, "nombre": user.nombre, "rol": user.rol}


# ---------- Catálogos ----------
@app.get("/api/catalogos")
def catalogos(db: Session = Depends(get_db), _=Depends(requiere("ver"))):
    def lista(m):
        return [{"id": r.id, "codigo": r.codigo, "nombre": r.nombre} for r in db.query(m).order_by(m.codigo)]

    gestiones = sorted(
        {g for (g,) in db.query(Presupuesto.gestion).distinct()} | {g for (g,) in db.query(Movimiento.gestion).distinct()},
        reverse=True,
    )
    return {
        "gestiones": gestiones,
        "rubro": lista(Rubro),
        "cuenta": [{"id": c.id, "codigo": c.codigo, "nombre": c.nombre, "rubro_id": c.rubro_id} for c in db.query(Cuenta).order_by(Cuenta.codigo)],
        "financiador": lista(Financiador),
        "area": lista(Area),
        "region": lista(Region),
        "mes": [{"id": i, "codigo": str(i), "nombre": reports.nombre_mes(i)} for i in range(13)],
        "reportes": [{"id": k, "titulo": v["titulo"]} for k, v in reports.REPORTES.items()],
    }


# ---------- Reportes ----------
def _generar(db, reporte, gestion, filtros, comparar, limite=500, offset=0):
    if reporte not in reports.REPORTES:
        raise HTTPException(404, "Reporte no existe")
    if reporte == "movimientos":
        return reports.movimientos(db, gestion, filtros, limite, offset)
    return reports.generar(db, reporte, gestion, filtros, comparar)


@app.get("/api/reportes/{reporte}")
def reporte(reporte: str, gestion: int, request: Request, comparar: int | None = None, limite: int = 500, offset: int = 0,
            db: Session = Depends(get_db), _=Depends(requiere("ver"))):
    return _generar(db, reporte, gestion, filtros_query(request), comparar, limite, offset)


@app.get("/api/reportes/{reporte}/export")
def exportar(reporte: str, gestion: int, formato: str, request: Request, comparar: int | None = None,
             db: Session = Depends(get_db), user: Usuario = Depends(requiere("ver"))):
    rep = _generar(db, reporte, gestion, filtros_query(request), comparar, limite=100_000)
    if formato == "xlsx":
        data, mime = exports.excel(rep), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif formato == "pdf":
        data, mime = exports.pdf(rep), "application/pdf"
    else:
        raise HTTPException(400, "Formato debe ser xlsx o pdf")
    auditar(db, user.username, "exportar", {"reporte": reporte, "gestion": gestion, "formato": formato})
    nombre = f"{reporte}_{gestion}.{formato}"
    return Response(data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@app.get("/api/dashboard")
def dashboard(gestion: int, request: Request, db: Session = Depends(get_db), _=Depends(requiere("ver"))):
    f = filtros_query(request)
    gestiones = {g for (g,) in db.query(Movimiento.gestion).distinct()} | {g for (g,) in db.query(Presupuesto.gestion).distinct()}
    anterior = max((g for g in gestiones if g < gestion), default=None)

    def filas(rep):
        return [{k: n[k] for k in ("id", "nombre", "vigente", "ejecutado", "saldo", "porcentaje")}
                for n in reports.generar(db, rep, gestion, f)["filas"]]

    rubro_cuenta = reports.generar(db, "rubro-cuenta", gestion, f)
    total = rubro_cuenta["total"]
    por_rubro = [{k: n[k] for k in ("id", "nombre", "vigente", "ejecutado", "saldo", "porcentaje")} for n in rubro_cuenta["filas"]]
    por_fin, por_area, por_region = filas("financiador"), filas("area-financiador"), filas("region")
    mensual = reports.serie_mensual(db, gestion, f)
    meses_con_dato = [m for m in mensual if m["acumulado"] is not None and m["mes"] <= max((x["mes"] for x in mensual if x["ejecutado"]), default=0)]
    programado = meses_con_dato[-1]["presupuesto_acumulado"] if meses_con_dato else 0.0
    sin_programar = reports.generar(db, "mes", gestion, f)
    sin_programar = next((n["vigente"] for n in sin_programar["filas"] if n["id"] == 0), 0.0)
    top_saldos = sorted(
        ({"rubro": r["nombre"], "cuenta": c["nombre"], "vigente": c["vigente"], "ejecutado": c["ejecutado"],
          "saldo": c["saldo"], "porcentaje": c["porcentaje"]} for r in rubro_cuenta["filas"] for c in r["hijos"]),
        key=lambda x: -x["saldo"])[:8]
    pend = db.query(FilaPendiente).filter_by(gestion=gestion, estado="pendiente")
    n_pend = pend.count()
    ultima = db.query(func.max(Movimiento.fecha)).filter(Movimiento.gestion == gestion).scalar()

    # Hallazgos automáticos para la lectura ejecutiva del tablero
    hallazgos = []
    bs = lambda v: f"Bs {v:,.0f}".replace(",", ".")
    if programado and meses_con_dato:
        cumpl = total["ejecutado"] / programado * 100
        hallazgos.append({"tipo": "ok" if cumpl >= 85 else "alerta",
                          "texto": f"Se ejecutó el {cumpl:.0f}% de lo programado entre Ene y {meses_con_dato[-1]['nombre']} "
                                   f"({bs(total['ejecutado'])} de {bs(programado)})."})
    if total["vigente"] and sin_programar:
        hallazgos.append({"tipo": "alerta", "texto": f"El {sin_programar / total['vigente'] * 100:.0f}% del presupuesto "
                                                     f"({bs(sin_programar)}) aún no está programado por mes (PTTO)."})
    relevantes = [r for r in por_rubro if total["vigente"] and r["vigente"] >= 0.05 * total["vigente"] and r["porcentaje"] is not None]
    if relevantes:
        bajo = min(relevantes, key=lambda r: r["porcentaje"])
        hallazgos.append({"tipo": "alerta", "texto": f"El rubro {bajo['nombre']} tiene la menor ejecución: {bajo['porcentaje']:.1f}% "
                                                     f"con un saldo de {bs(bajo['saldo'])}."})
    fins = [x for x in por_fin if x["porcentaje"] is not None]
    if len(fins) > 1:
        alto, bajo = max(fins, key=lambda x: x["porcentaje"]), min(fins, key=lambda x: x["porcentaje"])
        hallazgos.append({"tipo": "info", "texto": f"Por financiador, {alto['nombre']} lidera con {alto['porcentaje']:.1f}% de ejecución; "
                                                   f"{bajo['nombre']} es el más rezagado con {bajo['porcentaje']:.1f}%."})
    if any(m["ejecutado"] for m in mensual):
        pico = max((m for m in mensual if m["ejecutado"]), key=lambda m: m["ejecutado"])
        hallazgos.append({"tipo": "info", "texto": f"{pico['nombre']} fue el mes de mayor ejecución con {bs(pico['ejecutado'])}."})
    if n_pend:
        hallazgos.append({"tipo": "alerta", "texto": f"{n_pend} filas con etiquetas faltantes esperan validación del administrador "
                                                     f"y aún no suman en los reportes."})

    return {
        "gestion": gestion,
        "total": total,
        "programado_a_la_fecha": round(programado, 2),
        "sin_programar": round(sin_programar, 2),
        "por_rubro": por_rubro,
        "por_financiador": por_fin,
        "por_region": por_region,
        "por_area": por_area,
        "top_saldos": top_saldos,
        "mensual": mensual,
        "mensual_anterior": reports.serie_mensual(db, anterior, f) if anterior else None,
        "gestion_anterior": anterior,
        "hallazgos": hallazgos,
        "pendientes": n_pend,
        "ultima_actualizacion": ultima.isoformat() if ultima else None,
    }


# ---------- Importación ----------
@app.post("/api/importar")
async def importar(tipo: str = Form("movimientos"), archivo: UploadFile = File(...), gestion: int | None = Form(None),
                   db: Session = Depends(get_db), user: Usuario = Depends(requiere("importar"))):
    if tipo not in ("movimientos", "presupuestos"):
        raise HTTPException(400, "tipo debe ser movimientos o presupuestos")
    try:
        imp = importer.importar(db, await archivo.read(), archivo.filename, tipo, user.id, gestion)
    except ValueError as e:
        raise HTTPException(400, str(e))
    auditar(db, user.username, "importar", {"archivo": archivo.filename, "tipo": imp.tipo, "ok": imp.filas_ok, "errores": imp.filas_error})
    return {"id": imp.id, "tipo": imp.tipo, "filas_ok": imp.filas_ok, "filas_error": imp.filas_error, "errores": imp.errores, "resumen": imp.resumen}


@app.post("/api/importar/previsualizar")
async def previsualizar_archivo(archivo: UploadFile = File(...), gestion: int | None = Form(None),
                                db: Session = Depends(get_db), _=Depends(requiere("importar"))):
    """Vista previa del Excel (una pestaña por hoja) sin guardar nada."""
    try:
        return previsualizar.previsualizar(db, await archivo.read(), archivo.filename, gestion)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/importaciones")
def importaciones(db: Session = Depends(get_db), _=Depends(requiere("ver"))):
    return [
        {"id": i.id, "archivo": i.archivo, "tipo": i.tipo, "fecha": i.fecha.isoformat(), "filas_ok": i.filas_ok, "filas_error": i.filas_error, "resumen": i.resumen}
        for i in db.query(Importacion).order_by(Importacion.id.desc()).limit(50)
    ]


@app.get("/api/plantilla/{tipo}")
def descargar_plantilla(tipo: str, _=Depends(requiere("ver"))):
    return Response(importer.plantilla(tipo), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="plantilla_{tipo}.xlsx"'})


# ---------- Tipos de cambio ----------
class TipoCambioIn(BaseModel):
    fecha: date
    moneda: str
    valor: float


@app.get("/api/tipos-cambio")
def listar_tc(db: Session = Depends(get_db), _=Depends(requiere("ver"))):
    return [{"id": t.id, "fecha": t.fecha.isoformat(), "moneda": t.moneda, "valor": float(t.valor)}
            for t in db.query(TipoCambio).order_by(TipoCambio.fecha.desc()).limit(100)]


@app.post("/api/tipos-cambio")
def crear_tc(body: TipoCambioIn, db: Session = Depends(get_db), user: Usuario = Depends(requiere("importar"))):
    db.add(TipoCambio(**body.model_dump()))
    db.commit()
    auditar(db, user.username, "tipo_cambio", body.model_dump(mode="json"))
    return {"ok": True}


# ---------- Administración ----------
class UsuarioIn(BaseModel):
    username: str
    nombre: str
    password: str
    rol: str = "consulta"


@app.get("/api/usuarios")
def listar_usuarios(db: Session = Depends(get_db), _=Depends(requiere("administrar"))):
    return [{"id": u.id, "username": u.username, "nombre": u.nombre, "rol": u.rol, "activo": u.activo} for u in db.query(Usuario)]


@app.post("/api/usuarios")
def crear_usuario(body: UsuarioIn, db: Session = Depends(get_db), user: Usuario = Depends(requiere("administrar"))):
    if body.rol not in ROLES:
        raise HTTPException(400, "Rol inválido")
    if db.query(Usuario).filter_by(username=body.username).first():
        raise HTTPException(400, "El usuario ya existe")
    db.add(Usuario(username=body.username, nombre=body.nombre, rol=body.rol, password_hash=hash_password(body.password)))
    db.commit()
    auditar(db, user.username, "crear_usuario", {"username": body.username, "rol": body.rol})
    return {"ok": True}


class UsuarioPatch(BaseModel):
    rol: str | None = None
    activo: bool | None = None


@app.patch("/api/usuarios/{uid}")
def editar_usuario(uid: int, body: UsuarioPatch, db: Session = Depends(get_db), user: Usuario = Depends(requiere("administrar"))):
    u = db.get(Usuario, uid)
    if not u:
        raise HTTPException(404, "Usuario no existe")
    if u.id == user.id:
        raise HTTPException(400, "No puede modificar su propio usuario")
    if body.rol is not None:
        if body.rol not in ROLES:
            raise HTTPException(400, "Rol inválido")
        u.rol = body.rol
    if body.activo is not None:
        u.activo = body.activo
    db.commit()
    auditar(db, user.username, "editar_usuario", {"username": u.username, **body.model_dump(exclude_none=True)})
    return {"ok": True}


@app.get("/api/auditoria")
def auditoria(db: Session = Depends(get_db), _=Depends(requiere("administrar"))):
    return [{"id": a.id, "fecha": a.fecha.isoformat(), "usuario": a.usuario, "accion": a.accion, "detalle": a.detalle}
            for a in db.query(Auditoria).order_by(Auditoria.id.desc()).limit(200)]


# ---------- Validación de filas con etiquetas faltantes (solo admin) ----------
def _pendiente_json(p: FilaPendiente) -> dict:
    return {
        "id": p.id, "gestion": p.gestion, "fila": p.fila, "mes": p.mes, "mes_nombre": reports.nombre_mes(p.mes),
        "fecha": p.fecha.isoformat() if p.fecha else None, "comprobante": p.comprobante, "descripcion": p.descripcion,
        "cuenta_contable": p.cuenta_contable, "presupuesto": float(p.presupuesto), "ejecucion": float(p.ejecucion),
        "etiquetas": p.etiquetas, "faltantes": p.faltantes, "prediccion": p.prediccion or {}, "valores": p.valores,
        "estado": p.estado, "origen": p.origen, "validado_por": p.validado_por,
        "validado_en": p.validado_en.isoformat() if p.validado_en else None,
        "confianza_min": min((v["confianza"] for v in (p.prediccion or {}).values()), default=None)
        if len(p.prediccion or {}) == len(p.faltantes) else None,
    }


@app.get("/api/pendientes")
def listar_pendientes(gestion: int | None = None, estado: str = "pendiente", db: Session = Depends(get_db), _=Depends(requiere("validar"))):
    q = db.query(FilaPendiente).filter_by(estado=estado)
    if gestion:
        q = q.filter_by(gestion=gestion)
    filas = [_pendiente_json(p) for p in q.order_by(FilaPendiente.fila)]
    conteo = dict(db.query(FilaPendiente.estado, func.count()).filter(*( [FilaPendiente.gestion == gestion] if gestion else [] ))
                  .group_by(FilaPendiente.estado).all())
    return {"filas": filas, "conteo": {e: conteo.get(e, 0) for e in ("pendiente", "validada", "descartada")}}


@app.get("/api/pendientes/opciones")
def opciones_etiquetas(db: Session = Depends(get_db), _=Depends(requiere("validar"))):
    """Valores existentes por campo, para completar etiquetas a mano."""
    return {
        "fondo": sorted(f.codigo for f in db.query(Financiador)),
        "rubro": sorted(r.codigo for r in db.query(Rubro)),
        "cuenta": sorted({c.nombre for c in db.query(Cuenta)}),
        "area": sorted(a.codigo for a in db.query(Area)),
        "region": sorted(r.codigo for r in db.query(Region)),
    }


class ValidarIn(BaseModel):
    ids: list[int] = []
    # Etiquetas completadas o corregidas por el admin: {id: {campo: valor}}
    valores: dict[int, dict[str, str]] = {}
    # Validar en bloque todas las pendientes cuya predicción tenga al menos esta confianza
    umbral: float | None = None
    gestion: int | None = None


@app.post("/api/pendientes/validar")
def validar_pendientes(body: ValidarIn, db: Session = Depends(get_db), user: Usuario = Depends(requiere("validar"))):
    q = db.query(FilaPendiente).filter_by(estado="pendiente")
    if body.umbral is not None:
        if body.gestion:
            q = q.filter_by(gestion=body.gestion)
        filas = [p for p in q if (c := _pendiente_json(p)["confianza_min"]) is not None and c >= body.umbral]
    else:
        filas = q.filter(FilaPendiente.id.in_(body.ids)).all() if body.ids else []

    cat = importer.Catalogos(db)
    validadas, incompletas = [], []
    for p in filas:
        manual = {k: v.strip() for k, v in body.valores.get(p.id, {}).items() if v and v.strip()}
        valores, origenes = dict(p.etiquetas), set()
        for campo in p.faltantes:
            if campo in manual:
                valores[campo] = manual[campo]
                origenes.add("manual")
            elif campo in (p.prediccion or {}):
                valores[campo] = p.prediccion[campo]["valor"]
                origenes.add("prediccion")
        if any(not valores.get(c) for c in prediccion.CAMPOS):
            incompletas.append(p.fila)
            continue
        registrar_validada(db, cat, p, valores)
        p.valores, p.estado = valores, "validada"
        p.origen = "mixto" if len(origenes) > 1 else (origenes.pop() if origenes else "manual")
        p.validado_por, p.validado_en = user.username, datetime.utcnow()
        validadas.append(p.id)
    db.commit()
    auditar(db, user.username, "validar_filas", {"cantidad": len(validadas), "umbral": body.umbral, "ids": validadas[:50]})
    return {"validadas": len(validadas), "incompletas": incompletas}


@app.post("/api/pendientes/descartar")
def descartar_pendientes(body: ValidarIn, db: Session = Depends(get_db), user: Usuario = Depends(requiere("validar"))):
    filas = db.query(FilaPendiente).filter(FilaPendiente.id.in_(body.ids), FilaPendiente.estado == "pendiente").all()
    for p in filas:
        p.estado, p.validado_por, p.validado_en = "descartada", user.username, datetime.utcnow()
    db.commit()
    auditar(db, user.username, "descartar_filas", {"ids": [p.id for p in filas]})
    return {"descartadas": len(filas)}


@app.post("/api/pendientes/predecir")
def repredecir(db: Session = Depends(get_db), user: Usuario = Depends(requiere("validar"))):
    """Reentrena con todas las filas completas (incluidas las ya validadas) y vuelve a predecir."""
    modelos = prediccion.entrenar(prediccion.filas_entrenamiento(db))
    filas = db.query(FilaPendiente).filter_by(estado="pendiente").all()
    for p in filas:
        d = {"tipo": "ejec" if float(p.ejecucion) else "ppto", "mes": p.mes, "descripcion": p.descripcion,
             "cuenta_contable": p.cuenta_contable, "etiquetas": p.etiquetas}
        p.prediccion = prediccion.predecir(modelos, d, p.faltantes)
    db.commit()
    auditar(db, user.username, "repredecir", {"filas": len(filas)})
    return {"filas": len(filas)}


_cache_eval: dict = {}


@app.get("/api/prediccion/evaluacion")
def evaluacion_modelo(db: Session = Depends(get_db), _=Depends(requiere("validar"))):
    """Precisión del modelo medida ocultando etiquetas conocidas (hold-out 20%)."""
    filas = prediccion.filas_entrenamiento(db)
    clave = (len(filas), db.query(func.max(Movimiento.id)).scalar(), db.query(func.max(Presupuesto.id)).scalar())
    if _cache_eval.get("clave") != clave:
        _cache_eval.update(clave=clave, valor=prediccion.evaluar(filas))
    return _cache_eval["valor"]


# ---------- Frontend compilado (producción: un solo servidor) ----------
_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="web")

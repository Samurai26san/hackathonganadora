import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Auditoria, Usuario

SECRET = os.getenv("JWT_SECRET", "cambiar-en-produccion-esta-clave-de-32-bytes-min")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Separación de funciones: quien administra accesos no toca los datos financieros,
# quien carga y valida datos no administra accesos, y la consulta es de solo lectura.
ROLES = ("admin", "validador", "consulta")
PERMISOS = {
    "admin": {"administrar"},
    "validador": {"ver", "importar", "validar"},
    "consulta": {"ver"},
}


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    salt, dk = stored.split("$")
    calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000)
    return hmac.compare_digest(calc.hex(), dk)


def create_token(user: Usuario) -> str:
    payload = {"sub": user.username, "rol": user.rol, "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> Usuario:
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Token inválido o expirado")
    user = db.query(Usuario).filter_by(username=data["sub"], activo=True).first()
    if not user:
        raise HTTPException(401, "Usuario no encontrado")
    return user


def requiere(permiso: str):
    def dep(user: Usuario = Depends(current_user)) -> Usuario:
        if permiso not in PERMISOS.get(user.rol, set()):
            raise HTTPException(403, f"Permiso '{permiso}' requerido")
        return user
    return dep


def auditar(db: Session, usuario: str | None, accion: str, detalle: dict | None = None):
    db.add(Auditoria(usuario=usuario, accion=accion, detalle=detalle))
    db.commit()

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# PostgreSQL en producción (docker compose); SQLite como respaldo para desarrollo rápido.
_SQLITE = Path(__file__).resolve().parent.parent / "presupuesto.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_SQLITE}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""Async Alembic runner using the configured PostgreSQL URL."""
import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings
from app.core.database import Base
import app.models  # noqa: F401

target_metadata = Base.metadata


def migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run():
    engine = create_async_engine(get_settings().database_uri)
    async with engine.connect() as connection:
        await connection.run_sync(migrations)
    await engine.dispose()


asyncio.run(run())

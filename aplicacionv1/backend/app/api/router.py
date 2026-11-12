"""Versioned API routing."""

from fastapi import APIRouter

from app.api.v1 import (
    accounting,
    admin,
    auth,
    budget,
    chat,
    curation,
    data_changes,
    technical_reports,
)

api_router = APIRouter()
for router in [
    auth.router,
    budget.router,
    chat.router,
    admin.router,
    data_changes.router,
    curation.router,
    accounting.router,
    technical_reports.router,
]:
    api_router.include_router(router)

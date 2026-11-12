"""Versioned API routing."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, budget, chat, data_changes

api_router = APIRouter()
for router in [
    auth.router,
    budget.router,
    chat.router,
    admin.router,
    data_changes.router,
]:
    api_router.include_router(router)

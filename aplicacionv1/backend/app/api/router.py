"""Versioned API routing."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, budget, chat

api_router = APIRouter()
for router in [auth.router, budget.router, chat.router, admin.router]:
    api_router.include_router(router)

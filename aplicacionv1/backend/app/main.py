"""ExB API lifecycle, precise error mapping, request IDs and CSRF origin guard."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import jwt
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import AppException

settings = get_settings()
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30, connect=5), follow_redirects=False
    ) as http:
        app.state.http = http
        yield
    await engine.dispose()


app = FastAPI(title=settings.project_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["Content-Disposition", "X-Request-ID"],
)


@app.middleware("http")
async def request_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = str(uuid4())
    started = time.monotonic()
    origin = request.headers.get("origin")
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and origin
        and origin not in settings.backend_cors_origins
        and origin != f"{request.url.scheme}://{request.headers.get('host')}"
    ):
        return JSONResponse(
            {
                "detail": "Origen de solicitud no autorizado.",
                "code": "csrf_origin",
                "status": 403,
            },
            status_code=403,
        )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path.startswith(settings.api_v1_prefix):
        response.headers["Cache-Control"] = "no-store"
    logger.info(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=round((time.monotonic() - started) * 1000),
    )
    return response


@app.exception_handler(AppException)
async def domain_error(request: Request, error: AppException) -> JSONResponse:
    return JSONResponse(
        {"detail": error.detail, "code": error.code, "status": error.status},
        status_code=error.status,
    )


@app.exception_handler(httpx.HTTPError)
async def upstream_error(request: Request, error: httpx.HTTPError) -> JSONResponse:
    return JSONResponse(
        {
            "detail": "Un servicio institucional no está disponible. Intenta nuevamente.",
            "code": "upstream_unavailable",
            "status": 503,
        },
        status_code=503,
    )


@app.exception_handler(IntegrityError)
async def conflict(request: Request, error: IntegrityError) -> JSONResponse:
    return JSONResponse(
        {
            "detail": "El registro entra en conflicto con información existente.",
            "code": "conflict",
            "status": 409,
        },
        status_code=409,
    )


@app.get(
    "/health",
    summary="Estado del proceso",
    description="No expone secretos ni información financiera.",
)
async def health() -> dict[str, object]:
    return {"status": "ok", "auth_mode": settings.auth_mode, "version": "1.0.0"}


@app.get(
    "/ready",
    summary="Disponibilidad de base de datos",
    description="Comprueba PostgreSQL sin invocar el LLM ni TEI.",
)
async def ready() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready"}


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.exception_handler(jwt.InvalidTokenError)
async def invalid_identity(
    request: Request, error: jwt.InvalidTokenError
) -> JSONResponse:
    return JSONResponse(
        {
            "detail": "La identidad institucional no pudo verificarse.",
            "code": "invalid_identity",
            "status": 401,
        },
        status_code=401,
    )

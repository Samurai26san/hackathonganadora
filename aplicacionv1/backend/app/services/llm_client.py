"""OpenAI-compatible local llama.cpp client; no hosted model fallback."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppException


class LLMClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.http = http

    async def chat_completion(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        settings = get_settings()
        try:
            response = await self.http.post(
                f"{settings.llm_server_url.rstrip('/')}/chat/completions",
                json={
                    "model": settings.llm_model_name,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "stream": False,
                    "temperature": 0.1,
                    "max_tokens": 1024,
                },
                timeout=settings.llm_timeout,
            )
        except httpx.ConnectError as error:
            raise AppException(
                "Qwen local todavía no está disponible. En el primer arranque debe terminar la descarga y cargar el modelo. Los informes financieros siguen disponibles mientras se prepara Juku.",
                503,
                "llm_not_ready",
            ) from error
        if response.status_code == 503:
            raise AppException(
                "Qwen está cargando el modelo. Espera a que finalice y vuelve a enviar tu consulta.",
                503,
                "llm_loading",
            )
        response.raise_for_status()
        data: dict[str, Any] = response.json()["choices"][0]["message"]
        return data

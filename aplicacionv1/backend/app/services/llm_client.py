"""OpenAI-compatible local llama.cpp client; no hosted model fallback."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class LLMClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self.http = http

    async def chat_completion(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        settings = get_settings()
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
        response.raise_for_status()
        data: dict[str, Any] = response.json()["choices"][0]["message"]
        return data

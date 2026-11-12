"""Validated configuration; production never enables demo authentication."""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    app_env: str = "development"
    project_name: str = "ExB Finanzas · Juku"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = ""
    database_uri: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/budget_ai"
    )
    backend_cors_origins: list[str] = ["http://localhost:8080"]
    auth_mode: str = "oidc"
    cookie_secure: bool = True
    session_hours: int = 8
    oidc_provider_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:8080/api/v1/auth/callback"
    oidc_scopes: str = "openid profile email"
    llm_server_url: str = "http://localhost:18081/v1"
    llm_model_name: str = "qwen2.5-7b-instruct-q4_k_m"
    llm_timeout: int = 90
    embeddings_server_url: str = "http://localhost:8082"
    embedding_dim: int = 1024
    rag_similarity_threshold: float = 0.60

    @model_validator(mode="after")
    def production_guards(self) -> Settings:
        if self.auth_mode not in {"oidc", "demo"}:
            raise ValueError("AUTH_MODE debe ser oidc o demo")
        if self.app_env == "production":
            if self.auth_mode != "oidc" or not self.cookie_secure:
                raise ValueError("Producción exige OIDC y cookies Secure")
            if len(self.secret_key) < 32 or not self.oidc_provider_url:
                raise ValueError("Configura SECRET_KEY y proveedor OIDC en producción")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

# PROMPT MAESTRO IMPLEMENTACIÓN — FASE 1 MVP: COPILOTO PRESUPUESTARIO INSTITUCIONAL
**Objetivo:** Generar **repositorio completo, funcional y probado** para la Fase 1 (MVP Web).
**Stack:** Flutter Web (Frontend) + FastAPI/PostgreSQL/pgvector (Backend) + Qwen2.5-7B-GGUF/llama.cpp (LLM Server) + BGE-m3/TEI (Embeddings RAG).
**Arquitectura:** Tool Calling Estricto (Motor Financiero Determinista + RAG Normativo). **Sin App Móvil Nativa. Sin Inferencia Local en Cliente.**

---

## 1. REGLAS INNEGOCIABLES (LEER ANTES DE ESCRIBIR UNA LÍNEA)

1.  **CÁLCULOS MONETARIOS:** Solo `Decimal` (Python) / `int` (centavos) / `decimal.dart` (Flutter). **NUNCA `float`/`double`.**
2.  **SQL:** Solo parametrizado via SQLAlchemy Core/ORM en `FinancialEngine`. **El LLM NUNCA genera SQL.**
3.  **TOOL CALLING:** Definición centralizada (JSON Schema/OpenAI). Validador Pydantic estricto **antes** de ejecutar.
4.  **SEPARACIÓN DE PREOCUPACIONES:**
    *   **Datos Duros (Montos, Ejecución, Saldos, Comparativas):** Herramientas Financieras (`get_execution_*`, `compare_*`) -> `FinancialEngine` -> PostgreSQL.
    *   **Conocimiento Normativo (Leyes, Manuales, Clasificadores, FAQs, Procedimientos):** Herramienta `search_institutional_knowledge` -> `RAGService` -> pgvector/TEI.
    *   **El LLM decide qué tool usar basándose en `description`.**
5.  **DICCIONARIO DE DATOS:** Tabla `DataDictionary` en BD. Prompt del sistema se inyecta dinámicamente al arrancar chat.
6.  **CONTEXTO CONVERSACIONAL:** Objeto `ConversationContext` (filtros activos: años, región, área, financiador, agrupación, reporte_base) persistido en BD por sesión. **No solo historial de texto.**
7.  **SEGURIDAD:** OAuth2/OIDC PKCE (Auth0/Keycloak/Google). RBAC (Roles + Alcance Datos: región/área/financiador). Auditoría (`AuditLog`). Cookies HttpOnly Secure.
8.  **7 INFORMES OBLIGATORIOS:** El `FinancialEngine` debe cubrir exactamente estos 7 endpoints base deterministas.
9.  **NO IMPLEMENTAR EN FASE 1:** App Android/iOS nativa, Inferencia local (llama.cpp FFI), SQLite Cifrado, Sincronización Offline, Fine-tuning, Escritura en BD.
10. **CALIDAD:** `mypy --strict` pasa en backend. `ruff` + `black` formatean. `flutter analyze` sin errores. Tests unitarios críticos (`FinancialEngine`, `RAGService`, `Auth`).

---

## 2. ARQUITECTURA FÍSICA (DOCKER COMPOSE - 5 SERVICIOS)

```text
[Usuario Navegador] <--HTTPS/WSS (Puerto 80/443)--> [Frontend: Nginx + Flutter Web Build]
                                                           |
                                                           |-- REST/WS (API) --> [Backend: FastAPI :8000]
                                                                                           |
                                                                                           |---> [PostgreSQL :5432] (Datos Presupuestarios + Diccionario + Knowledge Chunks + Auditoria + Sesiones + Usuarios)
                                                                                           |
                                                                                           |---> [LLM Server: llama.cpp :8080] (Qwen2.5-7B-Instruct-Q4_K_M.GGUF --ctx-size 8192 --n-gpu-layers -1)
                                                                                           |
                                                                                           |---> [Embeddings Server: TEI :8082] (BAAI/bge-m3 -- CPU/GPU)
3. ESTRUCTURA DE REPOSITORIO A GENERAR (EXACTA)
Genera todos los directorios y archivos listados. Si es código, pon el esqueleto completo con imports, tipado, docstrings y lógica central. Si es configuración, pon el contenido completo.
budget-ai-copilot/
│
├── docker-compose.yml          # ORQUESTADOR PRINCIPAL (5 servicios, redes, volúmenes, healthchecks)
├── .env.example                # TODAS las variables de entorno (Ver Sección 5)
├── README.md                   # Instrucciones: Levantar, Variables, Modelos, Ingesta, Tests
├── Makefile                    # Comandos cortos: make up, make down, make logs, make test, make migrate, make seed
│
├── backend/
│   ├── Dockerfile              # Multi-stage: builder (poetry/pip) -> runtime (slim). Non-root user.
│   ├── requirements.txt        # Dependencias pinned (Ver Sección 4)
│   ├── pyproject.toml          # Config: mypy, ruff, black, pytest, coverage
│   ├── alembic.ini
│   ├── scripts/
│   │   ├── seed_data.py        # Datos sintéticos realistas (Usuarios, Roles, Regiones, Áreas, Financiadores, Rubros, Cuentas, Presupuestos, Movimientos, Tipos Cambio, Gestion)
│   │   └── ingest_knowledge.py # Ingesta docs (PDF/DOCX/TXT/MD) -> Chunks -> Embeddings (TEI) -> pgvector
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI App, Lifespan (DB, HTTP Clients), Middlewares (CORS, Logging, Error Handler), Routers
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py       # Pydantic Settings v2 (Carga .env, Valida, Computed Properties)
│   │   │   ├── database.py     # AsyncEngine (asyncpg), AsyncSessionLocal, Base, get_db Dependency
│   │   │   ├── security.py     # OAuth2 PKCE, JWT Decode/Validate, get_current_user, require_roles/scopes, Hash (bcrypt)
│   │   │   ├── exceptions.py   # Custom Exceptions (AppException, NotFound, Forbidden, Validation) + Handlers Globales
│   │   │   └── prompts.py      # SYSTEM_PROMPT_BASE (String), build_system_prompt(dict_context) function
│   │   ├── models/             # SQLAlchemy 2.0 (Mapped, MappedColumn, relationship)
│   │   │   ├── __init__.py
│   │   │   ├── user.py         # User, Role, Permission, UserRole, UserScope (Alcance: region_ids, area_ids, financier_ids)
│   │   │   ├── budget.py       # Gestion, Region, Area, Financier, Rubro, Cuenta, Budget, BudgetModification, Movement, ExchangeRate, ImportLog
│   │   │   ├── dictionary.py   # DataDictionary (termino_usuario, columna_canonica, tabla_origen, descripcion, sinonimos_json, version, activo)
│   │   │   ├── knowledge.py    # KnowledgeChunk (id, content, content_tokens, embedding:Vector(1024), source_type, source_id, source_title, chunk_index, tags, metadata_json, created_at) + HNSW Index
│   │   │   ├── audit.py        # AuditLog (user_id, action, resource_type, resource_id, payload_json, ip, timestamp, status)
│   │   │   └── session.py      # ChatSession (user_id, title, created_at), ChatMessage (session_id, role, content_json, tool_calls_json, tool_results_json, sequence), ConversationContext (session_id PK, active_filters_json, current_report, updated_at)
│   │   ├── schemas/            # Pydantic v2 (Request/Response/OpenAPI Docs)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # Token, UserOut, LoginResponse
│   │   │   ├── budget.py       # BudgetFilterParams, KPISummary, DataRow, FinancialReportResult, ExportRequest
│   │   │   ├── chat.py         # ChatRequest, ChatEvent (delta/tool_call/tool_result/context_update/done/error), ToolCallRequest, ToolResultPayload, ContextUpdatePayload, SearchKnowledgeParams
│   │   │   ├── dictionary.py   # DictionaryEntryCreate, DictionaryEntryOut
│   │   │   └── knowledge.py    # KnowledgeIngestRequest, KnowledgeSearchRequest, KnowledgeChunkOut
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py             # POST /login, GET /callback, GET /me, POST /refresh, POST /logout
│   │   │   │   ├── budget.py           # GET /execution/account, /financier, /area, /region, /monthly, /movements, /summary, /compare (7 Informes + Comparativa)
│   │   │   │   ├── chat.py             # POST /chat/stream (SSE), GET /sessions, POST /sessions, GET /sessions/{id}/context, POST /sessions/{id}/context/reset
│   │   │   │   ├── dictionary.py       # CRUD Admin (GET, POST, PUT, DELETE /dictionary)
│   │   │   │   └── knowledge.py        # POST /knowledge/ingest (Admin), POST /knowledge/search (Test)
│   │   │   └── router.py               # api_router = APIRouter(); include_routers(v1)
│   │   ├── services/         # LÓGICA DE NEGOCIO PURA (Sin FastAPI, Inyectables via Depends)
│   │   │   ├── __init__.py
│   │   │   ├── financial_engine.py # **NÚCLEO DURO** Clase FinancialEngine(db, user). 7 Métodos públicos + _build_base_query + _apply_permissions + _calculate_kpis. Retorna FinancialReportResult (Pydantic).
│   │   │   ├── llm_client.py       # Cliente HTTPX a llama.cpp (/v1/chat/completions). Método chat_completion(messages, tools, stream=True). Manejo errores/timeout.
│   │   │   ├── chat_service.py     # Orquestador Principal. process_message(user, session_id, msg) -> AsyncGenerator[ChatEvent]. Loop Tool Calling (Max 3 iter). Inyecta System Prompt + Dict + Contexto. Ejecuta Tools (FinancialEngine | RAGService). Actualiza ConversationContext. Persiste ChatMessage.
│   │   │   ├── rag_service.py      # Clase RAGService(db). _get_embedding(tei), ingest_text(chunking tiktoken), search(query, top_k, filters) -> Hybrid Search (Vector + BM25 via TEI sparse o SQL tsvector), format_context_for_prompt.
│   │   │   ├── context_manager.py  # get_context, update_context (merge filters), reset_context.
│   │   │   ├── dictionary_service.py # get_system_prompt_context() -> str (Markdown).
│   │   │   └── auth_service.py     # authenticate_oidc_callback, create_user_from_oidc, create_tokens, verify_token.
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py         # Fixtures: db_session (transaction rollback), test_client, sample_user, sample_budget_data, auth_headers
│   │       ├── test_financial_engine.py # **CRÍTICO**: Decimales exactos, Fórmulas (Vigente = Inicial + Modif), Permisos (User Region A no ve Region B), Comparativas, Div/Zero.
│   │       ├── test_rag_service.py     # Ingesta -> Búsqueda -> Umbral similitud -> Formato Prompt.
│   │       ├── test_chat_flow.py       # Integración: Tool Calling Financiero, Tool Calling RAG, Contexto Persistente, Streaming.
│   │       └── test_auth.py            # Login flow, RBAC, Scope filtering.
│   └── migrations/                 # Alembic (env.py, script.py.mako, versions/...)
│
├── frontend/
│   ├── Dockerfile              # Multi-stage: Builder (flutter build web --release) -> Runtime (Nginx Alpine + SPA config + gzip + CSP headers)
│   ├── pubspec.yaml            # Dependencias (Ver Sección 6)
│   ├── analysis_options.yaml   # Lint estricto (flutter_lints, prefer_single_quotes, etc.)
│   ├── web/
│   │   ├── index.html          # Base href, CSP, Preconnect llama.cpp/tei, Loading spinner, Flutter bootstrap
│   │   └── manifest.json       # PWA básico
│   ├── lib/
│   │   ├── main.dart           # Entry: ProviderScope, GoRouter (Redirect Guard Auth), Theme (Material 3, Dark/Light), Global Error Handler
│   │   ├── core/
│   │   │   ├── config/         # Environment (dev/prod), API Base URL, Feature Flags
│   │   │   ├── auth/           # AuthController (Riverpod StateNotifier<AuthState>), TokenStorage (SharedPreferences/Web), OIDC Flow (PKCE Code Challenge, Window Listener Callback)
│   │   │   ├── api/            # Dio Client (Singleton), Interceptors: Auth (Bearer + AutoRefresh 401), Logging, Error Mapping (AppException)
│   │   │   ├── theme/          # AppTheme (ColorScheme, Typography, Component Themes)
│   │   │   └── utils/          # format_currency (int/Decimal -> "Bs 1,234.50"), format_date, decimal_helpers, responsive_breakpoints
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   │   ├── screens/login_screen.dart          # Botón "Iniciar Sesión Institucional" -> AuthController.login()
│   │   │   │   └── widgets/
│   │   │   ├── chat/
│   │   │   │   ├── screens/chat_screen.dart           # Scaffold, AppBar (Titulo, Session Menu, Logout), ChatView (ListView), ChatInputBar
│   │   │   │   ├── widgets/
│   │   │   │   │   ├── chat_message_bubble.dart       # Render User / AssistantText / AssistantToolCall("Consultando motor financiero...") / AssistantData / Error
│   │   │   │   │   ├── chat_input_bar.dart            # TextField, Send Button, Loading State, Char Counter
│   │   │   │   │   ├── financial_card_row.dart        # 4 KPIs: Vigente, Ejecutado, Saldo, % (Responsive Grid/Row)
│   │   │   │   │   ├── chart_widget.dart              # Wrapper: fl_chart (Barras, Línea, Pie) o Syncfusion. Recibe chart_spec (type, xKey, yKeys, seriesName).
│   │   │   │   │   ├── data_table_widget.dart         # DataTable2 / PaginatedDataTable: Columnas dinámicas (keys de DataRow), Sort, Pagination, Row Select, Export CSV/Excel Button (llama API /reports/export).
│   │   │   │   │   └── active_filters_chip_bar.dart   # Chips clickeables (x) para quitar filtro individual -> Envía mensaje "Quita filtro [X]" al ChatController.
│   │   │   │   ├── providers/chat_controller.dart     # Riverpod AsyncNotifier/StreamController. Estado: messages, context, isStreaming. Método sendMessage(text) -> EventSource (SSE) parse -> yield states.
│   │   │   │   └── models/                            # ChatMessage (type, text, toolCall?, financialData?, citations?), FinancialDataPacket (reportType, metadata, summary, rows, chartSpec), ActiveFilter.
│   │   │   ├── dashboard/           # Esqueleto: DashboardScreen, Widgets Placeholders (KPIs Globales, Gráfico Tendencia)
│   │   │   └── reports/             # Esqueleto: ReportViewerScreen (PDF Viewer, Excel Viewer)
│   │   └── shared/
│   │       ├── widgets/             # LoadingOverlay, ErrorDisplay, EmptyState, ResponsiveLayout (Mobile < 600, Tablet < 900, Desktop), AppDrawer (Desktop Sidebar)
│       └── constants/             # App Strings, Routes, API Endpoints
│   └── test/
│       ├── widget_test.dart
│       └── mocks/                 # Mockito mocks para AuthController, ApiClient, ChatController
│
├── llama.cpp/
│   └── models/                   # Directorio para modelos GGUF (gitkeep). El script de arranque descarga aquí.
│
├── data_docs/                    # **VOLUMEN HOST** para ingesta RAG. Usuario pone PDFs/DOCs/TXTs aquí.
│   ├── leer_primero.txt
│   └── .gitkeep
│
└── docs/
    ├── architecture.md           # Diagramas Mermaid, Decisiones (ADR)
    ├── api_contract.md           # Export OpenAPI (generado en CI)
    ├── data_dictionary_guide.md  # Cómo poblar DataDictionary
    ├── deployment.md             # Prod: Nginx, SSL, Systemd, Backups, Monitoring
    └── rag_guide.md              # Cómo ingesta, chunking, evaluación retrieval
4. backend/requirements.txt (PINNED VERSIONS)
# Core
fastapi==0.111.0
uvicorn[standard]==0.30.1
pydantic==2.7.4
pydantic-settings==2.3.4
python-multipart==0.0.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-oauthlib==3.2.2
httpx==0.27.0
email-validator==2.1.0.post1

# DB & ORM
sqlalchemy==2.0.30
asyncpg==0.29.0
alembic==1.12.1
pgvector==0.2.5          # CRITICAL: Vector extension for SQLAlchemy
psycopg2-binary==2.9.9   # Para Alembic sync operations

# RAG & NLP
tiktoken==0.7.0
rank-bm25==0.2.2         # Fallback BM25 if TEI sparse not used
pypdf==4.2.0
python-docx==1.1.0
markdown-it-py==3.0.0

# Utils
python-dotenv==1.0.1
structlog==24.1.0
tenacity==8.2.3
orjson==3.9.10           # Fast JSON for SSE streaming

# Testing
pytest==8.2.2
pytest-asyncio==0.23.3
pytest-cov==5.0.0
httpx==0.27.0            # TestClient
faker==25.2.0            # Synthetic data
5. .env.example (COPIA EXACTA - LLENAR VALORES REALES)
# ---------------------------------------------------------
# GENERAL
# ---------------------------------------------------------
APP_ENV=development
PROJECT_NAME="Copiloto Presupuestario"
API_V1_PREFIX=/api/v1
SECRET_KEY=GENERATE_A_STRONG_RANDOM_KEY_32_CHARS_MIN  # openssl rand -hex 32
BACKEND_CORS_ORIGINS='["http://localhost:8080", "http://127.0.0.1:8080"]'

# ---------------------------------------------------------
# POSTGRESQL (Docker Service Name: postgres)
# ---------------------------------------------------------
POSTGRES_SERVER=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=budget_ai
DATABASE_URI=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_SERVER}:${POSTGRES_PORT}/${POSTGRES_DB}

# ---------------------------------------------------------
# AUTENTICACIÓN OIDC (KEYCLOAK / AUTH0 / GOOGLE / AZURE AD)
# CONFIGURA UN CLIENT "Confidential" con "Standard Flow" + PKCE + "Web Origins" + "Redirect URIs"
# ---------------------------------------------------------
OIDC_PROVIDER_URL=https://your-keycloak-domain/realms/your-realm
OIDC_CLIENT_ID=budget-copilot-web
OIDC_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
OIDC_REDIRECT_URI=http://localhost:8080/api/v1/auth/callback
OIDC_SCOPES="openid profile email roles"
OIDC_AUDIENCE=budget-copilot-api  # Si tu proveedor lo valida (Auth0/Azure). Keycloak a veces no.
OIDC_ISSUER_URL=https://your-keycloak-domain/realms/your-realm  # Para validación JWT 'iss'

# ---------------------------------------------------------
# LLAMA.CPP SERVER (Internal Docker Network)
# ---------------------------------------------------------
LLM_SERVER_URL=http://llama-cpp:8080/v1
LLM_MODEL_NAME=qwen2.5-7b-instruct-q4_k_m
LLM_TEMPERATURE=0.1
LLM_TOP_P=0.9
LLM_MAX_TOKENS=2048
LLM_CTX_SIZE=8192
LLM_N_GPU_LAYERS=-1  # -1 = all (GPU), 0 = CPU only. Ajusta en docker-compose deploy.resources.

# ---------------------------------------------------------
# EMBEDDINGS SERVER (TEI - Text Embeddings Inference)
# ---------------------------------------------------------
EMBEDDINGS_SERVER_URL=http://embeddings:80
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_DIM=1024
EMBEDDING_MAX_LENGTH=8192

# ---------------------------------------------------------
# FINANCIAL ENGINE
# ---------------------------------------------------------
DEFAULT_CURRENCY=BOB
DECIMAL_PLACES=2
# Reglas de cálculo (Pueden ser override por Gestion en BD si varían)
# EXECUTION_TYPE=accrual  # 'accrual' (Devengado) o 'cash' (Pagado)

# ---------------------------------------------------------
# FRONTEND (Build-time args en Dockerfile)
# ---------------------------------------------------------
VITE_API_BASE_URL=http://localhost:8000/api/v1
6. frontend/pubspec.yaml (DEPENDENCIAS CLAVE)
name: budget_copilot_frontend
description: Copiloto Presupuestario Flutter Web
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.3.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  flutter_localizations:
    sdk: flutter
  flutter_web_plugins:
    sdk: flutter

  # State & Routing
  flutter_riverpod: ^2.4.9
  riverpod_annotation: ^2.3.3
  go_router: ^13.0.1

  # Network & Auth
  dio: ^5.4.0
  flutter_secure_storage: ^9.0.0  # Web usa SharedPreferences automáticamente
  oauth2_client: ^2.0.0           # PKCE Helper (o implementación manual en AuthController)

  # Data & Visualization
  decimal: ^3.0.1                 # CRITICAL: Manejo monetario exacto
  intl: ^0.19.0
  fl_chart: ^0.66.2               # Gráficos nativos Flutter (Barras, Línea, Pie)
  # syncfusion_flutter_charts: ^25.1.39  # Alternativa robusta (Licencia Community)
  syncfusion_flutter_datagrid: ^25.1.39 # Tabla profesional (Sort, Filter, Export, Pagination)
  # syncfusion_flutter_pdfviewer: ^25.1.39 # Visor PDF reportes
  # syncfusion_flutter_xlsio: ^25.1.39     # Export Excel nativo (Opcional, backend también exporta)

  # Utils
  uuid: ^4.3.3
  logger: ^2.0.2+1
  url_launcher: ^6.2.2
  collection: ^1.18.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.1
  riverpod_generator: ^2.3.9
  build_runner: ^2.4.7
  custom_lint: ^0.6.4
  riverpod_lint: ^2.3.7
  mockito: ^5.4.4
  integration_test:
    sdk: flutter

flutter:
  uses-material-design: true
  assets:
    - assets/images/
    - assets/icons/
7. CÓDIGO CRÍTICO: ARCHIVOS CLAVE (CONTENIDO COMPLETO PARA COPIAR)
7.1 backend/app/core/config.py
# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyUrl, computed_field
from typing import List, Optional
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False)

    APP_ENV: str = "development"
    PROJECT_NAME: str = "Copiloto Presupuestario"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str
    BACKEND_CORS_ORIGINS: str = '["http://localhost:8080"]'

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.BACKEND_CORS_ORIGINS)

    # DB
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URI: str  # Se construye en .env o property

    # Auth OIDC
    OIDC_PROVIDER_URL: str
    OIDC_CLIENT_ID: str
    OIDC_CLIENT_SECRET: str
    OIDC_REDIRECT_URI: str
    OIDC_SCOPES: str = "openid profile email roles"
    OIDC_AUDIENCE: Optional[str] = None
    OIDC_ISSUER_URL: str

    # LLM
    LLM_SERVER_URL: str
    LLM_MODEL_NAME: str
    LLM_TEMPERATURE: float = 0.1
    LLM_TOP_P: float = 0.9
    LLM_MAX_TOKENS: int = 2048

    # Embeddings
    EMBEDDINGS_SERVER_URL: str
    EMBEDDING_MODEL_NAME: str
    EMBEDDING_DIM: int = 1024

    # Financial
    DEFAULT_CURRENCY: str = "BOB"
    DECIMAL_PLACES: int = 2

settings = Settings()
7.2 backend/app/models/knowledge.py (PGVECTOR)
# backend/app/models/knowledge.py
import uuid
import json
from sqlalchemy import Column, Integer, String, Text, DateTime, func, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index(
            "ix_knowledge_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
        Index("ix_knowledge_chunks_source_type", "source_type"),
        Index("ix_knowledge_chunks_source_id", "source_id"),
        Index("ix_knowledge_chunks_tags_gin", "tags", postgresql_using="gin"),
        {"comment": "Chunks de conocimiento institucional para RAG (normativa, manuales, FAQs)"}
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="Texto original del chunk")
    content_tokens: Mapped[int] = mapped_column(Integer, nullable=False, comment="Número de tokens (tiktoken cl100k_base)")
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False, comment="Embedding BGE-m3 (1024 dims)")
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="regulation, manual, faq, classifier, law")
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="ID único documento origen")
    source_title: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Título legible para citas")
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="Orden en documento original")
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, comment="Tags para filtrado (ej: ['modificaciones', 'reglamento'])")
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="Metadatos flexibles: {page: 5, article: 'Art. 12'}")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<KnowledgeChunk(id={self.id}, source='{self.source_title}', type={self.source_type})>"
7.3 backend/app/schemas/chat.py (TOOLS SCHEMAS)
# backend/app/schemas/chat.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal, Union
from decimal import Decimal
from datetime import date
from uuid import UUID

# --- Parámetros Entrada Herramientas Financieras ---
class BudgetFilterParams(BaseModel):
    years: List[int] = Field(..., min_length=1, max_length=5, description="Gestiones/años fiscales a consultar")
    region_ids: Optional[List[UUID]] = None
    area_ids: Optional[List[UUID]] = None
    financier_ids: Optional[List[UUID]] = None
    rubro_ids: Optional[List[UUID]] = None
    cuenta_ids: Optional[List[UUID]] = None
    group_by: Optional[Literal["financier", "area", "region", "rubro", "cuenta", "month"]] = None
    metric: Optional[Literal["executed", "percentage", "balance", "initial", "modified", "current"]] = "executed"
    date_from: Optional[date] = None
    date_to: Optional[date] = None

# --- Salida Estructurada Motor Financiero ---
class KPISummary(BaseModel):
    initial_budget: Decimal
    modifications: Decimal
    current_budget: Decimal
    executed: Decimal
    balance: Decimal
    execution_percentage: Decimal

class DataRow(BaseModel):
    labels: Dict[str, str]  # ej: {"financier": "MINISTERIO SALUD", "region": "NORTE"}
    values: Dict[str, Decimal] # ej: {"current_budget": "1000000.00", "executed": "450000.00", "percentage": "45.00"}

class FinancialReportResult(BaseModel):
    report_type: str
    metadata: Dict[str, Any] # filtros_aplicados, moneda, fecha_corte, fuente_datos, user_id
    summary: KPISummary
    rows: List[DataRow]
    chart_spec: Optional[Dict[str, Any]] = None # {"type": "bar", "x": "financier", "y": "execution_percentage", "series": [...]}

# --- Tool: Búsqueda Conocimiento (RAG) ---
class SearchKnowledgeParams(BaseModel):
    query: str = Field(..., description="Pregunta en lenguaje natural sobre normativa, manuales, clasificadores, leyes, FAQs.")
    source_types: Optional[List[Literal["regulation", "manual", "faq", "classifier", "law"]]] = None
    top_k: int = Field(default=5, ge=1, le=10)

# --- Eventos SSE Chat ---
class ChatEvent(BaseModel):
    event: Literal["delta", "tool_call", "tool_result", "context_update", "done", "error"]
    data: Any
    session_id: UUID

class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]
    call_id: str

class ToolResultPayload(BaseModel):
    call_id: str
    result: Union[FinancialReportResult, Dict[str, Any]] # FinancialReportResult o Dict para RAG
    is_error: bool = False

class ContextUpdatePayload(BaseModel):
    active_filters: BudgetFilterParams
    current_report: Optional[str] = None

# --- Request/Response API ---
class ChatRequest(BaseModel):
    session_id: Optional[UUID] = None
    message: str = Field(..., min_length=1, max_length=4000)

class ChatSessionOut(BaseModel):
    id: UUID
    title: str
    created_at: date
    message_count: int
7.4 backend/app/core/prompts.py (SYSTEM PROMPT DINÁMICO)
# backend/app/core/prompts.py
from app.services.dictionary_service import DictionaryService
from sqlalchemy.ext.asyncio import AsyncSession

SYSTEM_PROMPT_BASE = """
# ROL: Copiloto Presupuestario Institucional
# OBJETIVO: Asistir a usuarios técnicos en consultas de ejecución presupuestaria y conocimiento normativo mediante lenguaje natural.

## HERRAMIENTAS DISPONIBLES (USA LA ADECUADA SEGÚN LA INTENCIÓN):

### 1. HERRAMIENTAS FINANCIERAS (DATOS DUROS - MONTOS, EJECUCIÓN, SALDOS, TENDENCIAS)
Úsalas SOLO cuando el usuario pida: números, porcentajes, comparativas, detalle de movimientos, ejecución por X, "muéstrame...", "descarga...", "gráfico de...".
- get_budget_summary, get_execution_by_account, get_execution_by_financier, get_execution_by_area, get_execution_by_region, get_monthly_execution, get_transaction_details, compare_budget_periods, get_budget_variations, generate_financial_report.

### 2. HERRAMIENTA CONOCIMIENTO INSTITUCIONAL (NORMATIVA, CONCEPTOS, PROCEDIMIENTOS)
Úsala SOLO cuando el usuario pregunte: "¿Qué dice el reglamento...?", "¿Cuál es la ley...?", "Definición de...", "¿Cómo se clasifica...?", "Procedimiento para...", "Manual de...", "Clasificador...".
- search_institutional_knowledge(query: str, source_types?: list, top_k?: int).

## REGLAS DE ORO:
1. NO CALCULES NUNCA. Usa SOLO las herramientas. El motor financiero es la única fuente de verdad numérica.
2. NO INVENTES DATOS. Si una herramienta falla o no hay datos, informa la limitación exacta: "No hay datos para la Región X en 2025".
3. CONTEXTO: Mantén filtros activos (años, región, área, financiador, agrupación, reporte_base). El usuario refina progresivamente ("Ahora por financiador", "Compara con 2025").
4. CITAS OBLIGATORIAS: Si usas 'search_institutional_knowledge', CITA SIEMPRE las fuentes al final: "[Fuente 1: Manual Clasificador 2024]", "[Fuente 2: Ley 1178 Art. 15]".
5. IDIOMA: Español, tono profesional, técnico pero accesible. Moneda: {currency}.
6. FORMATO RESPUESTA FINAL:
   - 1-2 frases explicando QUÉ se consultó y QUÉ muestra el resultado.
   - NO repitas tablas completas en texto. Di: "La tabla muestra 5 financiadores con su ejecución. El gráfico de barras compara porcentajes."
   - Si el motor detecta anomalía (regla determinista), menciónala: "Alerta: El financiador X tiene ejecución < 20%."
"""

# Diccionario se inyecta al final del System Prompt en ChatService
DICTIONARY_PROMPT_HEADER = "\n## DICCIONARIO INSTITUCIONAL ACTIVO\n"
DICTIONARY_PROMPT_FOOTER = "\n---\nUsa estos términos exactos al mapear preguntas del usuario a parámetros de herramientas financieras."

async def build_system_prompt(db: AsyncSession, currency: str = "BOB") -> str:
    dict_service = DictionaryService(db)
    dict_context = await dict_service.get_system_prompt_context()
    base = SYSTEM_PROMPT_BASE.format(currency=currency)
    if dict_context:
        return base + DICTIONARY_PROMPT_HEADER + dict_context + DICTIONARY_PROMPT_FOOTER
    return base
7.5 backend/app/services/financial_engine.py (NÚCLEO DURO - ESQUELETO COMPLETO)
# backend/app/services/financial_engine.py
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, or_, text, join
from sqlalchemy.orm import selectinload

from app.models.budget import Budget, BudgetModification, Movement, Rubro, Cuenta, Financier, Area, Region, Gestion, ExchangeRate
from app.models.user import User
from app.schemas.budget import BudgetFilterParams, FinancialReportResult, KPISummary, DataRow

class FinancialEngine:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.user = current_user
        self.currency = "BOB"  # TODO: Obtener de config/gestion

    # --- HELPER: Permisos (Alcance de Datos) ---
    def _apply_scope_filters(self, query, model_alias=None):
        """Aplica filtros de alcance (Region, Area, Financier) según UserScope."""
        prefix = f"{model_alias}." if model_alias else ""
        scopes = self.user.scopes # Relación UserScope cargada
        if scopes.region_ids:
            query = query.where(getattr(model_alias or Budget, 'region_id').in_(scopes.region_ids))
        if scopes.area_ids:
            query = query.where(getattr(model_alias or Budget, 'area_id').in_(scopes.area_ids))
        if scopes.financier_ids:
            query = query.where(getattr(model_alias or Budget, 'financier_id').in_(scopes.financier_ids))
        return query

    # --- HELPER: Query Base Presupuestos + Movimientos ---
    def _build_base_query(self, params: BudgetFilterParams):
        # Joins: Budget -> Gestion, Region, Area, Financier, Rubro, Cuenta
        # Movimientos LEFT JOIN para Execution
        # Filtros: years, region_ids, area_ids, financier_ids, rubro_ids, cuenta_ids, date_from, date_to
        # Retorna: Select statement con columnas base + aggregates
        pass # IMPLEMENTACIÓN DETALLADA EN CÓDIGO FINAL (Ver notas abajo)

    # --- HELPER: Cálculos Estándar Institucional ---
    @staticmethod
    def _calculate_kpis(initial: Decimal, modifications: Decimal, executed: Decimal) -> KPISummary:
        current = initial + modifications
        balance = current - executed
        pct = (executed / current * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if current != 0 else Decimal('0.00')
        return KPISummary(
            initial_budget=initial.quantize(Decimal('0.01')),
            modifications=modifications.quantize(Decimal('0.01')),
            current_budget=current.quantize(Decimal('0.01')),
            executed=executed.quantize(Decimal('0.01')),
            balance=balance.quantize(Decimal('0.01')),
            execution_percentage=pct
        )

    # --- 7 MÉTODOS PÚBLICOS (INFORMES OBLIGATORIOS) ---
    async def get_execution_by_account(self, params: BudgetFilterParams) -> FinancialReportResult:
        # 1. Validar params (Pydantic ya lo hizo)
        # 2. Query Base + Group By: Cuenta (y Rubro padre)
        # 3. Agregados: SUM(inicial), SUM(modif), SUM(ejecutado)
        # 4. KPIs Totales (Summary)
        # 5. Filas (DataRow) con labels {cuenta, rubro} + values {inicial, modif, vigente, ejecutado, saldo, pct}
        # 6. Chart Spec: Bar chart x=cuenta, y=execution_percentage
        pass

    async def get_execution_by_financier(self, params: BudgetFilterParams) -> FinancialReportResult: ...
    async def get_execution_by_area(self, params: BudgetFilterParams) -> FinancialReportResult: ...
    async def get_execution_by_region(self, params: BudgetFilterParams) -> FinancialReportResult: ...
    async def get_monthly_execution(self, params: BudgetFilterParams) -> FinancialReportResult: ...
    async def get_transaction_details(self, params: BudgetFilterParams) -> FinancialReportResult: ...
    async def get_general_summary(self, params: BudgetFilterParams) -> FinancialReportResult: ...

    # --- COMPARATIVA (Innovación) ---
    async def compare_budget_periods(self, params: BudgetFilterParams) -> FinancialReportResult:
        # Requiere params.years con 2+ años.
        # Ejecuta query base para cada año.
        # Calcula diff absolutos y % entre años.
        # Rows: labels {financier, year} + values {current, executed, pct, diff_pct_vs_base_year}
        # Chart Spec: Grouped Bar Chart.
        pass

    # --- EXPORT ---
    async def generate_financial_report(self, params: BudgetFilterParams, format: Literal["excel", "pdf"]) -> bytes:
        # Llama al método correspondiente (ej. get_execution_by_financier)
        # Formatea salida (pandas/openpyxl para Excel, reportlab/weasyprint para PDF)
        # Retorna bytes.
        pass
7.6 backend/app/services/rag_service.py (RAG COMPLETO)
# backend/app/services/rag_service.py
import httpx
import json
import tiktoken
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pgvector.sqlalchemy import Vector

from app.models.knowledge import KnowledgeChunk
from app.core.config import settings

class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tei_url = settings.EMBEDDINGS_SERVER_URL.rstrip('/')
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.dim = settings.EMBEDDING_DIM

    # --- EMBEDDING ---
    async def _get_embedding(self, text: str) -> List[float]:
        async with httpx.AsyncClient(timeout=30.0, base_url=self.tei_url) as client:
            resp = await client.post("/embed", json={"inputs": [text], "truncate": True, "pooling": "cls"})
            resp.raise_for_status()
            return resp.json()[0]  # List[float] len=1024

    # --- INGESTA (Chunking Simple por Tokens) ---
    async def ingest_text(
        self,
        content: str,
        source_type: str,
        source_id: str,
        source_title: str = "",
        tags: List[str] = None,
        metadata: Dict = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> List[KnowledgeChunk]:
        tokens = self.encoder.encode(content)
        chunks_created = []
        for i in range(0, len(tokens), chunk_size - chunk_overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self.encoder.decode(chunk_tokens)
            embedding = await self._get_embedding(chunk_text)
            chunk = KnowledgeChunk(
                content=chunk_text,
                content_tokens=len(chunk_tokens),
                embedding=embedding,
                source_type=source_type,
                source_id=source_id,
                source_title=source_title,
                chunk_index=len(chunks_created),
                tags=tags or [],
                metadata_json=metadata or {}
            )
            self.db.add(chunk)
            chunks_created.append(chunk)
        await self.db.flush()
        return chunks_created

    # --- BÚSQUEDA HÍBRIDA (Vector + BM25 via TEI Sparse) ---
    async def search(
        self,
        query: str,
        top_k: int = 5,
        source_types: List[str] = None,
        tags: List[str] = None,
        similarity_threshold: float = 0.65
    ) -> List[Dict[str, Any]]:
        query_embedding = await self._get_embedding(query)

        # 1. Vector Search (Dense) via pgvector HNSW
        # 2. Sparse Search (BM25) via TEI /embed (bge-m3 devuelve sparse vec) -> Requiere pgvector sparse support o tabla auxiliar.
        # FASE 1 MVP: Solo Vector Search + Filtros Metadata + Threshold. Suficiente para arrancar.
        # TODO FASE 2: Hybrid RRF Fusion.

        filters = []
        params = {"query_emb": query_embedding, "top_k": top_k, "threshold": similarity_threshold}
        if source_types:
            filters.append("source_type = ANY(:source_types)")
            params["source_types"] = source_types
        if tags:
            filters.append("tags::jsonb ?| :tags") # Requiere tags JSONB
            params["tags"] = tags

        where_clause = " AND ".join(filters) if filters else "true"

        sql = f"""
            SELECT
                id, content, source_type, source_id, source_title, chunk_index, metadata_json,
                1 - (embedding <=> :query_emb) AS similarity
            FROM knowledge_chunks
            WHERE {where_clause}
              AND 1 - (embedding <=> :query_emb) > :threshold
            ORDER BY embedding <=> :query_emb
            LIMIT :top_k
        """
        result = await self.db.execute(text(sql), params)
        return [dict(row) for row in result.mappings().all()]

    # --- FORMATO PARA PROMPT LLM ---
    @staticmethod
    def format_context_for_prompt(results: List[Dict]) -> str:
        if not results:
            return "No se encontró información relevante en la base de conocimiento institucional para la consulta."
        blocks = []
        for i, r in enumerate(results, 1):
            cite = f"[Fuente {i}: {r['source_title'] or r['source_id']} ({r['source_type']})]"
            # Truncar chunk si es muy grande para no saturar contexto LLM
            content = r['content'][:2000] + ("..." if len(r['content']) > 2000 else "")
            blocks.append(f"{cite}\n{content}")
        return "\n\n---\n\n".join(blocks)
7.7 backend/app/services/chat_service.py (ORQUESTADOR TOOL CALLING)
# backend/app/services/chat_service.py
import json
import uuid
from typing import AsyncGenerator, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.session import ChatSession, ChatMessage, ConversationContext
from app.models.user import User
from app.schemas.chat import ChatEvent, ToolCallRequest, ToolResultPayload, ContextUpdatePayload, BudgetFilterParams
from app.services.llm_client import LLMClient
from app.services.financial_engine import FinancialEngine
from app.services.rag_service import RAGService
from app.services.context_manager import ContextManager
from app.core.prompts import build_system_prompt
from app.core.config import settings

# Definición de Tools para OpenAI Function Calling (Inyectar en LLMClient)
AVAILABLE_TOOLS = [
    # ... (Pegar JSON Schemas de FinancialEngine methods + SearchKnowledgeParams aquí) ...
    # Ejemplo estructura:
    # {"type": "function", "function": {"name": "get_execution_by_financier", "description": "...", "parameters": BudgetFilterParams.model_json_schema()}},
    # {"type": "function", "function": {"name": "search_institutional_knowledge", "description": "...", "parameters": SearchKnowledgeParams.model_json_schema()}},
]

class ChatService:
    def __init__(self, db: AsyncSession, llm_client: LLMClient):
        self.db = db
        self.llm = llm_client
        self.fin_engine = None # Se inicializa con user en process_message
        self.rag_service = RAGService(db)
        self.ctx_manager = ContextManager(db)

    async def process_message(self, user: User, session_id: uuid.UUID | None, user_message: str) -> AsyncGenerator[ChatEvent, None]:
        # 1. Obtener/Crear Sesión
        session = await self._get_or_create_session(user, session_id)
        session_id = session.id

        # 2. Inicializar Motor Financiero con User (Permisos)
        self.fin_engine = FinancialEngine(self.db, user)

        # 3. Obtener Contexto Actual (Filtros Activos)
        context = await self.ctx_manager.get_context(session_id)
        active_filters = context.active_filters if context else BudgetFilterParams(years=[])

        # 4. Construir Historial Reciente (Últimos 6 turnos)
        history = await self._get_recent_history(session_id, limit=6)

        # 5. System Prompt Dinámico (Base + Diccionario)
        system_prompt = await build_system_prompt(self.db, settings.DEFAULT_CURRENCY)

        # 6. Inyectar Contexto Activo como mensaje System previo
        context_msg = f"CONTEXTO ACTIVO (Filtros vigentes): {active_filters.model_dump_json(exclude_none=True)}"
        if context and context.current_report:
            context_msg += f"\nReporte base actual: {context.current_report}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": context_msg},
            *history,
            {"role": "user", "content": user_message}
        ]

        # 7. Guardar Mensaje Usuario
        await self._append_message(session_id, "user", user_message)

        # 8. LOOP TOOL CALLING (Max 3 iteraciones)
        for iteration in range(3):
            yield ChatEvent(event="delta", data="", session_id=session_id) # Heartbeat/Start

            # Llamada LLM
            response = await self.llm.chat_completion(
                messages=messages,
                tools=AVAILABLE_TOOLS,
                tool_choice="auto",
                stream=False # Tool calling requiere respuesta completa para parsear tool_calls
            )

            msg = response.choices[0].message
            tool_calls = msg.tool_calls

            if not tool_calls:
                # Respuesta Final del LLM (Streaming)
                final_content = msg.content or ""
                yield ChatEvent(event="delta", data=final_content, session_id=session_id)
                yield ChatEvent(event="done", data={"content": final_content}, session_id=session_id)
                await self._append_message(session_id, "assistant", final_content)
                break

            # Hay Tool Calls -> Ejecutar
            assistant_msg_with_tools = {"role": "assistant", "content": msg.content, "tool_calls": [tc.model_dump() for tc in tool_calls]}
            messages.append(assistant_msg_with_tools)

            for tc in tool_calls:
                yield ChatEvent(event="tool_call", data={"name": tc.function.name, "args": json.loads(tc.function.arguments)}, session_id=session_id)

                tool_result = await self._execute_tool(tc, user, active_filters)
                
                yield ChatEvent(event="tool_result", data=tool_result, session_id=session_id)

                # Añadir resultado al historial para siguiente vuelta
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

                # ACTUALIZAR CONTEXTO CONVERSACIONAL (Merge Filtros)
                if tc.function.name in ["get_execution_by_account", "get_execution_by_financier", "get_execution_by_area", "get_execution_by_region", "get_monthly_execution", "get_general_summary", "compare_budget_periods"]:
                    try:
                        result_data = tool_result.get("result", {})
                        if isinstance(result_data, dict) and "metadata" in result_data:
                            new_filters = BudgetFilterParams(**result_data["metadata"].get("filtros_aplicados", {}))
                            await self.ctx_manager.update_context(session_id, new_filters, tc.function.name)
                            yield ChatEvent(event="context_update", data=ContextUpdatePayload(active_filters=new_filters, current_report=tc.function.name).model_dump(), session_id=session_id)
                    except Exception as e:
                        print(f"Warning: Failed to update context: {e}")

            # Continuar loop para que LLM genere respuesta final con resultados
        else:
            yield ChatEvent(event="error", data="Max tool iterations reached", session_id=session_id)

    async def _execute_tool(self, tool_call, user, current_filters) -> Dict[str, Any]:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        call_id = tool_call.id

        try:
            # --- FINANCIAL TOOLS ---
            if hasattr(self.fin_engine, name):
                # Merge current_filters with args (args prevalece)
                merged_args = current_filters.model_dump(exclude_none=True)
                merged_args.update(args)
                params = BudgetFilterParams(**merged_args)
                
                method = getattr(self.fin_engine, name)
                result: FinancialReportResult = await method(params)
                return {"call_id": call_id, "result": result.model_dump(mode='json'), "is_error": False}

            # --- RAG TOOL ---
            elif name == "search_institutional_knowledge":
                from app.schemas.chat import SearchKnowledgeParams
                params = SearchKnowledgeParams(**args)
                results = await self.rag_service.search(
                    query=params.query,
                    top_k=params.top_k,
                    source_types=params.source_types
                )
                context_text = RAGService.format_context_for_prompt(results)
                citations = [{"source_id": r["source_id"], "source_title": r["source_title"], "source_type": r["source_type"]} for r in results]
                return {
                    "call_id": call_id,
                    "result": {
                        "query": params.query,
                        "results_count": len(results),
                        "context": context_text,
                        "citations": citations
                    },
                    "is_error": False
                }

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            return {"call_id": call_id, "result": {"error": str(e)}, "is_error": True}

    # ... Helpers _get_or_create_session, _get_recent_history, _append_message ...
7.8 frontend/lib/features/chat/providers/chat_controller.dart (FLUTTER SSE + STATE)
// frontend/lib/features/chat/providers/chat_controller.dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../../models/chat_models.dart';
import '../../../core/api/dio_client.dart';

final chatControllerProvider = StateNotifierProvider<ChatController, ChatState>((ref) {
  return ChatController(ref.read(dioProvider));
});

class ChatState {
  final List<ChatMessage> messages;
  final ConversationContext? context;
  final bool isStreaming;
  final String? error;
  const ChatState({this.messages = const [], this.context, this.isStreaming = false, this.error});
  ChatState copyWith({List<ChatMessage>? messages, ConversationContext? context, bool? isStreaming, String? error}) {
    return ChatState(messages: messages ?? this.messages, context: context ?? this.context, isStreaming: isStreaming ?? this.isStreaming, error: error);
  }
}

class ChatController extends StateNotifier<ChatState> {
  final DioClient _dio;
  StreamSubscription? _sseSub;
  String? _currentSessionId;
  ChatMessage? _pendingAssistantMsg;

  ChatController(this._dio) : super(const ChatState());

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty || state.isStreaming) return;
    
    state = state.copyWith(isStreaming: true, error: null);
    
    // 1. Add User Message Optimistically
    final userMsg = ChatMessage.user(text);
    state = state.copyWith(messages: [...state.messages, userMsg]);

    // 2. Prepare Assistant Placeholder
    _pendingAssistantMsg = ChatMessage.assistantStreaming();
    state = state.copyWith(messages: [...state.messages, _pendingAssistantMsg!]);

    try {
      // 3. SSE Connection
      final url = '${_dio.options.baseUrl}/chat/stream';
      final request = http.Request('POST', Uri.parse(url))
        ..headers.addAll({'Content-Type': 'application/json', 'Accept': 'text/event-stream', 'Authorization': 'Bearer ${_dio.authToken}'})
        ..body = jsonEncode({'session_id': _currentSessionId, 'message': text});

      final client = http.Client();
      final response = await client.send(request);
      
      if (response.statusCode != 200) throw Exception('Error ${response.statusCode}');

      // 4. Parse SSE Stream
      await for (final event in _parseSSE(response.stream)) {
        _handleSSEEvent(event);
      }
      
      _currentSessionId = _extractSessionIdFromLastEvent(); // Si el backend lo devuelve en evento 'done'
      
    } catch (e) {
      state = state.copyWith(isStreaming: false, error: e.toString());
      // Reemplazar placeholder por error
      state = state.copyWith(messages: state.messages.map((m) => m.id == _pendingAssistantMsg?.id ? m.copyWith(type: MsgType.error, text: e.toString()) : m).toList());
    } finally {
      _pendingAssistantMsg = null;
    }
  }

  Stream<Map<String, dynamic>> _parseSSE(Stream<List<int>> stream) async* {
    final transformer = utf8.decoder.bind(stream).transform(const LineSplitter());
    String eventType = 'message';
    String dataBuffer = '';
    
    await for (final line in transformer) {
      if (line.startsWith('event:')) {
        eventType = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        dataBuffer += line.substring(5).trim();
      } else if (line.isEmpty && dataBuffer.isNotEmpty) {
        yield {'event': eventType, 'data': jsonDecode(dataBuffer)};
        dataBuffer = '';
        eventType = 'message';
      }
    }
  }

  void _handleSSEEvent(Map<String, dynamic> event) {
    final type = event['event'] as String;
    final data = event['data'] as Map<String, dynamic>;
    final sessionId = data['session_id'] as String?;
    if (sessionId != null) _currentSessionId = sessionId;

    switch (type) {
      case 'delta':
        final text = data['data'] as String? ?? '';
        _appendToPending(text);
        break;
      case 'tool_call':
        _replacePending(ChatMessage.assistantToolCall(data['data']['name'] as String));
        break;
      case 'tool_result':
        final result = data['data'] as Map<String, dynamic>;
        if (result['result'] is Map && result['result'].containsKey('summary')) {
          // Financial Data
          final packet = FinancialDataPacket.fromJson(result['result']);
          _replacePending(ChatMessage.assistantData(packet));
        } else {
          // RAG Context (Internal, no mostramos burbuja separada, solo alimenta al LLM)
        }
        break;
      case 'context_update':
        final ctx = ConversationContext.fromJson(data['data']);
        state = state.copyWith(context: ctx);
        break;
      case 'done':
        state = state.copyWith(isStreaming: false);
        break;
      case 'error':
        state = state.copyWith(isStreaming: false, error: data['data'].toString());
        break;
    }
  }

  void _appendToPending(String text) {
    if (_pendingAssistantMsg == null) return;
    final updated = _pendingAssistantMsg!.copyWith(text: _pendingAssistantMsg!.text + text);
    _pendingAssistantMsg = updated;
    state = state.copyWith(messages: state.messages.map((m) => m.id == updated.id ? updated : m).toList());
  }

  void _replacePending(ChatMessage newMsg) {
    _pendingAssistantMsg = newMsg;
    state = state.copyWith(messages: state.messages.map((m) => m.id == newMsg.id ? newMsg : m).toList());
  }
}
7.9 frontend/lib/features/chat/widgets/financial_card_row.dart (KPIs)
// frontend/lib/features/chat/widgets/financial_card_row.dart
import 'package:flutter/material.dart';
import 'package:decimal/decimal.dart';
import '../../../core/utils/formatters.dart';

class FinancialCardRow extends StatelessWidget {
  final KPISummary summary;
  const FinancialCardRow({super.key, required this.summary});

  @override
  Widget build(BuildContext context) {
    final cards = [
      _CardData('Presupuesto Vigente', summary.currentBudget, Icons.account_balance),
      _CardData('Ejecutado', summary.executed, Icons.trending_up),
      _CardData('Saldo', summary.balance, Icons.savings),
      _CardData('% Ejecución', summary.executionPercentage, Icons.percent, isPercent: true),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 600;
        return Wrap(
          spacing: 12, runSpacing: 12,
          children: cards.map((c) => SizedBox(
            width: isMobile ? (constraints.maxWidth - 12) / 2 : null,
            child: _KPICard(data: c),
          )).toList(),
        );
      },
    );
  }
}

class _CardData {
  final String title; final Decimal value; final IconData icon; final bool isPercent;
  _CardData(this.title, this.value, this.icon, {this.isPercent = false});
}

class _KPICard extends StatelessWidget {
  final _CardData data;
  const _KPICard({required this.data});
  @override
  Widget build(BuildContext context) {
    final color = data.value < Decimal.zero && !data.isPercent ? Colors.red : Theme.of(context).colorScheme.primary;
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [Icon(data.icon, size: 20, color: color), const SizedBox(width: 8), Text(data.title, style: Theme.of(context).textTheme.labelLarge)]),
            const SizedBox(height: 8),
            Text(
              data.isPercent ? '${formatDecimal(data.value)}%' : formatCurrency(data.value),
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: color, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }
}
8. docker-compose.yml (COMPLETO - 5 SERVICIOS)
# docker-compose.yml
version: '3.8'

services:
  # ---------------------------------------------------------
  # 1. POSTGRESQL + PGVECTOR
  # ---------------------------------------------------------
  postgres:
    image: pgvector/pgvector:pg16
    container_name: budget-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-budget_ai}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro # Para CREATE EXTENSION vector;
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-budget_ai}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - budget-net
    deploy:
      resources:
        limits:
          memory: 2G

  # ---------------------------------------------------------
  # 2. LLM SERVER (llama.cpp) - Qwen2.5-7B-GGUF
  # ---------------------------------------------------------
  llama-cpp:
    image: ghcr.io/ggerganov/llama.cpp:server-cuda  # Cambia a :server si solo CPU
    container_name: budget-llm
    command: >
      --model /models/qwen2.5-7b-instruct-q4_k_m.gguf
      --host 0.0.0.0
      --port 8080
      --ctx-size 8192
      --n-gpu-layers -1
      --batch-size 512
      --ubatch-size 512
      --flash-attn
      --cont-batching
      --embedding
      --parallel 4
    volumes:
      - ./llama.cpp/models:/models:ro
    ports:
      - "8081:8080"  # Expuesto en host para debugging directo
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 60s # Tiempo para cargar modelo en VRAM/RAM
    networks:
      - budget-net
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
        limits:
          memory: 12G # Ajusta según tu GPU VRAM + RAM sistema. Q4_K_M ~ 5GB VRAM + KV Cache.

  # ---------------------------------------------------------
  # 3. EMBEDDINGS SERVER (TEI - Text Embeddings Inference) - BGE-m3
  # ---------------------------------------------------------
  embeddings:
    image: ghcr.io/huggingface/text-embeddings-inference:cpu-1.5  # Usa :1.5 para GPU si tienes VRAM
    container_name: budget-embeddings
    command: >
      --model-id BAAI/bge-m3
      --port 80
      --max-client-batch-size 1024
      --max-batch-size 32
      --max-concurrent-requests 128
    volumes:
      - tei_cache:/data # Cache modelos
    ports:
      - "8082:80"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - budget-net
    deploy:
      resources:
        limits:
          memory: 3G # bge-m3 en CPU ~1.5-2GB. En GPU menos.

  # ---------------------------------------------------------
  # 4. BACKEND (FastAPI)
  # ---------------------------------------------------------
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: budget-backend
    environment:
      - APP_ENV=development
      - DATABASE_URI=postgresql+asyncpg://postgres:postgres@postgres:5432/budget_ai
      - LLM_SERVER_URL=http://llama-cpp:8080/v1
      - EMBEDDINGS_SERVER_URL=http://embeddings:80
      # El resto de vars vienen de .env file
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      llama-cpp:
        condition: service_healthy
      embeddings:
        condition: service_healthy
    volumes:
      - ./backend:/app:ro  # Código (ro para seguridad)
      - ./data_docs:/app/data_docs:ro # Documentos para ingesta RAG
    networks:
      - budget-net
    deploy:
      resources:
        limits:
          memory: 1G

  # ---------------------------------------------------------
  # 5. FRONTEND (Nginx + Flutter Web Build)
  # ---------------------------------------------------------
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: http://localhost:8000/api/v1 # Build-time arg
    container_name: budget-frontend
    ports:
      - "8080:80"
    depends_on:
      - backend
    networks:
      - budget-net

networks:
  budget-net:
    driver: bridge

volumes:
  postgres_data:
  tei_cache:
9. backend/init-db.sh (PARA EXTENSION PGVECTOR)
#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Para búsqueda trigram/BM25 fallback
    CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
EOSQL
10. SCRIPTS DE INGESTA Y SEMILLA (EJECUTAR TRAS make up)
backend/scripts/seed_data.py (DATOS SINTÉTICOS REALISTAS)
# backend/scripts/seed_data.py
import asyncio
import random
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import User, Role, Permission, UserRole, UserScope
from app.models.budget import Gestion, Region, Area, Financier, Rubro, Cuenta, Budget, BudgetModification, Movement, ExchangeRate
from app.models.dictionary import DataDictionary
from app.core.security import hash_password

async def main():
    engine = create_async_engine(settings.DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Roles & Permisos
        admin_role = Role(name="admin", description="Administrador Total")
        analyst_role = Role(name="analyst", description="Analista Presupuestario (Lectura)")
        viewer_role = Role(name="viewer", description="Solo Visualización")
        db.add_all([admin_role, analyst_role, viewer_role])
        
        # 2. Usuarios de Prueba
        users = []
        for i, (email, name, role) in enumerate([
            ("admin@inst.gov", "Admin Sistema", admin_role),
            ("analista.norte@inst.gov", "Juan Pérez (Región Norte)", analyst_role),
            ("analista.sur@inst.gov", "María López (Región Sur)", analyst_role),
            ("director@inst.gov", "Director General", viewer_role),
        ]):
            user = User(email=email, full_name=name, hashed_password=hash_password("Password123!"), is_active=True)
            db.add(user)
            await db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id))
            users.append(user)
        
        # 3. Alcances (Scopes) - Crítico para test de permisos
        # Admin: Sin scope (ve todo)
        # Juan: Solo Región Norte (id 1)
        # María: Solo Región Sur (id 2)
        # Director: Sin scope (ve todo pero solo lectura)
        norte_region = Region(code="NTE", name="Región Norte")
        sur_region = Region(code="SUR", name="Región Sur")
        db.add_all([norte_region, sur_region])
        await db.flush()
        
        db.add(UserScope(user_id=users[1].id, region_ids=[norte_region.id])) # Juan -> Norte
        db.add(UserScope(user_id=users[2].id, region_ids=[sur_region.id]))   # María -> Sur
        # Admin y Director no tienen scope -> Ven todo (lógica en FinancialEngine)
        
        # 4. Datos Maestros (Gestiones, Áreas, Financiadores, Rubros, Cuentas)
        gestiones = [Gestion(year=y, name=f"Gestión {y}", is_active=(y==2026)) for y in [2024, 2025, 2026]]
        db.add_all(gestiones)
        
        areas = [Area(code=c, name=n) for c,n in [("SAL", "Salud"), ("EDU", "Educación"), ("INF", "Infraestructura")]]
        db.add_all(areas)
        
        financiadores = [Financier(code=c, name=n) for c,n in [("TGN", "Tesoro General"), ("PRT", "Préstamos Externos"), ("DON", "Donaciones")]]
        db.add_all(financiadores)
        
        rubros = [Rubro(code=c, name=n, level=1) for c,n in [("1", "Gastos Corrientes"), ("2", "Gastos de Capital")]]
        db.add_all(rubros)
        await db.flush()
        
        cuentas = [
            Cuenta(code="1.1.1", name="Remuneraciones", rubro_id=rubros[0].id),
            Cuenta(code="1.1.2", name="Bienes y Servicios", rubro_id=rubros[0].id),
            Cuenta(code="2.1.1", name="Construcciones", rubro_id=rubros[1].id),
            Cuenta(code="2.1.2", name="Maquinaria y Equipo", rubro_id=rubros[1].id),
        ]
        db.add_all(cuentas)
        
        await db.flush() # Obtener IDs
        
        # 5. Presupuestos, Modificaciones, Movimientos (Datos Sintéticos Consistentes)
        random.seed(42)
        for g in gestiones:
            for reg in [norte_region, sur_region]:
                for area in areas:
                    for fin in financiadores:
                        for cta in cuentas:
                            # Presupuesto Inicial
                            inicial = Decimal(random.randint(500_000, 5_000_000)).quantize(Decimal('0.01'))
                            b = Budget(
                                gestion_id=g.id, region_id=reg.id, area_id=area.id,
                                financier_id=fin.id, cuenta_id=cta.id,
                                initial_amount=inicial, current_amount=inicial
                            )
                            db.add(b)
                            await db.flush()
                            
                            # Modificación (Solo 2025, 2026)
                            if g.year >= 2025 and random.random() < 0.3:
                                mod = Decimal(random.randint(-200_000, 500_000)).quantize(Decimal('0.01'))
                                b.current_amount += mod
                                db.add(BudgetModification(budget_id=b.id, amount=mod, type="ampliacion" if mod > 0 else "reduccion", description="Modificación automática seed"))
                            
                            # Movimientos (Ejecución) - Acumulado hasta mes 6 (Junio) para 2026
                            exec_pct = random.uniform(0.1, 0.9) if g.year < 2026 else random.uniform(0.3, 0.7)
                            ejecutado = (b.current_amount * Decimal(str(exec_pct))).quantize(Decimal('0.01'))
                            if ejecutado > 0:
                                db.add(Movement(
                                    budget_id=b.id, date=date(g.year, 6, 30), amount=ejecutado,
                                    type="devengado", description="Ejecución acumulada seed"
                                ))
        
        # 6. Tipos de Cambio (Ejemplo)
        db.add(ExchangeRate(date=date(2026,1,1), base_currency="USD", target_currency="BOB", rate=Decimal("6.96")))
        
        # 7. Diccionario de Datos (Ejemplos Críticos)
        dict_entries = [
            DataDictionary(termino_usuario="presupuesto vigente", columna_canonica="current_amount", tabla_origen="budgets", descripcion="Presupuesto Inicial + Modificaciones (Ampliaciones - Reducciones)", sinonimos=["presupuesto actual", "vigente"], activo=True),
            DataDictionary(termino_usuario="ejecutado", columna_canonica="SUM(movements.amount)", tabla_origen="movements", descripcion="Suma de movimientos devengados (o pagados según configuración)", sinonimos=["ejecución", "gasto"], activo=True),
            DataDictionary(termino_usuario="saldo", columna_canonica="current_amount - executed", tabla_origen="budgets", descripcion="Presupuesto Vigente - Ejecutado", sinonimos=["disponible", "restante"], activo=True),
            DataDictionary(termino_usuario="financiador", columna_canonica="financiers.name", tabla_origen="financiers", descripcion="Entidad que provee los fondos", sinonimos=["fuente de financiamiento", "fuente"], activo=True),
            DataDictionary(termino_usuario="rubro", columna_canonica="rubros.name", tabla_origen="rubros", descripcion="Clasificación funcional del gasto (Nivel 1)", sinonimos=["partida", "clasificador"], activo=True),
        ]
        db.add_all(dict_entries)
        
        await db.commit()
        print("✅ Seed data completado: Usuarios, Scopes, 3 Años, 2 Regiones, 3 Áreas, 3 Financ, 2 Rubros, 4 Cuentas, Presupuestos, Modifs, Movimientos, Diccionario.")

if __name__ == "__main__":
    asyncio.run(main())
backend/scripts/ingest_knowledge.py (RAG INGESTA)
# backend/scripts/ingest_knowledge.py
import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.rag_service import RAGService

# Helpers extracción texto (Instalar: pypdf, python-docx, markdown-it-py)
def extract_text(filepath: Path) -> str:
    suffix = filepath.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        return "\n".join([p.extract_text() for p in PdfReader(filepath).pages])
    elif suffix == ".docx":
        from docx import Document
        return "\n".join([p.text for p in Document(filepath).paragraphs])
    elif suffix in [".txt", ".md"]:
        return filepath.read_text(encoding="utf-8")
    return ""

async def main():
    engine = create_async_engine(settings.DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    docs_path = Path("/app/data_docs")
    if not docs_path.exists():
        print(f"❌ Directorio {docs_path} no existe. Monta volumen en docker-compose.")
        return

    files = list(docs_path.rglob("*"))
    if not files:
        print("⚠️ No hay archivos en data_docs. Pon tus PDFs/DOCs/TXTs allí.")
        return

    async with async_session() as db:
        rag = RAGService(db)
        for f in files:
            if f.is_file() and f.suffix.lower() in [".pdf", ".docx", ".txt", ".md"]:
                print(f"📄 Procesando: {f.name}...")
                text = extract_text(f)
                if not text.strip():
                    print(f"   ⚠️ Vacío o error extracción.")
                    continue
                # Metadatos heurísticos
                source_type = "manual"
                if "ley" in f.name.lower() or "decreto" in f.name.lower(): source_type = "law"
                elif "reglamento" in f.name.lower(): source_type = "regulation"
                elif "faq" in f.name.lower(): source_type = "faq"
                elif "clasificador" in f.name.lower(): source_type = "classifier"
                
                await rag.ingest_text(
                    content=text,
                    source_type=source_type,
                    source_id=f.stem,
                    source_title=f.name,
                    tags=[source_type, f.stem],
                    chunk_size=512,
                    chunk_overlap=50
                )
                print(f"   ✅ {f.name} ingestado.")
        await db.commit()
        print("🎉 Ingesta RAG completada.")

if __name__ == "__main__":
    asyncio.run(main())
11. COMANDOS DE VALIDACIÓN (COPIA Y PEGA EN TERMINAL)
# 1. CLONAR / ENTRAR
cd budget-ai-copilot

# 2. CONFIGURAR ENTORNO
cp .env.example .env
# EDITAR .env: Poner tus credenciales OIDC reales (Keycloak/Auth0/Google), SECRET_KEY, etc.
# MÍNIMO REQUERIDO PARA ARRANCAR: SECRET_KEY, OIDC_*, POSTGRES_*

# 3. DESCARGAR MODELO LLM (Una vez, ~4.5 GB)
mkdir -p llama.cpp/models
cd llama.cpp/models
wget -q --show-progress https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf
cd ../..

# 4. LEVANTAR STACK COMPLETO
docker-compose up --build -d

# 5. VERIFICAR LOGS (Esperar a que todos estén healthy)
docker-compose logs -f --tail=50
# Esperar: postgres (healthy), llama-cpp (loaded model), embeddings (healthy), backend (started), frontend (nginx ready)

# 6. EJECUTAR MIGRACIONES Y SEEDS (Dentro contenedor backend)
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/seed_data.py
docker-compose exec backend python scripts/ingest_knowledge.py

# 7. ABRIR NAVEGADOR
# Frontend: http://localhost:8080
# Backend Swagger: http://localhost:8000/docs
# LLM Health: http://localhost:8081/health
# Embeddings Health: http://localhost:8082/health

# 8. PRUEBA MANUAL COMPLETA (Checklist Aceptación)
# [ ] Login con analista.norte@inst.gov / Password123!
# [ ] Chat: "Muéstrame ejecución 2026" -> Ver KPIs, Gráfico, Tabla, Chips Filtros (Año:2026)
# [ ] Chat: "Desglosa por financiador" -> Contexto mantiene 2026, Agrega group_by=financier
# [ ] Chat: "Compara con 2025" -> Tool compare_budget_periods, Gráfico agrupado, Diff %
# [ ] Chat: "¿Qué dice el reglamento sobre ampliaciones?" -> Tool search_institutional_knowledge, Respuesta con CITAS [Fuente 1: ...]
# [ ] Verificar Aislamiento: Login con analista.sur@inst.gov -> "Muéstrame ejecución 2026" -> SOLO ve Región Sur.
# [ ] Exportar Excel/PDF desde tabla (Botón en DataTable).
# [ ] Ver Swagger /audit/logs -> Registros de consultas.
12. CRITERIOS DE ACEPTACIÓN FASE 1 (DEFINICIÓN DE HECHO - DO NOT MERGE SI FALLA)
#	Criterio	Verificación Automatizada / Manual
A1	Repo Estructura	tree -L 3 coincide exactamente con Sección 3.
A2	Docker Compose Up	docker-compose up --build -d → 5 contenedores healthy en < 5 min (incluyendo carga modelo LLM).
A3	Auth OIDC Flow	Login redirige a Proveedor → Callback crea User en BD → Cookie HttpOnly Secure → /api/v1/auth/me devuelve user+roles+scopes.
A4	Motor Financiero - Exactitud	pytest backend/app/tests/test_financial_engine.py -v → 100% Passed. Tests cubren: Decimales exactos, Fórmulas (Vigente=Inicial+Modif), Permisos (Scope Region), Comparativas, Div/Zero, Agregados 7 Informes.
A5	RAG Ingesta + Búsqueda	python scripts/ingest_knowledge.py sin errores. pytest backend/app/tests/test_rag_service.py → Búsqueda semántica devuelve chunks relevantes > threshold.
A6	Chat Tool Calling Financiero	Pregunta "Ejecución 2026 por financiador" → Logs muestran tool_call: get_execution_by_financier → Resultado → Respuesta final con KPIs/Tabla/Gráfico.
A7	Chat Tool Calling RAG	Pregunta "Ley modificaciones presupuestarias" → Logs muestran tool_call: search_institutional_knowledge → Respuesta final CITA FUENTES [Fuente 1: ...].
A8	Contexto Conversacional	3 Turnos: "2026" → "por financiador" → "compara 2025" → ConversationContext en BD actualizado correctamente (years=[2025,2026], group_by=financier). Chips UI reflejan filtros.
A9	Aislamiento Datos (RBAC + Scope)	User "Norte" NO ve datos "Sur" en Chat ni en API /budget/* directo. test_auth.py cubre esto.
A10	Frontend Web Funcional	Carga en Chrome/Firefox. Login → Chat renderiza: Burbujas, Tarjetas KPI, Gráfico (fl_chart), Tabla Paginada/Ordenable (syncfusion), Chips Filtros Activos. Responsive (Mobile < 600px / Desktop).
A11	Streaming SSE	Primer token delta < 2s en red local. Tool calls intermedios visibles en UI ("Consultando motor financiero...").
A12	Calidad Código	mypy --strict backend/app → 0 errors. ruff check backend → 0 errors. flutter analyze → 0 errors. black --check backend → Pass.
A13	Auditoría	Tabla audit_logs poblada en cada consulta chat y API financiera (user_id, action, resource, payload, status).
13. NOTAS FINALES PARA EL AGENTE (IMPORTANTE)
 1. NO IMPROVISES FÓRMULAS CONTABLES. Si en FinancialEngine no está 100% claro cómo la institución calcula "Ejecutado" (Devengado vs Pagado) o "Modificaciones", pon un TODO comentado y usa la fórmula estándar (Inicial + Ampl - Red = Vigente; Ejecutado = SUM Movimientos tipo 'devengado'). Pregunta al usuario humano antes de asumir.
 2. TIPEO ESTRICTO. mypy --strict es obligatorio en backend/app. Usa from __future__ import annotations. Tipar todo: args, returns, generics.
 3. MANEJO DE ERRORES. Excepciones personalizadas (AppException, NotFoundException, ForbiddenException, ValidationException) + Handler global en main.py que devuelve ProblemDetail (RFC 9457) o JSON estándar {detail, code, status}.
 4. LOGGING ESTRUCTURADO. Usa structlog en backend. Logs JSON con request_id, user_id, tool_name, latency_ms. Crítico para depurar Tool Calling.
 5. SEGURIDAD POR DEFECTO.
- Cookies: HttpOnly; Secure; SameSite=lax; Path=/.
- CORS: Solo BACKEND_CORS_ORIGINS exactos.
- Headers Nginx (Frontend): CSP, X-Frame-Options: DENY, Referrer-Policy: strict-origin-when-cross-origin.
- Rate Limiting: Añadir slowapi en Fase 2. En Fase 1 confía en red privada.
 6. COMMITS ATÓMICOS. Un commit por tarea lógica (T0 Docker, T1 Auth, T2 FinancialEngine, T3 RAG, T4 ChatService, T5 Frontend Base, T6 Chat UI, T7 Integración). Mensajes: feat(financial): implement execution_by_financier engine, feat(rag): add bge-m3 ingestion script, feat(chat): implement tool calling loop.
 7. DOCS MÍNIMAS. Cada archivo .py principal tiene docstring módulo. Cada endpoint @router.get/post tiene summary y description para OpenAPI.
 8. PRUEBAS UNITARIAS REALES. No mocks tontos. test_financial_engine.py usa fixture db_session con transacción rollback y datos seed_data reales insertados en setup. Verifica Decimal exactos.
 9. VOLÚMENES DOCKER. backend monta ./backend:/app:ro y ./data_docs:/app/data_docs:ro. llama.cpp/models y tei_cache son volúmenes named para persistencia.
10. SI ALGO FALLA EN docker-compose up: Revisa docker-compose logs <servicio>. Común: LLM OOM (baja n-gpu-layers o usa imagen CPU), PGVector extension missing (revisa init-db.sh), OIDC redirect mismatch (revisa .env vs Config Proveedor).
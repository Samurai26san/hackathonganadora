# ExB Finanzas + Juku

MVP Flutter Web para el presupuesto institucional de Enseña por Bolivia, con
FastAPI, PostgreSQL/pgvector y un orquestador de herramientas para Juku.

La interfaz respeta `fronted/Interfaz_ExB_Juku.md`, el logo y la mascota originales,
la paleta verde/lima y la navegación Dashboard → Presupuesto, Reportes,
Movimientos y Gestiones. El backend conserva las dimensiones e informes de
`backend/hackaton/` y usa `Decimal` en lugar de sus cálculos previos con float.
Las fuentes recibidas permanecen intactas.

El Excel se reconcilia exactamente: **presupuesto Bs 3.163.379,01**, **ejecución
Bs 528.694,16**, **saldo Bs 2.634.684,85**. Solo contiene 2026; no se simulan otros
años. Los siete informes y las exportaciones aplican los mismos alcances y filtros.

## Ejecutar localmente

Requisitos: Python 3.12, uv, Docker Compose y Flutter con Dart >=3.8.

```bash
make backend-setup
flutter pub get
cp .env.example .env
# Configura .env según docs/deployment.md.
docker compose up -d postgres
make migrate
make seed
make api
```

En otra terminal:

```bash
make web
# Alternativa: make web-build && make web-preview
```

Abre **http://localhost:8080**. API: **http://localhost:8000/docs**.

Para demo local: `.env` debe declarar `AUTH_MODE=demo`, `APP_ENV=development` y
`COOKIE_SECURE=false`. La semilla habilita `tecnico@exb.demo` y `admin@exb.demo`,
contraseña `Demo2026!`. El formulario nunca permite escoger un rol libremente.
No uses credenciales institucionales reales en este modo.

En producción se exige OIDC con PKCE, cookies Secure y HTTPS. Debes configurar
el proveedor y provisionar el correo institucional del primer administrador.

## Juku e IA local

Juku selecciona únicamente herramientas financieras permitidas o búsqueda
institucional. El motor aplica permisos en SQL y calcula en Decimal; el modelo
no genera SQL ni escribe datos financieros. Las conversaciones guardan filtros,
reporte, mensajes y resultados. SSE muestra herramientas y resultados en tiempo
real, con evidencia y citas para los documentos recuperados.

Para IA real, descarga Qwen2.5-7B GGUF y arranca llama.cpp con `--jinja`; TEI carga
BAAI/bge-m3. Coloca documentos autorizados en `data_docs/` y ejecuta `make ingest`.
Sin esos servicios, el panel y los informes funcionan y Juku explica la ausencia
de conexión, sin inventar respuestas. Detalles en [despliegue](docs/deployment.md)
y [RAG](docs/rag_guide.md).

## Comprobaciones

```bash
make backend-check    # ruff, black, mypy estricto y pytest
flutter analyze
flutter test
make web-build
```

Las pruebas backend usan SQLite temporal como banco aislado. Para repetirlas
sobre PostgreSQL/pgvector crea una base **separada** y ejecuta:

```bash
TEST_DATABASE_URI=postgresql+asyncpg://postgres:postgres@localhost:55432/budget_ai_test make backend-test
```

[Validación realizada](docs/VALIDATION.md) · [Arquitectura](docs/architecture.md) ·
[Contrato API](docs/api_contract.md) · [OpenAPI](docs/openapi.json) ·
[Diccionario](docs/data_dictionary_guide.md) · [Especificación](SPEC.md).

## Skills del proyecto

Las skills y herramientas de `agents/` siguen disponibles mediante
[AGENTS.md](AGENTS.md), el [catálogo](docs/AGENT_CATALOG.md) y la
[guía de instalación](docs/AGENTS_SETUP.md).

.PHONY: agents-setup agents-sync agents-config agents-check agents-doctor agents-test agents-graph check

agents-setup:
	uv venv --allow-existing .agents/.venv
	uv pip install --python .agents/.venv/bin/python -r tools/agents-requirements.txt
	.agents/.venv/bin/python tools/agents.py sync
	.agents/.venv/bin/python tools/agents.py configure-mcp

agents-sync:
	.agents/.venv/bin/python tools/agents.py sync

agents-config:
	.agents/.venv/bin/python tools/agents.py configure-mcp

agents-check:
	.agents/.venv/bin/python tools/agents.py check

agents-doctor:
	.agents/.venv/bin/python tools/agents.py doctor

agents-test:
	.agents/.venv/bin/python -m unittest discover -s tools -p 'test_*.py'

agents-graph:
	.agents/.venv/bin/python tools/agents.py graph-build

check: agents-check agents-test backend-check
	flutter analyze
	flutter test

.PHONY: backend-setup backend-test backend-check api web web-build web-preview up down logs migrate seed ingest test
ADMIN_EMAIL ?= admin@exb.demo
EXCEL ?= hackaton/Prueba ExB Nov 2026 (1) (1).xlsx

backend-setup:
	uv venv --python python3 --allow-existing backend/.venv
	uv pip install --python backend/.venv/bin/python -r backend/requirements.txt

backend-test:
	cd backend && PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p pytest_asyncio.plugin app/tests -q

backend-check:
	backend/.venv/bin/ruff check backend/app backend/scripts
	backend/.venv/bin/black --check backend/app backend/scripts
	PYTHONPATH=backend backend/.venv/bin/mypy --config-file backend/pyproject.toml backend/app
	$(MAKE) backend-test

api:
	cd backend && PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload --reload-dir app --no-access-log --host 127.0.0.1 --port 8000

web:
	flutter run -d web-server --web-port 8080 --dart-define=API_BASE_URL=http://localhost:8000/api/v1/

web-build:
	flutter build web --release --no-web-resources-cdn --no-wasm-dry-run

web-preview:
	python3 tools/serve_web.py --port 8080

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=50

migrate:
	cd backend && .venv/bin/alembic upgrade head

seed:
	cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_data.py --excel "$(EXCEL)" --admin-email "$(ADMIN_EMAIL)"

ingest:
	cd backend && PYTHONPATH=. .venv/bin/python scripts/ingest_knowledge.py ../data_docs

test: backend-test
	flutter test

.PHONY: models oidc-local ai-local runtime-check
models:
	python3 tools/download_models.py
	python3 tools/download_models.py --manifest ops/embeddings.json --folder ops/runtime/bge-m3 --workers 4

oidc-local:
	python3 tools/setup_local_oidc.py
	docker compose -f docker-compose.yml -f docker-compose.local.yml up -d keycloak

ai-local:
	docker compose -f docker-compose.yml -f docker-compose.local.yml up -d llama-cpp embeddings

runtime-check:
	backend/.venv/bin/python backend/scripts/validate_runtime.py --phase all

.PHONY: mobile
mobile:
	python3 tools/run_mobile.py

.PHONY: qwen
qwen:
	systemd-run --user --scope --collect -p MemoryMax=1400M -p MemorySwapMax=0 nice -n 10 python3 tools/run_qwen.py

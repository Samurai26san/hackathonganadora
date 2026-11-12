# Desarrollo y despliegue

## Desarrollo local verificable

Se requiere Flutter compatible con Dart >=3.8, Python 3.12, uv y Docker Compose.

```bash
make backend-setup
flutter pub get
cp .env.example .env
```

Para una demostración local, establece en `.env`:

```dotenv
APP_ENV=development
AUTH_MODE=demo
COOKIE_SECURE=false
DATABASE_URI=postgresql+asyncpg://postgres:postgres@localhost:55432/budget_ai
```

Genera `SECRET_KEY` con `openssl rand -hex 32`. No uses cuentas institucionales
reales en modo demo. Nunca habilites este modo en producción.

```bash
docker compose up -d postgres
make migrate
make seed
make api
```

En otra terminal: `make web` para desarrollo con Flutter o `make web-build` y
`make web-preview` para el build de producción con proxy local. Abre
`http://localhost:8080`. API: `http://localhost:8000/docs`.

`make seed` ingiere el Excel incluido por su ruta original. No reinicia tablas
ni añade gestiones ficticias. Cuentas exclusivamente demo:
`tecnico@exb.demo` y `admin@exb.demo`, contraseña `Demo2026!`.

## Cinco servicios Docker

El Compose incluye postgres, llama-cpp, embeddings, backend y frontend. Los
modelos son requisitos externos reales, no archivos vacíos que simulen IA.

```bash
python3 tools/download_models.py
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_data.py \
  --excel '/app/source_data/Prueba ExB Nov 2026 (1) (1).xlsx' \
  --admin-email admin@tu-institucion.org
docker compose exec backend python scripts/ingest_knowledge.py
docker compose ps
```

La semilla anterior exige OIDC configurado. Para demo dentro de contenedores,
usa las variables demo y el correo `admin@exb.demo`. TEI descarga BGE-m3 en el
volumen `tei_cache`; la primera carga necesita red y memoria. El LLM usa CPU
por defecto. El modelo oficial tiene dos partes GGUF: el descriptor
`ops/models.json` fija revisión, tamaño y SHA-256. El descargador conserva
checkpoints por rangos y solo publica archivos cuyo hash coincide. Reanuda
el mismo comando si se interrumpe; evita ejecutarlo dos veces simultáneamente.
Para CUDA local usa el archivo adicional descrito abajo.

La API puede arrancar sin IA para que los informes sigan disponibles. Si Juku
no encuentra llama.cpp o TEI, muestra un error explícito y no simula resultados.
Los modelos no están expuestos directamente al navegador.

## Keycloak y modelos locales (P13–P15)

El usuario eligió Keycloak local para validar el flujo OIDC. Prepara `.env` con
una clave propia y conserva la base ya sembrada. El siguiente comando cambia
solo las opciones locales de identidad y endpoints, preservando esa clave:

```bash
python3 tools/setup_local_oidc.py
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d keycloak
# Reinicia la API propia para releer .env; sirve Flutter en localhost:8080.
make api
make web-preview
# Con Keycloak disponible, comprobar el flujo sin simular proveedor:
backend/.venv/bin/python backend/scripts/validate_runtime.py --phase oidc
# Informes y exportaciones con una sesión real, incluso sin modelos:
backend/.venv/bin/python backend/scripts/validate_runtime.py --phase finance
```

Keycloak usa `http://localhost:8180/realms/exb-local`, cliente público
`budget-copilot-web`, Authorization Code y PKCE S256. Las cuentas locales
`admin@exb.demo` y `tecnico@exb.demo` usan `Demo2026!` en la página de Keycloak.
`sin-acceso@exb.demo` permite verificar que una identidad sin cuenta provisionada
recibe 403. Los roles y alcances provienen de la aplicación. El realm queda en
un volumen propio; el import inicial no sobreescribe un realm ya existente.

Para los modelos reales:

```bash
python3 tools/download_models.py
python3 tools/download_models.py --manifest ops/embeddings.json --folder ops/runtime/bge-m3 --workers 4
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d llama-cpp embeddings
```

La configuración adicional usa GPU NVIDIA, un slot de contexto 8192, caché KV
q8 y límites de memoria. Expone llama solo en 127.0.0.1:18081 y TEI en
127.0.0.1:8082; no ocupa 8081, usado por otro proyecto en este equipo. API y
Flutter permanecen como procesos locales. Es un entorno de desarrollo HTTP con
cookies HttpOnly y SameSite=Lax; la configuración de producción exige HTTPS y
Secure. No equivale a un proveedor institucional desplegado.

## OIDC y HTTPS

Registra un cliente con flujo Authorization Code y PKCE S256. Configura
`OIDC_PROVIDER_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` si es confidencial,
`OIDC_REDIRECT_URI` y orígenes exactos. El usuario debe tener correo verificado
y estar prehabilitado en `users`; el proveedor no concede permisos financieros
automáticamente. La primera cuenta admin se provisiona por CLI con el correo
institucional correcto. Después, Usuarios permite habilitar más cuentas.

Para producción: `APP_ENV=production`, `AUTH_MODE=oidc`, `COOKIE_SECURE=true`,
HTTPS en el proxy de entrada y URI de callback HTTPS pública. Limita el acceso
a PostgreSQL y a los servicios internos. No incluyas `.env`, Excel ni documentos
institucionales en imágenes públicas o repositorios públicos. Revisa los
materiales recibidos antes de publicar: contienen información financiera.

## Respaldo y restauración

```bash
docker compose exec -T postgres pg_dump -U postgres -Fc budget_ai > budget_ai.dump
# Restaurar en una base nueva previamente creada y verificada:
docker compose exec -T postgres pg_restore -U postgres -d budget_ai_restore < budget_ai.dump
```

Programa los respaldos con el plan operativo institucional, cifra su almacenamiento
y ensaya restauraciones. `make down` no borra volúmenes. No se ofrece downgrade
destructivo de la migración inicial. `/health` verifica proceso; `/ready` verifica
conectividad de base de datos. Comprueba también logs, migración y servicios IA
antes de anunciar disponibilidad de producción.

El ensayo local reproducible es
`backend/.venv/bin/python backend/scripts/validate_backup.py`. Verifica que el
contenedor pertenece a este proyecto, guarda el dump con permisos 0600 bajo
`ops/runtime/backups/`, restaura en una base temporal nueva y la elimina al
terminar. Nunca restaura sobre la base de origen. El informe queda en
`docs/validation_operations.json`.

# Validación del MVP

Comprobaciones realizadas el 12 de noviembre de 2026. El avance y el punto de
reanudación están en [tasks/PROGRESS.md](../tasks/PROGRESS.md).

## Backend

- **21 pruebas aprobadas sobre PostgreSQL 16 con pgvector**, en una base de
  pruebas separada de los datos de la app.
- Los siete informes concilian con el Excel original: presupuesto `3163379.01`,
  ejecución `528694.16`, saldo `2634684.85` y porcentaje `16.71`.
- Se verificaron 3.574 filas, 1.478 movimientos fechados, fuente SHA-256 e
  ingesta idempotente. Último movimiento del archivo: `2026-09-30`.
- Pruebas de centavos exactos, modificaciones sin duplicación por joins,
  división por cero, paginación, filtros, scopes vacíos y regionales.
- Comparativas con gestiones existentes, rechazo de años ausentes e indicador
  de ejecución/presupuesto. Los años adicionales solo existen en fixtures.
- Autenticación, RBAC, logout revocable, bloqueo de origen no autorizado y
  transacción OIDC con token RSA firmado, emisor, audiencia, nonce y PKCE.
- RAG: ingesta real en tablas, dimensión de embedding, umbral, filtros de tipo,
  reemplazo idempotente, persistencia de resultados pgvector y citas.
- Orquestación: herramientas no permitidas/SQL rechazados, parámetros
  estrictos, contexto de tres turnos y búsqueda documental con citas.
- Ruff, Black y mypy en modo estricto: comprobados sin incidencias.

Las respuestas de llama.cpp, TEI y OIDC en las pruebas se suministran mediante
transportes HTTP controlados. La persistencia, los cálculos, los filtros y la
verificación criptográfica sí se ejecutan realmente. Eso no sustituye una
evaluación de los modelos ni un acceso a un proveedor institucional real.

## Flutter y navegador

- **6 pruebas Flutter aprobadas**: moneda, rutas API, SSE UTF-8 fragmentado,
  contexto de filtros, login/navegación y adaptación a 375 px.
- `flutter analyze`: sin incidencias.
- `flutter build web --release --no-web-resources-cdn --no-wasm-dry-run`:
  build generado correctamente con el SDK local Flutter 3.47.5/Dart 3.13.4.
- Chromium: login con la API real, totales institucionales, Reportes, Gestiones
  sin comparaciones inventadas, panel de Juku y vista de 375 px. No se
  observaron errores JavaScript en el recorrido aprobado.
- Por HTTP se ejecutaron los siete informes y se descargaron respuestas
  Excel, PDF y CSV reales. La exportación con fechas también tiene regresión
  automatizada en las pruebas de autenticación/API.

Capturas del recorrido en [screenshots/](screenshots/). La interfaz usa la
paleta, logotipo, mascota, libros y módulos de los materiales recibidos.

## Empaquetado y servicios

- Migración Alembic aplicada y Excel real cargado en el PostgreSQL propio del
  proyecto. No se reiniciaron tablas ni contenedores ajenos.
- `docker compose config --quiet`: válido, cinco servicios definidos.
- Imagen backend construida; usuario de ejecución UID/GID 10001 y carga de la
  aplicación/OpenAPI verificada dentro de la imagen.
- `nginx -t`: configuración válida, con proxy sin buffering para SSE y headers.
- Imagen Flutter estable resuelta y fijada por digest; contiene Flutter 3.44.0.
  No se ejecutó la compilación completa dentro de esa imagen; la compilación
  verificada es la del SDK local. CI queda configurado para 3.44.0 y no se ha
  ejecutado en un proveedor remoto.

## Validación externa pendiente

No se descargó ni ejecutó Qwen2.5-7B, no se arrancó TEI con BGE-m3 y no se
configuraron credenciales OIDC institucionales. No se certifican cinco
contenedores healthy, latencia de primer token, calidad semántica del modelo,
acceso real con OIDC, HTTPS productivo ni restauración operativa de respaldos.

El código, las rutas y Compose están preparados para esos servicios. La app
expone errores claros si no están disponibles y permite seguir consultando los
informes. La incorporación de documentos normativos reales y la preparación
de servicios se describen en [deployment.md](deployment.md) y
[rag_guide.md](rag_guide.md).
# Validación P13–P15 en curso

La preparación adicional incluye modelos con revisión y hashes fijados,
descarga por rangos reanudables, Compose local con límites y fixture Keycloak.
Todavía no se han validado inferencia ni embeddings contra estos servicios.
OIDC real ya pasó 30 comprobaciones contra Keycloak local, además del recorrido
Flutter → Keycloak → panel en Chromium sin errores JavaScript.
Los resultados de ejecución real se guardarán en `validation_oidc.json` y
`validation_ai.json`, con el campo `passed` y las comprobaciones individuales.

Tras estos cambios pasan 21 pruebas backend en PostgreSQL y las tres pruebas
del reanudador (localhost). Ruff, Black y mypy no encuentran incidencias.
No se modificó Flutter; su validación previa se conserva a continuación.


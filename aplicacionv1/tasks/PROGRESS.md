# Extensión implementada: curaduría, contabilidad e informes técnicos

Solicitud: documento `docs/contabilidad/REQUISITOS.md`. Instrucción posterior:
«solo haz la tarea olvida las skill de validacion y prueba». No se ejecutaron
pruebas ni se arrancaron PostgreSQL, API, web o modelos durante esta entrega.

Pasos implementados:
1. Seis tablas aditivas y migración Alembic 0002: lotes/filas de preparación,
   cuentas jerárquicas, asientos/líneas y dictámenes/notas. SQL y ERD documentados.
2. API y Flutter de curaduría: Excel/plantilla, limpieza, edición de celdas,
   clasificación supervisada por similitud, validación humana, consolidación
   con permisos/versiones/motivo y bitácora privada por fila. Sin Qwen requerido.
3. Libro separado de partida doble, seis bloques a fecha exacta, clasificación
   de efectivo, resultado escalonado con IUE registrado y riesgos en dashboard.
4. Generador mensual/anual determinista: comparación disponible, calidad,
   simulación opcional de IUE y exportaciones PDF/XLSX con fórmulas. Filtro de
   validación integrado en informes presupuestarios y exportaciones anteriores.
5. Documentación, contrato OpenAPI y ejemplo FICTICIO en PDF/XLSX/JSON.

Comprobación realizada: sintaxis Python y carga del contrato API, generación de
SQL y documentos ficticios; compilación web release correcta. La última
compilación incorpora historial por fila y actualización de alertas. No se
comprobaron operaciones contra PostgreSQL ni recorridos de navegador por
petición del usuario; no afirmar validación regulatoria ni funcional completa.

Siguiente paso operativo exacto: `make mobile`. Ahora inicia solo PostgreSQL del
proyecto, aplica `alembic upgrade head` y abre web/API. Cargar primero la plantilla
de Curaduría para preparar datos. El APK previo conserva la versión anterior;
esta entrega actualiza el build web. Se conservaron los cambios preexistentes.

---

# Proyecto detenido por petición del usuario

El usuario pidió: «para todos los procesos». Se detuvieron los procesos propios
web/API/Qwen y los contenedores del proyecto exb-budget-copilot. Se conservaron
volúmenes, modelos descargados, Excel y auditoría. No reiniciar servicios hasta
una nueva petición. No se detuvieron servicios ajenos, incluido Ollama global.

Último avance Qwen: modelo cargado realmente; /health y /v1/models respondían.
Se corrigió OOM de 1400M con 2400M, --no-repack/--no-warmup y lotes 256/128.
La comprobación de respuesta financiera completa estaba pendiente y se interrumpió
por la orden de parada. No afirmar que se completó esa respuesta.

---

# En curso: enlace real Qwen → API → Juku

El usuario pidió enlazar el Qwen ya descargado. Se confirmó que el proceso anterior
moría por OOM del scope de 1400M. Se ajustó a 2400M y se deshabilitaron repacking y
warmup. Se aumentaron lotes a 256/128 para acelerar el primer procesamiento CPU.

- Ambos GGUF tienen SHA-256 válido. Qwen2.5-7B Q4_K_M cargó realmente y responde
  /health=ok y /v1/models en 127.0.0.1:18081 con el alias esperado por la API.
- Servicio propio activo: scope exb-qwen-linked-fast.scope. Log de modelo:
  ops/runtime/qwen-linked.log. El runner móvil existente sigue sirviendo 8088 y
  apunta a ese endpoint; no fue necesario cambiar Flutter ni recompilar el APK.
- Se está comprobando una consulta real por /api/v1/chat/stream con una sesión
  técnica demo. Log: ops/runtime/qwen-chat-link.log. Sigue pendiente observar
  tool_call/tool_result/done antes de afirmar una respuesta financiera completada.
- Se interrumpió una primera comprobación propia para ajustar los lotes; no se
  ejecutaron suites de skills ni se alteraron datos financieros.
- Los arranques futuros make mobile y make qwen conservan el límite corregido.
  La primera carga en CPU es lenta; no marcar RAG/embeddings como verificados.

---

# Último punto: arranque de PostgreSQL corregido

El usuario reportó make mobile fallando por conexión rechazada a PostgreSQL.
Se encontró el contenedor detenido y se inició exclusivamente postgres del
proyecto. make mobile depende ahora de mobile-db, que ejecuta docker compose
up -d --wait --wait-timeout 60 postgres antes de abrir la API. No se borraron
volúmenes, no se resembró información y no se ejecutaron pruebas de skills.
Se lanzó el MVP con el comando corregido; revisar /tmp/exb-mobile.log y
ops/runtime/mobile-api.log para estado actual. Documentación móvil actualizada.

---

# Último punto: APK Android compilado

El usuario pidió compilar el APK Flutter. Se generó correctamente un APK release
(59.4 MB) en `build/app/outputs/flutter-apk/app-release.apk`, también disponible
como `build/web/descargas/exb-finanzas.apk`. Hash en app-release.apk.sha256.

- Build: flutter build apk --release --dart-define=API_BASE_URL=http://172.18.143.26:8088/api/v1/
- Android: permiso INTERNET, nombre ExB Finanzas y HTTP autorizado solo para la
  IP local indicada mediante network_security_config. El backend debe seguir
  activo con make mobile y el celular en la misma red.
- Sesiones nativas en memoria mediante interceptor de cookies; acceso demo del
  runner móvil. Android incorpora selector/guardado de PDF, CSV, JSON y lectura
  de Excel con el canal exb/files y el selector de documentos del sistema.
- Se corrigió InputDecoration const con etiqueta variable que impedía compilar.
- Se redujo el máximo de memoria Gradle y se limitaron sus workers a dos.
- Compilación final exitosa. No se ejecutaron pruebas de skills. No se instaló
  ni probó el APK en un teléfono físico. Firma local de desarrollo existente.
- Pendiente previo conservado: cerrar activación/documentación de las correcciones
  financieras. La nueva petición de APK tuvo prioridad; no borrar datos ni historia.

---

# En curso: correcciones financieras solicitadas

El usuario eligió persistencia en backend y permisos reales, compartidos entre
PC/celular. Se usan incremental-implementation y flutter-expert; no se ejecutan
pruebas de skills ni diagnósticos GPU.

- PDF/CSV completos: informe, rubros, cuentas y todos los movimientos filtrados,
  cuentas sin ejecución, gestión/filtros, niveles CSV y secciones PDF.
- Nueva API `/api/v1/data/*`: CRUD con motivo, confirmación y versiones; categorías
  y scopes validados, auditoría antes/después, exportación JSON y restauración
  transaccional sin borrar historia ni sobrescribir Excel. No requiere migración.
- Flutter: Control de cambios e Historial de datos en Administración. Formularios
  y confirmaciones; invalidación local y revisión remota cada 10 segundos.
- Cuatro controles puntuales pasan en SQLite temporal; 17 controles relacionados
  pasaron antes de la última ampliación. Flutter analyze sin incidencias y build
  web generado. Comprobación PostgreSQL aislada en curso. mypy estaba limpio.
- Falta cerrar comprobaciones finales, registrar resultados y reiniciar únicamente
  el runner móvil propio para cargar el backend actualizado. No marcar terminado
  antes de ese arranque. Documentación: docs/CORRECCIONES_MVP.md.

---

# Corrección del aviso de Qwen pendiente

El usuario mostró el error del chat y el mensaje repetido de espera. La descarga
está activa, aproximadamente 64% (2.98/4.68 GB) al intervenir. No se afirma que
haya inferencia disponible. run_qwen.py muestra bytes/bloques confirmados cada
30 segundos y ofrece --status. LLMClient traduce conexión rechazada y HTTP 503
en mensajes explícitos de preparación/carga. Se actualizó el servidor móvil
propio para aplicar esos cambios. No se ejecutaron pruebas ni diagnósticos GPU.
Continuar la descarga existente; no duplicarla ni eliminar sus checkpoints.

---

# Último punto: Qwen integrado en el arranque móvil

El usuario pidió integrar Qwen en el chatbot y mantener omitidas las pruebas.

- `make mobile` inicia ahora un coordinador Qwen local junto con la web/API.
  Se reinició exclusivamente el servidor móvil propio para aplicar el cambio.
- `tools/run_qwen.py` reutiliza el modelo si ya está servido o espera la descarga
  activa; si falta y no hay descargador, la reanuda. Verifica hashes oficiales y
  el binario antes de ejecutar Qwen2.5-7B Q4_K_M con Jinja y alias estable.
- Ejecución CPU, sin cambiar controladores: scope de usuario con MemoryMax=1400M,
  MemorySwapMax=0, un slot, cuatro hilos, contexto 8192 y KV q8.
- La nueva API móvil apunta explícitamente a http://127.0.0.1:18081/v1, modelo
  qwen2.5-7b-instruct-q4_k_m, timeout local 900 s. El proxy SSE admite esa espera.
- Estado observado: coordinador activo esperando la descarga, primer GGUF todavía
  parcial. No hay inferencia verificada ni se afirma que Qwen ya esté respondiendo.
- Logs: ops/runtime/qwen.log y ops/runtime/mobile-api.log. La web sigue en 8088.
  No se ejecutaron pruebas de skills ni suites. Al salir, el runner detiene su
  scope Qwen propio y su API; no detiene un servidor Qwen previo reutilizado.
- `make qwen` permite arrancar Qwen solo. `--without-qwen` sirve solo web/API.

---

# Punto actual: MVP para celular (prioridad del usuario)

El usuario pidió omitir pruebas de skills y priorizar abrir el programa desde
su celular. No ejecutar más suites ni diagnósticos de GPU sin una nueva petición.

- MVP iniciado en `http://172.18.143.26:8088`, escuchando en 0.0.0.0:8088.
- `tools/run_mobile.py` sirve el build Flutter existente y una API propia de
  demostración en loopback/puerto dinámico, conectada al PostgreSQL real.
- Acceso local: tecnico@exb.demo / Demo2026!; admin@exb.demo misma contraseña.
- La PC y el celular deben compartir WiFi. No se verificó desde un teléfono real.
- `.env` y el acceso OIDC del entorno de escritorio se conservan; solo el nuevo
  proceso usa AUTH_MODE=demo, APP_ENV=development y COOKIE_SECURE=false para HTTP.
- Comando de reanudación: `make mobile`. Comprobar antes si 8088 ya está servido.
  Estado del arranque: `ops/runtime/mobile.json`; logs: `ops/runtime/mobile-api.log`.
- Instrucciones: `docs/MVP_CELULAR.md`. El arranque no ejecuta pruebas ni compila
  Flutter si ya existe build/web. Ctrl+C detiene solo sus procesos propios.
- Juku real continúa pendiente de modelos y ejecución; no hay respuestas de IA
  simuladas. Las descargas anteriores siguen en segundo plano con checkpoints.
- El primer intento de arranque en sandbox falló por permiso de socket; el
  arranque con permiso ampliado sí se ejecutó y la API alcanzó ready (200).

Los detalles históricos y pendientes P13–P15 siguen debajo. Esta prioridad de
arranque móvil sustituye la continuación automática de las pruebas anteriores.

---

# Punto de reanudación — ExB Finanzas + Juku

Última actualización: 12 de noviembre de 2026, zona America/La_Paz.

## Instrucción permanente del usuario

Avanzar por pasos verificables. Si se corta la sesión, leer este archivo y
`tasks/todo.md`, volver al último punto completado y seguir por el primer
pendiente. Conservar el código; no empezar de nuevo ni repetir comprobaciones
que no estén afectadas por nuevos cambios.

## Último paso completado: P12

P1–P12 están implementados y verificados hasta los límites descritos en
`docs/VALIDATION.md`. La siguiente etapa es **P13: servicios externos reales**.

### Código entregado

- Flutter Web en `lib/`, activos institucionales en `assets/`, Nginx en `frontend/`.
  Se conserva el proyecto Flutter de la raíz y sus comandos habituales.
- FastAPI en `backend/app/`, scripts en `backend/scripts/`, migración Alembic en
  `backend/migrations/`. Las fuentes `fronted/` y `backend/hackaton/` no se alteraron.
- Docker Compose de cinco servicios, `.env.example`, CI y guías de operación.
- Especificación de decisiones: `SPEC.md`. Prompt original: `docs/MVP_PROMPT.md`.

### Evidencia del último punto completado

- PostgreSQL/pgvector propio en `127.0.0.1:55432`, base `budget_ai`; pruebas en
  `budget_ai_test`, sin afectar contenedores ajenos.
- Excel real ingestado idempotentemente: 3.574 filas, 1.478 movimientos fechados,
  presupuesto `3163379.01`, ejecución `528694.16`, saldo `2634684.85`.
  Último movimiento `2026-09-30`. Solo existe gestión real 2026.
- **21 pruebas backend pasan sobre PostgreSQL**, incluidas cifras exactas,
  siete informes, scopes, OIDC firmado/PKCE, contexto de tres turnos y RAG con
  citas. Los proveedores IA/OIDC se simulan únicamente en los tests HTTP.
- Ruff, Black y mypy estricto comprobados sin incidencias.
- **6 pruebas Flutter pasan**, analyze sin incidencias y build web generado.
- Último recorrido Chromium aprobado: login con API real, cifras del panel,
  Reportes, Gestiones, Juku y 375 px, sin errores JavaScript.
- Capturas finales en `docs/screenshots/`; no hay captura temporal debug.
- Imagen backend construida y ejecutada con UID/GID 10001; importación de app y
  OpenAPI verificada. Compose válido y configuración Nginx probada con nginx -t.
- La etiqueta Docker Flutter 3.47.5 no existe. El Dockerfile fija por digest una
  imagen estable verificada con Flutter 3.44.0. CI usa 3.44.0, mientras que el
  build local verificado usa 3.47.5. No se construyó todo el frontend dentro de
  la imagen Docker ni se ejecutó el workflow en un proveedor remoto.

## Ejecución actual: P13–P15

El usuario autorizó avanzar P13–P15 y eligió **Keycloak local** para probar el
proveedor OIDC real. Se aplican las skills incremental-implementation y
llm-application-dev-ai-assistant. **Estado actual:** P13 modelos en descarga;
P14.a OIDC real verificado (30 comprobaciones y navegador), P14.b ingesta
pendiente; P15 respaldo/restauración y finanzas con OIDC verificados,
conversaciones con IA pendientes.
Los checkpoints siguientes conservan la secuencia del trabajo; este estado y
el último checkpoint verificado tienen prioridad sobre las notas anteriores.

- Descriptor `ops/models.json`: revisión inmutable y SHA-256 oficiales de las
  dos partes de Qwen2.5-7B Q4_K_M. La URL de archivo único de la guía era inválida.
- `python3 tools/download_models.py` reanuda parciales y verifica tamaño y hash
  antes de publicar cada GGUF; no iniciar dos descargas simultáneas.
- Descarga en curso al guardar: primera parte parcial; logs temporales
  `/tmp/exb-model-download.log`, imágenes CUDA/TEI en `/tmp/exb-*-pull.log`.
- Equipo: 16 GB RAM, ~2,6 GB disponibles, RTX 3060 6 GB y runtime NVIDIA Docker.
  Usar límites y un solo slot de inferencia. No detener servicios ajenos.
- El puerto 8081 está ocupado por otra aplicación: llama local usará 18081;
  TEI 8082 y Keycloak 8180, sujetos a comprobación antes de arrancar.
- Próximo punto: terminar descargas, verificar GPU y hashes, arrancar servicios;
  preparar Keycloak local sin publicar secretos ni confundirlo con OIDC productivo.

### Checkpoint P13–P15 (12 de noviembre, continuación)

- `docker-compose.local.yml` y `tools/setup_local_oidc.py` preparados y Compose
  validado. Realm exb-local, PKCE obligatorio, correo verificado y cliente público;
  fixture adicional sin-acceso para probar la denegación a cuentas no provisionadas.
- API propia reiniciada en 8000 con AUTH_MODE=oidc. El proveedor todavía está
  descargándose: hasta arrancar Keycloak, el inicio OIDC no estará disponible.
  Se deshabilitó el access log de Uvicorn para no registrar códigos de callback;
  permanece el registro estructurado de rutas sin query strings.
- Backend: 21/21 pruebas en PostgreSQL, también sin forzar AUTH_MODE=demo en el
  comando. La fixture de pruebas aísla su ruta demo del entorno OIDC local.
  Ruff/Black/mypy correctos. Descargador: 3 pruebas reales con servidor localhost
  pasan (prefijo secuencial, archivo disperso y revisión incompatible).
- `backend/scripts/validate_runtime.py` prepara comprobaciones OIDC y AI reales;
  no se ejecutaron todavía contra Keycloak/modelos. Guarda informes JSON sin
  tokens, códigos ni cookies. Usar primero `--phase oidc`; después `--phase ai`.
- Nuevos comandos: `make models`, `make oidc-local`, `make ai-local`,
  `make runtime-check`. No usar `make seed` para reanudar esta base existente.
- Descargas Qwen/BGE en curso con archivos `.partial` y `.ranges.json`:
  conservar ambos; el tamaño aparente del archivo disperso NO indica avance.
  El checkpoint enumera bloques completos; el hash verifica finalmente cada archivo.
- Se descubrió CUDA 12.4 ya instalado. Para reducir descargas se está preparando
  también el binario oficial llama.cpp b12319 Vulkan (SHA-256 publicado en GitHub)
  en `ops/runtime/llama/`; todavía no se ejecutó. La imagen CUDA completa se pausó.
  No confundir binario descargado o configuración con inferencia probada.

### Checkpoint de red y operación

- El descargador usa ahora bloques de 8 MB, escritura atómica del checkpoint y
  bloqueo para impedir dos descargas en la misma carpeta. Migra los bloques
  completos de 64 MB sin descargarlos otra vez. Cuatro pruebas de reanudación
  pasan; los parciales en curso se conservan en sus carpetas originales.
- P15 operación: `backend/scripts/validate_backup.py` pasó en PostgreSQL real.
  Creó un dump privado bajo `ops/runtime/backups/`, lo restauró en una base
  temporal nueva y comparó 3574 presupuestos, 1478 movimientos, Bs 3163379.01
  y Bs 528694.16, además de pgvector. La base temporal se eliminó correctamente;
  la base original no se reemplazó. Informe: `docs/validation_operations.json`.
- Grafo actualizado con los cambios; excluye los artefactos grandes de runtime.
  Siguiente hito sigue siendo arrancar Keycloak y ejecutar la fase OIDC real.

### P14.a verificado: Keycloak y acceso desde Flutter

- Keycloak 26.4.7 en localhost:8180, realm exb-local importado y volumen persistente.
  Imagen fijada por digest. No eliminar ese volumen: los sujetos OIDC ya están
  vinculados con las cuentas locales prehabilitadas de la aplicación.
- `backend/scripts/validate_runtime.py --phase oidc`: **30 comprobaciones pasan**
  con proveedor real, PKCE S256, callback, cuenta no provisionada denegada, roles,
  cookies HttpOnly/SameSite, rotación, cookie anterior revocada, CSRF y logout.
  Informe reproducible: `docs/validation_oidc.json` (passed=true).
- Chromium real también completó Flutter → Keycloak → panel con importes del
  Excel y cookie HttpOnly, sin errores JS. Capturas nuevas:
  `docs/screenshots/login-oidc.png`, `keycloak-local.png`, `dashboard-oidc.png`.
- Se corrigió el cliente de validación para emular solo en localhost el envío
  de las cookies Secure de Keycloak que Chromium sí realiza en HTTP local.
  No se modificaron la política de cookies ni la validación de la aplicación.
- Prompt: esquemas de herramientas compactados de 5303 a 3840 tokens estimados;
  se conservan todas las restricciones. No se duplica el texto RAG en el prompt.
  Backend: 21 pruebas pasan; después de compactar RAG, 5 pruebas de chat/RAG pasan.
- P13 y P14.b/P15 AI siguen pendientes: modelos en descarga. El siguiente paso
  es verificar binario llama.cpp y terminar GGUF/BGE; después validar embeddings,
  ingesta y conversaciones reales con `--phase ai`. No marcar P14 completo aún.

Para reanudar identidad si el contenedor se detiene:
`docker compose -f docker-compose.yml -f docker-compose.local.yml up -d keycloak`.
No volver a sembrar la base ni recrear el realm.

### P15.b verificado: finanzas con OIDC real

- `backend/scripts/validate_runtime.py --phase finance`: **20 comprobaciones
  pasan**, siete informes con la misma conciliación exacta, Excel/PDF/CSV,
  catálogo solo 2026 y comparación con 2025 denegada. Informe:
  `docs/validation_finance.json` (passed=true).
- El helper financiero se reutiliza en la futura fase AI. No modifica hechos
  financieros; la sesión se obtuvo desde Keycloak por Authorization Code/PKCE.
- Herramientas: **12 pruebas pasan** (8 existentes y 4 del reanudador).
- Descargas activas usan Qwen `--workers 16` y BGE `--workers 8`; comprobar
  procesos antes de reanudar, pues el bloqueo evita ejecutar dos veces la misma
  carpeta. El archivo parcial puede ser disperso: leer `.ranges.json` para avance.
- Instalador reproducible del binario oficial: `python3 tools/setup_llama.py`.
  Esperar a que termine el curl actual antes de invocarlo; todavía no se ha probado
  el binario ni el modelo. Fuentes/hashes: `ops/llama-runtime.json`.

### Checkpoint de hardware P13 (pendiente de decisión de ejecución)

- Binario oficial llama.cpp b12319 descargado, SHA-256 válido y CLI ejecutable
  (0.9.0-dev, commit f3d7725a7). `tools/setup_llama.py` lo verifica/reutiliza.
- **No cargar Qwen en Vulkan0 automáticamente**: `--list-devices` solo detecta
  Intel UHD con RAM compartida. NVIDIA no aparece ni forzando su ICD instalado.
- CUDA nativo devuelve **100 / CUDA_ERROR_NO_DEVICE**. NVML/nvidia-smi sí ve la
  RTX 3060 (6 GB, ~5821 MiB libres). Los nodos UVM existen, tienen permisos de
  acceso y el módulo está cargado; la traza abre los dispositivos correctamente.
- Docker requiere `--runtime=nvidia` explícito por su modo CDI. La prueba efímera
  con ese runtime llega a CUDA, pero devuelve 999; la prueba con dispositivos y
  biblioteca local explícitos devuelve 100. No se han cambiado controladores,
  reiniciado GPU, descargado módulos ni detenido servicios ajenos.
- Se fijó revisión para una posible compilación CUDA en `ops/llama-cuda.json`,
  pero **no se inició ninguna compilación**: primero debe funcionar la API CUDA.
  Compilar otra aplicación no resuelve por sí solo este error del entorno.
- `systemd-run --user --scope -p MemoryMax=1800M -p MemorySwapMax=0 true` pasó;
  se pueden acotar procesos propios por memoria sin cambiar servicios globales.
- Se preguntó al usuario por CPU con límites / resolver NVIDIA / otro servidor.
  Mientras tanto las descargas continúan. Comprobar si llegó respuesta antes de
  elegir la ejecución. No afirmar que inferencia o embeddings están verificados.

## Alcance pendiente de P13–P15

1. Leer `docs/deployment.md` y comprobar recursos de RAM/GPU/disco disponibles.
2. Preparar el GGUF Qwen2.5-7B en `llama.cpp/models/` y arrancar llama.cpp con
   `--jinja`. No sustituir por respuestas inventadas.
3. Arrancar TEI con BGE-m3 y comprobar embeddings de 1024 componentes.
4. Ingerir documentos institucionales autorizados desde `data_docs/`.
5. OIDC real local ya verificado con Keycloak elegido por el usuario. Mantener
   su volumen. OIDC institucional/HTTPS productivo requieren configuración propia.
6. Probar end-to-end financiero y normativo con modelos reales, alcances,
   citas, cookies Secure y medición de latencia. Registrar resultados.

P13 no está verificado: los modelos grandes siguen parciales y no se arrancó
TEI. El proveedor OIDC local sí está verificado. No afirmar que hay cinco
servicios healthy, inferencia real validada o despliegue productivo listo.

## Arranque y continuidad local

Comprobar primero qué procesos siguen activos; pueden detenerse entre sesiones:

```bash
docker compose ps
# Si PostgreSQL propio no está iniciado:
docker compose up -d postgres
# En terminales separadas:
make api
make web-preview
# Solo si cambió Dart/web o falta build/web:
make web-build
```

La API usa puerto 8000 y el frontend 8080. Antes de reiniciar, verificar que el
proceso pertenece a este proyecto. No detener ni reconfigurar otros servicios.
La API de esta sesión se dejó con --reload-dir app y la vista previa con
`tools/serve_web.py`; los IDs de proceso/sesión no son permanentes.

Demo local: `tecnico@exb.demo` o `admin@exb.demo`, contraseña `Demo2026!`.
`.env` local usa ahora AUTH_MODE=oidc y el realm exb-local de Keycloak, por
elección del usuario. APP_ENV=development y COOKIE_SECURE=false para localhost.
Las credenciales se introducen en Keycloak. No revelar SECRET_KEY ni habilitar
demo en producción. No hay que volver a sembrar o recrear la base para continuar.

Comprobaciones disponibles:

```bash
make backend-check
TEST_DATABASE_URI=postgresql+asyncpg://postgres:postgres@localhost:55432/budget_ai_test make backend-test
flutter analyze
flutter test
```

Los logs `/tmp/exb-*.log` y scripts temporales de Playwright pueden no sobrevivir
entre sesiones; la fuente de continuidad es este archivo y el informe de
validación, no los logs ni IDs temporales.

# Contrato API v1

OpenAPI completo generado: `docs/openapi.json`. Swagger interactivo: `/docs`.

| Ruta | Uso |
| --- | --- |
| POST `/api/v1/auth/login` | URL OIDC o acceso demo habilitado |
| GET `/api/v1/auth/callback` | PKCE/state/nonce + ID token validado |
| GET `/api/v1/auth/me` | Identidad, rol y alcances |
| POST `/api/v1/auth/refresh`, `/logout` | Rotación/revocación de sesión |
| GET `/api/v1/catalogs` | Catálogos autorizados |
| GET `/api/v1/budget/execution/{type}` | account, financier, area, region, monthly, movements, summary |
| GET `/api/v1/budget/compare` | Comparación de gestiones existentes |
| POST `/api/v1/reports/export` | Excel, PDF o CSV con filtros idénticos |
| POST `/api/v1/chat/stream` | Conversación y herramientas por SSE |
| GET/POST `/api/v1/sessions` | Historial propio / conversación nueva |
| GET `/api/v1/sessions/{id}/messages`, `/context` | Mensajes y filtros propios |
| POST `/api/v1/sessions/{id}/context/reset` | Limpiar contexto estructurado |
| GET/POST/PUT/DELETE `/api/v1/dictionary` | Administración del diccionario |
| POST `/api/v1/knowledge/ingest`, `/search` | Ingesta administrativa y consulta |
| POST `/api/v1/imports/preview` | Validación Excel sin escritura financiera |
| GET/POST/PUT `/api/v1/users` | Usuarios y alcance, solo admin |
| GET `/api/v1/audit/logs` | Auditoría, solo admin |

Filtros: `years=2026`, `financier_ids=1,2`, `region_ids`, `area_ids`, `rubro_ids`,
`cuenta_ids`, `months=0,3`, `date_from=2026-03-01`, `date_to=2026-03-31`, `search`,
`page`, `page_size`. Los filtros nuevos se intersectan con permisos; nunca los
reemplazan. Un alcance `null` es irrestricto y `[]` deniega toda esa dimensión.

Los importes se devuelven como strings decimales. Los datos de un informe se
separan en `summary`, `rows`, `metadata` y `chart_spec`. Las filas conservan IDs de
dimensiones para navegar al detalle. El presupuesto se filtra por gestión y
mes BD; el rango de fechas acota ejecución y modificaciones, lo que se declara
en los metadatos. Las exportaciones omiten la paginación y repiten los filtros.

SSE usa `event: <tipo>` y `data: {event, data, session_id}`. Eventos válidos:
`delta`, `tool_call`, `tool_result`, `context_update`, `done`, `error`. Un fallo
no se presenta como respuesta financiera satisfactoria. El cliente conserva
tarjetas y texto como mensajes distintos y detecta conexiones incompletas.

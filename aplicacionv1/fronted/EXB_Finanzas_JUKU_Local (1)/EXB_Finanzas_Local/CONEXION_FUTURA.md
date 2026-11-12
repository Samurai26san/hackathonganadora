# Conexión futura — propuesta para el equipo

Este documento es un contrato de diseño, no una integración ya implementada. La versión actual no hace solicitudes de red. No requiere claves de API ni secretos.

## Camino de migración

1. Validar pantallas, nombres y reglas con la organización.
2. Crear FastAPI y PostgreSQL; cargar y reconciliar los datos originales del Excel en el servidor.
3. Sustituir el repositorio local por llamadas HTTP asíncronas y estados de carga/error. Mover agregaciones y filtros al backend para no descargar la base completa.
4. Implementar sesión real y comprobar permisos en cada endpoint y consulta. Los roles nunca deben confiar en una variable del navegador.
5. Implementar importación del Excel contable con vista previa, errores por fila, detección de duplicados y confirmación transaccional.
6. Generar XLSX y PDF en el servidor con los mismos filtros y reglas que usa la pantalla.
7. Añadir JUKU privado con acciones permitidas, parámetros validados y consultas limitadas por usuario.
8. Probar aislamiento de permisos, consistencia financiera, restauración de respaldos y auditoría antes de producción.

## Rutas propuestas

| Método y ruta | Propósito | Acceso |
| --- | --- | --- |
| POST /api/session | Iniciar sesión | Público con protección contra abuso |
| DELETE /api/session | Cerrar sesión | Autenticado |
| GET /api/me | Cuenta, rol y permisos | Autenticado |
| GET /api/catalogs | Gestiones y dimensiones autorizadas | Técnico / Administrador |
| GET /api/dashboard | Indicadores y series agregadas | Técnico / Administrador |
| GET /api/budgets | Presupuesto por rubro/cuenta y dimensiones | Técnico / Administrador |
| GET /api/reports/{type} | Uno de los siete informes | Técnico / Administrador |
| GET /api/movements | Transacciones filtradas y paginadas | Técnico / Administrador |
| GET /api/movements/{id} | Ficha de una transacción autorizada | Técnico / Administrador |
| GET /api/comparisons | Comparación de gestiones | Técnico / Administrador |
| GET /api/exports/{format} | Exportación con filtros vigentes | Técnico / Administrador |
| POST /api/imports/preview | Validar un Excel sin aplicarlo | Administrador |
| POST /api/imports/{id}/confirm | Confirmar una carga validada | Administrador |
| GET /api/imports | Historial de cargas | Administrador |
| GET /api/users | Consultar usuarios | Administrador |
| PATCH /api/users/{id} | Asignar rol/permisos | Administrador |
| GET /api/audit | Historial protegido | Administrador |
| POST /api/juku/query | Interpretar y ejecutar consultas autorizadas | Autenticado |

Parámetros comunes: `year`, `financier_id`, `region_id`, `area_id`, `rubro_id`, `account_id`, `month`, `date_from`, `date_to`, `search`, `page`, `page_size`. En exportaciones se omite la paginación, manteniendo los filtros.

Respuesta de resumen propuesta:

```json
{
  "year": 2026,
  "currency": "BOB",
  "budget": "3163379.01",
  "executed": "528694.16",
  "balance": "2634684.85",
  "execution_percent": "16.713"
}
```

Los importes financieros deben usar NUMERIC/Decimal en servidor y PostgreSQL, con reglas explícitas de redondeo y moneda. La versión local conserva los importes del Excel y suma en centavos; el backend debe usar Decimal y NUMERIC.

## Modelo de datos sugerido

Tablas separadas: usuarios, roles, financiadores, regiones, áreas, rubros, cuentas, presupuestos, modificaciones_presupuestarias, movimientos, tipos_cambio, importaciones, errores_importacion y auditoría. Relaciones por IDs y claves foráneas, no por el nombre visible de una categoría. Movimientos deben tener una clave de origen o huella para idempotencia de importación. La gestión debe estar explícita en presupuestos y movimientos. Las modificaciones deben conservar estado, autor y fecha.

El DTO local de presupuesto contiene `id`, `year`, `rubro`, `account`, `code`, `region`, `area`, `financier`, `amount`. El de movimiento agrega `budgetId`, `date`, `name`, `concept`, `type`, `number`, `no_cheque`, `debe`, `haber`, `dsus`, `hsus`, `tasa`. Estos nombres son internos del prototipo: el importador real necesita mapear y validar la hoja BD y los signos contables con la institución.

## JUKU

El modelo interpreta la intención; el servidor calcula y verifica permisos. Acciones posibles: `open_report`, `filter_movements`, `get_budget_summary`, `compare_years`. No permitir SQL libre generado por el modelo contra la base empresarial. Devolver filtros aplicados, fecha de actualización y enlace al detalle que respalda cada cifra. Cambios de información requieren una vista previa y confirmación.

La privacidad depende del alojamiento del modelo, los datos que recibe, los registros y los permisos; no se obtiene simplemente usando un nombre propio. No incluir credenciales de PostgreSQL ni claves del modelo en JavaScript entregado al navegador.

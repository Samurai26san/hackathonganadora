# Sistema Web de Control Presupuestario y Ejecución Financiera

Aplicativo web para que los usuarios técnicos tengan la ejecución presupuestaria al día: importa los Excel del sistema contable, acumula gestiones, genera los 7 reportes con drill-down, filtros combinados, comparativo entre gestiones y exportación a Excel/PDF, y un dashboard.

## Arquitectura

| Componente | Tecnología |
|---|---|
| Interfaz web | React + Vite, gráficos con Recharts |
| API y cálculos | Python + FastAPI |
| Base de datos | PostgreSQL (SQLite para desarrollo rápido) |
| Importación | openpyxl en servidor, mapeo flexible de columnas |
| Reportes | openpyxl (Excel) + reportlab (PDF) |
| Seguridad | JWT, autoregistro, 3 roles con separación de funciones, auditoría |
| Despliegue | Docker Compose (PostgreSQL + app + respaldo diario) |

```
backend/app/
  models.py    tablas: usuarios, financiadores, regiones, areas, rubros, cuentas, presupuestos,
               modificaciones, movimientos, tipos_cambio, importaciones, auditoria
  reports.py   motor genérico de reportes (niveles → árbol desplegable + comparativo)
  exports.py   Excel y PDF
  importer.py  importación de Excel (movimientos y presupuesto inicial)
  auth.py      login, roles/permisos, auditoría
  main.py      endpoints REST (/docs para Swagger)
  importer_contable.py  importación de la base contable (hoja BD) y registro de filas validadas
  prediccion.py   predicción de etiquetas faltantes (Naive Bayes) y su evaluación
  generar_prueba.py  copia del Excel con etiquetas borradas, para demostrar la predicción
  verificar.py comparación contra las tablas dinámicas del Excel
  seed.py      inicialización (usuarios + Excel real, o --demo con datos ficticios)
frontend/src/pages/  Dashboard, Reportes, Importar, Admin
```

### Base contable institucional (hoja `BD`)
El importador detecta automáticamente un libro con la hoja `BD` del sistema contable
(columnas `mes, codigo, nombre, cfecha, tipo, numero, region, ref, Ejecución, haber, dsus, tasa, fondo, rubro, Cuenta, area, presupuesto Bs`):

| Columna del Excel | En el sistema |
|---|---|
| `fondo` | financiador |
| `rubro` / `Cuenta` | rubro / cuenta presupuestaria |
| `area`, `region` (LP, SC…) | área, región |
| `presupuesto Bs` | presupuesto; `mes = PTTO` → presupuesto sin programar (mes 0), resto → programado en su mes |
| `Ejecución` − `haber` | movimiento ejecutado (con comprobante, glosa, cuenta contable, T/C y USD) |

- El archivo es acumulado: **cada importación reemplaza la gestión** que contiene y conserva las demás (histórico para comparativos).
- Detecta problemas de calidad de datos (p. ej. una cuenta registrada bajo un rubro que no le corresponde) y los informa como advertencias.
- `python -m app.verificar archivo.xlsx 2026` compara los reportes del sistema con las tablas dinámicas del Excel:
  con `Prueba ExB Nov 2026` los 6 reportes cuadran fila por fila (presupuesto Bs 3.163.379,01 · ejecución Bs 528.694,16).

### Usuarios y permisos (separación de funciones)
| Rol | Usuario demo | Puede | No puede |
|---|---|---|---|
| Administrador | `admin` / `1234` | crear, activar/desactivar usuarios, asignar roles, ver auditoría | ver, cargar ni validar datos financieros |
| Validador | `validador` / `1234` | cargar el Excel, validar/completar filas, dashboard y reportes | administrar usuarios |
| Consulta | `consulta` / `1234` | dashboard, reportes y exportación | modificar nada |

Quien se registra desde el login entra como **Consulta**; solo el administrador asigna otros roles (y no puede cambiar el suyo).
Todo queda en la auditoría.

### Filas con etiquetas faltantes: predicción y validación
1. Al importar, las filas sin financiador, rubro, cuenta, área o región **no entran a los reportes**: quedan en *Validación de datos*.
2. El modelo (Naive Bayes, `prediccion.py`) propone cada etiqueta faltante con su **confianza**, usando el código y nombre de la
   cuenta contable, las palabras de la glosa, el prefijo de la regional (LP./SC.) y las demás etiquetas de la fila.
3. El admin puede: **validar en bloque** todas las filas con confianza ≥ X%, **validar una por una**, **completar o corregir**
   a mano cualquier etiqueta (con autocompletado), o **descartar** filas. Las validadas se suman al presupuesto/ejecución y
   reentrenan el modelo (“Volver a predecir”).
4. La precisión se mide ocultando etiquetas de filas conocidas (hold-out 20%): ~86% global; con confianza ≥ 80% sube a 86–99% según el campo (53 de 54 aciertos en el archivo de demo).

Demo: `python -m app.generar_prueba "Prueba ExB Nov 2026 (1) (1).xlsx" "Prueba ExB etiquetas faltantes.xlsx" 60`
genera una copia con 60 filas sin etiquetas (las respuestas quedan en la hoja `_respuestas`).

### Cálculos
- **Vigente** = inicial + modificaciones
- **Saldo** = vigente − ejecutado
- **% ejecución** = ejecutado / vigente
- Montos en USD → Bs con el tipo de cambio vigente a la fecha del movimiento

### Agregar o cambiar un reporte
Cada reporte es una lista de niveles en `REPORTES` (`backend/app/reports.py`), por ejemplo
`"region": ["region", "area", "financiador"]`. Solo cambiando esa lista cambian el drill-down, la exportación y el frontend.

### Adaptar la importación al Excel real
Si la hoja original usa otros encabezados, agrégalos como sinónimos en `SINONIMOS` (`backend/app/importer.py`).

## Ejecutar en desarrollo

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed "../Prueba ExB Nov 2026 (1) (1).xlsx"   # o: --demo para datos ficticios
.venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Usuarios (contraseña `1234`): `admin` (usuarios), `validador` (carga y validación), `consulta` (lectura).
API documentada en http://localhost:8000/docs

## Producción con PostgreSQL

```bash
docker-compose up -d --build
docker-compose exec app python -m app.seed   # crea usuarios; luego importar el Excel desde la web
```
App en http://localhost:8000. El servicio `backup` deja un `pg_dump` diario en `./backups`.

## Pruebas

```bash
cd backend && .venv/bin/pytest -q
```

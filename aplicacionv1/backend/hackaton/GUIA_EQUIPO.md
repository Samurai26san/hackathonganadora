# Guía del proyecto – Sistema de Control Presupuestario y Ejecución Financiera

> Documento para el equipo: qué pide el reto, qué construimos, cómo correrlo, cómo está organizado el código
> y qué falta. Si solo tienes 5 minutos, lee **1. Resumen**, **3. Cómo correrlo** y **10. Guion de la demo**.

---

## 1. Resumen

**El reto:** la institución saca una base de datos del sistema contable en Excel y arma reportes con tablas
dinámicas. Piden un **sistema web** para que los técnicos tengan la información al día, que acumule
información por gestión (año), genere automáticamente **7 reportes** (con drill‑down, filtros combinados y
descarga en Excel/PDF), tenga seguridad (usuarios, roles, auditoría) y un **dashboard**.

**Lo que tenemos funcionando:**

- ✅ Importa el Excel real del sistema contable (hoja `BD`) tal como sale, sin modificarlo.
- ✅ Los **7 reportes**, con niveles desplegables, filtros combinados, comparativo entre gestiones y exportación a Excel y PDF.
- ✅ **Cuadran al 100%** con las tablas dinámicas del Excel original, fila por fila (lo comprueba un script).
- ✅ **Carga con vista previa tipo cuaderno**: una pestaña por hoja del Excel, filas incompletas resaltadas, antes de importar.
- ✅ **Dashboard** para la presentación: indicadores, hallazgos automáticos, gráficos y modo presentación.
- ✅ **3 roles con separación de funciones**: Administrador, Validador y Consulta. Incluye autoregistro y auditoría.
- ✅ **Filas incompletas:** las filas sin etiquetas no entran a los reportes; un modelo de IA **predice** las
  etiquetas faltantes y el validador las aprueba en bloque, una por una, o las corrige a mano.
- ✅ **19 pruebas automáticas** que pasan.

---

## 2. Tecnologías que usamos

### 2.1 La idea general (cómo se conectan)

```
┌──────────────────────┐   HTTP + JSON    ┌──────────────────────┐    SQL     ┌────────────────────┐
│  NAVEGADOR (frontend)│ ───────────────► │  SERVIDOR (backend)  │ ─────────► │   BASE DE DATOS    │
│  React + Vite        │ ◄─────────────── │  Python + FastAPI    │ ◄───────── │ PostgreSQL / SQLite│
│  Recharts (gráficos) │   token JWT      │  SQLAlchemy, openpyxl│            │                    │
└──────────────────────┘                  │  ReportLab, IA       │            └────────────────────┘
                                          └──────────────────────┘
```

1. El usuario usa la **página web** (React). Cuando pide algo, por ejemplo "reporte por región", la página llama a la **API**.
2. La **API** (FastAPI) revisa el **token** del usuario y sus permisos, consulta la **base de datos**, calcula y responde en JSON.
3. La página recibe el JSON y lo dibuja como tabla o gráfico.

### 2.2 Frontend (lo que ve el usuario)

| Tecnología | Versión | Para qué la usamos | Por qué |
|---|---|---|---|
| **JavaScript** | ES2023 | Lenguaje de la parte web | Es el lenguaje de los navegadores |
| **React** | 19 | Construir las pantallas como "componentes" reutilizables (KPI, filtros, tablas, cuaderno) | Estándar de la industria; la página se actualiza sin recargar |
| **Vite** | 8 | Servidor de desarrollo con recarga instantánea y empaquetado para producción | Mucho más rápido que las herramientas antiguas |
| **Recharts** | 3 | Gráficos de barras y líneas del dashboard | Hecho para React, con tooltips incluidos |
| **CSS propio** | — | Estilos, colores de estado (rojo/ámbar/verde) y diseño adaptable a celular | Sin frameworks pesados; control total del diseño |
| **Fetch API** | — | Llamar a la API desde el navegador (`frontend/src/api.js`) | Viene incluida en el navegador |

### 2.3 Backend (el cerebro)

| Tecnología | Versión | Para qué la usamos | Por qué |
|---|---|---|---|
| **Python** | 3.10+ | Lenguaje del servidor: cálculos, reportes, importación e IA | Muy usado en datos y finanzas; fácil de leer |
| **FastAPI** | 0.162 | Crear la **API REST** (las "direcciones" que consulta la web) | Muy rápido, valida datos solo y genera documentación en `/docs` |
| **Uvicorn** | 0.54 | Servidor que ejecuta FastAPI | Es el recomendado por FastAPI |
| **Pydantic** | 2 | Validar los datos que llegan (ej. que el rol sea válido) | Viene integrado con FastAPI |
| **SQLAlchemy** | 2.0 | **ORM**: trabajar con la base de datos usando clases de Python en vez de SQL a mano | El mismo código sirve para SQLite y PostgreSQL |
| **openpyxl** | 3.1 | Leer el Excel del sistema contable y generar reportes en Excel | Lee `.xlsx` sin necesitar Excel instalado |
| **ReportLab** | 5 | Generar los reportes en **PDF** | Librería madura para PDF profesionales |
| **PyJWT** | 2 | Crear y verificar los **tokens de sesión** (JWT) | Estándar para autenticación en APIs |
| **hashlib (PBKDF2)** | incluida en Python | Cifrar las contraseñas antes de guardarlas | Las contraseñas nunca se guardan en texto plano |
| **python-multipart** | 0.0.32 | Recibir archivos subidos (el Excel) | Necesario para subir archivos a FastAPI |

### 2.4 Base de datos

| Tecnología | Para qué | Cuándo |
|---|---|---|
| **SQLite** | Base de datos en un solo archivo (`backend/presupuesto.db`) | Desarrollo en la laptop: no hay que instalar nada |
| **PostgreSQL 16** | Base de datos profesional, multiusuario y robusta | Producción / servidor (con Docker) |
| **psycopg 3** | "Conector" entre Python y PostgreSQL | Lo usa SQLAlchemy por debajo |

Cambiar de una a otra es solo una variable: `DATABASE_URL=postgresql+psycopg://usuario:clave@servidor/presupuesto`.

### 2.5 Inteligencia artificial

| Concepto | Qué es, simple |
|---|---|
| **Machine learning** | El sistema **aprende de ejemplos** (las filas completas) en vez de reglas escritas a mano |
| **Naive Bayes** | Modelo clásico de clasificación: calcula **qué etiqueta es más probable** según las "pistas" de la fila (palabras de la glosa, código contable, región…). Lo programamos en Python puro (`prediccion.py`), sin librerías externas |
| **Confianza** | Probabilidad que da el modelo (ej. "IA 97%"). Con ella el validador decide si aprueba en bloque |
| **Evaluación hold‑out** | Para medir la precisión ocultamos etiquetas de filas que sí conocemos y vemos cuántas acierta: **86%** |
| **Humano en el ciclo** | La IA **propone**, una persona **valida**. Lo validado vuelve a entrenar al modelo |

### 2.6 Seguridad

| Concepto | Cómo lo aplicamos |
|---|---|
| **Autenticación** (¿quién eres?) | Login con usuario y contraseña → el servidor entrega un **token JWT** válido por 12 horas |
| **Autorización** (¿qué puedes hacer?) | 3 roles con permisos; el **servidor** rechaza con error 403 lo no permitido |
| **Separación de funciones** | Quien administra usuarios no toca datos; quien valida datos no administra usuarios |
| **Contraseñas cifradas** | PBKDF2‑SHA256 con 200.000 iteraciones y "sal" aleatoria |
| **Auditoría** | Tabla `auditoria`: quién, qué y cuándo (login, cargas, validaciones, cambios de rol) |

### 2.7 Infraestructura y calidad

| Tecnología | Para qué |
|---|---|
| **Docker + Docker Compose** | Empaquetar app y PostgreSQL en "contenedores" que corren igual en cualquier servidor o nube. Incluye **copia de seguridad diaria** (`pg_dump`) |
| **pytest** | **19 pruebas automáticas**: reportes, permisos, importación, predicción, validación, vista previa y cuadre con el Excel |
| **httpx / TestClient** | Simular llamadas a la API dentro de las pruebas |
| **Git** | Control de versiones: el `.gitignore` está listo, pero el repositorio aún no se inicializó (`git init`) |

### 2.8 Conceptos clave para explicar en la presentación

- **API REST:** "menú" de direcciones que el frontend consulta; por ejemplo `GET /api/reportes/region?gestion=2026`.
- **JSON:** formato de texto con el que viajan los datos entre el servidor y la página.
- **Base de datos normalizada:** cada cosa en su tabla (financiadores, cuentas, movimientos…), sin repetir información,
  a diferencia de una hoja de Excel plana.
- **ORM:** escribir consultas a la base de datos con Python en lugar de SQL.
- **Drill‑down:** abrir un total para ver su detalle (Región → Área → Financiador → Rubro → Cuenta).
- **Token JWT:** "pase de acceso" firmado que el navegador envía en cada consulta.

---

## 3. Cómo correrlo

### Requisitos
- Python 3.10 o superior, Node.js 18 o superior (probado con Node 22).

### Primera vez (instalación)

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Crea la base, los 3 usuarios demo e importa el Excel real:
.venv/bin/python -m app.seed "../Prueba ExB Nov 2026 (1) (1).xlsx"

cd ../frontend
npm install
```

> Para la demo de predicción, importa en su lugar el archivo con etiquetas borradas:
> `.venv/bin/python -m app.seed "../Prueba ExB etiquetas faltantes.xlsx"`

### Cada vez que lo uses (dos terminales)

```bash
# Terminal 1 – API
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2 – Web
cd frontend && npm run dev
```

Abrir **http://localhost:5173**. Documentación de la API: **http://localhost:8000/docs**.

### Usuarios demo (contraseña `1234` para los tres)

| Usuario | Rol | Qué ve |
|---|---|---|
| `admin` | Administrador | Solo *Usuarios y auditoría* |
| `validador` | Validador | Dashboard, Reportes, Cargar datos, Validación de datos |
| `consulta` | Consulta | Dashboard y Reportes |

> ⚠️ `1234` es solo para la demo. En producción hay que cambiar las contraseñas y definir la variable `JWT_SECRET`.

### Producción con Docker (PostgreSQL)

```bash
docker-compose up -d --build
docker-compose exec app python -m app.seed   # crea los usuarios; luego se importa el Excel desde la web
```
App en http://localhost:8000. El servicio `backup` guarda un `pg_dump` diario en `./backups`.
*(Esta parte está configurada pero no la probamos completa. Sí probamos la API con PostgreSQL real.)*

### Pruebas

```bash
cd backend && .venv/bin/pytest -q                 # 19 pruebas
.venv/bin/python -m app.verificar "../Prueba ExB Nov 2026 (1) (1).xlsx" 2026   # cuadre vs tablas dinámicas
```

---

## 4. Estructura del código

```
hackaton/
├── README.md                   documentación técnica corta
├── GUIA_EQUIPO.md              este documento
├── docker-compose.yml          PostgreSQL + app + backup diario
├── Prueba ExB Nov 2026 (1) (1).xlsx      Excel real de la institución
├── Prueba ExB etiquetas faltantes.xlsx   copia con 60 filas sin etiquetas (demo de IA)
├── backend/
│   ├── requirements.txt, Dockerfile, pytest.ini
│   ├── presupuesto.db          base SQLite de desarrollo (no se sube a git)
│   ├── tests/test_api.py       19 pruebas
│   └── app/
│       ├── main.py             todos los endpoints de la API
│       ├── db.py               conexión (SQLite por defecto, o DATABASE_URL)
│       ├── models.py           tablas de la base de datos
│       ├── auth.py             login, JWT, roles y permisos, auditoría
│       ├── reports.py          motor de reportes (árbol desplegable + comparativo)
│       ├── exports.py          Excel y PDF
│       ├── importer.py         importación genérica (plantillas) + detección del formato
│       ├── importer_contable.py importación de la hoja BD + registro de filas validadas
│       ├── prediccion.py       modelo Naive Bayes + evaluación de precisión
│       ├── verificar.py        compara reportes vs tablas dinámicas del Excel
│       ├── previsualizar.py    vista previa del Excel por hojas (cuaderno)
│       ├── generar_prueba.py   genera el Excel de demo con etiquetas borradas
│       └── seed.py             inicializa base y usuarios
└── frontend/src/
    ├── App.jsx                 menú por rol, modo presentación
    ├── api.js                  llamadas a la API y formato de números
    ├── styles.css
    └── pages/
        ├── Login.jsx           ingreso y registro
        ├── Dashboard.jsx       tablero de presentación
        ├── Reportes.jsx        los 7 reportes
        ├── Filtros.jsx         filtros combinados (multi‑selección)
        ├── Importar.jsx        carga de Excel
        ├── Validacion.jsx      revisión de filas con etiquetas faltantes
        └── Admin.jsx           usuarios, roles y auditoría
```

---

## 5. Base de datos

Tablas separadas, como pide el reto, para no depender de la estructura rígida de la hoja:

| Tabla | Contenido |
|---|---|
| `usuarios` | usuario, nombre, contraseña cifrada, rol, activo |
| `financiadores` | fuentes (columna `fondo`: CATALYST 18, CEL 2026, KJCF LACT) |
| `regiones` | LP = La Paz, SC = Santa Cruz… |
| `areas` | PROGRAMA, CAMBIO SISTEMICO… |
| `rubros` | 4. Consultoria, 5. Viajes… |
| `cuentas` | 4.1 Videos, 5.2 Viajes Nacionales… (cada una pertenece a un rubro) |
| `presupuestos` | monto por gestión + **mes** + cuenta + financiador + área + región |
| `modificaciones` | traspasos (+/−) al presupuesto *(estructura lista; el Excel actual no trae)* |
| `movimientos` | cada gasto ejecutado: fecha, comprobante, glosa, cuenta contable, Bs, USD, T/C |
| `tipos_cambio` | tipo de cambio por fecha y moneda |
| `importaciones` | historial de archivos cargados, con su resumen y errores |
| `filas_pendientes` | filas con etiquetas faltantes, la predicción y quién las validó |
| `auditoria` | quién hizo qué y cuándo |

**Fórmulas:** vigente = inicial + modificaciones · saldo = vigente − ejecutado · % ejecución = ejecutado / vigente.

---

## 6. Cómo se interpreta el Excel de la institución

El archivo tiene la hoja **`BD`** (la base) y 6 hojas de **tablas dinámicas** construidas sobre ella.
Columnas de `BD`:
`mes, codigo, nombre, cfecha, tipo, numero, no_cheque, region, ref, Ejecución, haber, dsus, hsus, tasa, fondo, rubro, Cuenta, area, presupuesto Bs`

| Columna | En el sistema |
|---|---|
| `fondo` | financiador |
| `rubro`, `Cuenta` | rubro y cuenta presupuestaria |
| `area`, `region` | área y región |
| `presupuesto Bs` | presupuesto de esa fila |
| `Ejecución` − `haber` | monto ejecutado (movimiento) |
| `codigo` + `nombre` | cuenta contable (plan de cuentas) |
| `tipo` + `numero` | comprobante |
| `ref` | glosa / descripción |
| `dsus`, `tasa` | monto en USD y tipo de cambio |

**Lo importante (nos costó entenderlo):**
- Las filas con `mes = PTTO` son **presupuesto aún no programado** por mes. Las guardamos con mes 0.
- Las filas con un mes y `ref = PRESUPUESTO` son el **saldo no ejecutado de ese mes**.
- Las filas de ejecución también traen `presupuesto Bs` igual a su ejecución. Así, *presupuesto del mes = ejecutado + saldo*.
- **Total 2026:** presupuesto **Bs 3.163.379,01** y ejecución **Bs 528.694,16** (16,7%).
- **Cada importación reemplaza la gestión** del archivo (el Excel es acumulado al día) y conserva las otras
  gestiones, para los comparativos.

**Problemas de calidad que encontramos en el Excel** (el sistema los avisa al importar):
- 7 cuentas registradas bajo un rubro que no les corresponde (ej. "8.3 Internet" con Bs 5.930 en "9. Otros
  Gastos Ope."). Las mostramos separadas, como hace la tabla dinámica, para que todo cuadre.
- Una cuenta llamada solo "9.2 " (Bs 12.000) → aparece como "9.2 (sin nombre)".
- La hoja `Detalle2` parece de otra versión del archivo (usa "91. Otros Gastos Ope."), así que no la usamos para verificar.

---

## 7. Los 7 reportes

| Reporte | Niveles desplegables | Hoja del Excel equivalente |
|---|---|---|
| Ejecución por rubro y cuenta | Rubro → Cuenta | `por cuenta` |
| Ejecución por financiador | Financiador → Rubro → Cuenta | `Financiador` |
| Ejecución por área y financiador | Área → Financiador → Rubro → Cuenta | `Por Area y Fin` |
| Ejecución por región | Región → Área → Financiador → Rubro → Cuenta | `Por region y Area` |
| Ejecución por mes | Mes → Rubro → Cuenta | `Por mes` |
| Detalle de movimientos | lista paginada | `Detalle2` |
| Resumen general consolidado | Rubro | `Rubro` |

- **Filtros combinados** por financiador, rubro, cuenta, área, región y mes, con selección múltiple.
- **Comparativo** con otra gestión (aparece cuando hay más de un año cargado).
- **Exportación** a Excel y PDF respetando filtros y comparativo.
- **Agregar un reporte:** basta con añadir una línea en `REPORTES` (`backend/app/reports.py`), con su lista de niveles.

**Verificación:** `python -m app.verificar` compara las 6 tablas dinámicas con el sistema. Resultado: **0 diferencias**.

---

## 8. Seguridad: 3 roles con separación de funciones

| Rol | Puede | No puede |
|---|---|---|
| **Administrador** | Crear usuarios, asignar roles, activar o desactivar, ver auditoría | Ver, cargar o validar datos financieros |
| **Validador** | Cargar el Excel, validar y completar filas, dashboard, reportes | Administrar usuarios |
| **Consulta** | Dashboard, reportes, exportar | Modificar nada |

- Quien se **registra** entra como Consulta. Solo el administrador asigna otros roles.
- El administrador **no puede cambiar su propio rol** ni desactivarse.
- Los permisos se controlan **en el servidor** (devuelve error 403), no solo ocultando botones.
- **Auditoría** de inicios de sesión, cargas, exportaciones, validaciones y cambios de usuarios.

---

## 9. Filas incompletas: predicción con IA y validación

1. Al importar, una fila sin financiador, rubro, cuenta, área o región **no entra a los reportes**: queda en
   *Validación de datos*.
2. El modelo **Naive Bayes** (`prediccion.py`) propone cada etiqueta faltante con un % de confianza. Usa:
   código y nombre de la cuenta contable, palabras de la glosa, prefijo de la regional (`LP.` / `SC.`), las
   demás etiquetas de la fila y el mes.
3. El validador puede:
   - **Validar en bloque** todas las filas con confianza ≥ X% (control deslizante).
   - **Validar o descartar** una por una, o las seleccionadas.
   - **Completar o corregir** a mano, con autocompletado.
   - **Volver a predecir**: el modelo reentrena con lo ya validado.
4. **Precisión medida** (ocultando etiquetas de filas conocidas): **86% global**. Con confianza ≥ 80%,
   entre 86% y 99% según el campo. En el archivo de demo acertó **53 de 54** predicciones de alta confianza.

**Archivo de demo:** `Prueba ExB etiquetas faltantes.xlsx`. Es una copia del Excel real con 60 filas sin alguna
etiqueta; las respuestas reales están en la hoja `_respuestas`. Se regenera con:
```bash
.venv/bin/python -m app.generar_prueba "../Prueba ExB Nov 2026 (1) (1).xlsx" "../Prueba ExB etiquetas faltantes.xlsx" 60
```

### Carga con vista previa ("cuaderno")
Al elegir o arrastrar un Excel en *Cargar datos*, **no se importa de inmediato**. Primero se muestra un cuaderno con
**una pestaña por cada hoja**, que se ve como una cuadrícula tipo Excel (letras de columna y número de fila real):
- ✓ **Base contable** (`BD`): es la única que se importa. Cada columna indica cómo se interpretará (→ Financiador, → Rubro…).
- ▦ **Tablas dinámicas**: se muestran como referencia; el sistema las reproduce como reportes.
- Resumen previo: gestión detectada, presupuesto, ejecución, movimientos, **filas incompletas por campo**, filas por mes y errores.
- Aviso si la gestión **ya tiene datos y se reemplazará**.
- Filtro **"Solo filas incompletas"**: las celdas faltantes aparecen en rojo como "— falta —".
- Botón **Importar** (o *Reemplazar e importar*) para confirmar, o **Cancelar**. Endpoint: `POST /api/importar/previsualizar`.

---

## 10. Guion de la demo (≈ 5 minutos)

1. **Login como `consulta`** → dashboard: "16,7% ejecutado", hallazgos automáticos, clic en un financiador
   para filtrar todo el tablero, **modo presentación**.
2. **Reportes** → "Por región", desplegar La Paz → Área → Financiador. Aplicar filtros y **descargar PDF/Excel**.
3. Mostrar el cuadre en terminal: `python -m app.verificar …` → 6 de 6 reportes **OK**.
4. **Login como `validador`** → *Cargar datos* → arrastrar `Prueba ExB etiquetas faltantes.xlsx` → recorrer el **cuaderno**
   (pestañas BD y `_respuestas`, "Solo filas incompletas") → **Importar** → aviso de 60 filas pendientes.
5. *Validación de datos* → mostrar las predicciones "IA 97%" y la precisión del modelo → **validar en bloque**
   las de ≥ 80% → corregir a mano una de baja confianza → volver al dashboard: los totales cambiaron.
6. **Login como `admin`** → solo ve usuarios y auditoría (no ve dinero): **separación de funciones**. Promover a
   un usuario registrado a Validador y mostrar el registro en la auditoría.

**Frase de cierre:**
> *"Una aplicación web con React, Python/FastAPI y PostgreSQL que importa el Excel contable tal cual, reproduce
> los 7 reportes cuadrando al 100% con las tablas dinámicas, aplica separación de funciones en la seguridad y usa
> IA para completar datos faltantes que un validador humano aprueba."*

---

## 11. API (para quien toque el backend)

Todo bajo `/api`, con token `Authorization: Bearer <token>`. Se puede probar en http://localhost:8000/docs.

| Método | Ruta | Permiso | Uso |
|---|---|---|---|
| POST | `/auth/login`, `/auth/registro` | — | Ingresar o registrarse (devuelve token) |
| GET | `/auth/me` | sesión | Usuario actual |
| GET | `/catalogos` | ver | Gestiones, financiadores, rubros… |
| GET | `/reportes/{reporte}?gestion=&comparar=&financiador=1,2…` | ver | Reporte en JSON |
| GET | `/reportes/{reporte}/export?formato=xlsx\|pdf` | ver | Descarga |
| GET | `/dashboard?gestion=` | ver | Datos del tablero + hallazgos |
| POST | `/importar/previsualizar` | importar | Vista previa por hojas (no guarda nada) |
| POST | `/importar` | importar | Subir Excel |
| GET | `/importaciones` | ver | Historial de cargas |
| GET | `/pendientes`, `/pendientes/opciones` | validar | Filas por validar y valores posibles |
| POST | `/pendientes/validar`, `/pendientes/descartar`, `/pendientes/predecir` | validar | Validación |
| GET | `/prediccion/evaluacion` | validar | Precisión del modelo |
| GET/POST/PATCH | `/usuarios` | administrar | Gestión de usuarios |
| GET | `/auditoria` | administrar | Registro de auditoría |

---

## 12. Pendientes e ideas

**Mejoras posibles:**
- Soporte para `.csv` (detectando separador, decimales y tildes).
- Registrar **modificaciones presupuestarias** (traspasos) desde la pantalla.
- Control "hecho por / revisado por": que quien carga un archivo no valide sus propias filas.
- Alertas automáticas cuando un rubro o financiador va por debajo de lo programado.
- Desplegar en la nube con HTTPS y copias de seguridad (Docker ya está listo).
- Cambio de contraseña y bloqueo tras varios intentos fallidos.

**Notas técnicas:**
- Si cambias `models.py`, la base SQLite se recrea con `python -m app.seed …`. Ojo: borra los datos.
- El backend se recarga solo con `--reload`, y el frontend con Vite.
- No subir a git: `backend/.venv`, `frontend/node_modules`, `*.db` (ya están en `.gitignore`).

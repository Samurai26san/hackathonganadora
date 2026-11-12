# Propuesta de interfaz web — ExB Finanzas + Juku

## 1. Descripción del proyecto

**ExB Finanzas** es una aplicación web para consultar y analizar el **presupuesto y la ejecución financiera** de Enseña por Bolivia (ExB). Su finalidad es sustituir la consulta manual de múltiples tablas dinámicas de Excel por una interfaz clara, interactiva y actualizable.

La aplicación utiliza como punto de partida la información del archivo contable proporcionado, especialmente la hoja `BD` y los reportes existentes. Permitirá visualizar indicadores, filtrar resultados, explorar niveles de detalle, comparar gestiones y exportar reportes en Excel o PDF.

La experiencia estará centrada en **dos pantallas principales**: ingreso y panel financiero. Dentro del panel se accederá a cuatro módulos: **Presupuesto, Reportes, Movimientos y Gestiones**. Además, contará con **Juku**, un chatbot de apoyo para consultar información financiera en lenguaje natural.

> **Nota de alcance:** la descripción siguiente es una propuesta de interfaz y comportamiento. Los nombres de las hojas y los siete reportes provienen de los materiales del reto; los detalles de navegación y las capacidades de Juku son funcionalidades planteadas para el desarrollo.

## 2. Estructura de navegación

```text
ExB Finanzas
│
├── 1. Ingreso
│   └── Validación de credenciales y rol: Técnico / Administrador
│
└── 2. Panel financiero (Dashboard)
    ├── Menú desplegable ☰
    │   ├── Presupuesto
    │   ├── Reportes
    │   ├── Movimientos
    │   └── Gestiones
    │
    ├── Juku 💬 (chatbot accesible desde todo el panel)
    └── Perfil de usuario
        └── Funciones administrativas, según permisos
```

El menú lateral se abre mediante un icono y puede cerrarse para dejar mayor espacio a los datos. Al desplazarse entre módulos, se conservan los filtros relevantes, en especial la **gestión seleccionada**. Una ruta de navegación o título indica siempre dónde se encuentra el usuario.

## 3. Pantalla 1 — Ingreso

**Objetivo:** permitir el acceso seguro al sistema.

**Elementos:**
- Identidad visual de ExB y nombre **ExB Finanzas**.
- Campo de correo o usuario y campo de contraseña.
- Botón **Ingresar** y mensajes claros ante errores de autenticación.
- Enlace para recuperar acceso, si se implementa ese mecanismo.

**Roles:**
- **Técnico:** consulta el dashboard, presupuestos, reportes, movimientos y comparaciones; aplica filtros y descarga resultados autorizados.
- **Administrador:** dispone de las consultas del técnico y, adicionalmente, puede importar/actualizar información, administrar usuarios y permisos y revisar auditorías.

El rol se obtiene de la cuenta autenticada: **no se selecciona manualmente** en el formulario.

## 4. Pantalla 2 — Dashboard financiero

**Objetivo:** ofrecer una visión inmediata del estado financiero de la gestión activa.

**Barra superior:** icono de menú, nombre de la plataforma, gestión activa, acceso a Juku, perfil y, para administradores, configuración.

**Filtros principales visibles:**
- **Gestión** (por ejemplo, 2026).
- **Financiador** (todos o uno específico).

**Indicadores principales:** presupuesto total, ejecución acumulada, saldo disponible y porcentaje de ejecución.

**Gráficos y elementos:**
- Ejecución por rubro, comparando presupuesto y monto ejecutado.
- Tendencia de ejecución por mes.
- Resumen por financiador o región, según los datos seleccionados.
- Accesos rápidos a los cuatro módulos.

**Interacción:** al hacer clic en un rubro, mes o financiador dentro de un gráfico, se abre el módulo correspondiente con los filtros aplicados. Los indicadores y gráficos se actualizan cuando cambia la selección global.

## 5. Módulo: Presupuesto

**Pregunta que responde:** «¿Cuánto se presupuestó, cuánto se ejecutó y cuánto queda?»

**Filtros visibles:** Financiador, Rubro y Área.

**Filtros avanzados desplegables:** Región, Cuenta y Mes.

**Contenido:**
- Tarjetas de presupuesto aprobado/vigente (según disponibilidad de datos), ejecutado, saldo y porcentaje de ejecución.
- Tabla con rubro, cuenta, presupuesto, ejecución, saldo y porcentaje.
- Desglose interactivo **Rubro → Cuenta → Movimientos**.

**Acciones:** seleccionar una cuenta para expandir su detalle; abrir sus transacciones en **Movimientos**; exportar la consulta filtrada.

## 6. Módulo: Reportes

**Pregunta que responde:** «¿Qué informe necesito generar y con qué desglose?»

El módulo reúne los **siete informes solicitados**:

1. Ejecución por rubro y cuenta.
2. Ejecución por financiador.
3. Ejecución por área y financiador.
4. Ejecución por región.
5. Ejecución por mes.
6. Detalle de movimientos.
7. Resumen general consolidado.

**Filtros visibles:** Tipo de reporte, Período y Financiador. Estos pueden cambiar de prioridad según el reporte; por ejemplo, en el informe regional se destacan Región y Área.

**Filtros avanzados:** Región, Área, Rubro y Cuenta, según correspondan.

**Contenido:** gráfico adaptado al informe, tabla de resultados y niveles de desglose expandibles.

**Acciones:** combinar filtros, expandir categorías, abrir el registro subyacente y descargar **Excel o PDF** con los resultados de la consulta actual.

## 7. Módulo: Movimientos

**Pregunta que responde:** «¿Qué transacción se realizó, cuándo, cuánto costó y a qué corresponde?»

**Filtros visibles:** Buscador general, Rango de fechas y Financiador.

**Filtros avanzados:** Región, Rubro, Cuenta, Tipo de movimiento y Número de comprobante, si están disponibles.

**Contenido:** tabla paginada y buscable con fecha, código/referencia, concepto, cuenta, financiador, región e importe. El detalle de cada movimiento permite mostrar sus campos contables disponibles, sin saturar el listado principal.

**Acciones:** buscar por referencia o comprobante, ordenar resultados, abrir una ficha de movimiento y exportar registros filtrados.

## 8. Módulo: Gestiones

**Pregunta que responde:** «¿Cómo cambió el presupuesto o la ejecución entre años?»

**Filtros visibles:** Gestión inicial, Gestión final e Indicador a comparar.

**Filtros avanzados:** Financiador, Región, Área y Rubro.

**Contenido:** indicadores lado a lado, gráfico comparativo por año y tabla de diferencias absolutas y porcentuales.

**Acciones:** cambiar las gestiones comparadas y abrir **Reportes** con el período correspondiente.

> Las comparaciones entre gestiones se habilitan conforme se incorporen datos de distintos años; no deben simularse cifras faltantes.

## 9. Juku — Chatbot integrado

**Juku** será un **asistente conversacional de consulta financiera** integrado en la aplicación. No sustituye los módulos ni sus filtros: ayuda al usuario a llegar más rápido a la información.

### Ubicación y presentación

- Icono flotante de chat en la esquina inferior derecha del dashboard y de los cuatro módulos.
- Al pulsarlo, abre un panel lateral que no oculta completamente la información financiera.
- El usuario puede minimizarlo o cerrarlo sin perder la navegación actual.
- El encabezado muestra **Juku — Asistente financiero ExB**.
- Puede mostrar sugerencias de preguntas relacionadas con el módulo activo.

### Consultas de ejemplo

- «Juku, ¿cuánto presupuesto queda disponible en 2026?»
- «Muéstrame la ejecución de Viajes por financiador».
- «¿Qué región ejecutó más presupuesto?»
- «Busca los movimientos de junio asociados a esta cuenta».
- «Compara la ejecución de 2025 con 2026» (solo si existen ambas gestiones).
- «Genera el reporte mensual del financiador seleccionado».

### Respuestas esperadas

Cuando la consulta sea posible con los datos disponibles, Juku podrá:
1. Interpretar la pregunta y los filtros activos, pidiendo una aclaración breve solo si falta un dato esencial.
2. Mostrar una respuesta resumida con importe, moneda, gestión, período y filtros aplicados.
3. Presentar una pequeña tabla o gráfico cuando aporte claridad.
4. Ofrecer la acción **Ver en Presupuesto / Reportes / Movimientos / Gestiones** con los filtros ya configurados.
5. Facilitar la exportación del resultado cuando sea compatible.

### Reglas importantes para Juku

- **Consultar datos reales del sistema:** no inventar montos, registros, comprobantes ni comparaciones ausentes.
- **Respetar permisos:** un técnico no debe recibir datos fuera de su acceso.
- **Explicar el contexto:** indicar gestión, período, moneda, filtros y origen del resultado.
- **No modificar datos financieros mediante el chat:** inicialmente será de solo lectura; las cargas y cambios seguirán los procesos administrativos autorizados.
- **Ser transparente:** si no hay información o una pregunta no se puede responder, indicarlo y sugerir un filtro o reporte apropiado.
- **Proteger la información:** registrar consultas y acciones conforme a las políticas institucionales, evitando exponer datos sensibles innecesariamente.

## 10. Criterios de usabilidad y filtros

La interfaz debe ser **breve en apariencia, pero profunda en consulta**:

- Máximo dos o tres filtros principales visibles por módulo.
- Botón **Filtros avanzados** para los demás campos.
- Filtros relacionados: elegir un rubro reduce las cuentas disponibles.
- Actualización de indicadores, tablas y gráficos al aplicar filtros.
- Opción **Limpiar filtros** y resumen de selecciones activas.
- Navegación entre módulos sin perder el contexto aplicable.
- Tablas con ordenación, búsqueda, paginación y detalle expandible.
- Exportación que respete el mismo alcance de la consulta mostrada.
- Estados claros de carga, sin resultados, error y datos desactualizados.
- Adaptación a pantallas de escritorio y dispositivos móviles.

## 11. Recorridos de usuario

**A. Consulta desde dashboard:** Ingreso → Dashboard → Clic en rubro → Presupuesto filtrado → Cuenta → Movimientos específicos.

**B. Generación de informe:** Dashboard → Reportes → Elegir informe → Ajustar filtros → Explorar detalle → Descargar Excel/PDF.

**C. Consulta asistida por Juku:** Dashboard o módulo → Abrir Juku → Preguntar → Revisar respuesta contextualizada → Pulsar «Ver detalle» → Módulo con filtros aplicados.

**D. Comparación anual:** Dashboard → Gestiones → Elegir años e indicador → Revisar diferencias → Abrir Reportes para profundizar.

**E. Actualización administrativa:** Ingreso de administrador → Configuración → Importación de Excel → Validación y vista previa → Confirmación → Datos disponibles en el dashboard y reportes.

## 12. Relación con el Excel original

| Origen en Excel | Uso en la aplicación |
|---|---|
| `BD` | Datos fuente para importación, movimientos y cálculos. |
| `Rubro` | Ejecución por rubro. |
| `por cuenta` | Detalle por cuenta. |
| `Financiador` | Ejecución por fuente financiadora. |
| `Por Area y Fin` | Desglose por área y financiador. |
| `Por region y Area` | Desglose regional. |
| `Por mes` | Evolución mensual. |
| `Detalle2` | Consulta detallada de movimientos. |
| `Dashboard` | Referencia para los indicadores y gráficos generales. |

Los reportes deben calcularse a partir de datos estructurados, no depender de conservar las tablas dinámicas como fuente de verdad. Durante la importación deben validarse registros duplicados, tipos de movimiento, monedas, períodos y reglas para diferenciar presupuesto y ejecución.

## 13. Tecnologías y prioridades

**Tecnologías sugeridas en las instrucciones del reto:** React o Next.js (interfaz), FastAPI/Python (API y cálculos), PostgreSQL (base de datos), procesamiento de Excel en el servidor y exportación Excel/PDF.

**Prioridad 1 — Experiencia esencial:** autenticación, dashboard, cuatro módulos, filtros útiles, siete reportes, navegación a detalle y exportación.

**Prioridad 2 — Juku integrado:** preguntas en lenguaje natural sobre datos reales, respuestas con contexto y acceso directo a vistas filtradas. La primera versión debe ser de consulta, no de edición.

**Prioridad 3 — Operación completa:** importación validada para administradores, auditoría, permisos refinados, comparación de nuevas gestiones y despliegue con respaldos.

## 14. Principio central de diseño

> **Un técnico debe poder pasar de una pregunta general —«¿cuánto queda?»— a la transacción que explica ese número en pocos clics, o preguntárselo directamente a Juku.**

La interfaz presenta solo cuatro módulos, pero conserva el acceso a todos los reportes exigidos, sus niveles de detalle y el histórico disponible. **Juku** actúa como una vía adicional de consulta, no como reemplazo de los controles y reportes verificables.

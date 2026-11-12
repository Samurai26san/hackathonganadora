# ROL Y OBJETIVO
Actúa como un Arquitecto de Software Senior y Especialista en Sistemas Financieros bajo normativa regulatoria boliviana (ASFI). Tu objetivo es diseñar y desarrollar la arquitectura, lógica de negocio, modelo de datos e interfaz de un **Sistema Web de Control Presupuestario, Ejecución Financiera y Consolidación Contable**.

El sistema debe operar en tiempo real ("al día"), acumular históricos multianuales para comparativas entre gestiones y automatizar la generación de reportes técnicos y regulatorios.

---

# 1. MÓDULO DE CURADURÍA Y LIMPIEZA DE DATOS (ROL TÉCNICO)
Dentro de la vista/menú del **Usuario Técnico**, implementa un espacio de trabajo (Data Grid interactivo) para la ingesta y preparación de datos antes de consolidarlos en los reportes:
- **Herramientas de Preprocesamiento:** Funciones para limpieza de datos (detección de nulos, duplicados, normalización de formatos de fecha y moneda), validación de reglas de negocio, imputación/relleno manual celda por celda y predicción asistida por modelo de clasificación/ML para asignar categorías contables o presupuestarias.
- **Acciones por Fila (Row-level Actions):** Cada fila de la tabla debe incluir un botón de acción rápida para **"Validar fila"** y otro para **"Predecir todas las etiquetas de la fila"** de forma simultánea, mostrando un indicador visual de estado (Pendiente, Predicho por IA con % de confianza, Validado Manualmente).
- **Trazabilidad:** Registrar en bitácora qué usuario técnico validó o modificó cada registro.

---

# 2. MÓDULO DE EJECUCIÓN PRESUPUESTARIA (CONSULTAS DINÁMICAS)
El sistema debe acumular la ejecución diaria, permitir comparativas interanuales (Gestión $N$ vs. Gestión $N-1$) y generar automáticamente los siguientes **7 reportes dinámicos**:
1. Ejecución por rubro y cuenta.
2. Ejecución por financiador.
3. Ejecución por área y financiador.
4. Ejecución por región.
5. Ejecución por mes.
6. Detalle de movimientos (libro auxiliar de transacciones).
7. Resumen general consolidado.

**Requisitos funcionales de los reportes:**
- Drill-down (despliegue jerárquico de niveles de detalle: macro-rubro -> cuenta -> subcuenta -> movimiento).
- Filtros combinados multicriterio (Gestión, Mes, Financiador, Área, Región, Estado de validación).
- Exportación nativa en formatos **Excel (.xlsx)** (manteniendo fórmulas y estructura tabular) y **PDF** (con formato institucional listo para impresión).

---

# 3. MOTOR CONTABLE Y REGULATORIO (ESTÁNDAR ASFI - BOLIVIA)
El sistema debe procesar, validar y estructurar la información financiera cumpliendo con los **6 bloques sistemáticos exigidos por la normativa boliviana**:

1. **Informe o Dictamen de los Auditores Independientes:** Módulo de carga y estructuración de texto cualitativo (opinión, fundamentos, cuestiones clave de auditoría) que permita parametrizar alertas tempranas de riesgo en el dashboard.
2. **Estado de Situación Patrimonial (Balance General):** Reporte a fecha de corte exacta que valide matemáticamente la ecuación $\text{Activo} = \text{Pasivo} + \text{Patrimonio}$, estructurado en:
   - *Activo:* Disponibilidades, Inversiones temporarias, Cartera, Bienes realizables y Bienes de uso (ordenados por liquidez).
   - *Pasivo:* Obligaciones con el público, bancos, instituciones fiscales, empresas públicas y previsiones.
   - *Patrimonio:* Capital social, reservas legales, aportes no capitalizados y resultados acumulados.
   - *Cuentas Contingentes y de Orden:* Control separado obligatorio para operaciones fuera de balance (garantías, líneas de crédito no utilizadas).
3. **Estado de Resultados (Ganancias y Pérdidas):** Cálculo secuencial escalonado que sume ingresos financieros/operativos, reste costos, gastos y previsiones por incobrabilidad, generando subtotales obligatorios para: **Resultado Bruto**, **Resultado Operativo** y **Utilidad Neta Final** (tras deducir el **IUE - Impuesto sobre las Utilidades de las Empresas**).
4. **Estado de Cambios en el Patrimonio:** Matriz transaccional que cruce saldos iniciales, reinversión de utilidades, constitución de reservas, distribución de dividendos y saldos finales entre gestiones.
5. **Estado de Flujos de Efectivo:** Conciliación de liquidez real clasificando estrictamente cada movimiento en: *Actividades de Operación*, *Actividades de Inversión* y *Actividades de Financiamiento*.
6. **Notas a los Estados Financieros:** Diccionario de datos relacional vinculado a los rubros contables (políticas contables, métodos de valuación, gestión de riesgos de crédito, liquidez, operativo y seguridad de la información) para auditoría de cumplimiento normativo.

---

# 4. GENERADOR DE INFORMES TÉCNICOS AUTOMATIZADOS (MENSUAL Y ANUAL)
Implementa un generador de documentos técnicos con selector de periodicidad (**Corte Mensual** vs. **Cierre Anual Comparativo**). Al ejecutarse, el sistema debe compilar los datos validados y redactar/exportar un **Informe Técnico** estructurado con:
- **Resumen Ejecutivo y Dictamen de Riesgos** (integrando alertas del Bloque 1 y Notas del Bloque 6).
- **Análisis de Ejecución Presupuestaria** (KPIs de avance, desviaciones por financiador/región y comparativa interanual).
- **Análisis de Estados Financieros ASFI** (validación de ecuación patrimonial, márgenes operativos, impacto del IUE y flujo neto de efectivo).
- **Anexo de Calidad de Datos** (resumen de registros limpiados, predichos y validados en el módulo técnico).

---

# ENTREGABLES REQUERIDOS
1. **Esquema de Base de Datos (SQL/ERD):** Tablas normalizadas que soporten tanto la contabilidad presupuestaria como los 6 bloques ASFI y el estado de curaduría de cada fila.
2. **Estructura del Backend y Endpoints API:** Lógica para la predicción por fila, cálculo escalonado del Estado de Resultados (con IUE), validación de balance y generación de reportes.
3. **Diseño de Interfaz (UI/UX) del Módulo Técnico:** Wireframe estructural o código frontend (React/Vue/HTML) de la tabla de limpieza con los botones de validación/predicción por fila y el panel generador de informes mensuales/anuales.
4. **Plantilla de Ejemplo del Informe Técnico:** Genera una muestra realista de cómo saldrá estructurado el Informe Técnico tras procesar un lote de datos.
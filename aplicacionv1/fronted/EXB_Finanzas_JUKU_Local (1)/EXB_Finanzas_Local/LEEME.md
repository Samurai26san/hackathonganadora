# Enseña por Bolivia + JUKU — versión local personalizada

## Abrir en Windows

1. Extrae TODO el ZIP en una carpeta nueva.
2. Abre `index.html` con Chrome o Edge.
3. Completa una cuenta de prueba y pulsa Ingresar. Los botones Técnico y Administrador completan el formulario automáticamente.

| Cuenta | Contraseña | Rol |
| --- | --- | --- |
| tecnico@exb.demo | Demo2026! | Técnico |
| admin@exb.demo | Demo2026! | Administrador |

Las cuentas y roles siguen siendo simulados. Los datos financieros ya son exclusivamente del Excel proporcionado. No ingreses una contraseña institucional real.

Sin Internet, instalaciones ni dependencias. Si el navegador restringe archivos locales, ejecuta `INICIAR_WINDOWS.bat` (Python 3) o `python local_server.py` desde la carpeta. El servidor opcional escucha solamente en 127.0.0.1:8080. Cierra la consola con Ctrl+C.

## Personalización

- Logo adjunto de Enseña por Bolivia en el ingreso, menú lateral y cabecera compartida de todas las ventanas.
- Presentación de JUKU y sus funciones como protagonista del ingreso.
- Eliminadas las frases “Finanzas con propósito” y “Más claridad, más impacto”.
- Gráficos de barras representados como pilas de libros: altura proporcional a los importes.
- Desplegables con una reinterpretación SVG de los puntos de la espiral: al abrir se extienden y continúan en el menú. El logo institucional original se usa sin modificar en las cabeceras.
- Navegación por teclado: Enter/Espacio abre el selector, flechas recorren las opciones y Escape lo cierra. La opción seleccionada queda identificada.

## Fuente y reconciliación

Archivo: `Prueba ExB Nov 2026 (1) (1).xlsx`.

Hoja base: BD, filas 3 a 3576. Se usan 3.574 registros y 1.478 movimientos con fecha. El archivo contiene únicamente 2026, con movimientos del 8 de enero al 30 de septiembre.

| Indicador | Importe Bs |
| --- | ---: |
| Presupuesto | 3.163.379,01 |
| Ejecución | 528.694,16 |
| Saldo | 2.634.684,85 |
| Porcentaje | 16,71 % |

Reglas para reproducir el archivo:

1. Presupuesto = suma de la columna `presupuesto Bs` de TODAS las filas de BD. Incluye filas PTTO, filas presupuestarias sin fecha con mes y valores presupuestarios en filas de movimientos. Limitarse a PTTO produciría otro total.
2. Ejecución = suma de la columna `Ejecución`. Se conserva ese valor; no se sustituye por una interpretación de debe − haber.
3. Saldo = presupuesto − ejecución. El porcentaje divide la ejecución entre el presupuesto.
4. Rubros, cuentas, financiadores, áreas y regiones conservan sus etiquetas originales. Las regiones se muestran como LP y SC, tal como aparecen en BD.
5. Mes filtra el campo original de BD. PTTO se mantiene como categoría separada; no se distribuye artificialmente en meses.
6. Los meses disponibles son enero a septiembre y PTTO. El reporte Por mes conserva su presupuesto, ejecución y saldo como en el Excel.
7. Detalle2 es un extracto con etiquetas/datos distintos de BD. No se suma a BD, para evitar duplicar operaciones o mezclar clasificaciones. La ficha muestra los campos originales disponibles en BD y su fila de origen.
8. No se inventan 2024, 2025 o 2027. Gestiones muestra 2026 y explica que aún no hay otra gestión para comparar.
9. No se inventan ni se multiplican gastos para llenar los gráficos. Los ceros se conservan: “9. Otros Gastos Ope.” no tiene ejecución en la tabla BD proporcionada.

`FUENTE_DATOS.json` conserva encabezados, filas originales y SHA-256 del Excel para rastrear cada registro. Los IDs BD-<fila> son identificadores técnicos, no nuevos registros financieros.

Los controles iniciales por rubro se reconciliaron con la hoja Rubro y el reporte mensual con Por mes. Los filtros y exportaciones se calculan desde BD para mantener una misma fuente.

## Funciones

- Dashboard con gestión/financiador; clic en una pila de libros abre el rubro.
- Presupuesto con filtros y Rubro → Cuenta → Movimientos.
- Siete informes de la consigna, filtros adaptativos y detalle.
- Movimientos con búsqueda, fechas, financiador y filtros avanzados; ficha de campos originales.
- Excel .xlsx con todas las filas filtradas y números exportados como números.
- PDF mediante el diálogo de impresión: selecciona Guardar como PDF.
- JUKU con animaciones y consultas guiadas: “presupuesto de viajes”, “movimientos de marzo”, “abrir reportes”, “ver gestiones” o “explica el dashboard”. Sus respuestas usan las cifras del archivo, pero no hay IA conectada.
- Administrador: revisión de la fuente, recarga del Excel extraído, exportación JSON, roles de cuentas de prueba e historial local.

Esta revisión retira el importador JSON de prueba y la plantilla 2027 para mantener exclusivamente la fuente solicitada. La incorporación de nuevos Excel reales queda para el backend.

## Datos locales y producción

Los datos financieros se cargan siempre desde la extracción del Excel incluida en el paquete. No se reutiliza el almacenamiento de datos sintéticos de la versión anterior. Solo se guardan usuarios de prueba e historial en el navegador cuando se permite localStorage. No se guarda la contraseña ni hay sesión persistente.

No hay conexión a la nube, envío de datos o IA externa. La autenticación de prueba no protege información: usa el paquete solo en equipos autorizados. Esta versión no se ha publicado ni reemplaza la demo web anterior.

Para conectar PostgreSQL y FastAPI, consulta `CONEXION_FUTURA.md`. El frontend actual usa HTML/CSS/JavaScript sin dependencias; la migración requiere implementar el servidor, permisos y llamadas asíncronas. Las credenciales de la base de datos nunca deben ir en el navegador.

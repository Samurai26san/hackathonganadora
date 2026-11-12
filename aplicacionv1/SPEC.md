# MVP — ExB Finanzas + Juku

Especificación de entrada: `docs/MVP_PROMPT.md`, proporcionada por el usuario.
Diseño obligatorio: `fronted/Interfaz_ExB_Juku.md` y su prototipo HTML/CSS.
Dominio de referencia: `backend/hackaton/backend/app/`, su guía y Excel original.

## Decisiones para integrar en el proyecto existente

- Flutter Web permanece en `lib/` con `pubspec.yaml` en la raíz. `frontend/`
  contiene el contenedor y Nginx. No se genera otra aplicación ni interfaz React.
- Se conservan las referencias originales sin modificarlas. El backend del MVP
  vive en `backend/app/`; reutiliza sus dimensiones y jerarquías de informes,
  reemplazando el cálculo con float por Decimal y agregaciones independientes.
- Colores originales: fondo #F5F7F1, papel #FFFFFF, verde #245741,
  texto #203E31, secundario #768577, lima #D9EDAA, borde #E0E7DA, ámbar #9B6A24.
  El texto secundario pequeño puede usar un tono más oscuro para contraste.
- Navegación: Dashboard, Presupuesto, Reportes, Movimientos, Gestiones;
  administración según rol y Juku lateral accesible desde todo el panel.
- Regla contable reconciliada de `LEEME.md`/`FUENTE_DATOS.json`: presupuesto es
  la suma de TODAS las filas de `presupuesto Bs`; ejecución es `Ejecución`
  directamente. No se resta `haber` de nuevo ni se agrega la hoja Detalle2.
  PTTO es mes 0. Solo hay 2026; no se inventan comparaciones.
- Se entrega OIDC mediante backend (PKCE, state y nonce, cookies HttpOnly).
  El acceso de demostración es explícito, local y deshabilitado en producción.
- Los datos financieros son de lectura en HTTP y chat. La ingesta financiera
  se realiza por CLI; la importación web de esta fase solo valida/vista previa.
- Documentos normativos requieren ingesta real y TEI; no se inventan leyes,
  citas ni respuestas del modelo cuando sus servicios no están disponibles.

## Módulos y orden

| ID | Responsabilidad | Dependencias |
| --- | --- | --- |
| identity | OIDC, usuarios, roles y alcances | persistencia |
| finance | Excel, Decimal, siete informes, exportación | identity |
| knowledge | Ingesta y búsqueda vectorial/BM25 con citas | identity |
| conversation | Herramientas permitidas, SSE, contexto e historial | finance, knowledge |
| web | Login, panel, cuatro módulos, Juku y estados | API |
| operations | Docker, migraciones, documentación y pruebas | todos |

## Verificación

Backend: pytest contra PostgreSQL para integración y motor, ruff, black y
mypy estricto. Tests aislados usan SQLite temporal únicamente como banco de
pruebas, sin ofrecer sincronización/offline ni SQLite en el cliente.
Frontend: flutter analyze, flutter test, flutter build web y comprobación visual.
Las cifras se serializan como strings y se procesan con Decimal/int en Flutter;
solo la geometría del gráfico se convierte a double.

## Límites externos

OIDC necesita proveedor y credenciales. Llama.cpp necesita el GGUF y TEI debe
descargar BGE-m3. No se afirman validaciones reales de esos servicios sin
ejecutarlas. Se documenta cada comprobación realizada y sus límites.

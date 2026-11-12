# Implementación del MVP

- [x] P1 — Revisar prompt, interfaz, prototipo y backend; registrar decisiones en SPEC.md.
- [x] P2 — Persistencia, importador BD y reconciliación exacta de 3.574 filas.
- [x] P3 — Siete informes, alcances, comparativa y exportación Excel/PDF/CSV.
- [x] P4 — OIDC/PKCE, sesiones revocables, demostración local y auditoría.
- [x] P5 — RAG, diccionario, herramientas estrictas y conversación SSE persistida.
- [x] P6 — Flutter: identidad, login, navegación, filtros, panel y cuatro módulos.
- [x] P7 — Flutter: Juku, historial, exportación, administración y estados.
- [x] P8 — PostgreSQL migrado y sembrado con el Excel real; 21 pruebas backend pasan.
- [x] P9 — Flutter: 6 pruebas pasan, analyze sin incidencias y build web generado.
- [x] P10 — Imagen backend construida como UID 10001; configuración Nginx válida.
- [x] P11 — Terminar revisión del último build en navegador y capturas finales.
- [x] P12 — Cerrar informe de validación y comandos de reanudación/arranque.

La ejecución real de Qwen/TEI y OIDC institucional requiere modelos, documentos
y credenciales externos. No marcar esos servicios como probados sin ejecutarlos.

- [ ] P13 — Preparar modelos/documentos reales y configurar proveedor OIDC; ejecutar validación end-to-end con esos servicios.

## Ejecución autorizada P13–P15

- [ ] P13.a — Descargar y verificar Qwen oficial por partes y BGE-m3; preparar inferencia con límites de recursos.
- [ ] P13.b — Ejecutar inferencia y embeddings reales; corregir problemas de compatibilidad observados.
- [ ] P14 — Configurar y comprobar OIDC real y la ingesta de documentación existente autorizada. Usar Keycloak local si no se proporciona otro proveedor.
  - [x] P14.a — Keycloak real: 30 comprobaciones pasan; acceso desde Flutter verificado en Chromium, sin errores JS.
  - [ ] P14.b — Ingesta y recuperación con BGE-m3 real (espera la descarga del modelo).
- [ ] P15 — Validar recorridos financieros/normativos reales, aislamiento y operación; registrar métricas, resultados y siguiente punto de reanudación.
  - [x] P15.a — Respaldo/restauración aislada: filas, totales y pgvector coinciden; base temporal eliminada.
  - [x] P15.b — 20 comprobaciones con sesión OIDC: siete informes conciliados, tres exportaciones y gestión inexistente denegada.
  - [ ] P15.c — Inferencia, RAG y aislamiento con modelos reales; requiere finalizar P13.

P13 conserva su alcance original. Las comprobaciones de identidad, documentos y
end-to-end se detallan en P14/P15; no se considera cerrado hasta verificarlas.


## Extensión solicitada: preparación y estados contables

- [x] C1 — Esquema aditivo, migración 0002, SQL y ERD.
- [x] C2 — API y Flutter de curaduría, clasificador supervisado, validación humana, permisos y bitácora.
- [x] C3 — Libro de partida doble, subcuentas, seis bloques y alertas.
- [x] C4 — Informe mensual/anual, PDF/XLSX con fórmulas y ejemplo ficticio.
- [x] C5 — Documentación, contrato API, sintaxis Python y compilación web.

No se ejecutan pruebas por petición expresa. Arranque operativo pendiente de
`make mobile` para aplicar 0002 en la base existente; no se reiniciaron servicios.
El build web incorpora las pantallas; el APK anterior requiere recompilarse si
se desea esta extensión instalada de forma nativa.

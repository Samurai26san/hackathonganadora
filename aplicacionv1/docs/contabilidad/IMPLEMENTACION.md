# Curaduría, contabilidad e informes técnicos

La aplicación conserva Flutter, el diseño institucional y las pestañas originales. Añade **Curaduría técnica**, **Contabilidad** e **Informes técnicos**. La información se guarda en PostgreSQL y se comparte entre equipos; no depende del almacenamiento del navegador.

## Arranque sin pruebas

Desde la raíz:

```bash
make mobile
```

El comando inicia PostgreSQL, aplica las migraciones Alembic aditivas y abre la web/API. Imprime la URL para PC y celular. Conserva los modelos, el Excel y los datos existentes. No ejecuta pruebas. Qwen puede tardar en cargar; la curaduría, los estados y los documentos son deterministas y funcionan sin esperar al modelo.

Para usar otros modos de arranque, aplica primero:

```bash
docker compose up -d --wait postgres
make migrate
```

Esta entrega compila la aplicación web. Un APK instalado anteriormente debe volver a compilarse para incorporar estas pantallas. Los servicios no se arrancaron durante la implementación.

## Curaduría técnica

Acceso: técnico (`analyst`/`technician`) y administrador. Cada usuario tiene lotes privados. No se revelan lotes ajenos ni se utilizan sus filas como entrenamiento.

1. Descarga **Plantilla**, con columnas y catálogos de IDs del alcance del usuario.
2. Completa la primera hoja y carga el Excel, o utiliza **Nueva fila**.
3. Pulsa una celda o **Editar fila** para rellenar o corregir campos. Selecciona el rubro y su cuenta dependiente. Indica el motivo.
4. **Predecir todas las etiquetas** propone conjuntamente rubro, cuenta, región, área y financiador a partir de validaciones anteriores del mismo usuario. **Revisar y aplicar sugerencias** abre un formulario; no sobrescribe ni aprueba automáticamente.
5. **Validar fila** exige importe exacto, gestión y categorías existentes, alcance autorizado, fecha para movimientos y correspondencia rubro/cuenta. Los duplicados del lote impiden validar.
6. **Consolidar** incorpora una fila validada al presupuesto o a los movimientos compartidos, en la misma transacción que su bitácora. Repetir la publicación se rechaza. Los paneles existentes detectan la revisión financiera.

Preparación admite hasta 5000 filas y 40 columnas; se limita el tamaño comprimido/descomprimido del libro. Los lotes idénticos del mismo usuario se rechazan. Los duplicados semánticos entre archivos diferentes requieren revisión del técnico; no se presume que dos transacciones iguales sean necesariamente la misma operación.

Normalización: espacios, enteros, fechas ISO o DD/MM/AAAA e importes con punto decimal o una coma decimal. Importes con separadores ambiguos se dejan pendientes para corrección manual. No se rellenan nulos con ceros ni se redondean silenciosamente importes con más de dos decimales.

Clasificador implementado: vecino más cercano supervisado sobre palabras de descripción/comprobante, similitud Jaccard y umbral 0,25. Predice todas las categorías de una fila de ejemplo aprobada. El porcentaje es una puntuación de similitud **no calibrada**, no una probabilidad de acierto; si no hay ejemplos suficientes devuelve abstención. No depende de Qwen ni presenta reglas como un modelo entrenado externo.

La bitácora conserva usuario, acción, motivo y antes/después. El Excel original permanece intacto. Una edición posterior por administración deja la validación consolidada como superada; la fila curada no puede volver a publicarse. Una restauración administrativa invalida las marcas de validación vinculadas para no atribuir aprobación a registros restaurados.

## Reportes presupuestarios

Se mantienen los siete informes, filtros de gestión/mes/financiador/área/región/rubro/cuenta, comparativas y exportaciones completas. Se añade **Filtros avanzados → Validación de datos**:

- Todos: hechos originales y cambios registrados.
- Validados y consolidados: hechos publicados desde la curaduría cuya aprobación sigue vigente.
- Sin validación vigente: hechos originales o modificados después de la aprobación.

La jerarquía presupuestaria del Excel sigue siendo rubro → cuenta → movimientos. No se inventan subcuentas que no existen en esa fuente. Las subcuentas contables se crean explícitamente en el plan de cuentas del libro contable y tienen su propio despliegue jerárquico.

Las hojas Excel preservan valores numéricos, filtros, encabezados y fórmulas de saldo, presupuesto vigente y avance cuando esas métricas están presentes. Los PDF/CSV detallados conservan la implementación anterior con todos los movimientos y cuentas sin movimientos.

## Contabilidad y seis bloques

El presupuesto no es un libro de partida doble. La nueva contabilidad tiene cuentas/subcuentas, asientos y líneas separados de `budgets`/`movements`. Administración con alcance institucional completo crea cuentas y registra asientos. Los usuarios con restricciones por región/área/financiador no pueden acceder a estados institucionales consolidados, para evitar divulgar información fuera de su alcance.

1. **Dictamen**: texto aportado por el responsable, incluyendo opinión/fundamentos/cuestiones clave; las alertas media/alta aparecen en el panel financiero. El sistema no se atribuye la condición de auditor ni genera una opinión profesional automática.
2. **Balance**: activos ordenados por liquidez, pasivos y patrimonio; se añade el resultado todavía no cerrado para conciliar activo = pasivo + patrimonio. Las cuentas contingentes y de orden se muestran separadas y no integran dicha ecuación.
3. **Resultados**: ingresos financieros − costos financieros = bruto; más ingresos operativos − gastos operativos − previsiones = operativo; más otros ingresos − otros gastos = antes de IUE; menos **IUE registrado** = utilidad neta. Las cuentas de gasto correctoras se registran por la contrapartida correspondiente.
4. **Patrimonio**: apertura, movimientos clasificados (reinversión, reservas, dividendos, aportes, otros), cierre y resultados todavía no cerrados. No se suma dos veces el resultado después de un asiento de cierre.
5. **Efectivo**: saldos de disponibilidades y movimientos de operación, inversión y financiamiento. Toda línea de efectivo requiere clasificación salvo apertura al 1 de enero. La conciliación muestra saldo inicial + flujo neto − saldo final.
6. **Notas**: documentos cualitativos vinculables a cuentas, gestión y riesgo. Las nuevas notas/dictámenes se agregan conservando sus versiones anteriores.

Los asientos deben cuadrar en Decimal, tener dos o más líneas con un único importe positivo por línea, cuentas finales existentes y comprobante único. Un asiento contingente/de orden no puede mezclarse con cuentas de balance. Las cuentas agrupadoras no reciben apuntes y no pueden crearse subcuentas bajo una cuenta ya utilizada. Los asientos contabilizados no se editan ni eliminan: se corrigen mediante contraasientos documentados.

La tasa de IUE no se impone como una conclusión tributaria. El generador permite introducir base y tasa para una **simulación explícita**; esta no modifica los asientos ni sustituye la liquidación tributaria. El estado de resultados descuenta el IUE contabilizado.

## Informe técnico

Selecciona **Corte mensual acumulado** o **Cierre anual comparativo**, gestión y mes. Por defecto usa solo hechos curados validados y consolidados; puedes incluir todos los registros mediante el selector. El presupuesto PTTO (mes 0) se conserva completo, sin prorratearlo; la ejecución se limita a la fecha de corte. La comparación emplea el mismo mes del año anterior si esa gestión existe.

El generador incluye resumen ejecutivo, riesgos de dictámenes/notas, ejecución y desviaciones por financiador/región, comparación disponible, seis bloques contables, IUE registrado/simulado y anexo de calidad. Exporta PDF institucional y Excel con secciones y hoja de fórmulas. Si faltan asientos, dictamen, notas o gestión anterior, lo declara; no genera importes contables a partir del presupuesto.

## Alcance normativo

Referencia consultada: [Manual de Cuentas para Entidades Financieras, ASFI](https://www.asfi.gob.bo/la/manual-cuentas-para-entidades-financieras-mcef). ASFI indica que su aplicación es obligatoria para las entidades bajo su supervisión. Esta implementación ofrece una estructura funcional de preparación y cálculo, **no acredita cumplimiento ASFI** ni asume que Enseña por Bolivia sea una entidad supervisada. El responsable debe definir la aplicabilidad, cargar el plan y códigos oficiales correspondientes, y revisar los formatos y criterios antes de presentar documentación regulatoria.

## Endpoints principales

Todos están bajo `/api/v1` y requieren sesión; el contrato OpenAPI contiene los cuerpos completos.

| Método y ruta | Acción | Permiso |
| --- | --- | --- |
| GET `/curation/catalogs` | Categorías autorizadas | Técnico/admin |
| POST `/curation/template` | Plantilla XLSX y catálogos | Técnico/admin |
| GET, POST `/curation/batches` | Lotes privados / ingesta | Técnico/admin |
| GET `/curation/batches/{id}` | Filas paginadas por estado | Propietario |
| PUT `/curation/rows/{id}` | Corrección y relleno manual | Propietario |
| POST `/curation/rows/{id}/predict` | Proponer todas las etiquetas | Propietario |
| POST `/curation/rows/{id}/validate` | Validación humana | Propietario |
| POST `/curation/rows/{id}/consolidate` | Publicación transaccional | Propietario y alcance |
| GET `/curation/rows/{id}/history` | Bitácora de esa fila | Propietario |
| GET `/accounting/catalogs` | Plan de cuentas y secciones | Alcance completo |
| POST `/accounting/accounts` | Nueva cuenta/subcuenta | Admin sin restricciones |
| POST `/accounting/entries` | Asiento cuadrado e inmutable | Admin sin restricciones |
| POST `/accounting/disclosures` | Dictamen/nota y riesgo | Admin sin restricciones |
| GET `/accounting/statements?cutoff=AAAA-MM-DD` | Seis bloques a fecha exacta | Alcance completo |
| GET `/accounting/alerts?year=2026` | Alertas del dashboard | Sin datos consolidados para cuentas restringidas |
| POST `/technical-reports/generate` | JSON, PDF o Excel mensual/anual | Alcance completo |

Las operaciones de fila exigen `version` para rechazar conflictos simultáneos con HTTP 409 y `reason` para documentar la acción. Las publicaciones y asientos comparten el bloqueo transaccional de escrituras financieras.

## Entregables y continuidad

- `REQUISITOS.md`: documento solicitado.
- `schema.sql`: esquema PostgreSQL completo de referencia; actualizar instalaciones con Alembic, no ejecutando SQL sobre tablas existentes.
- `ERD.md`: relaciones principales.
- `EJEMPLO_INFORME.md` y `ejemplo-informe.pdf`: muestra ficticia, sin cargarla en la base real.
- `../openapi.json`: contrato completo de endpoints, esquemas y permisos.
- Migración `0002_curation_accounting.py`: seis tablas aditivas; no modifica los importes anteriores.

No se ejecutaron pruebas por petición del usuario. La compilación no acredita las operaciones reales en PostgreSQL, permisos en ejecución ni una revisión regulatoria. El siguiente paso operativo es `make mobile`, abrir las pantallas y trabajar con un lote controlado. La bitácora de continuidad está en `tasks/PROGRESS.md`.

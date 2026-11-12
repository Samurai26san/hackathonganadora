# Conocimiento institucional y Juku

Coloca documentos autorizados PDF/DOCX/TXT/MD en `data_docs/`. Ejecuta `make ingest`
con TEI disponible en `EMBEDDINGS_SERVER_URL`, o el comando de ingesta dentro del
contenedor. El script conserva nombre y ruta de origen; no carga archivos Excel
financieros como conocimiento normativo. También hay ingreso de texto en
Administración → Conocimiento.

El texto se fragmenta por tokens cl100k_base: 512 tokens con 50 de solapamiento.
TEI debe devolver exactamente 1024 componentes finitos y un vector no nulo de
BGE-m3. La ingesta obtiene todos los embeddings antes de reemplazar fragmentos
de una fuente; si falla, la transacción no deja una fuente parcialmente cargada.

La búsqueda combina candidatos densos pgvector/HNSW y búsqueda léxica en español.
BM25 y Reciprocal Rank Fusion ordenan candidatos; un umbral de similitud densa
descarta coincidencias débiles. Los resultados contienen texto, fuente, índice y
similitud. Juku muestra citas identificadas y conserva el resultado de herramienta
en el historial. Ninguna recuperación habilita ejecutar instrucciones del texto.

Sin documentos relevantes, se indica ausencia de evidencia. El repositorio no
incluye leyes, manuales o citas inventadas para aparentar una base institucional.
La prueba automatizada usa un manual de prueba identificado y un TEI HTTP
controlado; no mide calidad semántica real de BGE-m3. Antes de producción, evalúa
un conjunto institucional de preguntas con relevancia y citas revisadas por una
persona responsable. Mide recall@k, precisión, umbral y latencia en el modelo real.

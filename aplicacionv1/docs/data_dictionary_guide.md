# Diccionario de datos

`DataDictionary` almacena término, columna canónica, tabla, descripción, sinónimos,
versión y estado activo. Administración → Diccionario permite agregar y editar
definiciones. La API DELETE desactiva sin perder trazabilidad. El contenido activo
se vuelve a leer en cada turno; no depende de reiniciar Juku.

La semilla incluye presupuesto vigente, ejecutado, saldo, financiador y PTTO,
con las reglas reconciliadas de la hoja BD. No se interpretan las columnas del
diccionario como SQL ni se permite al modelo construir consultas con ellas.
Las dimensiones disponibles provienen del catálogo autorizado del usuario.

Al modificar definiciones institucionales, revisa las fórmulas con la persona
responsable y añade pruebas de reconciliación antes de cambiar el motor. El
diccionario explica semántica; no reemplaza validaciones, permisos o cálculos.

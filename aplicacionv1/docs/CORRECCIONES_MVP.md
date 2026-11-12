# Correcciones financieras del MVP

La carpeta `correcciones/` contiene imágenes de Juku. Los requisitos funcionales
son los cinco puntos del mensaje del usuario. Por elección explícita posterior,
la persistencia y los permisos se implementan en el backend: PC y celular
comparten los cambios. No se usan copias financieras en localStorage.

## Exportaciones completas

Los botones PDF y CSV incluyen el informe seleccionado, el desglose de rubros y
cuentas y todos los movimientos del alcance. La exportación no depende de abrir
las cuentas ni de la paginación de pantalla. Conserva cuentas con presupuesto y
sin ejecución. Se mantienen las reglas originales del motor para fechas, meses,
financiadores y permisos; las fechas limitan ejecución y ajustes, no eliminan el
presupuesto de la gestión.

El PDF separa el informe, los rubros/cuentas y los movimientos en secciones.
El CSV incluye `Gestión`, `Filtros`, `Sección` y `Nivel`. Para sumar presupuesto,
ejecución y saldo del desglose, utiliza solo `Nivel=Cuenta`. Para analizar los
movimientos, utiliza solo `Nivel=Movimiento`. No sumes grupos, cuentas y
movimientos entre sí: representan distintos niveles de los mismos importes.
Excel mantiene su exportación del informe seleccionado.

## Control de cambios

Entra como administrador y abre el icono de configuración/Administración →
**Control de cambios**. Selecciona Presupuesto o Movimientos. La lista respeta la
gestión y los filtros del panel y permite añadir, editar y eliminar registros.
Los formularios ofrecen categorías existentes del Excel; la cuenta debe
pertenecer al rubro elegido. Los importes se guardan con Decimal/NUMERIC y un
máximo de dos decimales. El presupuesto editable es el importe inicial del
registro; el motor sigue calculando el vigente con sus modificaciones.

Cada operación exige un motivo de al menos cinco caracteres. El borrado exige
confirmación. Si otra persona cambia el registro mientras lo editas, el servidor
rechaza el envío con 409: actualiza la lista y revisa los datos antes de guardar.
Los técnicos conservan consulta, filtros y exportación y reciben 403 al intentar
modificar datos o consultar el historial. Los administradores también respetan
sus alcances de región, área y financiador. Juku conserva herramientas de lectura;
no puede invocar las rutas de modificación.

## Historial y restauración

Administración → **Historial de datos** muestra administrador, fecha/hora local,
acción, motivo y valores anteriores/nuevos. Su botón JSON descarga todo el
historial autorizado, incluyendo páginas que no estén visibles.

**Restaurar datos originales** deshace, en orden inverso y en una transacción,
los cambios administrativos registrados desde la última restauración. Devuelve
los registros al estado previo a esos cambios (el Excel importado inicialmente),
incluidas las modificaciones asociadas a presupuestos eliminados. No reimporta
ni sobrescribe el archivo Excel. Conserva cada evento anterior y añade un evento
de restauración. Requiere confirmación, motivo y un administrador sin
restricciones de alcance. Una revisión desactualizada se rechaza con 409.

Los cambios y su auditoría se confirman juntos en PostgreSQL; persisten al
recargar o reiniciar la API. Los informes y las exportaciones coordinan sus
lecturas con las escrituras para evitar mezclar estados. El dispositivo que
modifica datos actualiza sus paneles; otros dispositivos conectados detectan
la nueva revisión aproximadamente cada diez segundos.

## Uso y comprobaciones

Arranque habitual: `make mobile`. Recarga el navegador con Ctrl+Shift+R después
de actualizar el build. No hace falta migración adicional: se utiliza la tabla
existente de auditoría. No elimines el volumen de PostgreSQL para actualizar.

Se añadieron cuatro comprobaciones puntuales en `test_data_changes.py`: ciclo
presupuestario con restauración de ajustes e historial, restricciones de rol y
cuenta/rubro, exportación completa con cuenta sin movimientos y ciclo de
movimientos con permisos por región. Se ejecutan sobre bases temporales/de
pruebas, nunca sobre los hechos financieros del MVP. No son pruebas de skills.

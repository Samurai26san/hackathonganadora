# Abrir el MVP desde el celular

Desde la carpeta del proyecto ejecuta:

```bash
make mobile
```

El comando muestra la dirección de la PC, por ejemplo `http://192.168.1.20:8088`.
Abre esa dirección en el navegador del celular, conectado a la misma WiFi.
En la PC también puedes usar `http://localhost:8088`.

Acceso de demostración: `tecnico@exb.demo`, contraseña `Demo2026!`.
Administración local: `admin@exb.demo`, misma contraseña.

Se sirve el build Flutter existente, con una API separada que consulta los datos
reales del PostgreSQL del proyecto. No modifica `.env` ni la configuración OIDC.
Este arranque de desarrollo usa HTTP y acceso demo para que el celular no dependa
de un proveedor con direcciones localhost. Ctrl+C detiene estos procesos propios.

PostgreSQL debe estar iniciado. Si se detuvo, usa `docker compose up -d postgres`.
Si el celular no abre la dirección, comprueba que ambos dispositivos comparten
red y que el firewall permite conexiones entrantes al puerto 8088. No hace falta
abrir puertos del router para esta conexión local.

Presupuesto, Reportes, Movimientos y Gestiones usan los datos ya importados.
Juku sigue pendiente de terminar los modelos y su puesta en marcha; el arranque
no simula respuestas de IA. Registro de arranque: `ops/runtime/mobile-api.log`.

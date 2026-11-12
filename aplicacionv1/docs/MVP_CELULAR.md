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
`make mobile` inicia también Qwen2.5-7B en segundo plano, por CPU con memoria
limitada a 1400 MB. Espera o reanuda las descargas y verifica los hashes oficiales
antes de cargar el modelo. La primera carga puede ser lenta. Juku solo podrá
responder cuando termine esa carga; no se simulan respuestas.

Progreso: `tail -f ops/runtime/qwen.log`. API: `ops/runtime/mobile-api.log`.
Para iniciar Qwen por separado: `make qwen`. Para servir solo la web/API:
`python3 tools/run_mobile.py --without-qwen`. Consultas sobre documentos requieren
además el servicio de embeddings; el arranque de Qwen habilita las consultas
financieras mediante las herramientas del servidor.

---
name: garrafa-ble
description: Implementar y verificar la integración Flutter con los sensores BLE-Ultra de este proyecto Garrafa, conservando su protocolo ESP32.
---

Lee `esp32/BLE-Connect_UART/main/main.c` y la variante `BLE-Connect_UART_SPI/main/main.c` desde la raíz del proyecto antes de cambiar el contrato BLE.
Ambas anuncian BLE-Ultra por nombre, sin UUID de servicio en advertising. Escanea sin filtro de servicio y permite elegir la dirección si hay varios sensores.
Servicio 0x0180; notificaciones y escritura 0xDEAD; lectura 0xFEF4 responde únicamente OK.
Cada notificación contiene `Dist: N.N cm`. Actualizar significa esperar la siguiente notificación válida: el firmware no implementa comandos para forzar mediciones.
El porcentaje requiere distancias reales de lleno y vacío, persistidas localmente; no asumir dimensiones, kilogramos ni equivalencia entre altura y volumen. Conservar distancia cruda y hora de lectura, y señalar datos desactualizados.
Aplica `agentes/skills/flutter-expert/SKILL.md` para UI y estado. Usa `agentes/skills/c-pro/SKILL.md` solo al trabajar en firmware.
Ejecuta análisis y pruebas Flutter; documenta por separado lo verificado con hardware. No modificar UART, checksum, colas, SD o UUID incidentalmente.

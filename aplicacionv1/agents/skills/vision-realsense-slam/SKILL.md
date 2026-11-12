---
name: vision-realsense-slam
description: >-
  Instrucciones, flujos de trabajo y comandos para la cámara Intel RealSense D435,
  detección de pose con MediaPipe y ViTPose, escaneo 2D tipo LiDAR y mapeado SLAM 3D
  en este proyecto. Úsalo cuando se requiera ejecutar, calibrar o extender tareas de visión y SLAM.
---

# Skill: Visión por Computador y SLAM 3D con Intel RealSense D435

Esta habilidad proporciona los procedimientos operativos, mejores prácticas y comandos
para el hardware de la RealSense D435 y los algoritmos de visión del proyecto.

## Estructura del Proyecto y Entorno

- **Entorno Virtual de Python:** `tesiskinet` ubicado en `/home/samuel/tesis1/tesiskinet`.
  - Activación: `source tesiskinet/bin/activate`
- **Librerías Clave:** `pyrealsense2`, `opencv-python`, `mediapipe==0.10.14`, `open3d`, `torch`, `transformers`.

## Scripts Principales y Cuándo Usarlos

1. **Estimación de Pose Corporal y Rastreo de Patadas a 60 FPS:**
   - Script: `prueba_kinect_mediapipe.py`
   - Uso: Captura y trazo de esqueleto anatómico con medición 3D de distancia al cuerpo y tobillos.
   - Ejecución: `python prueba_kinect_mediapipe.py`

2. **Detección de Manos y Medición Z:**
   - Script: `prueba kinet.py`
   - Uso: MediaPipe Hands con cálculo de profundidad métrica en la punta de los dedos.
   - Ejecución: `python "prueba kinet.py"`

3. **Escáner 2D Fidedigno (LiDAR 2D sobre BEV Grid):**
   - Script: `escaner_2d_desde_3d.py`
   - Uso: Filtro de franja de altura (ignora suelo y techo) proyectando mapa top-down 2D.
   - Ejecución: `python escaner_2d_desde_3d.py`

4. **Mapeado SLAM 3D con Fusión Voxel:**
   - Script: `mapeado_slam_3d_limpio.py` / `mapeado_slam_3d_realsense.py`
   - Uso: Reconstrucción volumétrica 3D continua en Open3D a 60 FPS y exportación `.ply`.
   - Ejecución: `python mapeado_slam_3d_limpio.py`

## Referencias Rápidas

- Para la lista completa de comandos de hardware y solución de problemas:
  Consulta [comandos.md](./references/comandos.md).

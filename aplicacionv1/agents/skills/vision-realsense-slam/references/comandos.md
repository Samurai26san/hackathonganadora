# Referencia de Comandos: RealSense D435 y SLAM

Este documento reúne los comandos esenciales de verificación, ejecución y pruebas.

## 1. Verificación del Entorno y Librerías

Comprueba que todas las dependencias funcionen y que la GPU esté disponible:

```bash
/home/samuel/tesis1/tesiskinet/bin/python -c "
import pyrealsense2 as rs
import cv2
import mediapipe as mp
import open3d as o3d
import torch
import transformers
print('Estado: OK')
print('CUDA activo:', torch.cuda.is_available())
"
```

## 2. Detección Física de la Cámara USB 3.0

Comprueba que la cámara esté conectada por USB 3.0 (SuperSpeed):

```bash
lsusb | grep -i intel
rs-enumerate-devices -s
```

## 3. Mapeado SLAM en ROS 2 Jazzy (RTAB-Map)

Para correr SLAM denso en ROS 2:

```bash
./lanzar_slam_realsense.sh
```

O comando manual del nodo:
```bash
ros2 launch realsense2_camera rs_launch.py \
    enable_color:=true \
    enable_depth:=true \
    align_depth.enable:=true \
    pointcloud.enable:=true \
    rgb_camera.profile:=848x480x60 \
    depth_module.profile:=848x480x60
```

## 4. Teclas Rápidas en Scripts de Mapeado 3D

- `a`: Alternar auto-acumulación de mapa.
- `g`: Alternar filtro de suelo/techo.
- `s`: Guardar mapa a archivo `.ply`.
- `r`: Reiniciar lienzo 3D.
- `q`: Salir.

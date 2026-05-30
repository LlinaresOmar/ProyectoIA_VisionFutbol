# Contexto del proyecto: football-ai-analysis

Este proyecto implementa un prototipo en Python para analizar clips cortos de futbol mediante vision artificial.

## Objetivo

Analizar clips cortos de futbol de SoccerNet. El sistema debe detectar jugadores y balon cuando sean visibles, clasificar frames analizables y no analizables, y generar un video anotado con informacion visual sobre el resultado.

## Decisiones actuales

- Usar SoccerNet como unica fuente principal de videos y datos.
- No usar otros datasets en esta fase.
- No entrenar ni reentrenar YOLO por ahora.
- Ejecutar inicialmente en CPU.
- Trabajar con clips cortos, no con partidos completos.
- Mantener codigo Python simple y directo.

## Entorno

- Windows 11 + PowerShell.
- Conda env: `football-ai`.
- Python esperado: 3.11.15.
- Python detectado del entorno: `C:\Users\javie\miniconda3\envs\football-ai\python.exe`.
- Modelo: `yolo26n.pt`.
- Resolucion actual de prueba: 224p.
- SoccerNet puede proporcionar videos de mayor calidad, por ejemplo 720p. Conviene usar 720p en una bateria posterior para mejorar la deteccion del balon y comparar coste de CPU.

## Datos disponibles

- `videos/input/1_224p.mkv`
- `videos/input/2_224p.mkv`
- Clips preparados en `videos/clips/prepared/`.
- `video_download.py` permite descargar `224p` o `720p` usando `--quality` y otro partido usando `--game`.

## Umbrales iniciales

- `MODEL_CONF = 0.05`
- `PERSON_CONF = 0.25`
- `BALL_CONF = 0.10`
- `PERSON_CLASS_ID = 0`
- `BALL_CLASS_ID = 32`
- `IMGSZ = 640`
- `DEVICE = cpu`
- `min_green_ratio = 0.35`
- `max_person_area_ratio_for_closeup = 0.25`
- Los candidatos a balon dentro de `ball_filter.ignore_regions` se descartan. Esto evita falsos positivos provocados por el logo fijo de TV en la esquina inferior derecha.
- Las etiquetas de persona se dibujan pequenas, translucidas, debajo del jugador y escaladas segun resolucion. Las cajas de persona se dibujan como una U inferior.

## Roadmap

### video_analise.py v1

- CLI con `argparse`.
- Carga de YOLO.
- Procesamiento frame a frame con OpenCV.
- Inferencia con `classes=[0, 32]`.
- Filtrado manual con umbrales separados para personas y balon.
- Seleccion de un unico balon por frame.
- Memoria corta del balon.
- Clasificacion basica del frame:
  - `PLAY_ANALYZABLE`
  - `NO_BALL_VISIBLE`
  - `CLOSE_UP`
  - `UNKNOWN`
- Dibujo de cajas, balon y texto de estado.
- Guardado en `videos/output/`.

### Versiones posteriores

- v2: tracking de jugadores con ByteTrack/BoT-SORT.
- v3: posesion visible y pases aproximados.
- v4: posibles fueras, posibles goles y clips desde anotaciones SoccerNet.

## Regla importante

No implementar pases, fueras ni goles en v1. Primero estabilizar deteccion, anotacion visual, seleccion del balon y clasificacion de frames.

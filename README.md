# football-ai-analysis

Prototipo en Python para analizar clips cortos de futbol mediante vision artificial.

El objetivo inmediato es trabajar con clips de SoccerNet en 224p, detectar personas y balon con YOLO, clasificar frames basicos y generar un video anotado. En esta fase no se entrena ningun modelo y no se implementan todavia pases, fueras ni goles.

## Entorno

Entorno Conda usado:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe
```

Comprobacion rapida:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe -c "import torch, ultralytics; print(torch.__version__); print(torch.cuda.is_available()); print(ultralytics.__version__)"
```

## Scripts

- `diagnose_clip.py`: cuenta detecciones por clase sobre un clip.
- `debug_ball.py`: genera video visual de depuracion del balon.
- `video_analise.py`: version principal v1 del analisis de clips.

## Ejecutar diagnostico

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe diagnose_clip.py
```

## Ejecutar analisis

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe video_analise.py --input videos/clips/prepared/clip_00m00s_20s.mp4
```

Salida por defecto:

```text
videos/output/clip_00m00s_20s_analysed.mp4
```

El analisis tambien genera metricas JSON para el panel grafico futuro:

```text
videos/output/stats/clip_00m00s_20s_stats.json
```

## Descargar otro video de SoccerNet

Antes de descargar, configurar la contrasena en la variable de entorno `SOCCERNET_PASSWORD`.

Ejemplo en 224p:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe video_download.py --quality 224p
```

Ejemplo en 720p:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe video_download.py --quality 720p --halves 1
```

Para probar otro partido/canal, pasar el identificador SoccerNet con `--game`.

## Estado de v1

Implementado:

- CLI con `argparse`.
- Carga de `yolo26n.pt`.
- Procesamiento frame a frame con OpenCV.
- Inferencia YOLO en CPU con `classes=[0, 32]`.
- Umbrales separados para personas y balon.
- Seleccion de un unico balon por frame.
- Memoria breve del balon.
- Ajuste inicial de heuristicas:
  - `ball_conf: 0.10`
  - `min_green_ratio: 0.35`
  - `max_person_area_ratio_for_closeup: 0.25`
- Filtro configurable de regiones ignoradas para el balon, usado inicialmente para descartar el logo de TV en la esquina inferior derecha.
- Etiquetas de persona reducidas al 40%, con fondo translucido al 50%, colocadas bajo el jugador y escaladas segun resolucion.
- Estados de frame:
  - `PLAY_ANALYZABLE`
  - `NO_BALL_VISIBLE`
  - `CLOSE_UP`
  - `UNKNOWN`
- Escritura de video anotado en `videos/output`.

## Estado de v2

Implementado inicialmente:

- Tracking de jugadores con ByteTrack.
- `track_id` visible sobre cada jugador detectado cuando existe asociacion.
- Deteccion normal y tracking separados para no degradar la deteccion del balon.
- Matching por IoU entre detecciones de personas y tracks.
- Memoria basica por jugador:
  - primer frame visto;
  - ultimo frame visto;
  - frames vistos;
  - confianza media;
  - distancia aproximada recorrida en pixeles;
  - color medio de camiseta en BGR/RGB/HSV.
- Agrupacion inicial de tracks en `team_1`/`team_2` mediante color medio RGB de camiseta.
- Exportacion de metricas JSON por clip para alimentar un futuro panel HTML/CSS/JS.

Pendiente dentro de v2:

- Comparacion formal ByteTrack vs BoT-SORT.
- Afinar estabilidad de IDs.
- Mejorar la agrupacion de equipos usando solo frames analizables y crops de camiseta mas robustos.

## Comparar Trackers

Ejemplo rapido:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/compare_trackers.py --input videos/clips/prepared/clip_05m00s_20s.mp4 --process-every 5
```

Ejemplo completo:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/compare_trackers.py --input videos/clips/prepared/clip_05m00s_20s.mp4
```

## Generar Panel HTML

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/generate_report_panel.py --stats videos/output/stats/clip_05m00s_20s_stats.json
```

Salida por defecto:

```text
videos/output/stats/clip_05m00s_20s_stats.html
```

Pendiente para versiones posteriores:

- Posesion visible y pases aproximados.
- Posibles salidas de campo y goles.
- Comparar los mismos clips en 720p desde SoccerNet para mejorar la deteccion del balon.

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

## Ejecutar analisis v1

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe video_analise.py --input videos/clips/prepared/clip_00m00s_20s.mp4
```

Salida por defecto:

```text
videos/output/clip_00m00s_20s_analysed.mp4
```

## Estado de v1

Implementado:

- CLI con `argparse`.
- Carga de `yolo26n.pt`.
- Procesamiento frame a frame con OpenCV.
- Inferencia YOLO en CPU con `classes=[0, 32]`.
- Umbrales separados para personas y balon.
- Seleccion de un unico balon por frame.
- Memoria breve del balon.
- Estados de frame:
  - `PLAY_ANALYZABLE`
  - `NO_BALL_VISIBLE`
  - `CLOSE_UP`
  - `UNKNOWN`
- Escritura de video anotado en `videos/output`.

Pendiente para versiones posteriores:

- Tracking de jugadores.
- Clasificacion de equipos por color.
- Posesion visible y pases aproximados.
- Posibles salidas de campo y goles.

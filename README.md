# football-ai-analysis

Prototipo en Python para analizar clips de futbol mediante vision artificial y generar videos anotados, metricas JSON y paneles HTML.

El cierre del proyecto se centra en una demo tecnica defendible:

- deteccion de jugadores y agrupacion heuristica por equipo;
- deteccion heuristica de arbitro como track outlier y pintado en blanco;
- conteo aproximado de pases por equipo mediante asociacion balon-jugador;
- comparativa entre camara panoramica full-pitch y retransmision TV.

Los goles y salidas de banda/fondo quedan documentados como evolucion futura.

## Entorno

Entorno Conda usado:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe
```

Comprobacion rapida:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe -c "import torch, ultralytics; print(torch.__version__); print(torch.cuda.is_available()); print(ultralytics.__version__)"
```

## Analisis de un clip

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe video_analise.py `
  --input videos/clips/prepared/clip_00m00s_20s.mp4 `
  --team-render-mode two-pass
```

Salida por defecto:

```text
videos/output/<clip>_analysed.mp4
videos/output/stats/<clip>_stats.json
```

El modo `two-pass` realiza una primera pasada para deteccion, tracking, equipos,
roles y eventos; despues reabre el video para pintar equipos, arbitro y
contadores de pases con la informacion ya consolidada.

## Panel HTML de un clip

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/generate_report_panel.py `
  --stats videos/output/stats/clip_05m00s_20s_stats.json
```

El panel muestra estados del clip, tracks principales, equipo/rol por track,
pases candidatos y posesion estimada.

## Suite mixta final

La suite curada compara fuentes panoramicas full-pitch con retransmision TV:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/run_clip_suite.py `
  --suite config/clip_suite.yaml `
  --clip-limit 2
```

Sin `--clip-limit`, procesa los 8 clips configurados en `config/clip_suite.yaml`.
El indice final queda en:

```text
videos/output/mixed_suite/index.html
```

Este panel comparativo incluye:

- tipo de fuente;
- objetivo del clip;
- tracks unicos y duracion media;
- porcentaje de balon visible;
- frames analizables;
- pases detectados por equipo;
- conclusion automatica: `apto para eventos tacticos`, `solo deteccion visual` o `no recomendable`.

## Batch full-pitch para calibracion

Para probar matrices de configuraciones sobre videos panoramicos:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/run_full_pitch_test_batch.py `
  --input-dir videos/input/test `
  --video-glob "128058*.mp4" `
  --clips-per-video 3 `
  --duration 10 `
  --experiment-config config/full_pitch_experiments.yaml `
  --continue-on-error
```

Este flujo sirve para calibrar una instalacion real: misma bateria de clips,
varios perfiles de modelo/tracker/umbrales, ranking global y revision visual de
los mejores candidatos.

## Estado implementado

- YOLO para personas y balon con umbrales separados.
- Filtros de falsos positivos de balon por regiones ignoradas y polilineas.
- Clasificacion de frame: `PLAY_ANALYZABLE`, `NO_BALL_VISIBLE`, `CLOSE_UP`, `UNKNOWN`.
- Tracking con ByteTrack o BoT-SORT.
- `track_id` visible.
- Memoria de color de camiseta por track.
- Clustering heuristico `team_1`/`team_2`.
- Roles por track: `team_1`, `team_2`, `referee_candidate`, `unknown`.
- Arbitro pintado en blanco cuando se detecta como outlier estable.
- Pases candidatos por equipo mediante cambio de poseedor dentro del mismo equipo.
- Overlay de video con pases y posesion.
- JSON compatible con paneles anteriores y ampliado con `role`, `possession` y `events`.
- Suite mixta para defender por que full-pitch es adecuado para metricas tacticas y TV broadcast no lo es.

## Limitaciones conocidas

El conteo de pases es aproximado: se basa en la proximidad del balon al pie del
jugador y en cambios de poseedor entre tracks del mismo equipo. No usa aun un
modelo entrenado de contacto balon-jugador ni calibracion metrica real del
campo.

La deteccion de arbitro tambien es heuristica: busca tracks estables cuyo color
medio queda fuera de los clusters de equipo y coincide con reglas amplias de
color de arbitro. Puede fallar con equipaciones negras, blancas o amarillas.

Los clips de TV con cambios de plano sirven para mostrar deteccion visual, pero
no son una fuente fiable para tracking largo, posesion ni pases. La camara
full-pitch es la fuente recomendada para eventos tacticos.

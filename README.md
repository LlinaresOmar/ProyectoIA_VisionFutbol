# football-ai-analysis

Prototipo en Python para analizar clips de futbol mediante vision artificial y generar videos anotados, metricas JSON y paneles HTML.

El cierre del proyecto se centra en una demo tecnica defendible:

- deteccion de jugadores y agrupacion heuristica por equipo;
- separacion heuristica entre portero candidato y arbitro candidato;
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
roles y eventos; despues reabre el video para pintar equipos, porteros,
arbitro y contadores de pases con la informacion ya consolidada.

Por defecto el MP4 final se recodifica con `ffmpeg` a H.264/yuv420p para que
los enlaces de los informes HTML funcionen en navegadores como Chrome. Se puede
desactivar con `--no-web-video`.

Para que la demo sea legible, el overlay de jugadores muestra solo `#track_id`
en las detecciones trazadas y oculta detecciones de persona sin ID. Esto reduce
el parpadeo visual cuando el tracker pierde una asociacion durante algun frame.

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
  --output-dir videos/output/final_demo `
  --clips-dir videos/clips/final_demo `
  --overwrite
```

El indice final queda en:

```text
videos/output/final_demo/index.html
```

Este panel comparativo incluye:

- tipo de fuente;
- objetivo del clip;
- tracks unicos y duracion media;
- porcentaje de balon visible;
- frames analizables;
- pases detectados por equipo;
- conclusion automatica: `apto para eventos tacticos`, `solo deteccion visual` o `no recomendable`.

Para crear un mosaico visual rapido de todos los videos anotados:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/create_contact_sheet.py `
  --input videos/output/final_demo `
  --output-dir videos/output/final_demo/contact_sheets `
  --overwrite
```

Para abrir los informes con enlaces de video en Chrome:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/serve_output.py `
  --directory videos/output/final_demo
```

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
- Roles por track: `team_1`, `team_2`, `goalkeeper_candidate`, `referee_candidate`, `unknown`.
- Portero candidato pintado en amarillo/cian y arbitro candidato pintado en blanco.
- Pases candidatos por equipo mediante cambio de poseedor dentro del mismo equipo.
- Overlay de video con pases y posesion.
- JSON compatible con paneles anteriores y ampliado con `role`, `possession` y `events`.
- Suite mixta para defender por que full-pitch es adecuado para metricas tacticas y TV broadcast no lo es.

## Limitaciones conocidas

El conteo de pases es aproximado: se basa en la proximidad del balon al pie del
jugador y en cambios de poseedor entre tracks del mismo equipo. No usa aun un
modelo entrenado de contacto balon-jugador ni calibracion metrica real del
campo.

La separacion entre portero y arbitro tambien es heuristica: ambos parten de
tracks estables cuyo color medio queda fuera de los clusters de equipo. El
portero se favorece cerca de zonas de porteria o bordes defensivos, mientras el
arbitro se favorece en zonas interiores. Puede fallar con cambios de plano,
equipaciones similares o detecciones parciales.

Los clips de TV con cambios de plano sirven para mostrar deteccion visual, pero
no son una fuente fiable para tracking largo, posesion ni pases. La camara
full-pitch es la fuente recomendada para eventos tacticos.

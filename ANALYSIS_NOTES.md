# Notas de evaluacion visual

Fecha: 2026-05-30

## Clips evaluados

- `clip_00m00s_20s.mp4`
- `clip_05m00s_20s.mp4`
- `clip_10m00s_20s.mp4`
- `clip_25m00s_30s.mp4`
- `porteria_33m00s_30s.mp4`
- `primer_plano_12m30s_20s.mp4`

## Configuracion inicial

- `ball_conf: 0.05`
- `min_green_ratio: 0.25`
- `max_person_area_ratio_for_closeup: 0.35`

Observaciones:

- El balon se detecta con frecuencia en 224p, pero aparecen falsos positivos debiles.
- En algunos planos cerrados hay suficientes personas y cesped para ser marcados como `PLAY_ANALYZABLE`.
- `primer_plano_12m30s_20s.mp4` seguia teniendo demasiado porcentaje de frames analizables.

## Medicion de umbrales de balon

Conteo de frames con algun candidato de balon por umbral:

| Clip | Frames | >=0.05 | >=0.07 | >=0.10 | >=0.15 |
| --- | ---: | ---: | ---: | ---: | ---: |
| clip_00m00s_20s | 499 | 320 | 266 | 192 | 134 |
| clip_05m00s_20s | 500 | 336 | 321 | 313 | 283 |
| clip_10m00s_20s | 500 | 337 | 288 | 230 | 160 |
| clip_25m00s_30s | 750 | 448 | 398 | 324 | 218 |
| porteria_33m00s_30s | 750 | 413 | 354 | 294 | 226 |
| primer_plano_12m30s_20s | 500 | 258 | 237 | 203 | 184 |

Decision:

- Subir `ball_conf` a `0.10`.
- Es un ajuste conservador: reduce candidatos debiles sin eliminar completamente el balon en clips de juego.

## Medicion de cesped y primeros planos

El ratio medio de cesped en clips de juego esta normalmente por encima de `0.50`, mientras que el clip de primer plano baja a `0.322`.

Decision:

- Subir `min_green_ratio` a `0.35`.
- Bajar `max_person_area_ratio_for_closeup` a `0.25`.

## Resultado con configuracion ajustada

- `ball_conf: 0.10`
- `min_green_ratio: 0.35`
- `max_person_area_ratio_for_closeup: 0.25`

| Clip | Ball visible | PLAY_ANALYZABLE | CLOSE_UP | NO_BALL_VISIBLE | UNKNOWN |
| --- | ---: | ---: | ---: | ---: | ---: |
| clip_00m00s_20s | 192 | 356 | 0 | 99 | 44 |
| clip_05m00s_20s | 313 | 218 | 212 | 4 | 66 |
| clip_10m00s_20s | 230 | 319 | 2 | 115 | 64 |
| clip_25m00s_30s | 324 | 437 | 206 | 80 | 27 |
| porteria_33m00s_30s | 294 | 487 | 44 | 162 | 57 |
| primer_plano_12m30s_20s | 203 | 225 | 205 | 10 | 60 |

## Recomendacion sobre calidad de video

La deteccion del balon esta limitada por la resolucion 224p. SoccerNet permite descargar videos de mayor calidad, por ejemplo 720p. Para mejorar el reconocimiento de objetos pequenos, especialmente el balon, conviene crear una bateria equivalente de clips en 720p y comparar:

- precision visual del balon;
- falsos positivos de `sports ball`;
- coste de CPU por frame;
- si hace falta reducir `imgsz` o procesar clips mas cortos.

La configuracion actual debe entenderse como una configuracion razonable para 224p, no como el ajuste final para videos de mayor resolucion.

## Falso positivo del logo de TV

Durante la revision visual se detecto un falso positivo recurrente: el logo fijo de retransmision en la esquina inferior derecha se confunde con `sports ball`.

Ejemplos:

- `clip_05m00s_20s_analysed.mp4`, aproximadamente entre 00:00:06 y 00:00:11.
- Planos `CLOSE_UP` en `clip_25m00s_30s_analysed.mp4`.
- Planos `CLOSE_UP` en `primer_plano_12m30s_20s_analysed.mp4`.

Decision:

- Anadir `ball_filter.ignore_regions` en `config/config.yaml`.
- Descartar candidatos a balon cuyo centro caiga dentro de la esquina inferior derecha configurada.
- Mantenerlo configurable porque puede variar entre canales, resoluciones y partidos.
- Suprimir la visualizacion de `ball memory` en frames `CLOSE_UP`, porque en primeros planos la memoria del balon no aporta valor y puede parecer un falso positivo.

La primera region configurada es:

```yaml
ball_filter:
  ignore_regions:
    - name: tv_logo_bottom_right
      x_min_ratio: 0.82
      y_min_ratio: 0.70
      x_max_ratio: 1.00
      y_max_ratio: 1.00
```

## Ajuste visual de anotaciones

Se redujo el impacto visual de las etiquetas de personas:

- Texto de persona al 40% del tamano base.
- Fondo translucido al 50%.
- Etiqueta colocada debajo del jugador, ligeramente separada.
- Escalado automatico segun resolucion, usando 224p como altura de referencia.
- Rectangulo completo sustituido por una marca en U en la parte inferior del jugador.
- La U ocupa el 25% inferior de la caja original.

Esto mejora la legibilidad del video y reduce solapes entre etiquetas.

## Primera prueba 720p

Se descargo `1_720p.mkv` del partido actual y se preparo:

- `videos/clips/prepared_720p/clip_05m00s_20s_720p.mp4`
- Resolucion: 1280x720.
- FPS: 25.
- Frames: 500.

Resultado de `video_analise.py`:

| Clip | Ball visible | PLAY_ANALYZABLE | CLOSE_UP | NO_BALL_VISIBLE | UNKNOWN |
| --- | ---: | ---: | ---: | ---: | ---: |
| clip_05m00s_20s_720p | 203 | 220 | 220 | 10 | 50 |

Observaciones:

- El procesamiento de un clip de 20s en 720p con `imgsz=640` sigue siendo viable en CPU.
- La deteccion del balon mejora respecto al 224p equivalente tras filtrar el logo de TV.
- Las anotaciones deben escalar con la resolucion para seguir siendo legibles.

## Inicio de v2: tracking y metricas

Se inicia v2 con ByteTrack como tracker base.

Decision de implementacion:

- Usar deteccion normal para personas y balon, conservando el comportamiento de v1.
- Ejecutar tracking de personas en una segunda pasada por frame.
- Asociar tracks a detecciones de personas mediante IoU.

Motivo:

- Usar directamente la salida de `track` para todo alteraba el comportamiento del balon y cambiaba demasiado la clasificacion de frames.
- Separar deteccion y tracking mantiene estable la v1 y permite anadir IDs encima.

Metricas generadas:

- resumen de frames;
- conteo de estados;
- frames con balon visible;
- tracks unicos;
- duracion media y maxima de tracks;
- color medio de camiseta por track;
- agrupacion inicial `team_1`/`team_2` por color RGB medio de camiseta;
- metricas frame a frame para futuro panel HTML/CSS/JS.

La comparacion ByteTrack vs BoT-SORT queda como siguiente bloque de v2.

## Comparacion rapida ByteTrack vs BoT-SORT

Se anadio `tools/compare_trackers.py` para ejecutar el mismo clip con varios trackers y comparar las metricas generadas.

Prueba rapida:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/compare_trackers.py --input videos/clips/prepared/clip_05m00s_20s.mp4 --process-every 5
```

Resultado inicial sobre `clip_05m00s_20s.mp4`:

| Tracker | Tracks unicos | Longitud media | Longitud maxima | Tracks >=25 frames |
| --- | ---: | ---: | ---: | ---: |
| ByteTrack | 24 | 13.46 | 74 | 5 |
| BoT-SORT | 28 | 11.54 | 39 | 3 |

Conclusion provisional:

- ByteTrack queda como tracker principal inicial.
- BoT-SORT funciona, pero en esta prueba rapida genera mas IDs y tracks mas cortos.
- Falta una comparacion completa sobre varios clips antes de cerrar la decision.

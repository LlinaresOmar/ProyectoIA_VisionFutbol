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

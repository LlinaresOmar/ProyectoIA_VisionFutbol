# Memoria del proyecto

# Analisis de video de futbol con inteligencia artificial

## 1. Resumen

Este proyecto desarrolla un prototipo de analisis de partidos de futbol mediante vision artificial. El sistema recibe videos de entrada, detecta jugadores y balon, realiza tracking de los jugadores, agrupa equipos de forma aproximada, genera videos anotados y produce informes HTML con metricas del clip analizado.

El punto de partida fue el enunciado original, orientado a obtener informacion deportiva a partir de video. Sin embargo, durante la fase inicial de investigacion se detecto que el primer reto importante no era solamente aplicar un modelo de inteligencia artificial, sino disponer de diferentes tipos de videos y poder probar el sistema en condiciones variadas. En un caso real, un tecnico o emprendedor que quisiera ofrecer analisis deportivo a clubes se encontraria con grabaciones muy distintas: retransmisiones de television, camaras panoramicas, resoluciones diferentes, cambios de iluminacion, deformaciones de lente, personas fuera del campo, balones en la banda o elementos graficos que pueden confundir al detector.

Por este motivo el proyecto no se ha centrado solo en analizar un video concreto, sino en construir un pequeno flujo de trabajo para preparar clips, ejecutar pruebas, comparar resultados y generar una demo tecnica defendible. La solucion final permite analizar una suite mixta de clips, comparar camara panoramica de campo completo frente a retransmision de television y explicar que tipo de fuente es mas adecuada para obtener metricas tacticas.

El resultado obtenido es un prototipo funcional que cumple el objetivo principal de demostrar deteccion, tracking, agrupacion aproximada por equipo y conteo aproximado de pases por equipo. Al mismo tiempo, identifica con claridad las limitaciones actuales y deja planteado un camino de mejora hacia versiones futuras.

## 2. Introduccion y justificacion

Al comenzar el proyecto, la idea inicial podia parecer relativamente directa: tomar un video de futbol, aplicar un modelo de deteccion y extraer informacion como jugadores, balon, pases o eventos relevantes. Sin embargo, al empezar la investigacion se comprobo rapidamente que el problema real es mas amplio.

En vision artificial, el resultado depende mucho de la calidad y del tipo de imagen de entrada. No es lo mismo analizar una retransmision de television, que cambia de plano constantemente, que una grabacion fija donde se ve todo el campo. Tampoco es igual trabajar con un video de baja resolucion que con uno panoramico, con deformacion de lente, con buena iluminacion o con sombras. Por tanto, antes de intentar obtener metricas deportivas complejas, era necesario crear una forma ordenada de probar el sistema con distintos videos.

El caso de uso elegido para orientar el proyecto fue el de un emprendedor con perfil tecnico que quisiera ofrecer servicios reales de analisis deportivo capturados por video. En este escenario, el problema no consiste solo en ejecutar un script, sino en poder llegar a una instalacion deportiva, probar distintas camaras o fuentes de video, ajustar parametros y comprobar que resultados son fiables.

Durante el desarrollo se identificaron dos grandes familias de videos:

- **Retransmision de television**: suele tener buena calidad visual, planos cercanos y movimiento de camara profesional, pero tambien incluye cambios de plano, zooms, primeros planos, grafismos, logotipos, repeticiones o cortes que rompen la continuidad del tracking.
- **Camara panoramica o full-pitch**: permite ver el campo de forma continua y es mas adecuada para tracking, posesion o pases, pero puede tener deformacion optica, jugadores muy pequenos, problemas de perspectiva o elementos del entorno que generan falsos positivos.

En las pruebas aparecieron problemas reales y bastante representativos: el logotipo de una television se confundia con el balon, letras pintadas en el cesped parecian balones, habia balones reales fuera del terreno de juego, personas caminando alrededor del campo y planos cortos donde el sistema no podia mantener una referencia tactica del partido.

Por todo ello, el proyecto evoluciono hacia una idea mas completa: crear no solo un analizador de video, sino tambien un pequeno framework de pruebas que permita comparar fuentes y configuraciones. Esta aproximacion es interesante porque se parece mas a un escenario profesional: no se trata de prometer metricas perfectas con cualquier video, sino de evaluar que entrada permite obtener datos utiles.

## 3. Objetivos del proyecto

El objetivo general del proyecto es desarrollar un prototipo capaz de analizar clips de futbol mediante inteligencia artificial y generar resultados visuales y estadisticos comprensibles.

Los objetivos concretos trabajados han sido:

- Detectar jugadores en los frames del video.
- Detectar el balon con umbrales propios.
- Clasificar si un frame es analizable o no.
- Realizar tracking de jugadores para mantener identificadores en el tiempo.
- Mostrar el `track_id` de los jugadores en el video.
- Agrupar jugadores en dos equipos de forma aproximada usando el color de la camiseta.
- Detectar roles visuales especiales de forma heuristica, como portero o arbitro candidato.
- Asociar el balon al jugador mas cercano cuando sea posible.
- Contar pases aproximados por equipo.
- Generar un video anotado con la informacion principal.
- Exportar metricas en formato JSON.
- Generar informes HTML para revisar cada clip.
- Crear una suite mixta de clips para comparar full-pitch y television.
- Preparar una demo final limpia y reproducible.

Algunos objetivos del enunciado original, como la deteccion fiable de goles o salidas de banda/fondo, se han dejado como evolucion futura. La razon principal es que requieren una calibracion del campo y una fiabilidad de deteccion superior a la alcanzada en esta fase. En lugar de forzar una solucion poco fiable, se ha preferido centrar la entrega en los elementos que se pueden demostrar con mayor claridad.

## 4. Tecnologias utilizadas

El proyecto se ha desarrollado principalmente en Python, utilizando librerias y herramientas habituales en vision artificial.

Las tecnologias principales son:

- **Python**: lenguaje principal del proyecto.
- **OpenCV**: lectura de video, escritura de video, procesamiento de frames y dibujo de anotaciones.
- **Ultralytics YOLO**: modelo de deteccion usado para localizar personas y balon.
- **ByteTrack / BoT-SORT**: trackers disponibles a traves de Ultralytics para mantener identificadores de jugadores en el tiempo.
- **NumPy**: operaciones numericas y manejo de imagenes.
- **PyYAML**: lectura de configuraciones en YAML.
- **FFmpeg**: conversion de los videos finales a H.264/yuv420p para que funcionen correctamente en navegadores.
- **HTML, CSS y JavaScript**: generacion de paneles visuales para revisar resultados.
- **Git y GitHub**: control de versiones, publicacion del repositorio y release final.

El modelo utilizado es un modelo YOLO ya entrenado. En esta fase del proyecto no se ha entrenado un modelo propio. Esto es importante porque el entrenamiento requeriria preparar un dataset con imagenes etiquetadas, dividirlo correctamente en train, validation y test, entrenar el modelo y evaluar sus resultados. Ese proceso queda planteado dentro del roadmap futuro.

## 5. Instalacion y preparacion del entorno

El proyecto esta pensado para ejecutarse en un entorno local de Python. Durante el desarrollo se ha utilizado un entorno Conda llamado `football-ai`.

### 5.1. Descargar el proyecto desde GitHub

El primer paso es clonar el repositorio:

```powershell
git clone https://github.com/LlinaresOmar/ProyectoIA_VisionFutbol.git
cd ProyectoIA_VisionFutbol
```

Tambien puede descargarse el proyecto como ZIP desde GitHub, aunque para desarrollo es recomendable usar Git.

### 5.2. Crear o activar el entorno Python

En el equipo usado durante el desarrollo, el Python del entorno era:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe
```

Para comprobar que el entorno esta funcionando:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe -c "import torch, ultralytics; print(torch.__version__); print(torch.cuda.is_available()); print(ultralytics.__version__)"
```

El proyecto se ha ejecutado principalmente en CPU. Esto hace que los analisis sean mas lentos, pero permite demostrar que el sistema funciona incluso sin una tarjeta grafica dedicada. En un escenario profesional, disponer de GPU NVIDIA con CUDA, o explorar aceleracion mediante OpenVINO en hardware Intel, seria una mejora importante para reducir tiempos de procesamiento.

### 5.3. CPU y GPU

Durante las pruebas se trabajo con un equipo portatil con CPU Intel y grafica integrada Intel UHD. Aunque Windows muestra memoria compartida para la GPU, el cuello de botella principal del proyecto es la inferencia del modelo YOLO. En la configuracion actual, PyTorch no esta usando esa GPU integrada para acelerar la deteccion.

Esto significa que:

- El sistema funciona en CPU.
- Los tiempos de analisis pueden ser altos.
- Para ejecutar muchas pruebas conviene usar clips cortos.
- Una GPU compatible aceleraria mucho el proceso.
- La conversion final de video con FFmpeg no es el principal cuello de botella.

Por esta razon, la suite final usa clips cortos de 10 a 20 segundos. Es una decision practica: permite probar muchos escenarios sin esperar demasiado tiempo.

## 6. Datos y videos utilizados

Una parte importante del proyecto ha sido conseguir y organizar videos de entrada. Se han utilizado varios tipos de fuente:

- Clips preparados de retransmision de television.
- Videos de SoccerNet en distintas calidades.
- Videos panoramicos de campo completo.
- Clips recortados manualmente o mediante scripts.

El proyecto no entrena un modelo propio, por lo que no utiliza todavia un dataset dividido en train, validation y test. Aun asi, esta idea es importante:

- **Train**: datos usados para entrenar un modelo.
- **Validation**: datos usados para ajustar parametros durante el entrenamiento.
- **Test**: datos separados que sirven para evaluar si el modelo generaliza.

En este proyecto se ha trabajado mas bien con una bateria de pruebas o suite de evaluacion. La idea es parecida a un conjunto de test funcional: se eligen clips representativos y se comprueba como se comporta el sistema. Para una version futura, seria muy interesante crear un dataset etiquetado propio con ejemplos de jugadores, balon, porteros, arbitros y eventos.

## 7. Funcionamiento general del sistema

El flujo de trabajo del sistema puede resumirse asi:

1. Se recibe un video de entrada.
2. Se procesa frame a frame.
3. YOLO detecta personas y balon.
4. Se aplican umbrales separados para persona y balon.
5. Se filtran falsos positivos conocidos del balon.
6. Se realiza tracking de jugadores.
7. Se asigna un `track_id` a los jugadores detectados.
8. Se calcula un color medio de camiseta por track.
9. Se agrupan tracks en dos equipos aproximados.
10. Se asocia el balon al jugador mas cercano si esta dentro de un umbral.
11. Se generan eventos aproximados de pase cuando cambia el poseedor dentro del mismo equipo.
12. Se escribe un video anotado.
13. Se genera un JSON con metricas.
14. Se genera un panel HTML para revisar resultados.

El video anotado incluye marcas visuales sobre jugadores, balon, estado del frame, pases acumulados y posesion estimada. Para mejorar la claridad visual, las etiquetas de jugadores muestran solo el identificador `#track_id`, evitando mostrar continuamente la confianza de cada deteccion.

## 8. Configuracion del sistema

El sistema es configurable porque durante el desarrollo se vio que no existe una unica configuracion valida para todos los videos. Algunos parametros importantes son:

- Tamano de entrada del modelo (`imgsz`).
- Confianza minima del modelo.
- Confianza minima para personas.
- Confianza minima para balon.
- Tracker utilizado.
- Numero minimo de jugadores para considerar un frame analizable.
- Ratio minimo de cesped.
- Umbral para detectar primeros planos.
- Zonas ignoradas donde no debe aceptarse el balon.
- Polilineas para excluir zonas fuera del terreno de juego.
- Transparencia y posicion de etiquetas.

Esta configuracion es clave para un caso real. Un tecnico que instalase camaras en distintos campos se encontraria con condiciones muy variables: distinta altura de camara, distinta iluminacion, cesped natural o artificial, sombras, publicidad, personas fuera del campo, banquillos, balones en la banda o marcas en el suelo. En el proyecto se han observado varios de estos problemas de forma practica.

Un ejemplo claro fue una letra pintada en el campo, dentro del texto "University of Tsukuba", que se confundia con un balon. Otro ejemplo fue el logotipo de una cadena de television en la esquina inferior derecha, que tambien generaba falsos positivos. Estos casos justifican que el sistema tenga filtros configurables por regiones y por tipo de fuente.

## 9. Tracking, equipos y pases

Una mejora importante respecto a una deteccion simple es el tracking. Detectar personas en cada frame permite saber que hay jugadores, pero no permite saber si el jugador de un frame es el mismo que aparece unos segundos despues. Para obtener metricas deportivas es necesario mantener una identidad temporal.

El proyecto utiliza trackers como ByteTrack o BoT-SORT para asignar un `track_id` a los jugadores. Esto permite mostrar etiquetas como `#12` y calcular metricas como:

- cuantos frames se ha visto un jugador;
- que distancia aproximada ha recorrido en pixeles;
- que color medio de camiseta tiene;
- que jugador estaba cerca del balon;
- si un posible pase ha ido de un track a otro.

La agrupacion de equipos se hace de forma heuristica mediante el color medio de la camiseta. El sistema intenta separar los tracks en `team_1` y `team_2`. No es perfecto, pero permite construir una primera aproximacion al conteo de pases por equipo.

El conteo de pases tambien es aproximado. El sistema busca el jugador mas cercano al balon y considera que existe un pase candidato cuando el poseedor cambia a otro jugador del mismo equipo dentro de una ventana temporal plausible. Esto no equivale a una deteccion profesional de pases, pero permite demostrar el flujo completo: deteccion, tracking, asociacion balon-jugador y generacion de eventos.

## 10. Comparacion de fuentes: television frente a full-pitch

Uno de los resultados mas importantes del proyecto es la comparacion entre distintos tipos de video.

La retransmision de television es visualmente atractiva y suele tener buena resolucion, pero no esta pensada para analisis tactico automatico. Cambia de plano, enfoca a jugadores concretos, muestra repeticiones, realiza zooms y pierde la continuidad de todos los jugadores del campo. Esto provoca que los tracks se fragmenten y que el sistema no pueda mantener una vision estable del partido.

La camara panoramica de campo completo es menos espectacular visualmente, pero resulta mucho mas util para metricas tacticas. Al ver el campo de forma continua, el sistema puede seguir mas jugadores a la vez y mantener mejor el contexto del juego. Por eso, en la demo final, los clips full-pitch son los mas adecuados para defender tracking y pases aproximados.

La conclusion es que no todos los videos sirven para todo. La television puede servir para demostrar deteccion visual basica, pero una instalacion profesional que busque metricas tacticas deberia utilizar camaras fijas, elevadas y calibradas.

## 11. Suite final de pruebas

Para ordenar las pruebas se creo una suite mixta definida en `config/clip_suite.yaml`. Esta suite incluye clips full-pitch y clips de retransmision TV. Cada clip tiene un objetivo concreto, por ejemplo:

- balon visible en campo;
- control de falsos positivos;
- camara panoramica con deformacion;
- plano general de television;
- zona de area o porteria;
- cambio de camara;
- falso positivo historico del logo de TV;
- primer plano.

La suite se ejecuta con:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/run_clip_suite.py `
  --suite config/clip_suite.yaml `
  --output-dir videos/output/final_demo `
  --clips-dir videos/clips/final_demo `
  --overwrite
```

La salida principal es:

```text
videos/output/final_demo/index.html
```

Este indice HTML permite navegar por los resultados de la demo final. Ademas, cada clip tiene:

- video anotado;
- JSON de metricas;
- informe HTML propio;
- conclusion automatica;
- datos de balon visible, tracks, frames analizables y pases.

Tambien se genero una herramienta de contact sheets:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/create_contact_sheet.py `
  --input videos/output/final_demo `
  --output-dir videos/output/final_demo/contact_sheets `
  --overwrite
```

Estas imagenes permiten ver de un vistazo varios momentos de cada video sin tener que reproducirlo completo.

## 12. Herramientas desarrolladas

Ademas del script principal de analisis, durante el proyecto se han creado varias herramientas auxiliares. Esta parte es importante porque el resultado final no depende solo de un modelo de IA, sino de un flujo completo de trabajo.

Las herramientas principales son:

- `video_analise.py`: script principal. Analiza un clip, detecta personas y balon, aplica tracking, genera el video anotado y exporta metricas JSON.
- `tools/run_clip_suite.py`: ejecuta una suite completa de clips definidos en YAML. Es la herramienta central de la demo final porque permite comparar fuentes de video diferentes de forma repetible.
- `tools/create_video_clips.py`: permite recortar clips cortos desde videos largos. Fue util para generar pruebas rapidas sin procesar partidos completos.
- `tools/generate_report_panel.py`: convierte un JSON de metricas en un informe HTML visual.
- `tools/create_contact_sheet.py`: genera mosaicos de imagenes a partir de los videos anotados. Sirve para revisar de un vistazo si una salida es buena o no.
- `tools/run_full_pitch_test_batch.py`: permite ejecutar baterias de pruebas sobre videos panoramicos y comparar configuraciones.
- `tools/compare_trackers.py`: herramienta de apoyo para comparar trackers como ByteTrack y BoT-SORT.
- `tools/serve_output.py`: levanta un servidor local para abrir los informes HTML y reproducir los videos desde Chrome sin problemas de seguridad del protocolo `file://`.

Estas herramientas hacen que el proyecto sea mas facil de probar, repetir y explicar. En lugar de tener una unica ejecucion manual, se puede lanzar una suite completa, revisar resultados, generar paneles y preparar capturas para la memoria o la defensa.

### 12.1. Contact sheets

Los contact sheets son imagenes compuestas por varios frames del mismo video. En este proyecto se usan para revisar rapidamente los videos anotados sin tener que reproducir cada clip completo.

Por ejemplo, para un video de salida se toman varios frames repartidos a lo largo del clip y se colocan en una unica imagen. Esto permite comprobar rapidamente:

- si los jugadores aparecen marcados;
- si el balon se detecta;
- si las etiquetas son legibles;
- si hay falsos positivos;
- si un clip de television cambia mucho de plano;
- si una camara panoramica mantiene mejor la continuidad.

En la demo final se generaron contact sheets para los 8 videos analizados. Estan en:

```text
videos/output/final_demo/contact_sheets
```

**Captura recomendada para la memoria:** insertar aqui una imagen de contact sheet full-pitch, por ejemplo:

```text
videos/output/final_demo/contact_sheets/full_pitch_128058_ball_visible_analysed_contact_sheet.jpg
```

**Captura recomendada para comparar:** insertar tambien una contact sheet de television, por ejemplo:

```text
videos/output/final_demo/contact_sheets/tv_720_camera_change_analysed_contact_sheet.jpg
```

Esta comparacion visual ayuda a explicar por que la fuente full-pitch es mas estable para metricas tacticas, mientras que la television sirve mejor para deteccion visual puntual.

## 13. Artefactos generados

La ejecucion del sistema genera varios artefactos:

- **Videos anotados**: muestran detecciones, identificadores, balon y contadores.
- **JSON de metricas**: contienen datos estructurados para cada clip.
- **Paneles HTML**: presentan las metricas de forma visual.
- **Indice comparativo**: resume todos los clips de la suite.
- **Contact sheets**: mosaicos de imagenes para revisar rapidamente los resultados.

Los videos finales se convierten a H.264/yuv420p para que puedan reproducirse correctamente en navegadores como Chrome. Esto fue necesario porque OpenCV genera inicialmente MP4 con codec `mp4v`, que no siempre se reproduce bien desde un informe HTML.

Para abrir la demo final mediante servidor local:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/serve_output.py `
  --directory videos/output/final_demo
```

Despues se puede acceder desde:

```text
http://127.0.0.1:8765/index.html
```

### 13.1. Capturas recomendadas de artefactos

Para que la memoria no sea solo texto, se recomienda insertar varias capturas de pantalla de la demo final. Las capturas mas utiles serian:

1. **Indice comparativo final**

   Archivo:

   ```text
   videos/output/final_demo/index.html
   ```

   Esta captura permite mostrar que el proyecto compara varios clips y fuentes de video en un unico panel.

2. **Panel HTML de un clip full-pitch**

   Ejemplo:

   ```text
   videos/output/final_demo/full_pitch_events/reports/full_pitch_128058_ball_visible_report.html
   ```

   Esta captura muestra metricas como frames analizables, balon visible, tracks, equipos y pases candidatos.

3. **Panel HTML de un clip de television**

   Ejemplo:

   ```text
   videos/output/final_demo/tv_detection/reports/tv_720_camera_change_report.html
   ```

   Sirve para explicar que la television puede detectar jugadores y balon, pero no mantiene igual de bien la continuidad tactica.

4. **Frame de video anotado**

   Puede capturarse desde cualquier MP4 de `videos/output/final_demo`. Lo ideal es elegir un frame donde se vean varios jugadores con `#track_id`, el balon y los contadores de pases.

5. **Contact sheet**

   Una contact sheet resume visualmente un clip completo y es especialmente util para el tribunal porque permite entender el comportamiento del sistema de un vistazo.

## 14. Resultados obtenidos

El proyecto consigue generar una demo final con varios clips de prueba. En los videos panoramicos se observa mejor continuidad de jugadores y mayor utilidad para eventos tacticos. En los videos de television se detectan jugadores y balon en muchos frames, pero la estabilidad de los tracks es menor y por tanto las metricas tacticas son menos fiables.

Los resultados confirman la hipotesis principal del proyecto: la fuente de video condiciona enormemente lo que se puede medir. No basta con tener un buen detector. Para obtener datos deportivos utiles es necesario controlar la captura, usar una camara adecuada y ajustar parametros segun el entorno.

El sistema tambien consigue mostrar pases aproximados por equipo. Esta parte debe interpretarse como una prueba de concepto, no como una estadistica oficial. Aun asi, es suficiente para demostrar que el pipeline puede evolucionar hacia metricas deportivas mas avanzadas.

Una forma sencilla de presentar los resultados en la defensa es apoyarse en tres elementos visuales:

- el indice final, para mostrar la comparacion global;
- un video full-pitch, para mostrar tracking y pases;
- un video de television, para mostrar las limitaciones de una fuente con cambios de plano.

De este modo, el tribunal puede ver tanto lo que el sistema hace bien como las razones tecnicas por las que algunos escenarios son mas dificiles.

## 15. Limitaciones

El proyecto tiene varias limitaciones importantes:

- No se ha entrenado un modelo propio.
- La deteccion del balon puede fallar con objetos parecidos.
- El arbitro y el portero se detectan solo de forma heuristica.
- La agrupacion por equipos depende del color de camiseta y puede confundirse.
- Los pases son candidatos aproximados, no eventos confirmados.
- No existe calibracion metrica real del campo.
- Las distancias recorridas se calculan en pixeles, no en metros.
- La television no permite tracking tactico estable por sus cambios de plano.
- No se han implementado goles ni salidas de campo/fondo.

Estas limitaciones no invalidan el proyecto. Al contrario, ayudan a explicar que se ha construido un prototipo realista y que se han identificado claramente los pasos necesarios para convertirlo en una solucion mas robusta.

## 16. Roadmap futuro

Las mejoras futuras mas importantes serian:

- Crear un dataset propio etiquetado.
- Separar datos de train, validation y test.
- Entrenar o ajustar un modelo especifico para futbol.
- Mejorar la deteccion del balon.
- Entrenar clases especificas para arbitro y portero.
- Mejorar la asociacion balon-jugador.
- Calibrar el campo para convertir pixeles en metros.
- Calcular distancias recorridas reales.
- Mejorar el conteo de pases con validacion temporal y espacial.
- Detectar goles y salidas de campo.
- Integrar varias camaras fijas en una instalacion real.
- Crear una interfaz para que un tecnico pueda ajustar parametros sin tocar codigo.

En un escenario profesional, la instalacion ideal seria una o varias camaras fijas elevadas, con vision continua del campo, calibracion por instalacion y una fase previa de pruebas con clips cortos. Este proyecto ya deja preparada la parte de evaluacion y comparacion que permitiria elegir la mejor configuracion para cada campo.

## 17. Conclusion

El proyecto ha permitido desarrollar un prototipo completo de analisis de futbol mediante vision artificial. La solucion no se limita a ejecutar un modelo de deteccion, sino que construye un flujo de trabajo completo: preparacion de clips, analisis automatico, tracking, agrupacion de equipos, conteo aproximado de pases, generacion de videos anotados e informes HTML.

La principal conclusion es que la calidad y el tipo de fuente de video son decisivos. Las retransmisiones de television son utiles para deteccion visual, pero no son la mejor opcion para metricas tacticas estables. Las grabaciones panoramicas de campo completo, aunque tengan sus propios problemas, son mucho mas adecuadas para seguir jugadores y analizar eventos.

Desde el punto de vista tecnico, el proyecto demuestra integracion de inteligencia artificial, procesamiento de video, configuracion por YAML, generacion de informes, control de versiones y publicacion en GitHub. Desde el punto de vista practico, plantea una aproximacion realista para un futuro servicio de analisis deportivo basado en video.

Por tanto, el valor principal del proyecto no esta solo en las metricas obtenidas, sino en haber construido una base funcional y evaluable sobre la que se pueden seguir desarrollando nuevas capacidades.

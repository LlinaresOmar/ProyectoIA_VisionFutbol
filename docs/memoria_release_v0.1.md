# Nota de entrega v0.1

La release `v0.1` publicada en GitHub contiene el codigo del proyecto y un ZIP con la demo final generada localmente.

Release:

```text
https://github.com/LlinaresOmar/ProyectoIA_VisionFutbol/releases/tag/v0.1
```

Asset principal:

```text
football-ai-analysis-final-demo-v0.1.zip
```

El ZIP incluye:

- `index.html` de la demo final;
- videos anotados;
- informes HTML por clip;
- JSON de metricas;
- contact sheets;
- manifest de ejecucion.

Para reproducir la demo desde el codigo fuente, ejecutar:

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools/run_clip_suite.py `
  --suite config/clip_suite.yaml `
  --output-dir videos/output/final_demo `
  --clips-dir videos/clips/final_demo `
  --overwrite
```

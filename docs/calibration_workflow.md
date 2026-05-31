# Full-pitch calibration workflow

The final objective is to extract useful match events from real installations:

- team-level passes;
- possession approximations;
- goals and possible goal events;
- visible overlays in the analysed video.

Full-pitch calibration must therefore optimize the components that feed those
events, not only the visual look of detections.

## Recommended workflow

1. Record or download several full-pitch videos from the real camera setup.
2. Place the source videos in `videos/input/test`.
3. Generate uniformly distributed clips with the batch runner.
4. Reuse the same clips across a fixed experiment matrix.
5. Compare profile-specific metrics:
   - player/tracking profile for player continuity and team memory;
   - ball profile for ball visibility and stable ball motion.
6. Review the best candidate videos manually.
7. Promote the best settings into a named field/camera preset.

## Current execution pattern

```powershell
C:\Users\javie\miniconda3\envs\football-ai\python.exe tools\run_full_pitch_test_batch.py `
  --input-dir videos\input\test `
  --video-glob "128058*.mp4" `
  --clips-per-video 3 `
  --duration 10 `
  --experiment-config config\full_pitch_experiments.yaml `
  --continue-on-error
```

Without `--experiment-config`, the script keeps the previous single-run behavior.
Use `--exclude-video-glob "117093*"` when running a broader directory but
excluding the calibrated/flattened input that is too far away for the current
detector.

The batch runner writes:

- `index.html` with a global ranking by profile and clip-level details;
- `comparison_ranking.json` with the aggregate ranking in machine-readable form;
- one annotated video per clip and experiment;
- one stats JSON per clip and experiment;
- one panel HTML per clip and experiment.

For the current CPU-only laptop workflow, prefer short calibration clips first:
10 seconds, 3 clips per useful source video, and the CPU-friendly matrix in
`config/full_pitch_experiments.yaml`. Longer clips and larger image sizes should
be reserved for final verification on the best camera/source.

## Metrics that matter

For player and team tracking:

- median detected players per frame;
- percentage of frames near the expected 20-22 players;
- number of long tracks;
- average track length;
- excessive track fragmentation;
- team balance and stable team color assignment.

For the ball:

- percentage of frames with visible ball;
- longest gaps without ball;
- impossible jumps between ball positions;
- false positives in static visual regions;
- continuity near likely player possession.

For passes and goals later:

- ball-player association stability;
- team assigned to the possessing player;
- possession changes with plausible ball movement;
- ball entering or crossing configured goal-mouth zones.

## Blind spots

The current local Python environment uses PyTorch CPU only and OpenCV without
OpenVINO. The Intel UHD GPU is therefore not accelerating YOLO inference. Video
decode/encode acceleration may help later through FFmpeg Quick Sync or OpenVINO,
but the main bottleneck during experiments is model inference, not MP4 writing.

The expected 20-22 player count is a strong heuristic, not ground truth. Real
full-pitch video can include occlusions, players outside the visible area,
assistant referees, substitutes, goalkeepers that are tiny in the frame, and
non-player staff near the pitch.

Ball visibility near 100% is also not always correct. The ball can be hidden,
motion-blurred, outside the frame, or visually merged with pitch lines. A
configuration that reports the ball in every frame can still be worse if it
creates many false positives or impossible jumps.

Team-colored annotations now support an optional two-pass mode. The first pass
collects detections, tracking, jersey color summaries, and team clusters. The
second pass reopens the same video and renders team overlays:

- `team_1`: blue marker;
- `team_2`: red marker;
- unassigned or non-team tracks: white marker.

This is still an approximation for referees. A true referee class should be
added later using either manual calibration, color outlier logic, or a small
classifier trained on referee kits.

## Next implementation blocks

1. Add referee handling as a third visual class, initially based on team-color
   outliers and later improved with manual calibration or a small classifier.
2. Add field/camera presets for real installations.
3. Add v3 ball-player association metrics that directly support passes and
   possession.

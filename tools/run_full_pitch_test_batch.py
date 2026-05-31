"""Prepare and analyze a reproducible full-pitch test batch."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path

import cv2
import yaml

from create_video_clips import cut_clip, parse_time


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class SourceVideo:
    path: str
    fps: float
    frames: int
    width: int
    height: int
    duration_seconds: float


@dataclass
class ClipArtifact:
    experiment: str
    profile: str
    source: str
    start_seconds: float
    clip: str
    analysed_video: str
    stats_json: str
    report_html: str


def video_metadata(path: Path) -> SourceVideo:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture.release()

    return SourceVideo(
        path=str(path),
        fps=float(fps),
        frames=frames,
        width=width,
        height=height,
        duration_seconds=float(frames / fps) if fps else 0.0,
    )


def auto_starts(duration_seconds: float, clip_duration: float, clips_per_video: int) -> list[float]:
    if clips_per_video <= 0:
        return []

    latest_start = max(0.0, duration_seconds - clip_duration)
    if clips_per_video == 1:
        return [min(latest_start, max(0.0, duration_seconds * 0.5 - clip_duration * 0.5))]

    # Avoid the very first and last seconds when possible, because many videos
    # have overlays, fades, or dead time around the edges.
    low = min(latest_start, 60.0)
    high = max(low, latest_start - min(60.0, latest_start * 0.1))
    if high <= low:
        low = 0.0
        high = latest_start

    step = (high - low) / (clips_per_video - 1)
    return [round(low + index * step, 2) for index in range(clips_per_video)]


def safe_stem(path: Path) -> str:
    return path.stem.replace(" ", "_")


def run_command(command: list[str], dry_run: bool, continue_on_error: bool = False) -> tuple[bool, str | None]:
    print("$ " + " ".join(command))
    if dry_run:
        return True, None
    try:
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        error = f"Command failed with exit code {exc.returncode}"
        if continue_on_error:
            print(f"WARNING: {error}")
            return False, error
        raise
    return True, None


def slugify(value: str) -> str:
    cleaned = []
    for char in value.lower():
        if char.isalnum():
            cleaned.append(char)
        elif char in {"-", "_"}:
            cleaned.append(char)
        else:
            cleaned.append("_")
    return "".join(cleaned).strip("_") or "experiment"


def load_experiments(args: argparse.Namespace) -> list[dict]:
    if args.experiment_config is None:
        return [
            {
                "name": "single",
                "profile": "manual",
                "model": args.model,
                "imgsz": args.imgsz,
                "model_conf": args.model_conf,
                "person_conf": args.person_conf,
                "ball_conf": args.ball_conf,
                "tracker": args.tracker,
                "process_every": args.process_every,
                "min_green_ratio": args.min_green_ratio,
                "min_players_for_play_frame": args.min_players_for_play_frame,
                "max_person_area_ratio_for_closeup": args.max_person_area_ratio_for_closeup,
                "team_render_mode": args.team_render_mode,
                "web_video": True,
            }
        ]

    config_path = (PROJECT_ROOT / args.experiment_config).resolve()
    with config_path.open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}

    experiments = payload.get("experiments", [])
    if not experiments:
        raise ValueError(f"No experiments found in {config_path}")

    normalized = []
    for index, experiment in enumerate(experiments, start=1):
        item = {
            "name": experiment.get("name") or f"experiment_{index}",
            "profile": experiment.get("profile") or "mixed",
            "model": experiment.get("model", args.model),
            "imgsz": experiment.get("imgsz", args.imgsz),
            "model_conf": experiment.get("model_conf", args.model_conf),
            "person_conf": experiment.get("person_conf", args.person_conf),
            "ball_conf": experiment.get("ball_conf", args.ball_conf),
            "tracker": experiment.get("tracker", args.tracker),
            "process_every": experiment.get("process_every", args.process_every),
            "min_green_ratio": experiment.get("min_green_ratio", args.min_green_ratio),
            "min_players_for_play_frame": experiment.get(
                "min_players_for_play_frame",
                args.min_players_for_play_frame,
            ),
            "max_person_area_ratio_for_closeup": experiment.get(
                "max_person_area_ratio_for_closeup",
                args.max_person_area_ratio_for_closeup,
            ),
            "team_render_mode": experiment.get("team_render_mode", args.team_render_mode),
            "web_video": experiment.get("web_video", True),
        }
        normalized.append(item)

    if args.experiment_limit is not None:
        normalized = normalized[: args.experiment_limit]
    return normalized


def experiment_arg(command: list[str], option: str, value) -> None:
    if value is None:
        return
    command.extend([option, str(value)])


def experiment_bool_arg(command: list[str], option: str, value) -> None:
    if value is None:
        return
    command.append(option if bool(value) else f"--no-{option.removeprefix('--')}")


def exclude_videos(videos: list[Path], patterns: list[str]) -> list[Path]:
    if not patterns:
        return videos

    selected = []
    for video in videos:
        if any(fnmatch.fnmatch(video.name, pattern) for pattern in patterns):
            continue
        selected.append(video)
    return selected


def relative_link(target: Path, base_dir: Path) -> str:
    return Path(os.path.relpath(target.resolve(), base_dir.resolve())).as_posix()


def load_summary(stats_path: Path) -> dict:
    if not stats_path.exists():
        return {}
    with stats_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data.get("summary", {})


def load_stats(stats_path: Path) -> dict:
    if not stats_path.exists():
        return {}
    with stats_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def longest_false_streak(values: list[bool]) -> int:
    longest = 0
    current = 0
    for value in values:
        if value:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def comparison_metrics(stats_path: Path, expected_min: int, expected_max: int) -> dict:
    stats = load_stats(stats_path)
    summary = stats.get("summary", {})
    frames = stats.get("frames", [])
    frames_analyzed = int(summary.get("frames_analyzed", 0))
    ball_frames = int(summary.get("ball_visible_frames", 0))

    persons = [int(frame.get("persons", 0)) for frame in frames]
    avg_persons = sum(persons) / len(persons) if persons else 0.0
    expected_frames = sum(expected_min <= value <= expected_max for value in persons)
    expected_pct = (expected_frames / len(persons)) * 100 if persons else 0.0

    ball_visible = [bool(frame.get("ball_visible", False)) for frame in frames]
    ball_pct = (ball_frames / frames_analyzed) * 100 if frames_analyzed else 0.0
    longest_ball_gap = longest_false_streak(ball_visible)
    longest_ball_gap_pct = (longest_ball_gap / frames_analyzed) * 100 if frames_analyzed else 100.0

    avg_track_length = float(summary.get("avg_track_length_frames", 0.0))
    track_score = min(100.0, (avg_track_length / max(1, frames_analyzed * 0.35)) * 100)
    player_score = (expected_pct * 0.65) + (track_score * 0.35)
    ball_score = (ball_pct * 0.80) + ((100.0 - longest_ball_gap_pct) * 0.20)

    return {
        "avg_persons": avg_persons,
        "expected_players_pct": expected_pct,
        "ball_pct": ball_pct,
        "longest_ball_gap_frames": longest_ball_gap,
        "player_score": player_score,
        "ball_score": ball_score,
    }


def profile_score(profile: str, metrics: dict) -> float:
    if profile == "ball_detection":
        return metrics["ball_score"]
    if profile == "player_tracking":
        return metrics["player_score"]
    return (metrics["player_score"] + metrics["ball_score"]) / 2


def mean(values: list[float]) -> float:
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else 0.0


def ranked_experiments(
    artifacts: list[dict],
    expected_players_min: int,
    expected_players_max: int,
) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for artifact in artifacts:
        key = (artifact.get("experiment", "-"), artifact.get("profile", "-"))
        metrics = comparison_metrics(
            Path(artifact["stats_json"]),
            expected_players_min,
            expected_players_max,
        )
        groups.setdefault(key, []).append(metrics)

    rows = []
    for (experiment, profile), metrics_list in groups.items():
        player_score = mean([item["player_score"] for item in metrics_list])
        ball_score = mean([item["ball_score"] for item in metrics_list])
        score = profile_score(
            profile,
            {"player_score": player_score, "ball_score": ball_score},
        )
        rows.append(
            {
                "experiment": experiment,
                "profile": profile,
                "clips": len(metrics_list),
                "score": round(score, 2),
                "player_score": round(player_score, 2),
                "ball_score": round(ball_score, 2),
                "avg_persons": round(mean([item["avg_persons"] for item in metrics_list]), 2),
                "expected_players_pct": round(
                    mean([item["expected_players_pct"] for item in metrics_list]),
                    2,
                ),
                "ball_pct": round(mean([item["ball_pct"] for item in metrics_list]), 2),
                "longest_ball_gap_frames": round(
                    mean([item["longest_ball_gap_frames"] for item in metrics_list]),
                    2,
                ),
            }
        )

    return sorted(rows, key=lambda item: item["score"], reverse=True)


def write_index(
    artifacts: list[dict],
    reports_dir: Path,
    expected_players_min: int,
    expected_players_max: int,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    index_path = reports_dir / "index.html"
    rows = []
    ranking = ranked_experiments(
        artifacts,
        expected_players_min,
        expected_players_max,
    )
    ranking_path = reports_dir / "comparison_ranking.json"
    ranking_path.write_text(json.dumps(ranking, indent=2), encoding="utf-8")
    ranking_rows = []

    for artifact in artifacts:
        clip_path = Path(artifact["clip"])
        analysed_path = Path(artifact["analysed_video"])
        stats_path = Path(artifact["stats_json"])
        report_path = Path(artifact["report_html"])
        summary = load_summary(stats_path)
        metrics = comparison_metrics(
            stats_path,
            expected_players_min,
            expected_players_max,
        )
        statuses = ", ".join(
            f"{key}: {value}" for key, value in summary.get("status_counts", {}).items()
        )
        profile = artifact.get("profile", "-")
        score = profile_score(profile, metrics)

        rows.append(
            f"""
            <tr>
              <td>{escape(artifact.get("experiment", "-"))}</td>
              <td>{escape(profile)}</td>
              <td>{escape(clip_path.stem)}</td>
              <td>{artifact["start_seconds"]:.0f}s</td>
              <td>{summary.get("unique_player_tracks", "-")}</td>
              <td>{metrics["avg_persons"]:.1f}</td>
              <td>{metrics["expected_players_pct"]:.1f}%</td>
              <td>{metrics["ball_pct"]:.1f}%</td>
              <td>{score:.1f}</td>
              <td>{escape(statuses or "-")}</td>
              <td><a href="{relative_link(analysed_path, reports_dir)}" target="_blank" rel="noopener">video</a></td>
              <td><a href="{relative_link(report_path, reports_dir)}" target="_blank" rel="noopener">panel</a></td>
              <td><a href="{relative_link(stats_path, reports_dir)}" target="_blank" rel="noopener">json</a></td>
            </tr>
            """
        )

    for index, item in enumerate(ranking, start=1):
        ranking_rows.append(
            f"""
            <tr>
              <td>{index}</td>
              <td>{escape(item["experiment"])}</td>
              <td>{escape(item["profile"])}</td>
              <td>{item["clips"]}</td>
              <td>{item["score"]:.1f}</td>
              <td>{item["player_score"]:.1f}</td>
              <td>{item["ball_score"]:.1f}</td>
              <td>{item["avg_persons"]:.1f}</td>
              <td>{item["expected_players_pct"]:.1f}%</td>
              <td>{item["ball_pct"]:.1f}%</td>
              <td>{item["longest_ball_gap_frames"]:.1f}</td>
            </tr>
            """
        )

    index_path.write_text(
        f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Full Pitch Test Batch</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #f7f7f4;
      color: #191919;
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 20px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    p {{
      margin: 0 0 24px;
      color: #626262;
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 20px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid #deded6;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #ecece5;
      text-align: left;
      font-size: 14px;
      vertical-align: top;
    }}
    th {{
      background: #efefe8;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    a {{
      color: #176b5d;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Full Pitch Test Batch</h1>
    <p>Resumen navegable de clips panoramicos procesados con video_analise.py v2.</p>
    <h2>Ranking global por perfil</h2>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Experimento</th>
          <th>Perfil</th>
          <th>Clips</th>
          <th>Score perfil</th>
          <th>Score jugadores</th>
          <th>Score balon</th>
          <th>Jugadores media</th>
          <th>Frames {expected_players_min}-{expected_players_max}</th>
          <th>Balon visible</th>
          <th>Gap balon medio</th>
        </tr>
      </thead>
      <tbody>
        {''.join(ranking_rows)}
      </tbody>
    </table>
    <h2>Detalle por clip</h2>
    <table>
      <thead>
        <tr>
          <th>Experimento</th>
          <th>Perfil</th>
          <th>Clip</th>
          <th>Inicio</th>
          <th>Tracks</th>
          <th>Jugadores media</th>
          <th>Frames {expected_players_min}-{expected_players_max}</th>
          <th>Balon visible</th>
          <th>Score perfil</th>
          <th>Estados</th>
          <th>Video</th>
          <th>Panel</th>
          <th>Stats</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return index_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Cut several fixed-duration clips from full-pitch videos, analyze them, "
            "and generate one HTML report panel per clip."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("videos/input/test"),
        help="Directory with source MP4 videos.",
    )
    parser.add_argument(
        "--video-glob",
        default="*.mp4",
        help="Glob pattern for source videos inside input-dir. Defaults to *.mp4.",
    )
    parser.add_argument(
        "--exclude-video-glob",
        action="append",
        default=[],
        help="Exclude source videos by filename glob. Can be repeated.",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=None,
        help="Limit how many source videos are used after sorting by filename.",
    )
    parser.add_argument(
        "--clips-dir",
        type=Path,
        default=Path("videos/clips/full_pitch_test"),
        help="Directory where extracted clips will be written.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("videos/output/full_pitch_test"),
        help="Directory where analysed videos will be written.",
    )
    parser.add_argument(
        "--stats-dir",
        type=Path,
        default=Path("videos/output/full_pitch_test/stats"),
        help="Directory where stats JSON files will be written.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("videos/output/full_pitch_test/reports"),
        help="Directory where HTML report panels will be written.",
    )
    parser.add_argument(
        "--duration",
        type=parse_time,
        default=30.0,
        help="Clip duration. Defaults to 30 seconds.",
    )
    parser.add_argument(
        "--clips-per-video",
        type=int,
        default=3,
        help="Number of automatically spaced clips per source video.",
    )
    parser.add_argument(
        "--starts",
        nargs="+",
        type=parse_time,
        default=None,
        help="Optional explicit starts applied to every video.",
    )
    parser.add_argument(
        "--process-every",
        type=int,
        default=1,
        help="Forwarded to video_analise.py. Defaults to every frame.",
    )
    parser.add_argument(
        "--model",
        default="yolo26n.pt",
        help="YOLO model path passed to video_analise.py.",
    )
    parser.add_argument(
        "--model-conf",
        type=float,
        default=0.05,
        help="Minimum model inference confidence passed to video_analise.py.",
    )
    parser.add_argument(
        "--person-conf",
        type=float,
        default=0.25,
        help="Minimum person confidence passed to video_analise.py.",
    )
    parser.add_argument(
        "--ball-conf",
        type=float,
        default=0.10,
        help="Minimum ball confidence passed to video_analise.py.",
    )
    parser.add_argument(
        "--tracker",
        default="bytetrack.yaml",
        help="Tracker passed to video_analise.py.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="YOLO image size passed to video_analise.py.",
    )
    parser.add_argument(
        "--min-green-ratio",
        type=float,
        default=0.35,
        help="Minimum field green ratio passed to video_analise.py.",
    )
    parser.add_argument(
        "--min-players-for-play-frame",
        type=int,
        default=4,
        help="Minimum detected players for PLAY_ANALYZABLE.",
    )
    parser.add_argument(
        "--max-person-area-ratio-for-closeup",
        type=float,
        default=0.25,
        help="Close-up threshold passed to video_analise.py.",
    )
    parser.add_argument(
        "--team-render-mode",
        choices=["single-pass", "two-pass"],
        default="single-pass",
        help="How video_analise.py renders team colors in the output video.",
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=None,
        help="Optional YAML matrix with algorithm configurations to test.",
    )
    parser.add_argument(
        "--experiment-limit",
        type=int,
        default=None,
        help="Limit how many experiments from the YAML matrix are executed.",
    )
    parser.add_argument(
        "--expected-players-min",
        type=int,
        default=18,
        help="Lower bound for the expected full-pitch player count metric.",
    )
    parser.add_argument(
        "--expected-players-max",
        type=int,
        default=24,
        help="Upper bound for the expected full-pitch player count metric.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("videos/output/full_pitch_test/manifest.json"),
        help="Manifest path for source and artifact metadata.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate clips, analysed videos, stats, and reports if they exist.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with the next experiment if one analysis command fails.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned work without creating or processing files.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_dir = (PROJECT_ROOT / args.input_dir).resolve()
    videos = sorted(input_dir.glob(args.video_glob))
    videos = exclude_videos(videos, args.exclude_video_glob)
    if args.max_videos is not None:
        videos = videos[: args.max_videos]
    if not videos:
        raise FileNotFoundError(f"No videos matching {args.video_glob} found in {input_dir}")

    experiments = load_experiments(args)
    use_experiment_dirs = args.experiment_config is not None

    manifest = {
        "settings": {
            "duration_seconds": args.duration,
            "clips_per_video": args.clips_per_video,
            "starts": args.starts,
            "video_glob": args.video_glob,
            "exclude_video_glob": args.exclude_video_glob,
            "max_videos": args.max_videos,
            "experiment_config": str(args.experiment_config) if args.experiment_config else None,
            "expected_players_min": args.expected_players_min,
            "expected_players_max": args.expected_players_max,
            "continue_on_error": args.continue_on_error,
        },
        "experiments": experiments,
        "sources": [],
        "artifacts": [],
        "failures": [],
    }

    for source in videos:
        metadata = video_metadata(source)
        manifest["sources"].append(asdict(metadata))
        starts = args.starts or auto_starts(
            metadata.duration_seconds,
            args.duration,
            args.clips_per_video,
        )

        source_stem = safe_stem(source)
        for start_seconds in starts:
            clip_prefix = f"{source_stem}_clip"
            clip_path = (
                PROJECT_ROOT
                / args.clips_dir
                / f"{clip_prefix}_{int(round(start_seconds)):04d}s_{int(args.duration)}s.mp4"
            )

            if args.overwrite or not clip_path.exists():
                print(f"Cutting {clip_path.name}")
                if not args.dry_run:
                    generated = cut_clip(
                        source=source,
                        output_dir=clip_path.parent,
                        start_seconds=start_seconds,
                        duration_seconds=args.duration,
                        prefix=clip_prefix,
                    )
                    generated.rename(clip_path)

            for experiment in experiments:
                experiment_name = slugify(experiment["name"])
                if use_experiment_dirs:
                    analysed_path = (
                        PROJECT_ROOT
                        / args.output_dir
                        / experiment_name
                        / f"{clip_path.stem}_analysed.mp4"
                    )
                    stats_path = (
                        PROJECT_ROOT
                        / args.output_dir
                        / experiment_name
                        / "stats"
                        / f"{clip_path.stem}_stats.json"
                    )
                    report_path = (
                        PROJECT_ROOT
                        / args.output_dir
                        / experiment_name
                        / "reports"
                        / f"{clip_path.stem}_report.html"
                    )
                else:
                    analysed_path = (
                        PROJECT_ROOT / args.output_dir / f"{clip_path.stem}_analysed.mp4"
                    )
                    stats_path = PROJECT_ROOT / args.stats_dir / f"{clip_path.stem}_stats.json"
                    report_path = PROJECT_ROOT / args.reports_dir / f"{clip_path.stem}_report.html"

                should_analyze = (
                    args.overwrite
                    or not analysed_path.exists()
                    or not stats_path.exists()
                )
                if should_analyze:
                    command = [
                        sys.executable,
                        "video_analise.py",
                        "--input",
                        str(clip_path),
                        "--output",
                        str(analysed_path),
                        "--stats-output",
                        str(stats_path),
                    ]
                    experiment_arg(command, "--model", experiment.get("model"))
                    experiment_arg(command, "--imgsz", experiment.get("imgsz"))
                    experiment_arg(command, "--model-conf", experiment.get("model_conf"))
                    experiment_arg(command, "--person-conf", experiment.get("person_conf"))
                    experiment_arg(command, "--ball-conf", experiment.get("ball_conf"))
                    experiment_arg(command, "--process-every", experiment.get("process_every"))
                    experiment_arg(command, "--tracker", experiment.get("tracker"))
                    experiment_arg(command, "--min-green-ratio", experiment.get("min_green_ratio"))
                    experiment_arg(
                        command,
                        "--min-players-for-play-frame",
                        experiment.get("min_players_for_play_frame"),
                    )
                    experiment_arg(
                        command,
                        "--max-person-area-ratio-for-closeup",
                        experiment.get("max_person_area_ratio_for_closeup"),
                    )
                    experiment_arg(command, "--team-render-mode", experiment.get("team_render_mode"))
                    experiment_bool_arg(command, "--web-video", experiment.get("web_video"))
                    ok, error = run_command(command, args.dry_run, args.continue_on_error)
                    if not ok:
                        manifest["failures"].append(
                            {
                                "experiment": experiment["name"],
                                "profile": experiment["profile"],
                                "clip": str(clip_path),
                                "stage": "analysis",
                                "error": error,
                            }
                        )
                        continue

                if args.overwrite or not report_path.exists():
                    ok, error = run_command(
                        [
                            sys.executable,
                            "tools/generate_report_panel.py",
                            "--stats",
                            str(stats_path),
                            "--output",
                            str(report_path),
                        ],
                        args.dry_run,
                        args.continue_on_error,
                    )
                    if not ok:
                        manifest["failures"].append(
                            {
                                "experiment": experiment["name"],
                                "profile": experiment["profile"],
                                "clip": str(clip_path),
                                "stage": "report",
                                "error": error,
                            }
                        )
                        continue

                manifest["artifacts"].append(
                    asdict(
                        ClipArtifact(
                            experiment=experiment["name"],
                            profile=experiment["profile"],
                            source=str(source),
                            start_seconds=float(start_seconds),
                            clip=str(clip_path),
                            analysed_video=str(analysed_path),
                            stats_json=str(stats_path),
                            report_html=str(report_path),
                        )
                    )
                )

    manifest_path = (PROJECT_ROOT / args.manifest).resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        with manifest_path.open("w", encoding="utf-8") as file:
            json.dump(manifest, file, indent=2)
        index_dir = (
            (PROJECT_ROOT / args.output_dir).resolve()
            if use_experiment_dirs
            else (PROJECT_ROOT / args.reports_dir).resolve()
        )
        index_path = write_index(
            manifest["artifacts"],
            index_dir,
            args.expected_players_min,
            args.expected_players_max,
        )
        print(f"Batch index: {index_path}")

    print(f"Batch manifest: {manifest_path}")


if __name__ == "__main__":
    main()

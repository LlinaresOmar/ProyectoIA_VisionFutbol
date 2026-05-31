"""Run a curated mixed-source clip suite for final project comparison."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from html import escape
from pathlib import Path

import yaml

from create_video_clips import cut_clip, parse_time
from run_full_pitch_test_batch import load_stats, relative_link, slugify


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_duration(value):
    if isinstance(value, (int, float)):
        return float(value)
    return parse_time(str(value))


def resolve_path(value):
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def experiment_arg(command, option, value):
    if value is None:
        return
    command.extend([option, str(value)])


def run_command(command, dry_run):
    print("$ " + " ".join(command))
    if dry_run:
        return
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def load_suite(path):
    suite_path = resolve_path(path)
    with suite_path.open("r", encoding="utf-8") as file:
        suite = yaml.safe_load(file) or {}
    if not suite.get("clips"):
        raise ValueError(f"No clips configured in {suite_path}")
    return suite


def clip_path_for(item, clips_dir):
    if item.get("clip"):
        return resolve_path(item["clip"])

    source = resolve_path(item["source"])
    start = parse_duration(item.get("start", 0))
    duration = parse_duration(item.get("duration", 10))
    clip_id = slugify(item.get("id") or source.stem)
    return clips_dir / f"{clip_id}_{int(round(start)):04d}s_{int(duration)}s.mp4"


def ensure_clip(item, clips_dir, overwrite, dry_run):
    clip_path = clip_path_for(item, clips_dir)
    if item.get("clip"):
        if not clip_path.exists():
            raise FileNotFoundError(clip_path)
        return clip_path

    source = resolve_path(item["source"])
    start = parse_duration(item.get("start", 0))
    duration = parse_duration(item.get("duration", 10))
    if clip_path.exists() and not overwrite:
        return clip_path

    print(f"Cutting {clip_path.name}")
    if dry_run:
        return clip_path

    generated = cut_clip(
        source=source,
        output_dir=clip_path.parent,
        start_seconds=start,
        duration_seconds=duration,
        prefix=slugify(item.get("id") or source.stem),
    )
    if clip_path.exists():
        clip_path.unlink()
    generated.rename(clip_path)
    return clip_path


def profile_for_clip(item, profiles):
    name = item.get("profile", "default")
    defaults = profiles.get("default", {})
    selected = profiles.get(name, {})
    merged = dict(defaults)
    merged.update(selected)
    merged["name"] = name
    return merged


def analyze_clip(item, clip_path, profile, output_dir, overwrite, dry_run):
    clip_id = slugify(item.get("id") or clip_path.stem)
    profile_id = slugify(profile.get("name", "default"))
    artifact_dir = output_dir / profile_id
    analysed_path = artifact_dir / f"{clip_id}_analysed.mp4"
    stats_path = artifact_dir / "stats" / f"{clip_id}_stats.json"
    report_path = artifact_dir / "reports" / f"{clip_id}_report.html"

    if overwrite or not analysed_path.exists() or not stats_path.exists():
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
        for key, option in [
            ("model", "--model"),
            ("imgsz", "--imgsz"),
            ("model_conf", "--model-conf"),
            ("person_conf", "--person-conf"),
            ("ball_conf", "--ball-conf"),
            ("process_every", "--process-every"),
            ("tracker", "--tracker"),
            ("min_green_ratio", "--min-green-ratio"),
            ("min_players_for_play_frame", "--min-players-for-play-frame"),
            ("max_person_area_ratio_for_closeup", "--max-person-area-ratio-for-closeup"),
            ("team_render_mode", "--team-render-mode"),
        ]:
            experiment_arg(command, option, profile.get(key))
        run_command(command, dry_run)

    if overwrite or not report_path.exists():
        run_command(
            [
                sys.executable,
                "tools/generate_report_panel.py",
                "--stats",
                str(stats_path),
                "--output",
                str(report_path),
            ],
            dry_run,
        )

    return {
        "id": item.get("id") or clip_path.stem,
        "source_type": item.get("source_type", "unknown"),
        "objective": item.get("objective", ""),
        "expected_quality": item.get("expected_quality", "unknown"),
        "profile": profile.get("name", "default"),
        "clip": str(clip_path),
        "analysed_video": str(analysed_path),
        "stats_json": str(stats_path),
        "report_html": str(report_path),
    }


def stats_metrics(stats):
    summary = stats.get("summary", {})
    frames = int(summary.get("frames_analyzed", 0))
    ball_visible = int(summary.get("ball_visible_frames", 0))
    ball_pct = (ball_visible / frames) * 100 if frames else 0.0
    status_counts = summary.get("status_counts", {})
    analyzable = int(status_counts.get("PLAY_ANALYZABLE", 0))
    analyzable_pct = (analyzable / frames) * 100 if frames else 0.0
    return {
        "frames": frames,
        "ball_pct": ball_pct,
        "analyzable_pct": analyzable_pct,
        "unique_tracks": int(summary.get("unique_player_tracks", 0)),
        "avg_track_length": float(summary.get("avg_track_length_frames", 0.0)),
        "team_1_passes": int(summary.get("team_1_passes", 0)),
        "team_2_passes": int(summary.get("team_2_passes", 0)),
        "pass_candidates": int(summary.get("pass_candidates", 0)),
    }


def clip_conclusion(artifact, metrics):
    source_type = artifact.get("source_type")
    stable_tracking = (
        metrics["unique_tracks"] >= 10
        and metrics["avg_track_length"] >= max(5, metrics["frames"] * 0.10)
    )
    has_visual_signal = metrics["ball_pct"] > 0 or metrics["unique_tracks"] > 0

    if source_type == "full_pitch" and stable_tracking and metrics["analyzable_pct"] >= 5:
        return "apto para eventos tacticos"
    if has_visual_signal:
        return "solo deteccion visual"
    return "no recomendable"


def write_index(artifacts, output_dir):
    rows = []
    for artifact in artifacts:
        stats = load_stats(Path(artifact["stats_json"]))
        metrics = stats_metrics(stats)
        conclusion = clip_conclusion(artifact, metrics)
        artifact["metrics"] = {key: round(value, 2) for key, value in metrics.items()}
        artifact["conclusion"] = conclusion
        rows.append(
            f"""
            <tr>
              <td>{escape(artifact["id"])}</td>
              <td>{escape(artifact["source_type"])}</td>
              <td>{escape(artifact["objective"])}</td>
              <td>{escape(artifact["profile"])}</td>
              <td>{metrics["unique_tracks"]}</td>
              <td>{metrics["avg_track_length"]:.1f}</td>
              <td>{metrics["ball_pct"]:.1f}%</td>
              <td>{metrics["analyzable_pct"]:.1f}%</td>
              <td>{metrics["team_1_passes"]}</td>
              <td>{metrics["team_2_passes"]}</td>
              <td>{escape(conclusion)}</td>
              <td><a href="{relative_link(Path(artifact["analysed_video"]), output_dir)}" target="_blank" rel="noopener">video</a></td>
              <td><a href="{relative_link(Path(artifact["report_html"]), output_dir)}" target="_blank" rel="noopener">panel</a></td>
              <td><a href="{relative_link(Path(artifact["stats_json"]), output_dir)}" target="_blank" rel="noopener">json</a></td>
            </tr>
            """
        )

    index_path = output_dir / "index.html"
    index_path.write_text(
        f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mixed Clip Suite</title>
  <style>
    body {{ margin:0; font-family:Arial, Helvetica, sans-serif; background:#f7f7f4; color:#191919; }}
    main {{ max-width:1320px; margin:0 auto; padding:32px 20px; }}
    h1 {{ margin:0 0 8px; font-size:28px; }}
    p {{ margin:0 0 24px; color:#626262; line-height:1.45; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid #deded6; }}
    th, td {{ padding:10px 12px; border-bottom:1px solid #ecece5; text-align:left; font-size:13px; vertical-align:top; }}
    th {{ background:#efefe8; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
    a {{ color:#176b5d; font-weight:700; }}
  </style>
</head>
<body>
  <main>
    <h1>Mixed Clip Suite</h1>
    <p>Comparativa curada entre camara panoramica full-pitch y retransmision TV. El objetivo es mostrar que TV sirve para deteccion visual basica, mientras full-pitch ofrece mas estabilidad para tracking, equipos y pases aproximados.</p>
    <table>
      <thead>
        <tr>
          <th>Clip</th>
          <th>Fuente</th>
          <th>Objetivo</th>
          <th>Perfil</th>
          <th>Tracks</th>
          <th>Track medio</th>
          <th>Balon visible</th>
          <th>Analizable</th>
          <th>Pases T1</th>
          <th>Pases T2</th>
          <th>Conclusion</th>
          <th>Video</th>
          <th>Panel</th>
          <th>Stats</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return index_path


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run a curated mixed-source suite and build a comparison index."
    )
    parser.add_argument(
        "--suite",
        type=Path,
        default=Path("config/clip_suite.yaml"),
        help="YAML suite with curated clips and profiles.",
    )
    parser.add_argument(
        "--clips-dir",
        type=Path,
        default=Path("videos/clips/mixed_suite"),
        help="Directory for generated suite clips.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("videos/output/mixed_suite"),
        help="Directory for analysed videos, stats, reports and index.",
    )
    parser.add_argument("--clip-limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    suite = load_suite(args.suite)
    clips_dir = resolve_path(args.clips_dir)
    output_dir = resolve_path(args.output_dir)
    clips_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    profiles = suite.get("profiles", {})
    artifacts = []
    clips = suite["clips"]
    if args.clip_limit is not None:
        clips = clips[: args.clip_limit]

    for item in clips:
        clip_path = ensure_clip(item, clips_dir, args.overwrite, args.dry_run)
        profile = profile_for_clip(item, profiles)
        artifacts.append(
            analyze_clip(item, clip_path, profile, output_dir, args.overwrite, args.dry_run)
        )

    manifest_path = output_dir / "manifest.json"
    if not args.dry_run:
        index_path = write_index(artifacts, output_dir)
        manifest_path.write_text(json.dumps({"artifacts": artifacts}, indent=2), encoding="utf-8")
        print(f"Suite index: {index_path}")
    print(f"Suite manifest: {manifest_path}")


if __name__ == "__main__":
    main()

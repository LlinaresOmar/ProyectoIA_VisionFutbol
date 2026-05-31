"""Prepare and analyze a reproducible full-pitch test batch."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2

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


def run_command(command: list[str], dry_run: bool) -> None:
    print("$ " + " ".join(command))
    if dry_run:
        return
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


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
        "--dry-run",
        action="store_true",
        help="Print the planned work without creating or processing files.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_dir = (PROJECT_ROOT / args.input_dir).resolve()
    videos = sorted(input_dir.glob("*.mp4"))
    if not videos:
        raise FileNotFoundError(f"No MP4 videos found in {input_dir}")

    manifest = {
        "settings": {
            "duration_seconds": args.duration,
            "clips_per_video": args.clips_per_video,
            "starts": args.starts,
            "process_every": args.process_every,
            "tracker": args.tracker,
            "imgsz": args.imgsz,
        },
        "sources": [],
        "artifacts": [],
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
            analysed_path = (
                PROJECT_ROOT / args.output_dir / f"{clip_path.stem}_analysed.mp4"
            )
            stats_path = PROJECT_ROOT / args.stats_dir / f"{clip_path.stem}_stats.json"
            report_path = PROJECT_ROOT / args.reports_dir / f"{clip_path.stem}_report.html"

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

            should_analyze = args.overwrite or not analysed_path.exists() or not stats_path.exists()
            if should_analyze:
                run_command(
                    [
                        sys.executable,
                        "video_analise.py",
                        "--input",
                        str(clip_path),
                        "--output",
                        str(analysed_path),
                        "--stats-output",
                        str(stats_path),
                        "--process-every",
                        str(args.process_every),
                        "--tracker",
                        args.tracker,
                        "--imgsz",
                        str(args.imgsz),
                    ],
                    args.dry_run,
                )

            if args.overwrite or not report_path.exists():
                run_command(
                    [
                        sys.executable,
                        "tools/generate_report_panel.py",
                        "--stats",
                        str(stats_path),
                        "--output",
                        str(report_path),
                    ],
                    args.dry_run,
                )

            manifest["artifacts"].append(
                asdict(
                    ClipArtifact(
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

    print(f"Batch manifest: {manifest_path}")


if __name__ == "__main__":
    main()

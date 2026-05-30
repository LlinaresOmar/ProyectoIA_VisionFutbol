"""Cut fixed-duration clips from a local video file."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import cv2


def parse_time(value: str) -> float:
    """Parse seconds, MM:SS, or HH:MM:SS into seconds."""
    if re.fullmatch(r"\d+(\.\d+)?", value):
        return float(value)

    parts = value.split(":")
    if len(parts) not in {2, 3}:
        raise argparse.ArgumentTypeError(
            f"Invalid time '{value}'. Use seconds, MM:SS, or HH:MM:SS."
        )

    try:
        numbers = [float(part) for part in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid time '{value}'.") from exc

    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds

    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def format_stamp(seconds: float) -> str:
    rounded = int(round(seconds))
    hours = rounded // 3600
    minutes = (rounded % 3600) // 60
    secs = rounded % 60
    if hours:
        return f"{hours:02d}h{minutes:02d}m{secs:02d}s"
    return f"{minutes:02d}m{secs:02d}s"


def make_writer(path: Path, fps: float, width: int, height: int) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not create output video: {path}")
    return writer


def cut_clip(
    source: Path,
    output_dir: Path,
    start_seconds: float,
    duration_seconds: float,
    prefix: str,
) -> Path:
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open input video: {source}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    start_frame = int(round(start_seconds * fps))
    max_frames = int(round(duration_seconds * fps))
    if total_frames and start_frame >= total_frames:
        capture.release()
        raise ValueError(
            f"Start {start_seconds:.2f}s is outside the video "
            f"({total_frames / fps:.2f}s)."
        )

    output_path = output_dir / f"{prefix}_{format_stamp(start_seconds)}_{int(duration_seconds)}s.mp4"
    writer = make_writer(output_path, fps, width, height)
    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    written = 0
    while written < max_frames:
        ok, frame = capture.read()
        if not ok:
            break
        writer.write(frame)
        written += 1

    capture.release()
    writer.release()

    if written == 0:
        raise RuntimeError(f"No frames written for {output_path}")

    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cut one or more clips from a local full-pitch video."
    )
    parser.add_argument("--input", required=True, type=Path, help="Input video path.")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where clips will be written.",
    )
    parser.add_argument(
        "--starts",
        required=True,
        nargs="+",
        type=parse_time,
        help="Start times. Accepts seconds, MM:SS, or HH:MM:SS.",
    )
    parser.add_argument(
        "--duration",
        default=60.0,
        type=parse_time,
        help="Clip duration. Defaults to 60 seconds.",
    )
    parser.add_argument(
        "--prefix",
        default="full_pitch",
        help="Output filename prefix. Defaults to full_pitch.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    source = args.input.resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    outputs = []
    for start_seconds in args.starts:
        outputs.append(
            cut_clip(
                source=source,
                output_dir=args.output_dir,
                start_seconds=start_seconds,
                duration_seconds=args.duration,
                prefix=args.prefix,
            )
        )

    print("Created clips:")
    for output in outputs:
        print(f"- {output}")


if __name__ == "__main__":
    main()

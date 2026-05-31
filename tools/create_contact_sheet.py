"""Create contact sheets from analysed football videos."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create image contact sheets from one or more video files."
    )
    parser.add_argument(
        "--input",
        required=True,
        nargs="+",
        type=Path,
        help="Input video files or directories. Directories are searched recursively for MP4 files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("videos/output/final_demo/contact_sheets"),
        help="Directory where contact sheet JPEG files will be written.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=12,
        help="Number of evenly spaced frames to sample per video.",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=4,
        help="Number of columns in each contact sheet.",
    )
    parser.add_argument(
        "--thumb-width",
        type=int,
        default=480,
        help="Thumbnail width in pixels.",
    )
    parser.add_argument(
        "--pattern",
        default="*_analysed.mp4",
        help="Filename glob used when an input is a directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing contact sheets.",
    )
    return parser.parse_args()


def iter_videos(inputs: list[Path], pattern: str) -> list[Path]:
    videos = []
    for item in inputs:
        if item.is_dir():
            videos.extend(sorted(item.rglob(pattern)))
        elif item.is_file():
            videos.append(item)
        else:
            raise FileNotFoundError(item)
    return list(dict.fromkeys(video.resolve() for video in videos))


def sample_frame_indices(total_frames: int, samples: int) -> list[int]:
    if total_frames <= 0:
        return []
    count = max(1, min(samples, total_frames))
    if count == 1:
        return [0]
    return [
        min(total_frames - 1, int(round(index * (total_frames - 1) / (count - 1))))
        for index in range(count)
    ]


def read_sampled_frames(video_path: Path, samples: int, thumb_width: int) -> list:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for frame_index in sample_frame_indices(total_frames, samples):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            continue
        height, width = frame.shape[:2]
        thumb_height = max(1, int(round(height * (thumb_width / max(1, width)))))
        thumb = cv2.resize(frame, (thumb_width, thumb_height), interpolation=cv2.INTER_AREA)
        cv2.putText(
            thumb,
            f"frame {frame_index}",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        frames.append(thumb)

    capture.release()
    return frames


def make_contact_sheet(frames: list, columns: int):
    if not frames:
        return None

    columns = max(1, columns)
    rows = int(math.ceil(len(frames) / columns))
    thumb_height, thumb_width = frames[0].shape[:2]
    sheet = 255 * frames[0].copy()
    sheet = cv2.resize(sheet, (thumb_width * columns, thumb_height * rows))

    for index, frame in enumerate(frames):
        row = index // columns
        column = index % columns
        y1 = row * thumb_height
        x1 = column * thumb_width
        sheet[y1 : y1 + thumb_height, x1 : x1 + thumb_width] = frame
    return sheet


def write_contact_sheet(video_path: Path, output_dir: Path, samples: int, columns: int, thumb_width: int, overwrite: bool) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_path.stem}_contact_sheet.jpg"
    if output_path.exists() and not overwrite:
        return output_path

    frames = read_sampled_frames(video_path, samples, thumb_width)
    sheet = make_contact_sheet(frames, columns)
    if sheet is None:
        raise RuntimeError(f"No frames sampled from {video_path}")
    ok = cv2.imwrite(str(output_path), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not ok:
        raise RuntimeError(f"Could not write contact sheet: {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    videos = iter_videos(args.input, args.pattern)
    if not videos:
        raise FileNotFoundError("No videos found for contact sheet generation.")

    print(f"Creating contact sheets for {len(videos)} video(s)")
    for video in videos:
        output = write_contact_sheet(
            video_path=video,
            output_dir=args.output_dir,
            samples=args.samples,
            columns=args.columns,
            thumb_width=args.thumb_width,
            overwrite=args.overwrite,
        )
        print(f"- {output}")


if __name__ == "__main__":
    main()

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_TRACKERS = ["bytetrack.yaml", "botsort.yaml"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compara trackers de Ultralytics sobre el mismo clip."
    )
    parser.add_argument(
        "--input",
        default="videos/clips/prepared/clip_05m00s_20s.mp4",
        help="Video de entrada.",
    )
    parser.add_argument(
        "--trackers",
        nargs="+",
        default=DEFAULT_TRACKERS,
        help="Trackers a comparar.",
    )
    parser.add_argument(
        "--process-every",
        type=int,
        default=1,
        help="Procesar uno de cada N frames.",
    )
    parser.add_argument(
        "--output-dir",
        default="videos/output/tracker_comparison",
        help="Directorio para videos, stats y comparativa.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python a usar para ejecutar video_analise.py.",
    )
    return parser.parse_args()


def safe_tracker_name(tracker):
    return Path(tracker).stem.replace("-", "_")


def run_analysis(args, tracker):
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tracker_name = safe_tracker_name(tracker)
    video_output = output_dir / f"{input_path.stem}_{tracker_name}_analysed.mp4"
    stats_output = output_dir / f"{input_path.stem}_{tracker_name}_stats.json"

    command = [
        args.python,
        "video_analise.py",
        "--input",
        str(input_path),
        "--output",
        str(video_output),
        "--stats-output",
        str(stats_output),
        "--tracking",
        "--tracker",
        tracker,
        "--process-every",
        str(args.process_every),
    ]

    print(f"Ejecutando {tracker}...")
    subprocess.run(command, check=True)
    return stats_output, video_output


def load_stats(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def summarize_tracker(tracker, stats_path, video_output):
    stats = load_stats(stats_path)
    summary = stats.get("summary", {})
    tracks = stats.get("tracks", [])
    long_tracks = [track for track in tracks if track.get("frames_seen", 0) >= 25]

    return {
        "tracker": tracker,
        "video_output": str(video_output),
        "stats_output": str(stats_path),
        "frames_analyzed": summary.get("frames_analyzed", 0),
        "ball_visible_frames": summary.get("ball_visible_frames", 0),
        "unique_player_tracks": summary.get("unique_player_tracks", 0),
        "avg_track_length_frames": summary.get("avg_track_length_frames", 0),
        "max_track_length_frames": summary.get("max_track_length_frames", 0),
        "long_tracks_25_plus_frames": len(long_tracks),
        "status_counts": summary.get("status_counts", {}),
    }


def write_comparison(args, summaries):
    output_dir = Path(args.output_dir)
    output_path = output_dir / f"{Path(args.input).stem}_tracker_comparison.json"
    payload = {
        "input": args.input,
        "process_every": args.process_every,
        "summaries": summaries,
    }

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    print()
    print("======================================")
    print("COMPARACION DE TRACKERS")
    print("======================================")
    for item in summaries:
        print(
            f"{item['tracker']}: "
            f"tracks={item['unique_player_tracks']} | "
            f"avg_len={item['avg_track_length_frames']} | "
            f"max_len={item['max_track_length_frames']} | "
            f"long_25+={item['long_tracks_25_plus_frames']}"
        )
    print(f"Comparativa generada: {output_path}")


def main():
    args = parse_args()
    summaries = []
    for tracker in args.trackers:
        stats_path, video_output = run_analysis(args, tracker)
        summaries.append(summarize_tracker(tracker, stats_path, video_output))

    write_comparison(args, summaries)


if __name__ == "__main__":
    main()

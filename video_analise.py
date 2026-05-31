import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLO


DEFAULT_CONFIG_PATH = Path("config/config.yaml")


@dataclass
class Detection:
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float
    track_id: int | None = None

    @property
    def center(self):
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def area(self):
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)


@dataclass
class BallMemory:
    detection: Detection | None = None
    missed_frames: int = 0


@dataclass
class FrameAnnotation:
    frame_index: int
    status: str
    persons: list[Detection]
    ball: Detection | None
    ball_from_memory: bool
    fps_estimate: float


@dataclass
class TrackSummary:
    track_id: int
    first_frame: int
    last_frame: int
    frames_seen: int = 0
    total_conf: float = 0.0
    total_distance_px: float = 0.0
    last_center: tuple[int, int] | None = None
    jersey_bgr_sum: tuple[float, float, float] = (0.0, 0.0, 0.0)
    jersey_hsv_sum: tuple[float, float, float] = (0.0, 0.0, 0.0)
    jersey_samples: int = 0

    def update(self, detection, frame_index, frame=None, config=None):
        center = detection.center
        if self.last_center is not None:
            self.total_distance_px += math.hypot(
                center[0] - self.last_center[0],
                center[1] - self.last_center[1],
            )

        self.frames_seen += 1
        self.total_conf += detection.conf
        self.last_center = center
        self.last_frame = frame_index
        if frame is not None and config is not None:
            jersey_color = sample_jersey_color(frame, detection, config)
            if jersey_color is not None:
                bgr, hsv = jersey_color
                self.jersey_bgr_sum = tuple(
                    self.jersey_bgr_sum[index] + float(bgr[index])
                    for index in range(3)
                )
                self.jersey_hsv_sum = tuple(
                    self.jersey_hsv_sum[index] + float(hsv[index])
                    for index in range(3)
                )
                self.jersey_samples += 1

    def to_dict(self):
        avg_conf = self.total_conf / self.frames_seen if self.frames_seen else 0.0
        avg_bgr = [
            round(value / self.jersey_samples, 2)
            for value in self.jersey_bgr_sum
        ] if self.jersey_samples else None
        avg_hsv = [
            round(value / self.jersey_samples, 2)
            for value in self.jersey_hsv_sum
        ] if self.jersey_samples else None
        avg_rgb = [avg_bgr[2], avg_bgr[1], avg_bgr[0]] if avg_bgr else None
        return {
            "track_id": self.track_id,
            "first_frame": self.first_frame,
            "last_frame": self.last_frame,
            "frames_seen": self.frames_seen,
            "avg_conf": round(avg_conf, 4),
            "total_distance_px": round(self.total_distance_px, 2),
            "last_center": list(self.last_center) if self.last_center else None,
            "jersey_samples": self.jersey_samples,
            "avg_jersey_bgr": avg_bgr,
            "avg_jersey_rgb": avg_rgb,
            "avg_jersey_hsv": avg_hsv,
        }


def load_config(path):
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def nested_get(config, keys, default):
    value = config
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def parse_args():
    config = load_config(DEFAULT_CONFIG_PATH)

    parser = argparse.ArgumentParser(
        description="Analiza un clip corto de futbol con YOLO y genera un video anotado."
    )
    parser.add_argument(
        "--input",
        default=nested_get(config, ["video", "input_path"], "videos/clips/prepared/clip_00m00s_20s.mp4"),
        help="Ruta del video de entrada.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Ruta del video de salida. Si no se indica, se genera en videos/output.",
    )
    parser.add_argument(
        "--model",
        default=nested_get(config, ["model", "path"], "yolo26n.pt"),
        help="Ruta del modelo YOLO.",
    )
    parser.add_argument(
        "--device",
        default=nested_get(config, ["model", "device"], "cpu"),
        help="Dispositivo para inferencia: cpu, cuda, etc.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=int(nested_get(config, ["model", "imgsz"], 640)),
        help="Tamano de imagen para YOLO.",
    )
    parser.add_argument(
        "--model-conf",
        type=float,
        default=float(nested_get(config, ["model", "model_conf"], 0.05)),
        help="Confianza minima de inferencia YOLO.",
    )
    parser.add_argument(
        "--person-conf",
        type=float,
        default=float(nested_get(config, ["thresholds", "person_conf"], 0.25)),
        help="Confianza minima para aceptar personas.",
    )
    parser.add_argument(
        "--ball-conf",
        type=float,
        default=float(nested_get(config, ["thresholds", "ball_conf"], 0.10)),
        help="Confianza minima para aceptar balon.",
    )
    parser.add_argument(
        "--ball-memory-frames",
        type=int,
        default=int(nested_get(config, ["frame_analysis", "ball_memory_frames"], 12)),
        help="Frames durante los que se mantiene la ultima posicion del balon.",
    )
    parser.add_argument(
        "--min-green-ratio",
        type=float,
        default=float(nested_get(config, ["frame_analysis", "min_green_ratio"], 0.35)),
        help="Ratio minimo de cesped para clasificar un frame como analizable.",
    )
    parser.add_argument(
        "--min-players-for-play-frame",
        type=int,
        default=int(nested_get(config, ["frame_analysis", "min_players_for_play_frame"], 4)),
        help="Minimo de jugadores detectados para considerar juego analizable.",
    )
    parser.add_argument(
        "--max-person-area-ratio-for-closeup",
        type=float,
        default=float(
            nested_get(config, ["frame_analysis", "max_person_area_ratio_for_closeup"], 0.25)
        ),
        help="Area maxima relativa de una persona antes de considerar CLOSE_UP.",
    )
    parser.add_argument(
        "--process-every",
        type=int,
        default=int(nested_get(config, ["video", "process_every_n_frames"], 1)),
        help="Procesar uno de cada N frames. Por defecto procesa todos.",
    )
    parser.add_argument(
        "--tracking",
        action=argparse.BooleanOptionalAction,
        default=bool(nested_get(config, ["tracking", "enabled"], True)),
        help="Activar/desactivar tracking de jugadores.",
    )
    parser.add_argument(
        "--tracker",
        default=nested_get(config, ["tracking", "tracker"], "bytetrack.yaml"),
        help="Tracker de Ultralytics. Ejemplo: bytetrack.yaml o botsort.yaml.",
    )
    parser.add_argument(
        "--stats-output",
        default=None,
        help="Ruta del JSON de metricas. Si no se indica, se genera en videos/output/stats.",
    )
    parser.add_argument(
        "--team-render-mode",
        choices=["single-pass", "two-pass"],
        default=nested_get(config, ["annotation", "team_render_mode"], "single-pass"),
        help="single-pass mantiene el estilo actual; two-pass pinta equipos tras resolver clusters.",
    )
    return parser.parse_args()


def make_output_path(input_path, explicit_output):
    if explicit_output:
        return Path(explicit_output)

    output_dir = Path("videos/output")
    return output_dir / f"{input_path.stem}_analysed.mp4"


def make_stats_path(input_path, explicit_stats_output, config):
    if explicit_stats_output:
        return Path(explicit_stats_output)

    output_dir = Path(nested_get(config, ["stats", "output_dir"], "videos/output/stats"))
    return output_dir / f"{input_path.stem}_stats.json"


def make_writer(output_path, fps, width, height):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"No se pudo crear el video de salida: {output_path}")
    return writer


def clamp_box(box, width, height):
    x1, y1, x2, y2 = box
    return (
        max(0, min(width - 1, int(x1))),
        max(0, min(height - 1, int(y1))),
        max(0, min(width - 1, int(x2))),
        max(0, min(height - 1, int(y2))),
    )


def box_iou(first, second):
    x_left = max(first.x1, second.x1)
    y_top = max(first.y1, second.y1)
    x_right = min(first.x2, second.x2)
    y_bottom = min(first.y2, second.y2)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection = (x_right - x_left) * (y_bottom - y_top)
    union = first.area + second.area - intersection
    return intersection / union if union > 0 else 0.0


def assign_track_ids(persons, tracked_persons, config):
    min_iou = float(nested_get(config, ["tracking", "match_iou_threshold"], 0.30))
    available_tracks = [person for person in tracked_persons if person.track_id is not None]
    used_track_ids = set()

    for person in persons:
        best_track = None
        best_iou = 0.0
        for tracked_person in available_tracks:
            if tracked_person.track_id in used_track_ids:
                continue

            iou = box_iou(person, tracked_person)
            if iou > best_iou:
                best_iou = iou
                best_track = tracked_person

        if best_track is not None and best_iou >= min_iou:
            person.track_id = best_track.track_id
            used_track_ids.add(best_track.track_id)


def green_ratio(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 35, 35])
    upper_green = np.array([95, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    return float(cv2.countNonZero(mask)) / float(frame.shape[0] * frame.shape[1])


def sample_jersey_color(frame, detection, config):
    if not bool(nested_get(config, ["team_memory", "enabled"], True)):
        return None

    box_width = max(1, detection.x2 - detection.x1)
    box_height = max(1, detection.y2 - detection.y1)
    crop_config = nested_get(config, ["team_memory", "jersey_crop"], {})

    x1 = detection.x1 + int(box_width * float(crop_config.get("x_min_ratio", 0.25)))
    x2 = detection.x1 + int(box_width * float(crop_config.get("x_max_ratio", 0.75)))
    y1 = detection.y1 + int(box_height * float(crop_config.get("y_min_ratio", 0.20)))
    y2 = detection.y1 + int(box_height * float(crop_config.get("y_max_ratio", 0.60)))

    height, width = frame.shape[:2]
    x1, y1, x2, y2 = clamp_box((x1, y1, x2, y2), width, height)
    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    mean_bgr = cv2.mean(crop)[:3]
    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mean_hsv = cv2.mean(hsv_crop)[:3]
    return mean_bgr, mean_hsv


def detection_center_in_region(detection, region, width, height):
    cx, cy = detection.center
    x_min = float(region.get("x_min_ratio", 0.0)) * width
    y_min = float(region.get("y_min_ratio", 0.0)) * height
    x_max = float(region.get("x_max_ratio", 1.0)) * width
    y_max = float(region.get("y_max_ratio", 1.0)) * height
    return x_min <= cx <= x_max and y_min <= cy <= y_max


def is_ignored_ball_candidate(detection, config, width, height):
    regions = nested_get(config, ["ball_filter", "ignore_regions"], [])
    if not isinstance(regions, list):
        return False

    return any(
        detection_center_in_region(detection, region, width, height)
        for region in regions
        if isinstance(region, dict)
    )


def select_ball(candidates, memory):
    if not candidates:
        return None

    if memory.detection is None:
        return max(candidates, key=lambda item: item.conf)

    previous_center = memory.detection.center

    def score(candidate):
        cx, cy = candidate.center
        distance = math.hypot(cx - previous_center[0], cy - previous_center[1])
        return distance - (candidate.conf * 100.0)

    return min(candidates, key=score)


def classify_frame(frame, persons, visible_ball, config, args=None):
    height, width = frame.shape[:2]
    frame_area = width * height
    min_players = (
        args.min_players_for_play_frame
        if args is not None
        else int(nested_get(config, ["frame_analysis", "min_players_for_play_frame"], 4))
    )
    min_green = (
        args.min_green_ratio
        if args is not None
        else float(nested_get(config, ["frame_analysis", "min_green_ratio"], 0.35))
    )
    max_closeup_area = (
        args.max_person_area_ratio_for_closeup
        if args is not None
        else float(nested_get(config, ["frame_analysis", "max_person_area_ratio_for_closeup"], 0.25))
    )

    largest_person_ratio = 0.0
    if persons:
        largest_person_ratio = max(person.area for person in persons) / float(frame_area)

    if largest_person_ratio >= max_closeup_area:
        return "CLOSE_UP"

    field_ratio = green_ratio(frame)

    if len(persons) >= min_players and visible_ball and field_ratio >= min_green:
        return "PLAY_ANALYZABLE"

    if len(persons) >= min_players and not visible_ball:
        return "NO_BALL_VISIBLE"

    return "UNKNOWN"


def draw_label(
    frame,
    text,
    x,
    y,
    bg_color,
    fg_color=(255, 255, 255),
    scale=0.45,
    bg_alpha=1.0,
):
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    (text_width, text_height), baseline = cv2.getTextSize(text, font, scale, thickness)
    label_width = text_width + 8
    label_height = text_height + baseline + 7
    height, width = frame.shape[:2]

    x = max(0, min(width - label_width - 1, int(x)))
    y = max(0, min(height - label_height - 1, int(y)))

    x2 = x + label_width
    y2 = y + label_height
    bg_alpha = max(0.0, min(1.0, float(bg_alpha)))

    if bg_alpha >= 1.0:
        cv2.rectangle(frame, (x, y), (x2, y2), bg_color, -1)
    elif bg_alpha > 0:
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x2, y2), bg_color, -1)
        cv2.addWeighted(overlay, bg_alpha, frame, 1.0 - bg_alpha, 0, frame)

    cv2.putText(
        frame,
        text,
        (x + 4, y + text_height + 3),
        font,
        scale,
        fg_color,
        thickness,
        cv2.LINE_AA,
    )


def annotation_resolution_scale(frame, config):
    if not bool(nested_get(config, ["annotation", "scale_with_resolution"], True)):
        return 1.0

    reference_height = float(nested_get(config, ["annotation", "reference_frame_height"], 224))
    if reference_height <= 0:
        return 1.0

    return max(1.0, frame.shape[0] / reference_height)


def draw_status_panel(frame, status, frame_index, persons, ball, ball_from_memory, fps_estimate):
    ball_text = "vis" if ball and not ball_from_memory else "mem" if ball else "no"
    tracked_persons = sum(1 for person in persons if person.track_id is not None)
    lines = [
        f"Frame {frame_index} | {status}",
        f"P:{len(persons)} T:{tracked_persons} Ball:{ball_text} FPS:{fps_estimate:.1f}",
    ]

    height, width = frame.shape[:2]
    panel_right = min(width - 8, 360)
    cv2.rectangle(frame, (8, 8), (panel_right, 62), (0, 0, 0), -1)
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (16, 30 + index * 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )


def detections_from_result(result, args, config, width, height):
    person_class_id = 0
    ball_class_id = 32
    persons = []
    balls = []

    if result.boxes is None:
        return persons, balls

    track_ids = result.boxes.id

    for index, box in enumerate(result.boxes):
        class_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        x1, y1, x2, y2 = clamp_box(box.xyxy[0].cpu().numpy(), width, height)
        track_id = None
        if track_ids is not None:
            raw_track_id = int(track_ids[index].item())
            if raw_track_id >= 0:
                track_id = raw_track_id
        detection = Detection(x1=x1, y1=y1, x2=x2, y2=y2, conf=conf, track_id=track_id)

        if class_id == person_class_id and conf >= args.person_conf:
            persons.append(detection)
        elif (
            class_id == ball_class_id
            and conf >= args.ball_conf
            and not is_ignored_ball_candidate(detection, config, width, height)
        ):
            balls.append(detection)

    return persons, balls


def draw_person_marker(frame, person, config, color=None):
    color = color or (60, 220, 80)
    visual_scale = annotation_resolution_scale(frame, config)
    thickness = max(
        1,
        int(round(int(nested_get(config, ["annotation", "person_marker_thickness"], 1)) * visual_scale)),
    )
    style = nested_get(config, ["annotation", "person_marker_style"], "lower_u")

    if style != "lower_u":
        cv2.rectangle(frame, (person.x1, person.y1), (person.x2, person.y2), color, thickness)
        return

    height = max(1, person.y2 - person.y1)
    u_ratio = float(nested_get(config, ["annotation", "person_marker_height_ratio"], 0.25))
    u_height = max(3, int(height * u_ratio))
    y_top = max(person.y1, person.y2 - u_height)

    cv2.line(frame, (person.x1, person.y2), (person.x1, y_top), color, thickness)
    cv2.line(frame, (person.x2, person.y2), (person.x2, y_top), color, thickness)
    cv2.line(frame, (person.x1, person.y2), (person.x2, person.y2), color, thickness)


def update_track_summaries(track_summaries, persons, frame_index, frame, config):
    for person in persons:
        if person.track_id is None:
            continue

        if person.track_id not in track_summaries:
            track_summaries[person.track_id] = TrackSummary(
                track_id=person.track_id,
                first_frame=frame_index,
                last_frame=frame_index,
            )

        track_summaries[person.track_id].update(person, frame_index, frame, config)


def build_frame_metrics(frame_index, status, persons, selected_ball, ball_from_memory):
    active_track_ids = sorted(
        person.track_id for person in persons if person.track_id is not None
    )
    ball_center = selected_ball.center if selected_ball is not None else None

    return {
        "frame": frame_index,
        "status": status,
        "persons": len(persons),
        "tracked_persons": len(active_track_ids),
        "active_track_ids": active_track_ids,
        "ball_visible": selected_ball is not None and not ball_from_memory,
        "ball_from_memory": bool(ball_from_memory),
        "ball_center": list(ball_center) if ball_center else None,
    }


def squared_distance(first, second):
    return sum((first[index] - second[index]) ** 2 for index in range(len(first)))


def mean_vector(vectors):
    if not vectors:
        return None

    return [
        sum(vector[index] for vector in vectors) / len(vectors)
        for index in range(len(vectors[0]))
    ]


def initial_centroids(vectors):
    if len(vectors) == 1:
        return [vectors[0], vectors[0]]

    best_pair = (vectors[0], vectors[1])
    best_distance = -1.0
    for first_index, first in enumerate(vectors):
        for second in vectors[first_index + 1:]:
            distance = squared_distance(first, second)
            if distance > best_distance:
                best_distance = distance
                best_pair = (first, second)

    return [list(best_pair[0]), list(best_pair[1])]


def assign_team_clusters(tracks, config):
    if not bool(nested_get(config, ["team_classification", "enabled"], True)):
        return tracks, {}

    num_teams = int(nested_get(config, ["team_classification", "num_teams"], 2))
    min_samples = int(nested_get(config, ["team_classification", "min_jersey_samples"], 5))
    if num_teams != 2:
        return tracks, {}

    candidates = [
        track
        for track in tracks
        if track.get("avg_jersey_rgb") is not None
        and int(track.get("jersey_samples", 0)) >= min_samples
    ]
    if len(candidates) < 2:
        for track in tracks:
            track["team_id"] = None
        return tracks, {}

    vectors = [track["avg_jersey_rgb"] for track in candidates]
    centroids = initial_centroids(vectors)
    assignments = [0 for _ in candidates]

    for _ in range(10):
        changed = False
        for index, vector in enumerate(vectors):
            distances = [squared_distance(vector, centroid) for centroid in centroids]
            assignment = int(distances[1] < distances[0])
            if assignment != assignments[index]:
                assignments[index] = assignment
                changed = True

        for team_index in range(2):
            team_vectors = [
                vector
                for vector, assignment in zip(vectors, assignments)
                if assignment == team_index
            ]
            centroid = mean_vector(team_vectors)
            if centroid is not None:
                centroids[team_index] = centroid

        if not changed:
            break

    team_info = {}
    for team_index, centroid in enumerate(centroids):
        team_id = f"team_{team_index + 1}"
        team_info[team_id] = {
            "avg_rgb": [round(value, 2) for value in centroid],
            "tracks": 0,
        }

    track_to_team = {}
    for track, assignment in zip(candidates, assignments):
        team_id = f"team_{assignment + 1}"
        track_to_team[track["track_id"]] = team_id
        team_info[team_id]["tracks"] += 1

    for track in tracks:
        track["team_id"] = track_to_team.get(track["track_id"])

    return tracks, team_info


def write_stats(
    config,
    stats_path,
    input_path,
    output_path,
    args,
    frame_index,
    processed_frames,
    ball_visible_frames,
    status_counts,
    track_summaries,
    frame_metrics,
):
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    tracks = [summary.to_dict() for summary in sorted(track_summaries.values(), key=lambda item: item.track_id)]
    tracks, team_info = assign_team_clusters(tracks, config)
    track_lengths = [track["frames_seen"] for track in tracks]

    payload = {
        "metadata": {
            "input": str(input_path),
            "output": str(output_path),
            "model": args.model,
            "imgsz": args.imgsz,
            "model_conf": args.model_conf,
            "person_conf": args.person_conf,
            "ball_conf": args.ball_conf,
            "min_green_ratio": args.min_green_ratio,
            "min_players_for_play_frame": args.min_players_for_play_frame,
            "max_person_area_ratio_for_closeup": args.max_person_area_ratio_for_closeup,
            "tracking_enabled": bool(args.tracking),
            "tracker": args.tracker if args.tracking else None,
        },
        "summary": {
            "frames_read": frame_index,
            "frames_analyzed": processed_frames,
            "ball_visible_frames": ball_visible_frames,
            "status_counts": status_counts,
            "unique_player_tracks": len(tracks),
            "team_counts": {
                team_id: item["tracks"]
                for team_id, item in team_info.items()
            },
            "avg_track_length_frames": round(sum(track_lengths) / len(track_lengths), 2)
            if track_lengths
            else 0.0,
            "max_track_length_frames": max(track_lengths) if track_lengths else 0,
        },
        "teams": team_info,
        "tracks": tracks,
        "frames": frame_metrics,
    }

    with stats_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    return payload


def team_color(track_id, track_team_map):
    if track_team_map is None:
        return (60, 220, 80)
    if track_id is None:
        return (245, 245, 245)

    team_id = track_team_map.get(int(track_id))
    if team_id == "team_1":
        return (230, 100, 40)
    if team_id == "team_2":
        return (40, 40, 230)
    return (245, 245, 245)


def annotate_frame(
    frame,
    persons,
    ball,
    ball_from_memory,
    status,
    frame_index,
    fps_estimate,
    config,
    track_team_map=None,
):
    visual_scale = annotation_resolution_scale(frame, config)
    base_person_label_scale = 0.45
    person_label_scale = base_person_label_scale * visual_scale * float(
        nested_get(config, ["annotation", "person_label_scale_ratio"], 0.40)
    )
    person_label_alpha = float(
        nested_get(config, ["annotation", "person_label_background_alpha"], 0.50)
    )
    person_label_offset = int(
        round(int(nested_get(config, ["annotation", "person_label_offset_px"], 4)) * visual_scale)
    )

    for person in persons:
        marker_color = team_color(person.track_id, track_team_map)
        draw_person_marker(frame, person, config, marker_color)
        person_label = f"#{person.track_id} {person.conf:.2f}" if person.track_id is not None else f"person {person.conf:.2f}"
        draw_label(
            frame,
            person_label,
            person.x1,
            person.y2 + person_label_offset,
            marker_color,
            fg_color=(0, 0, 0) if marker_color == (245, 245, 245) else (255, 255, 255),
            scale=person_label_scale,
            bg_alpha=person_label_alpha,
        )

    if ball is not None:
        color = (0, 255, 255) if not ball_from_memory else (0, 165, 255)
        cx, cy = ball.center
        cv2.rectangle(frame, (ball.x1, ball.y1), (ball.x2, ball.y2), color, 2)
        cv2.circle(frame, (cx, cy), 5, color, -1)
        label = f"ball {ball.conf:.2f}" if not ball_from_memory else "ball memory"
        draw_label(frame, label, ball.x1, ball.y1, color, fg_color=(0, 0, 0))

    draw_status_panel(frame, status, frame_index, persons, ball, ball_from_memory, fps_estimate)


def track_team_map_from_stats(stats_payload):
    if not stats_payload:
        return {}
    return {
        int(track["track_id"]): track.get("team_id")
        for track in stats_payload.get("tracks", [])
        if track.get("track_id") is not None
    }


def render_two_pass_video(input_path, output_path, fps, width, height, frame_annotations, config, track_team_map):
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo reabrir el video para render en dos pasadas: {input_path}")

    writer = make_writer(output_path, fps, width, height)
    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_index += 1
        annotation = frame_annotations.get(frame_index)
        if annotation is not None:
            annotate_frame(
                frame,
                annotation.persons,
                annotation.ball,
                annotation.ball_from_memory,
                annotation.status,
                annotation.frame_index,
                annotation.fps_estimate,
                config,
                track_team_map,
            )
        writer.write(frame)

    cap.release()
    writer.release()


def main():
    args = parse_args()
    config = load_config(DEFAULT_CONFIG_PATH)

    input_path = Path(args.input)
    output_path = make_output_path(input_path, args.output)
    stats_path = make_stats_path(input_path, args.stats_output, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    two_pass_team_render = args.team_render_mode == "two-pass"

    if not input_path.exists():
        raise FileNotFoundError(f"No existe el video de entrada: {input_path}")

    detection_model = YOLO(args.model)
    tracking_model = YOLO(args.model) if args.tracking else detection_model
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    writer = None
    if not two_pass_team_render:
        try:
            writer = make_writer(output_path, fps, width, height)
        except RuntimeError:
            cap.release()
            raise

    print("======================================")
    print("football-ai-analysis | video_analise v2")
    print("======================================")
    print(f"Entrada: {input_path}")
    print(f"Salida:  {output_path}")
    print(f"Modelo:  {args.model}")
    print(f"Tracking: {'on' if args.tracking else 'off'} | Tracker: {args.tracker if args.tracking else '-'}")
    print(f"Frames:  {total_frames} | FPS: {fps:.2f} | Size: {width}x{height}")
    print()

    frame_index = 0
    processed_frames = 0
    status_counts = {}
    ball_visible_frames = 0
    ball_memory = BallMemory()
    track_summaries = {}
    frame_metrics = []
    frame_annotations = {}
    start_tick = cv2.getTickCount()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_index += 1
        should_process = frame_index % max(1, args.process_every) == 0

        if should_process:
            processed_frames += 1
            common_infer_kwargs = {
                "source": frame,
                "imgsz": args.imgsz,
                "device": args.device,
                "verbose": False,
            }
            detection_results = detection_model.predict(
                **common_infer_kwargs,
                conf=args.model_conf,
                classes=[0, 32],
            )
            persons, ball_candidates = detections_from_result(
                detection_results[0],
                args,
                config,
                width,
                height,
            )

            if args.tracking:
                tracking_results = tracking_model.track(
                    **common_infer_kwargs,
                    conf=args.person_conf,
                    classes=[0],
                    persist=True,
                    tracker=args.tracker,
                )
                tracked_persons, _ = detections_from_result(
                    tracking_results[0],
                    args,
                    config,
                    width,
                    height,
                )
                assign_track_ids(persons, tracked_persons, config)
            selected_ball = select_ball(ball_candidates, ball_memory)
            ball_from_memory = False

            if selected_ball is not None:
                ball_memory.detection = selected_ball
                ball_memory.missed_frames = 0
            else:
                ball_memory.missed_frames += 1
                if (
                    ball_memory.detection is not None
                    and is_ignored_ball_candidate(ball_memory.detection, config, width, height)
                ):
                    ball_memory.detection = None
                if (
                    ball_memory.detection is not None
                    and ball_memory.missed_frames <= args.ball_memory_frames
                ):
                    selected_ball = ball_memory.detection
                    ball_from_memory = True
                else:
                    ball_memory.detection = None

            visible_ball = selected_ball is not None and not ball_from_memory
            if visible_ball:
                ball_visible_frames += 1

            status = classify_frame(frame, persons, selected_ball is not None, config, args)
            if (
                status == "CLOSE_UP"
                and ball_from_memory
                and bool(nested_get(config, ["frame_analysis", "suppress_ball_memory_on_closeup"], True))
            ):
                selected_ball = None
                ball_from_memory = False

            status_counts[status] = status_counts.get(status, 0) + 1
            update_track_summaries(track_summaries, persons, frame_index, frame, config)

            if bool(nested_get(config, ["stats", "write_frame_metrics"], True)):
                frame_metrics.append(
                    build_frame_metrics(
                        frame_index,
                        status,
                        persons,
                        selected_ball,
                        ball_from_memory,
                    )
                )

            elapsed = (cv2.getTickCount() - start_tick) / cv2.getTickFrequency()
            fps_estimate = processed_frames / elapsed if elapsed > 0 else 0.0
            if two_pass_team_render:
                frame_annotations[frame_index] = FrameAnnotation(
                    frame_index=frame_index,
                    status=status,
                    persons=list(persons),
                    ball=selected_ball,
                    ball_from_memory=ball_from_memory,
                    fps_estimate=fps_estimate,
                )
            else:
                annotate_frame(
                    frame,
                    persons,
                    selected_ball,
                    ball_from_memory,
                    status,
                    frame_index,
                    fps_estimate,
                    config,
                )

        if writer is not None:
            writer.write(frame)

        if frame_index % 50 == 0:
            print(f"Procesados {frame_index}/{total_frames} frames...")

    cap.release()
    if writer is not None:
        writer.release()

    print()
    print("======================================")
    print("RESUMEN")
    print("======================================")
    print(f"Frames leidos: {frame_index}")
    print(f"Frames analizados con YOLO: {processed_frames}")
    print(f"Frames con balon visible: {ball_visible_frames}")
    print(f"Tracks de jugadores unicos: {len(track_summaries)}")
    for status, count in sorted(status_counts.items()):
        percentage = (count / processed_frames) * 100 if processed_frames else 0.0
        print(f"{status}: {count} ({percentage:.2f}%)")
    stats_payload = None

    if bool(nested_get(config, ["stats", "enabled"], True)):
        stats_payload = write_stats(
            config,
            stats_path,
            input_path,
            output_path,
            args,
            frame_index,
            processed_frames,
            ball_visible_frames,
            status_counts,
            track_summaries,
            frame_metrics,
        )
        print(f"Metricas generadas: {stats_path}")

    if two_pass_team_render:
        track_team_map = track_team_map_from_stats(stats_payload)
        render_two_pass_video(
            input_path,
            output_path,
            fps,
            width,
            height,
            frame_annotations,
            config,
            track_team_map,
        )

    print(f"Video generado: {output_path}")


if __name__ == "__main__":
    main()

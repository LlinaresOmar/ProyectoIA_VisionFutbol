import argparse
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
        "--process-every",
        type=int,
        default=int(nested_get(config, ["video", "process_every_n_frames"], 1)),
        help="Procesar uno de cada N frames. Por defecto procesa todos.",
    )
    return parser.parse_args()


def make_output_path(input_path, explicit_output):
    if explicit_output:
        return Path(explicit_output)

    output_dir = Path("videos/output")
    return output_dir / f"{input_path.stem}_analysed.mp4"


def clamp_box(box, width, height):
    x1, y1, x2, y2 = box
    return (
        max(0, min(width - 1, int(x1))),
        max(0, min(height - 1, int(y1))),
        max(0, min(width - 1, int(x2))),
        max(0, min(height - 1, int(y2))),
    )


def green_ratio(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 35, 35])
    upper_green = np.array([95, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    return float(cv2.countNonZero(mask)) / float(frame.shape[0] * frame.shape[1])


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


def classify_frame(frame, persons, visible_ball, config):
    height, width = frame.shape[:2]
    frame_area = width * height
    min_players = int(nested_get(config, ["frame_analysis", "min_players_for_play_frame"], 4))
    min_green = float(nested_get(config, ["frame_analysis", "min_green_ratio"], 0.35))
    max_closeup_area = float(
        nested_get(config, ["frame_analysis", "max_person_area_ratio_for_closeup"], 0.25)
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
    ball_text = "visible" if ball and not ball_from_memory else "memory" if ball else "not visible"
    lines = [
        f"Frame {frame_index} | {status}",
        f"Persons: {len(persons)} | Ball: {ball_text} | FPS proc: {fps_estimate:.2f}",
    ]

    cv2.rectangle(frame, (8, 8), (390, 62), (0, 0, 0), -1)
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

    for box in result.boxes:
        class_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        x1, y1, x2, y2 = clamp_box(box.xyxy[0].cpu().numpy(), width, height)
        detection = Detection(x1=x1, y1=y1, x2=x2, y2=y2, conf=conf)

        if class_id == person_class_id and conf >= args.person_conf:
            persons.append(detection)
        elif (
            class_id == ball_class_id
            and conf >= args.ball_conf
            and not is_ignored_ball_candidate(detection, config, width, height)
        ):
            balls.append(detection)

    return persons, balls


def draw_person_marker(frame, person, config):
    color = (60, 220, 80)
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


def annotate_frame(frame, persons, ball, ball_from_memory, status, frame_index, fps_estimate, config):
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
        draw_person_marker(frame, person, config)
        draw_label(
            frame,
            f"person {person.conf:.2f}",
            person.x1,
            person.y2 + person_label_offset,
            (30, 120, 50),
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


def main():
    args = parse_args()
    config = load_config(DEFAULT_CONFIG_PATH)

    input_path = Path(args.input)
    output_path = make_output_path(input_path, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"No existe el video de entrada: {input_path}")

    model = YOLO(args.model)
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"No se pudo crear el video de salida: {output_path}")

    print("======================================")
    print("football-ai-analysis | video_analise v1")
    print("======================================")
    print(f"Entrada: {input_path}")
    print(f"Salida:  {output_path}")
    print(f"Modelo:  {args.model}")
    print(f"Frames:  {total_frames} | FPS: {fps:.2f} | Size: {width}x{height}")
    print()

    frame_index = 0
    processed_frames = 0
    status_counts = {}
    ball_visible_frames = 0
    ball_memory = BallMemory()
    start_tick = cv2.getTickCount()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_index += 1
        should_process = frame_index % max(1, args.process_every) == 0

        if should_process:
            processed_frames += 1
            results = model.predict(
                source=frame,
                imgsz=args.imgsz,
                conf=args.model_conf,
                classes=[0, 32],
                device=args.device,
                verbose=False,
            )
            persons, ball_candidates = detections_from_result(results[0], args, config, width, height)
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

            status = classify_frame(frame, persons, selected_ball is not None, config)
            if (
                status == "CLOSE_UP"
                and ball_from_memory
                and bool(nested_get(config, ["frame_analysis", "suppress_ball_memory_on_closeup"], True))
            ):
                selected_ball = None
                ball_from_memory = False

            status_counts[status] = status_counts.get(status, 0) + 1

            elapsed = (cv2.getTickCount() - start_tick) / cv2.getTickFrequency()
            fps_estimate = processed_frames / elapsed if elapsed > 0 else 0.0
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

        writer.write(frame)

        if frame_index % 50 == 0:
            print(f"Procesados {frame_index}/{total_frames} frames...")

    cap.release()
    writer.release()

    print()
    print("======================================")
    print("RESUMEN")
    print("======================================")
    print(f"Frames leidos: {frame_index}")
    print(f"Frames analizados con YOLO: {processed_frames}")
    print(f"Frames con balon visible: {ball_visible_frames}")
    for status, count in sorted(status_counts.items()):
        percentage = (count / processed_frames) * 100 if processed_frames else 0.0
        print(f"{status}: {count} ({percentage:.2f}%)")
    print(f"Video generado: {output_path}")


if __name__ == "__main__":
    main()

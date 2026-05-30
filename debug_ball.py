from pathlib import Path

import cv2
from ultralytics import YOLO


VIDEO_PATH = Path("videos/clips/prepared/clip_00m00s_20s.mp4")
OUTPUT_PATH = Path("videos/output/debug_ball_clip_00m00s_20s.mp4")

MODEL_PATH = "yolo26n.pt"

DEVICE = "cpu"
IMGSZ = 640
MODEL_CONF = 0.05

PERSON_CLASS_ID = 0
BALL_CLASS_ID = 32

PERSON_CONF = 0.25
BALL_CONF = 0.05


def draw_label(frame, text, x, y, color):
    cv2.rectangle(frame, (x, y - 22), (x + len(text) * 9 + 8, y), color, -1)
    cv2.putText(
        frame,
        text,
        (x + 4, y - 6),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (0, 0, 0),
        1,
        cv2.LINE_AA,
    )


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(str(VIDEO_PATH))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el vídeo: {VIDEO_PATH}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUTPUT_PATH), fourcc, fps, (width, height))

    frame_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_index += 1

        results = model.predict(
            source=frame,
            imgsz=IMGSZ,
            conf=MODEL_CONF,
            classes=[PERSON_CLASS_ID, BALL_CLASS_ID],
            device=DEVICE,
            verbose=False,
        )

        result = results[0]

        persons = []
        balls = []

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

                if class_id == PERSON_CLASS_ID and conf >= PERSON_CONF:
                    persons.append((x1, y1, x2, y2, conf))

                elif class_id == BALL_CLASS_ID and conf >= BALL_CONF:
                    balls.append((x1, y1, x2, y2, conf))

        # Dibujar personas
        for x1, y1, x2, y2, conf in persons:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 220, 80), 1)

        # Dibujar todos los candidatos a balón
        for x1, y1, x2, y2, conf in balls:
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)
            draw_label(frame, f"ball {conf:.2f}", x1, max(y1, 24), (0, 255, 255))

        status_text = (
            f"Frame: {frame_index} | Personas: {len(persons)} | "
            f"Candidatos balon: {len(balls)}"
        )

        cv2.rectangle(frame, (10, 10), (620, 42), (0, 0, 0), -1)
        cv2.putText(
            frame,
            status_text,
            (20, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        writer.write(frame)

        if frame_index % 50 == 0:
            print(f"Procesados {frame_index} frames...")

    cap.release()
    writer.release()

    print()
    print(f"Vídeo generado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
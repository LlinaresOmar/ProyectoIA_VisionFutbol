from collections import Counter
from pathlib import Path

from ultralytics import YOLO


VIDEO_PATH = Path("videos/clips/prepared/clip_00m00s_20s.mp4")
MODEL_PATH = "yolo26n.pt"

IMGSZ = 640
CONF = 0.05
DEVICE = "cpu"


def main():
    model = YOLO(MODEL_PATH)

    total_detections = Counter()
    frames_with_class = Counter()
    total_frames = 0

    results_stream = model.predict(
        source=str(VIDEO_PATH),
        imgsz=IMGSZ,
        conf=CONF,
        device=DEVICE,
        stream=True,
        verbose=False,
    )

    for frame_index, result in enumerate(results_stream, start=1):
        total_frames += 1

        if result.boxes is None or len(result.boxes) == 0:
            continue

        class_ids = result.boxes.cls.cpu().numpy().astype(int)
        classes_in_frame = set(class_ids)

        for class_id in class_ids:
            class_name = model.names[int(class_id)]
            total_detections[class_name] += 1

        for class_id in classes_in_frame:
            class_name = model.names[int(class_id)]
            frames_with_class[class_name] += 1

        if frame_index % 50 == 0:
            print(f"Procesados {frame_index} frames...")

    print()
    print("======================================")
    print("RESUMEN DEL CLIP")
    print("======================================")
    print(f"Vídeo: {VIDEO_PATH}")
    print(f"Modelo: {MODEL_PATH}")
    print(f"Frames procesados: {total_frames}")
    print(f"imgsz: {IMGSZ}")
    print(f"conf: {CONF}")
    print()

    print("Detecciones totales por clase:")
    for class_name, count in total_detections.most_common():
        print(f"  {class_name}: {count}")

    print()
    print("Frames en los que aparece cada clase:")
    for class_name, count in frames_with_class.most_common():
        percentage = (count / total_frames) * 100 if total_frames else 0
        print(f"  {class_name}: {count}/{total_frames} frames ({percentage:.2f}%)")


if __name__ == "__main__":
    main()
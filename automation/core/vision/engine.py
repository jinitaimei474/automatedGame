from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
from typing import Iterable, Protocol


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bbox: tuple[float, float, float, float]

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return round((x1 + x2) / 2), round((y1 + y2) / 2)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def select_detection(detections: Iterable[Detection], label: str, min_confidence: float = 0.5) -> Detection | None:
    candidates = [item for item in detections if item.label == label and item.confidence >= min_confidence]
    return max(candidates, key=lambda item: item.confidence, default=None)


def annotate_detections(image: bytes, detections: Iterable[Detection]) -> bytes:
    """Draw detections for the UI preview; returns the original PNG if OpenCV cannot decode it."""
    import cv2
    import numpy as np

    frame = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return image
    for item in detections:
        x1, y1, x2, y2 = (int(value) for value in item.bbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (59, 214, 113), 2)
        cv2.putText(frame, f"{item.label} {item.confidence:.2f}", (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (59, 214, 113), 2)
    ok, encoded = cv2.imencode(".png", frame)
    return encoded.tobytes() if ok else image


class Detector(Protocol):
    def detect(self, image: bytes) -> list[Detection]: ...


class VisionEngine:
    def __init__(self, model_path: str, confidence: float = 0.6) -> None:
        model = Path(model_path)
        if not model.is_file():
            raise FileNotFoundError(f"YOLO 模型不存在: {model_path}")
        if model.suffix.lower() not in {".pt", ".onnx"}:
            raise ValueError("YOLO 模型必须是 .pt 或 .onnx 文件")
        os.environ.setdefault("YOLO_CONFIG_DIR", str(Path.cwd() / ".runtime" / "ultralytics"))
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("请安装 ultralytics 后使用正式模型") from exc
        self.model = YOLO(model_path)
        self.confidence = confidence

    def detect(self, image: bytes) -> list[Detection]:
        import cv2
        import numpy as np

        frame = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
        results = self.model.predict(frame, conf=self.confidence, verbose=False)
        detections: list[Detection] = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                detections.append(Detection(result.names[cls_id], float(box.conf[0]), tuple(float(v) for v in box.xyxy[0])))
        return detections


class MockVisionEngine:
    def __init__(self, frames: list[list[Detection]] | None = None) -> None:
        self.frames = frames or []
        self.index = 0

    def detect(self, image: bytes = b"") -> list[Detection]:
        if not self.frames:
            return []
        frame = self.frames[min(self.index, len(self.frames) - 1)]
        self.index += 1
        return frame

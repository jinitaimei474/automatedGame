from __future__ import annotations

from collections import Counter

from automation.core.vision import Detection


class CrownConfirmationError(RuntimeError):
    pass


class CrownResultDetector:
    RESULT_LABELS = {f"result_crowns_{count}": count for count in range(4)}

    def __init__(self, required_frames: int = 3, confidence: float = 0.75) -> None:
        if required_frames < 1:
            raise ValueError("required_frames must be positive")
        self.required_frames = required_frames
        self.confidence = confidence
        self._observations: list[int | None] = []

    def reset(self) -> None:
        self._observations.clear()

    def observe(self, detections: list[Detection]) -> int | None:
        candidates = [
            (self.RESULT_LABELS[item.label], item.confidence)
            for item in detections
            if item.label in self.RESULT_LABELS and item.confidence >= self.confidence
        ]
        value = max(candidates, key=lambda item: item[1])[0] if candidates else None
        self._observations.append(value)
        if len(self._observations) > self.required_frames:
            self._observations.pop(0)
        if len(self._observations) == self.required_frames and len(set(self._observations)) == 1 and value is not None:
            return value
        return None

    def confirm_frames(self, frames: list[list[Detection]]) -> int:
        self.reset()
        for frame in frames:
            confirmed = self.observe(frame)
            if confirmed is not None:
                return confirmed
        values = [value for value in self._observations if value is not None]
        detail = dict(Counter(values))
        raise CrownConfirmationError(f"皇冠识别结果未达到连续 {self.required_frames} 帧一致: {detail}")


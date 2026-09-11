from __future__ import annotations

import time
from typing import Callable

from automation.core.vision import Detection, Detector, select_detection
from automation.core.workflow import CancellationToken


class ScreenMatcher:
    def __init__(self, detector: Detector, screenshot: Callable[[], bytes], token: CancellationToken) -> None:
        self.detector = detector
        self.screenshot = screenshot
        self.token = token

    async def wait_for(self, label: str, timeout: float, interval: float = 0.5, confidence: float = 0.5) -> Detection:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.token.throw_if_cancelled()
            detection = select_detection(self.detector.detect(self.screenshot()), label, confidence)
            if detection:
                return detection
            await self.token.sleep(interval)
        raise TimeoutError(f"等待目标超时: {label}")


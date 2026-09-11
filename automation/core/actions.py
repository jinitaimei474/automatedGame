from __future__ import annotations

import random

from automation.core.adb import AdbClient
from automation.core.vision import Detection
from automation.core.workflow import CancellationToken


class ActionExecutor:
    def __init__(self, adb: AdbClient, token: CancellationToken, safe_offset: int = 3) -> None:
        self.adb = adb
        self.token = token
        self.safe_offset = safe_offset

    async def click_detection(self, detection: Detection) -> None:
        self.token.throw_if_cancelled()
        x, y = detection.center
        x += random.randint(-self.safe_offset, self.safe_offset)
        y += random.randint(-self.safe_offset, self.safe_offset)
        await self.adb.tap(x, y)

    async def swipe(self, start: tuple[int, int], end: tuple[int, int], duration_ms: int) -> None:
        self.token.throw_if_cancelled()
        await self.adb.swipe(*start, *end, duration_ms)


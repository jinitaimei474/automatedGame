from __future__ import annotations

from automation.core.events import EventBus
from automation.core.safety import SafetyGuard, SafetyViolation
from automation.core.vision import Detection
from automation.core.workflow import CancellationToken


class DailyShopFreeItemTask:
    def __init__(self, event_bus: EventBus, token: CancellationToken, guard: SafetyGuard | None = None) -> None:
        self.event_bus = event_bus
        self.token = token
        self.guard = guard or SafetyGuard()

    async def evaluate_shop(self, detections: list[Detection]) -> str:
        self.token.throw_if_cancelled()
        try:
            if self.guard.can_claim_free_item(detections):
                await self.event_bus.emit("log_message", {"level": "INFO", "message": "已确认每日商人与免费标识，可以领取"})
                return "CLAIM_ALLOWED"
        except SafetyViolation as exc:
            await self.event_bus.emit("task_paused", {"reason": "SAFETY_PAUSE", "message": str(exc)})
            return "PAUSED"
        labels = {item.label for item in detections}
        if "claimed_state" in labels:
            return "ALREADY_CLAIMED"
        return "NOT_CONFIRMED"

    async def run_mock(self) -> str:
        await self.event_bus.emit("task_started", {"status": "RUNNING"})
        result = await self.evaluate_shop([
            Detection("daily_trader", 0.96, (50, 80, 1000, 700)),
            Detection("free_item", 0.94, (200, 220, 450, 520)),
            Detection("free_label", 0.99, (250, 470, 390, 520)),
        ])
        if result == "CLAIM_ALLOWED":
            await self.event_bus.emit("task_completed", {"status": "COMPLETED", "stopReason": "FREE_ITEM_CLAIMED"})
        return result


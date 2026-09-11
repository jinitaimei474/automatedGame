from __future__ import annotations

from dataclasses import dataclass

from automation.core.vision import Detection


class SafetyViolation(RuntimeError):
    pass


@dataclass
class SafetyGuard:
    max_retries: int = 3
    paid_labels: frozenset[str] = frozenset({"currency_price", "payment_confirmation"})
    blocking_labels: frozenset[str] = frozenset({"network_error", "maintenance_notice", "login_screen", "unknown_blocking_popup"})

    def inspect(self, detections: list[Detection]) -> None:
        labels = {item.label for item in detections}
        paid = labels & self.paid_labels
        if paid:
            raise SafetyViolation(f"检测到疑似付费内容，已暂停: {', '.join(sorted(paid))}")
        blocked = labels & self.blocking_labels
        if blocked:
            raise SafetyViolation(f"检测到需要用户处理的页面，已暂停: {', '.join(sorted(blocked))}")

    def can_claim_free_item(self, detections: list[Detection]) -> bool:
        self.inspect(detections)
        labels = {item.label for item in detections}
        return "daily_trader" in labels and "free_label" in labels and "free_item" in labels


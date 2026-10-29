from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum


class StopReason(StrEnum):
    TARGET_REACHED = "TARGET_REACHED"
    USER_STOPPED = "USER_STOPPED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    CROWN_DETECTION_FAILED = "CROWN_DETECTION_FAILED"
    SAFETY_PAUSE = "SAFETY_PAUSE"
    ERROR = "ERROR"
    ROUND_LIMIT = "ROUND_LIMIT"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CrownProgressTracker:
    target_crowns: int
    earned_crowns: int = 0
    round_count: int = 0
    last_round_crowns: int | None = 0
    last_confirmed_result_id: str | None = None
    started_at: str = ""
    completed_at: str | None = None
    stop_reason: StopReason | None = None
    target_rounds: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.target_crowns, int) or isinstance(self.target_crowns, bool) or not 1 <= self.target_crowns <= 9999:
            raise ValueError("target_crowns must be an integer between 1 and 9999")
        if not self.started_at:
            self.started_at = utc_now()
        if self.target_rounds is not None and (type(self.target_rounds) is not int or not 1 <= self.target_rounds <= 1000):
            raise ValueError('target_rounds must be an integer between 1 and 1000')

    @property
    def remaining_crowns(self) -> int:
        return max(self.target_crowns - self.earned_crowns, 0)

    @property
    def target_reached(self) -> bool:
        if self.target_rounds is not None:
            return self.round_count >= self.target_rounds
        return self.earned_crowns >= self.target_crowns

    def record_result(self, result_id: str, crowns: int | None) -> bool:
        if crowns not in (0, 1, 2, 3) and not (crowns is None and self.target_rounds is not None):
            raise ValueError("round crowns must be 0, 1, 2 or 3")
        if result_id == self.last_confirmed_result_id:
            return False
        self.last_confirmed_result_id = result_id
        self.last_round_crowns = crowns
        self.earned_crowns += crowns or 0
        self.round_count += 1
        if self.target_reached:
            self.complete(StopReason.TARGET_REACHED)
        return True

    def complete(self, reason: StopReason) -> None:
        self.stop_reason = reason
        self.completed_at = self.completed_at or utc_now()

    def as_protocol_dict(self, status: str = "RUNNING") -> dict[str, object]:
        raw = asdict(self)
        return {
            "targetRounds": self.target_rounds,
            "remainingRounds": max(self.target_rounds - self.round_count, 0) if self.target_rounds is not None else None,
            "targetCrowns": self.target_crowns,
            "earnedCrowns": self.earned_crowns,
            "remainingCrowns": self.remaining_crowns,
            "roundCount": self.round_count,
            "lastRoundCrowns": self.last_round_crowns,
            "lastConfirmedResultId": self.last_confirmed_result_id,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "stopReason": self.stop_reason.value if self.stop_reason else None,
            "status": status,
        }

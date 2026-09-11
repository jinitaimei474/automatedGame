from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Awaitable, Callable

from automation.core.events import EventBus
from .cancellation import CancellationToken


class WorkflowState(StrEnum):
    IDLE = "IDLE"
    VALIDATE_PARAMETERS = "VALIDATE_PARAMETERS"
    LAUNCH_EMULATOR = "LAUNCH_EMULATOR"
    CONNECT_DEVICE = "CONNECT_DEVICE"
    LAUNCH_GAME = "LAUNCH_GAME"
    WAIT_HOME = "WAIT_HOME"
    OPEN_GAME_MODES = "OPEN_GAME_MODES"
    SCROLL_FOR_CLASSIC_1V1 = "SCROLL_FOR_CLASSIC_1V1"
    SELECT_CLASSIC_1V1 = "SELECT_CLASSIC_1V1"
    START_MATCH = "START_MATCH"
    WAIT_MATCH = "WAIT_MATCH"
    IN_BATTLE = "IN_BATTLE"
    WAIT_RESULT = "WAIT_RESULT"
    DETECT_EARNED_CROWNS = "DETECT_EARNED_CROWNS"
    CONFIRM_EARNED_CROWNS = "CONFIRM_EARNED_CROWNS"
    UPDATE_CROWN_PROGRESS = "UPDATE_CROWN_PROGRESS"
    DISMISS_REWARDS = "DISMISS_REWARDS"
    CHECK_CROWN_TARGET = "CHECK_CROWN_TARGET"
    START_NEXT_ROUND = "START_NEXT_ROUND"
    TARGET_REACHED = "TARGET_REACHED"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class WorkflowEngine:
    def __init__(self, event_bus: EventBus, token: CancellationToken) -> None:
        self.event_bus = event_bus
        self.token = token
        self.state = WorkflowState.IDLE
        self._resume = asyncio.Event()
        self._resume.set()

    async def transition(self, state: WorkflowState) -> None:
        self.token.throw_if_cancelled()
        self.state = state
        await self.event_bus.emit("task_state_changed", {"state": state.value})

    async def checkpoint(self) -> None:
        self.token.throw_if_cancelled()
        await self._resume.wait()
        self.token.throw_if_cancelled()

    async def pause(self) -> None:
        self._resume.clear()
        self.state = WorkflowState.PAUSED
        await self.event_bus.emit("task_paused", {"state": self.state.value})

    async def resume(self) -> None:
        self._resume.set()
        await self.event_bus.emit("log_message", {"level": "INFO", "message": "任务已继续"})

    async def retry(self, operation: Callable[[], Awaitable[bool]], max_retries: int, delay: float = 0.1) -> bool:
        for attempt in range(max_retries + 1):
            await self.checkpoint()
            if await operation():
                return True
            if attempt < max_retries:
                await self.token.sleep(delay)
        return False


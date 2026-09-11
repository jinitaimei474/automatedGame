from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from automation.core.events import EventBus
from automation.core.tasks import CrownProgressTracker, StopReason
from automation.core.workflow import CancelledError, CancellationToken, WorkflowEngine, WorkflowState
from automation.games.clash_royale.detectors import CrownConfirmationError, CrownResultDetector
from automation.core.vision import Detection


class BattlePolicy(ABC):
    @abstractmethod
    async def run(self, token: CancellationToken, event_bus: EventBus) -> None:
        """Control or track one battle until its result page is available."""


class TrackingOnlyBattlePolicy(BattlePolicy):
    """MVP policy: follows battle state only and deliberately sends no card actions."""

    async def run(self, token: CancellationToken, event_bus: EventBus) -> None:
        await event_bus.emit("log_message", {"level": "INFO", "message": "MVP 对局策略仅跟踪状态，不执行出牌"})
        await token.sleep(0.04)


@dataclass
class MockRound:
    crowns: int
    inconsistent: bool = False


class Classic1v1LoopTask:
    def __init__(
        self,
        target_crowns: int,
        event_bus: EventBus,
        token: CancellationToken,
        mock_rounds: list[int] | None = None,
        confirmation_frames: int = 3,
        max_crown_failures: int = 5,
        battle_policy: BattlePolicy | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.token = token
        self.engine = WorkflowEngine(event_bus, token)
        self.progress = CrownProgressTracker(target_crowns)
        self.mock_rounds = mock_rounds or [1, 2, 2, 3]
        self.crown_detector = CrownResultDetector(confirmation_frames)
        self.max_crown_failures = max_crown_failures
        self.battle_policy = battle_policy or TrackingOnlyBattlePolicy()
        self.next_round_count = 0

    async def _state(self, state: WorkflowState, delay: float = 0.02) -> None:
        await self.engine.transition(state)
        await self.engine.checkpoint()
        await self.token.sleep(delay)

    async def _emit_progress(self, status: str = "RUNNING") -> None:
        await self.event_bus.emit("task_progress_updated", self.progress.as_protocol_dict(status))

    def _mock_frames(self, crowns: int) -> list[list[Detection]]:
        detection = Detection(f"result_crowns_{crowns}", 0.97, (440, 220, 620, 360))
        return [[detection] for _ in range(self.crown_detector.required_frames)]

    async def run(self) -> CrownProgressTracker:
        await self.event_bus.emit("task_started", self.progress.as_protocol_dict())
        try:
            for state in (
                WorkflowState.VALIDATE_PARAMETERS,
                WorkflowState.LAUNCH_EMULATOR,
                WorkflowState.CONNECT_DEVICE,
                WorkflowState.LAUNCH_GAME,
                WorkflowState.WAIT_HOME,
                WorkflowState.OPEN_GAME_MODES,
                WorkflowState.SCROLL_FOR_CLASSIC_1V1,
                WorkflowState.SELECT_CLASSIC_1V1,
            ):
                await self._state(state)

            for index, crowns in enumerate(self.mock_rounds, start=1):
                for state in (WorkflowState.START_MATCH, WorkflowState.WAIT_MATCH, WorkflowState.IN_BATTLE):
                    await self._state(state)
                await self.battle_policy.run(self.token, self.event_bus)
                await self._state(WorkflowState.WAIT_RESULT)
                await self._state(WorkflowState.DETECT_EARNED_CROWNS)
                frames = self._mock_frames(crowns)
                await self.event_bus.emit("crown_result_detected", {"round": index, "observations": [crowns] * len(frames)})
                await self._state(WorkflowState.CONFIRM_EARNED_CROWNS)
                confirmed: int | None = None
                for failure_count in range(1, self.max_crown_failures + 1):
                    try:
                        confirmed = self.crown_detector.confirm_frames(frames)
                        break
                    except CrownConfirmationError:
                        await self.event_bus.emit("log_message", {
                            "level": "WARNING",
                            "message": f"皇冠识别连续确认失败（{failure_count}/{self.max_crown_failures}），已保存现场并重试",
                        })
                        if failure_count < self.max_crown_failures:
                            await self.token.sleep(0.02)
                if confirmed is None:
                    self.progress.complete(StopReason.CROWN_DETECTION_FAILED)
                    await self.engine.pause()
                    await self.event_bus.emit("task_failed", {"message": "皇冠识别达到最大失败次数，任务已暂停并等待用户确认"})
                    return self.progress

                result_id = f"round-{index}-{uuid.uuid4().hex[:8]}"
                await self.event_bus.emit("crown_result_confirmed", {"resultId": result_id, "crowns": confirmed})
                await self._state(WorkflowState.UPDATE_CROWN_PROGRESS)
                self.progress.record_result(result_id, confirmed)
                await self._emit_progress("COMPLETED" if self.progress.target_reached else "RUNNING")
                await self._state(WorkflowState.DISMISS_REWARDS)
                await self._state(WorkflowState.CHECK_CROWN_TARGET)

                if self.progress.target_reached:
                    await self._state(WorkflowState.TARGET_REACHED, 0)
                    await self.event_bus.emit("task_target_reached", self.progress.as_protocol_dict("COMPLETED"))
                    await self.event_bus.emit("task_completed", self.progress.as_protocol_dict("COMPLETED"))
                    return self.progress

                await self._state(WorkflowState.START_NEXT_ROUND)
                self.next_round_count += 1

            raise RuntimeError("Mock 对局数据用尽，尚未达到皇冠目标")
        except CancelledError:
            reason = self.progress.stop_reason or StopReason.USER_STOPPED
            self.progress.complete(reason)
            self.engine.state = WorkflowState.STOPPED
            await self.event_bus.emit("task_stopped", self.progress.as_protocol_dict("STOPPED"))
            return self.progress
        except Exception as exc:
            self.progress.complete(StopReason.ERROR)
            self.engine.state = WorkflowState.ERROR
            await self.event_bus.emit("task_failed", {**self.progress.as_protocol_dict("FAILED"), "message": str(exc)})
            return self.progress

    async def pause(self) -> None:
        await self.engine.pause()

    async def resume(self) -> None:
        await self.engine.resume()

    def stop(self, emergency: bool = False) -> None:
        self.progress.stop_reason = StopReason.EMERGENCY_STOP if emergency else StopReason.USER_STOPPED
        self.token.cancel()

from __future__ import annotations

import asyncio
import base64
import hashlib
import time
from pathlib import Path

from automation.core.actions import ActionExecutor
from automation.core.adb import AdbClient, AdbCommandError
from automation.core.config import AppSettings
from automation.core.emulator import EmulatorManager
from automation.core.events import EventBus
from automation.core.safety import SafetyGuard, SafetyViolation
from automation.core.tasks import CrownProgressTracker, StopReason
from automation.core.vision import Detection, VisionEngine, annotate_detections, select_detection
from automation.core.workflow import CancelledError, CancellationToken, WorkflowEngine, WorkflowState
from automation.games.clash_royale.detectors import CrownResultDetector


class CrownDetectionFailure(RuntimeError):
    pass


class LiveClassic1v1Task:
    """YOLO-driven live runner. It clicks only freshly re-confirmed named targets."""

    def __init__(self, target_crowns: int, settings: AppSettings, event_bus: EventBus, token: CancellationToken) -> None:
        self.settings = settings
        self.event_bus = event_bus
        self.token = token
        self.engine = WorkflowEngine(event_bus, token)
        self.progress = CrownProgressTracker(target_crowns)
        self.adb = AdbClient(settings.adbPath, settings.adbSerial, token, settings.stateTimeoutSeconds)
        self.emulator = EmulatorManager(token)
        self.vision = VisionEngine(settings.modelPath, settings.yoloConfidence)
        self.actions = ActionExecutor(self.adb, token)
        self.guard = SafetyGuard(settings.maxRetries)
        self.crowns = CrownResultDetector(settings.crownConfirmationFrames, settings.crownConfidence)
        self._round_generation = 0

    async def _state(self, state: WorkflowState) -> None:
        await self.engine.transition(state)
        await self.engine.checkpoint()

    async def _capture(self) -> tuple[bytes, list[Detection]]:
        self.token.throw_if_cancelled()
        image = await self.adb.screenshot()
        detections = await asyncio.to_thread(self.vision.detect, image)
        self.guard.inspect(detections)
        try:
            preview = await asyncio.to_thread(annotate_detections, image, detections)
        except (ImportError, RuntimeError):
            preview = image
        await self.event_bus.emit("screenshot_updated", {"image": "data:image/png;base64," + base64.b64encode(preview).decode("ascii")})
        await self.event_bus.emit("detections_updated", {"detections": [item.as_dict() for item in detections]})
        return image, detections

    async def _wait_detection(self, labels: tuple[str, ...], timeout: float | None = None) -> tuple[bytes, Detection]:
        deadline = time.monotonic() + (timeout or self.settings.stateTimeoutSeconds)
        while time.monotonic() < deadline:
            await self.engine.checkpoint()
            image, detections = await self._capture()
            candidates = [item for label in labels if (item := select_detection(detections, label, self.settings.yoloConfidence))]
            if candidates:
                return image, max(candidates, key=lambda item: item.confidence)
            await self.token.sleep(self.settings.inferenceIntervalMs / 1000)
        raise TimeoutError(f"等待识别目标超时: {', '.join(labels)}")

    async def _confirmed_click(self, labels: tuple[str, ...]) -> None:
        _image, first = await self._wait_detection(labels)
        await self.token.sleep(max(self.settings.inferenceIntervalMs / 1000, 0.1))
        _image, second = await self._wait_detection((first.label,), timeout=5)
        await self.actions.click_detection(second)
        await self.event_bus.emit("log_message", {"level": "INFO", "message": f"已点击确认目标: {second.label} ({second.confidence:.2f})"})

    async def _connect_or_launch(self) -> None:
        try:
            await self.adb.resolution()
            return
        except (AdbCommandError, FileNotFoundError):
            if not self.settings.mumuExecutable:
                raise RuntimeError("ADB 未连接且未配置 MuMu 可执行文件")
        await self.emulator.launch(self.settings.mumuExecutable)
        deadline = time.monotonic() + max(self.settings.gameLaunchWaitSeconds, 30)
        while time.monotonic() < deadline:
            try:
                await self.adb.resolution()
                return
            except AdbCommandError:
                await self.token.sleep(1)
        raise TimeoutError("等待 MuMu ADB 设备在线超时")

    async def _find_classic_mode(self) -> None:
        width, height = await self.adb.resolution()
        for _ in range(12):
            _image, detections = await self._capture()
            target = select_detection(detections, "classic_1v1", self.settings.yoloConfidence)
            if target:
                await self.token.sleep(0.15)
                _image, confirmed = await self._wait_detection(("classic_1v1",), timeout=5)
                await self.actions.click_detection(confirmed)
                return
            await self.actions.swipe((width // 2, int(height * 0.78)), (width // 2, int(height * 0.28)), self.settings.swipeDurationMs)
            await self.token.sleep(0.4)
        raise TimeoutError("达到最大滑动次数仍未找到经典 1v1")

    async def _wait_battle_end(self) -> None:
        deadline = time.monotonic() + max(self.settings.stateTimeoutSeconds * 20, 300)
        while time.monotonic() < deadline:
            await self.engine.checkpoint()
            _image, detections = await self._capture()
            labels = {item.label for item in detections}
            if labels & {"battle_end", "victory_screen", "defeat_screen"}:
                return
            await self.token.sleep(max(self.settings.inferenceIntervalMs / 1000, 0.5))
        raise TimeoutError("等待对局结束超时")

    async def _confirm_crown_result(self) -> tuple[str, int]:
        self.crowns.reset()
        for failure in range(1, self.settings.maxCrownFailures + 1):
            image, detections = await self._capture()
            confirmed = self.crowns.observe(detections)
            await self.event_bus.emit("crown_result_detected", {"failureCount": failure, "candidate": confirmed})
            if confirmed is not None:
                digest = hashlib.sha256(image).hexdigest()[:16]
                return f"battle-{self._round_generation}-{digest}", confirmed
            if self.settings.saveDebugScreenshots:
                target = Path(self.settings.debugScreenshotDirectory) / f"crown-failure-{self._round_generation}-{failure}.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(image)
            await self.token.sleep(self.settings.inferenceIntervalMs / 1000)
        raise CrownDetectionFailure("皇冠识别达到最大失败次数，禁止开始下一局")

    async def _optional_cleanup(self) -> None:
        if self.settings.closeGameOnCompletion:
            await self.adb.run("shell", "am", "force-stop", self.settings.clashRoyalePackage)
        if self.settings.closeEmulatorOnCompletion:
            await self.emulator.close_if_owned()

    async def run(self) -> CrownProgressTracker:
        await self.event_bus.emit("task_started", self.progress.as_protocol_dict())
        try:
            await self._state(WorkflowState.VALIDATE_PARAMETERS)
            await self._state(WorkflowState.LAUNCH_EMULATOR); await self._connect_or_launch()
            await self._state(WorkflowState.CONNECT_DEVICE); await self.adb.resolution()
            await self._state(WorkflowState.LAUNCH_GAME); await self.adb.start_app(self.settings.clashRoyalePackage, self.settings.clashRoyaleActivity)
            await self.token.sleep(self.settings.gameLaunchWaitSeconds)
            await self._state(WorkflowState.WAIT_HOME); await self._wait_detection(("home_screen",))
            await self._state(WorkflowState.OPEN_GAME_MODES); await self._confirmed_click(("game_mode_button_1",))
            await self._state(WorkflowState.SCROLL_FOR_CLASSIC_1V1); await self._find_classic_mode()
            await self._state(WorkflowState.SELECT_CLASSIC_1V1)
            while True:
                self._round_generation += 1
                await self._state(WorkflowState.START_MATCH); await self._confirmed_click(("battle_button", "play_again_button"))
                await self._state(WorkflowState.WAIT_MATCH); await self._wait_detection(("matching_screen", "battle_screen"))
                await self._state(WorkflowState.IN_BATTLE); await self._wait_detection(("battle_screen",))
                await self.event_bus.emit("log_message", {"level": "INFO", "message": "MVP BattlePolicy 仅跟踪对局，不执行出牌"})
                await self._state(WorkflowState.WAIT_RESULT); await self._wait_battle_end()
                await self._state(WorkflowState.DETECT_EARNED_CROWNS)
                await self._state(WorkflowState.CONFIRM_EARNED_CROWNS); result_id, crowns = await self._confirm_crown_result()
                await self.event_bus.emit("crown_result_confirmed", {"resultId": result_id, "crowns": crowns})
                await self._state(WorkflowState.UPDATE_CROWN_PROGRESS); self.progress.record_result(result_id, crowns)
                await self.event_bus.emit("task_progress_updated", self.progress.as_protocol_dict("COMPLETED" if self.progress.target_reached else "RUNNING"))
                await self._state(WorkflowState.DISMISS_REWARDS)
                await self._state(WorkflowState.CHECK_CROWN_TARGET)
                if self.progress.target_reached:
                    await self._state(WorkflowState.TARGET_REACHED)
                    await self.event_bus.emit("task_target_reached", self.progress.as_protocol_dict("COMPLETED"))
                    await self.event_bus.emit("task_completed", self.progress.as_protocol_dict("COMPLETED"))
                    await self._optional_cleanup()
                    return self.progress
                await self._state(WorkflowState.START_NEXT_ROUND)
        except CancelledError:
            self.progress.complete(self.progress.stop_reason or StopReason.USER_STOPPED)
            await self.event_bus.emit("task_stopped", self.progress.as_protocol_dict("STOPPED"))
            return self.progress
        except (SafetyViolation, CrownDetectionFailure) as exc:
            self.progress.stop_reason = StopReason.SAFETY_PAUSE if isinstance(exc, SafetyViolation) else StopReason.CROWN_DETECTION_FAILED
            await self.engine.pause()
            await self.event_bus.emit("task_paused", {**self.progress.as_protocol_dict("PAUSED"), "message": str(exc)})
            return self.progress
        except Exception as exc:
            self.progress.complete(StopReason.ERROR)
            await self.event_bus.emit("task_failed", {**self.progress.as_protocol_dict("FAILED"), "message": str(exc)})
            return self.progress

    async def pause(self) -> None:
        await self.engine.pause()

    async def resume(self) -> None:
        await self.engine.resume()

    def stop(self, emergency: bool = False) -> None:
        self.progress.stop_reason = StopReason.EMERGENCY_STOP if emergency else StopReason.USER_STOPPED
        self.token.cancel()

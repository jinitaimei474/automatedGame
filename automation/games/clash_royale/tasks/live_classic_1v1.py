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
from automation.core.vision import Detection, annotate_detections, select_detection
from automation.core.workflow import CancelledError, CancellationToken, WorkflowEngine, WorkflowState
from automation.games.clash_royale.detectors import CrownResultDetector
from automation.core.vision.profile import ProfileDetector, create_detector
from automation.games.clash_royale.rule_policy import RuleBattlePolicy


class CrownDetectionFailure(RuntimeError):
    pass


class LiveClassic1v1Task:
    """Screenshot-driven runner with fixed-deck play and bounded navigation."""

    def __init__(self, target_crowns: int, settings: AppSettings, event_bus: EventBus, token: CancellationToken, *, target_rounds: int | None = None) -> None:
        self.settings = settings
        self.event_bus = event_bus
        self.token = token
        self.engine = WorkflowEngine(event_bus, token)
        self.progress = CrownProgressTracker(target_crowns, target_rounds=target_rounds)
        self.adb = AdbClient(settings.adbPath, settings.adbSerial, token, settings.stateTimeoutSeconds)
        self.emulator = EmulatorManager(token)
        self.vision = create_detector(settings)
        self.rule_vision = self.vision if settings.visionBackend == 'template' else ProfileDetector(settings.visionProfilePath)
        self.rule_vision.validate_battle()
        self.policy = RuleBattlePolicy(self.rule_vision.profile.get('deck', []))
        if settings.maxRounds < 1 or settings.battleTimeoutSeconds < 1:
            raise ValueError('最大局数和对局超时必须大于零')
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
        if self.rule_vision is not self.vision:
            rules = await asyncio.to_thread(self.rule_vision.detect, image)
            detections.extend(d for d in rules if d.label.startswith(('card_', 'elixir_')))
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
            generation = self.engine.pause_generation
            image, detections = await self._capture()
            await self.engine.checkpoint()
            if generation != self.engine.pause_generation:
                continue
            candidates = [item for label in labels if (item := select_detection(detections, label, self.settings.yoloConfidence))]
            if candidates:
                return image, max(candidates, key=lambda item: item.confidence)
            if 'dismiss_popup_button' not in labels and any(d.label == 'dismiss_popup_button' for d in detections):
                await self._confirmed_click(('dismiss_popup_button',))
            await self.token.sleep(self.settings.inferenceIntervalMs / 1000)
        raise TimeoutError(f"等待识别目标超时: {', '.join(labels)}")

    async def _confirmed_click(self, labels: tuple[str, ...]) -> None:
        _image, first = await self._wait_detection(labels)
        for _ in range(5):
            await self.token.sleep(max(self.settings.inferenceIntervalMs / 1000, 0.5))
            _image, second = await self._wait_detection((first.label,), timeout=5)
            if max(abs(a-b) for a,b in zip(first.center, second.center)) <= 12:
                await self.actions.click_detection(second)
                await self.event_bus.emit("log_message", {"level": "INFO", "message": f"已点击确认目标: {second.label} ({second.confidence:.2f})"})
                return
            first = second
        raise SafetyViolation('按钮仍在移动，取消点击')

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
        await self.token.sleep(2)
        for _ in range(20):
            _image, detections = await self._capture()
            target = select_detection(detections, "classic_1v1", self.settings.yoloConfidence)
            if target:
                await self._confirmed_click(('classic_1v1',))
                if self.rule_vision.profile.get('require_mode_ready'):
                    await self._wait_detection(('classic_mode_ready',), timeout=8)
                return
            await self.actions.swipe((width // 2, int(height * 0.78)), (width // 2, int(height * 0.66)), max(self.settings.swipeDurationMs, 800))
            await self.token.sleep(2)
        raise TimeoutError("达到最大滑动次数仍未找到经典 1v1")

    async def _wait_battle_end(self) -> None:
        deadline = time.monotonic() + self.settings.battleTimeoutSeconds
        self.policy.reset()
        last_known = time.monotonic()
        while time.monotonic() < deadline:
            await self.engine.checkpoint()
            generation = self.engine.pause_generation
            _image, detections = await self._capture()
            await self.engine.checkpoint()
            if generation != self.engine.pause_generation:
                continue
            labels = {item.label for item in detections}
            if labels & {"battle_end", "victory_screen", "defeat_screen"}:
                return
            if 'battle_screen' in labels:
                last_known = time.monotonic()
                try:
                    pending = self.policy.pending
                    move = self.policy.choose(detections, time.monotonic())
                    if pending and self.policy.pending is None:
                        await self.event_bus.emit('log_message', {'level': 'INFO', 'message': f'已确认出牌: {pending[0].card}'})
                except RuntimeError as exc:
                    await self.event_bus.emit('log_message', {'level': 'WARNING', 'message': f'{exc}；暂缓出牌，继续观察本局'})
                    self.policy.reset()
                    await self.token.sleep(3)
                    continue
                if move:
                    await self.adb.tap(*move.select)
                    await self.token.sleep(.1)
                    await self.engine.checkpoint()
                    if generation != self.engine.pause_generation:
                        continue
                    # Recheck after selecting: a result/overlay may have appeared.
                    _image, fresh = await self._capture()
                    await self.engine.checkpoint()
                    if generation != self.engine.pause_generation:
                        continue
                    fresh_labels = {d.label for d in fresh}
                    fresh_move = self.policy.choose(fresh, time.monotonic())
                    if ('battle_screen' in fresh_labels and
                        not fresh_labels & {'battle_end', 'victory_screen', 'defeat_screen'} and
                        fresh_move is not None and fresh_move.card == move.card and fresh_move.slot == move.slot):
                        import cv2
                        import numpy as np
                        frame = cv2.imdecode(np.frombuffer(_image, np.uint8), cv2.IMREAD_COLOR)
                        height, width = frame.shape[:2]
                        self.token.throw_if_cancelled()
                        await self.adb.tap(round(move.placement[0] * width), round(move.placement[1] * height))
                        self.policy.submitted(move, fresh, time.monotonic())
                        await self.event_bus.emit('log_message', {'level': 'INFO', 'message': f'已尝试出牌: {move.card}，等待手牌和圣水变化'})
            elif time.monotonic() - last_known > self.settings.stateTimeoutSeconds:
                raise SafetyViolation('对局画面持续无法识别，已停止出牌')
            await self.token.sleep(max(self.settings.inferenceIntervalMs / 1000, 0.5))
        raise TimeoutError("等待对局结束超时")

    async def _prepare_next_round(self) -> None:
        deadline = time.monotonic() + self.settings.stateTimeoutSeconds
        while time.monotonic() < deadline:
            await self.engine.checkpoint()
            _image, detections = await self._capture()
            labels = {d.label for d in detections}
            if 'home_screen' in labels:
                if 'classic_mode_ready' in labels:
                    return
                await self._confirmed_click(('game_mode_button_1',))
                await self._find_classic_mode()
                return
            if labels & {'play_again_button', 'battle_button'}:
                return
            if 'continue_button' in labels:
                await self._confirmed_click(('continue_button',))
            elif 'dismiss_popup_button' in labels:
                await self._confirmed_click(('dismiss_popup_button',))
            elif 'reward_popup' in labels and 'close_button' in labels:
                await self._confirmed_click(('close_button',))
            await self.token.sleep(.3)
        raise SafetyViolation('结算后未找到下一局入口，请补充继续/奖励弹窗模板')

    async def _confirm_crown_result(self) -> tuple[str, int | None]:
        self.crowns.reset()
        stable_results = 0
        for failure in range(1, self.settings.maxCrownFailures + 1):
            image, detections = await self._capture()
            confirmed = self.crowns.observe(detections)
            if self.progress.target_rounds is not None:
                labels = {d.label for d in detections}
                stable_results = stable_results + 1 if labels & {'battle_end', 'victory_screen', 'defeat_screen'} else 0
                if stable_results >= self.settings.crownConfirmationFrames:
                    digest = hashlib.sha256(image).hexdigest()[:16]
                    return f'battle-{self._round_generation}-{digest}', confirmed
            await self.event_bus.emit("crown_result_detected", {"failureCount": failure, "candidate": confirmed})
            if confirmed is not None and self.progress.target_rounds is None:
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
            await self._state(WorkflowState.WAIT_HOME)
            _image, initial = await self._wait_detection(('home_screen', 'battle_screen', 'battle_end'))
            recovering = initial.label != 'home_screen'
            prepared = False
            if initial.label == 'battle_end' and self.progress.target_rounds is not None:
                # A new round-count task must not count the previous task's result.
                await self._prepare_next_round()
                recovering = False
                prepared = True
            if not recovering and not prepared:
                await self._state(WorkflowState.OPEN_GAME_MODES); await self._confirmed_click(("game_mode_button_1",))
                await self._state(WorkflowState.SCROLL_FOR_CLASSIC_1V1); await self._find_classic_mode()
                await self._state(WorkflowState.SELECT_CLASSIC_1V1)
            while True:
                self._round_generation += 1
                if not recovering:
                    await self._state(WorkflowState.START_MATCH); await self._confirmed_click(("battle_button", "play_again_button"))
                    await self._state(WorkflowState.WAIT_MATCH); await self._wait_detection(("matching_screen", "battle_screen"), timeout=max(90, self.settings.stateTimeoutSeconds))
                    await self._wait_detection(("battle_screen",))
                recovering = False
                await self._state(WorkflowState.IN_BATTLE)
                await self._wait_battle_end()
                await self._state(WorkflowState.WAIT_RESULT)
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
                if self.progress.target_rounds is None and self.progress.round_count >= self.settings.maxRounds:
                    self.progress.complete(StopReason.ROUND_LIMIT)
                    await self.event_bus.emit('task_stopped', self.progress.as_protocol_dict('STOPPED'))
                    await self._optional_cleanup()
                    return self.progress
                await self._prepare_next_round()
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

from __future__ import annotations

import asyncio
import base64
import time

from automation.core.actions import ActionExecutor
from automation.core.adb import AdbClient
from automation.core.config import AppSettings
from automation.core.events import EventBus
from automation.core.safety import SafetyGuard, SafetyViolation
from automation.core.vision import Detection, annotate_detections, select_detection
from automation.core.workflow import CancelledError, CancellationToken
from automation.core.vision.profile import create_detector


class LiveDailyShopTask:
    def __init__(self, settings: AppSettings, event_bus: EventBus, token: CancellationToken) -> None:
        self.settings = settings
        self.event_bus = event_bus
        self.token = token
        self.adb = AdbClient(settings.adbPath, settings.adbSerial, token, settings.stateTimeoutSeconds)
        self.vision = create_detector(settings)
        self.actions = ActionExecutor(self.adb, token)
        self.guard = SafetyGuard(settings.maxRetries)
        self._resume = asyncio.Event()
        self._resume.set()

    async def _state(self, state: str) -> None:
        self.token.throw_if_cancelled()
        await self._resume.wait()
        self.token.throw_if_cancelled()
        await self.event_bus.emit("task_state_changed", {"state": state})

    async def _capture(self) -> tuple[bytes, list[Detection]]:
        await self._resume.wait()
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

    async def _wait(self, labels: tuple[str, ...], timeout: float | None = None) -> Detection:
        deadline = time.monotonic() + (timeout or self.settings.stateTimeoutSeconds)
        while time.monotonic() < deadline:
            _image, detections = await self._capture()
            found = [item for label in labels if (item := select_detection(detections, label, self.settings.yoloConfidence))]
            if found:
                return max(found, key=lambda item: item.confidence)
            await self.token.sleep(self.settings.inferenceIntervalMs / 1000)
        raise TimeoutError(f"等待目标超时: {', '.join(labels)}")

    async def _confirmed_click(self, labels: tuple[str, ...]) -> None:
        first = await self._wait(labels)
        await self.token.sleep(0.2)
        second = await self._wait((first.label,), timeout=5)
        await self.actions.click_detection(second)

    async def run(self) -> str:
        await self.event_bus.emit("task_started", {"status": "RUNNING"})
        try:
            await self._state("LAUNCH_GAME")
            await self.adb.start_app(self.settings.clashRoyalePackage, self.settings.clashRoyaleActivity)
            await self.token.sleep(self.settings.gameLaunchWaitSeconds)
            await self._state("WAIT_HOME")
            await self._wait(("home_screen",))
            await self._state("OPEN_SHOP")
            await self._confirmed_click(("leftmost_nav_tab",))
            width, height = await self.adb.resolution()
            await self._state("SCROLL_FOR_DAILY_TRADER")
            for _ in range(12):
                _image, detections = await self._capture()
                labels = {item.label for item in detections}
                if "claimed_state" in labels:
                    await self.event_bus.emit("task_completed", {"status": "COMPLETED", "stopReason": "ALREADY_CLAIMED", "message": "今日已领取"})
                    return "ALREADY_CLAIMED"
                if self.guard.can_claim_free_item(detections):
                    await self._state("CONFIRM_FREE_ITEM")
                    await self.token.sleep(0.2)
                    _image, confirmed = await self._capture()
                    if not self.guard.can_claim_free_item(confirmed):
                        raise SafetyViolation("免费标识二次确认失败，已暂停")
                    target = select_detection(confirmed, "claim_button", self.settings.yoloConfidence) or select_detection(confirmed, "free_item", self.settings.yoloConfidence)
                    if target is None:
                        raise SafetyViolation("未确认领取按钮，禁止点击")
                    await self.actions.click_detection(target)
                    await self._state("VERIFY_CLAIMED")
                    await self._wait(("claimed_state", "reward_popup"))
                    await self.event_bus.emit("task_completed", {"status": "COMPLETED", "stopReason": "FREE_ITEM_CLAIMED", "message": "免费物品领取完成"})
                    return "FREE_ITEM_CLAIMED"
                await self.actions.swipe((width // 2, int(height * 0.78)), (width // 2, int(height * 0.28)), self.settings.swipeDurationMs)
                await self.token.sleep(0.4)
            raise TimeoutError("达到最大滑动次数仍未找到每日商人免费物品")
        except SafetyViolation as exc:
            await self.event_bus.emit("task_paused", {"status": "PAUSED", "stopReason": "SAFETY_PAUSE", "message": str(exc)})
            return "PAUSED"
        except CancelledError:
            await self.event_bus.emit("task_stopped", {"status": "STOPPED", "stopReason": "USER_STOPPED"})
            return "STOPPED"
        except Exception as exc:
            await self.event_bus.emit("task_failed", {"status": "FAILED", "message": str(exc)})
            return "FAILED"

    async def pause(self) -> None:
        self._resume.clear()
        await self.event_bus.emit("task_paused", {"status": "PAUSED"})

    async def resume(self) -> None:
        self._resume.set()
        await self.event_bus.emit("log_message", {"level": "INFO", "message": "每日商店任务已继续"})

    def stop(self, emergency: bool = False) -> None:
        self.token.cancel()

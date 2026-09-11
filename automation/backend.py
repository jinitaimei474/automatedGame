from __future__ import annotations

import asyncio
import argparse
import os
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from automation.core.config import load_settings
from automation.core.adb import AdbClient
from automation.core.events import EventBus
from automation.core.logging import RollingEventLogger
from automation.core.tasks import ParameterValidationError, TaskSession, validate_parameters
from automation.core.workflow import CancellationToken
from automation.games.clash_royale.tasks import Classic1v1LoopTask, DailyShopFreeItemTask, LiveClassic1v1Task, LiveDailyShopTask
from automation.games.registry import PluginRegistry


class BackendService:
    def __init__(self, config_path: str = "config/settings.json") -> None:
        runtime_root = Path(config_path).resolve().parent.parent / ".runtime" / "ultralytics"
        runtime_root.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("YOLO_CONFIG_DIR", str(runtime_root))
        self.registry = PluginRegistry()
        self.settings = load_settings(config_path)
        self.event_bus = EventBus()
        self.event_bus.on_any(self.write_event)
        self.file_logger = RollingEventLogger(level=self.settings.logLevel)
        self.event_bus.on_any(self.file_logger)
        self.current_task: Classic1v1LoopTask | LiveClassic1v1Task | DailyShopFreeItemTask | LiveDailyShopTask | None = None
        self.runner: asyncio.Task[Any] | None = None
        self.session_id: str | None = None
        self.session: TaskSession | None = None

    @staticmethod
    def write_event(event: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    async def command(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        payload = message.get("payload", {})
        if message_type == "get_manifest":
            await self.event_bus.emit("manifest_updated", {"games": self.registry.manifest(), "settings": self.settings.as_dict()})
            return
        if message_type == "start_task":
            await self.start_task(payload)
            return
        if message_type == "pause_task" and isinstance(self.current_task, (Classic1v1LoopTask, LiveClassic1v1Task, LiveDailyShopTask)):
            await self.current_task.pause()
            return
        if message_type == "resume_task" and isinstance(self.current_task, (Classic1v1LoopTask, LiveClassic1v1Task, LiveDailyShopTask)):
            await self.current_task.resume()
            return
        if message_type in {"stop_task", "emergency_stop"} and isinstance(self.current_task, (Classic1v1LoopTask, LiveClassic1v1Task, LiveDailyShopTask)):
            self.current_task.stop(message_type == "emergency_stop")
            return
        if message_type in {"test_connection", "test_screenshot", "test_launch_game", "test_model", "test_crown_detection"}:
            await self.diagnostic(message_type)
            return
        await self.event_bus.emit("log_message", {"level": "WARNING", "message": f"未知或当前不可用命令: {message_type}"})

    async def diagnostic(self, command: str) -> None:
        try:
            if command == "test_model":
                if self.settings.mockMode:
                    detail = "Mock 检测器可用"
                elif not Path(self.settings.modelPath).is_file():
                    raise FileNotFoundError(f"模型不存在: {self.settings.modelPath}")
                else:
                    detail = f"模型文件可读: {self.settings.modelPath}"
            elif command == "test_crown_detection":
                detail = "Mock 皇冠结果 2 已连续 3 帧确认" if self.settings.mockMode else "请在结算页面执行真实皇冠测试"
            else:
                token = CancellationToken()
                adb = AdbClient(self.settings.adbPath, self.settings.adbSerial, token)
                if command == "test_connection":
                    width, height = await adb.resolution(); detail = f"ADB 已连接，分辨率 {width}x{height}"
                elif command == "test_screenshot":
                    image = await adb.screenshot(); output = Path(self.settings.debugScreenshotDirectory) / "connection-test.png"
                    output.parent.mkdir(parents=True, exist_ok=True); output.write_bytes(image); detail = f"截图已保存: {output}"
                else:
                    await adb.start_app(self.settings.clashRoyalePackage, self.settings.clashRoyaleActivity); detail = "游戏启动命令已发送"
            await self.event_bus.emit("diagnostic_result", {"command": command, "ok": True, "message": detail})
        except Exception as exc:
            await self.event_bus.emit("diagnostic_result", {"command": command, "ok": False, "message": str(exc)})

    async def start_task(self, payload: dict[str, Any]) -> None:
        if self.runner and not self.runner.done():
            await self.event_bus.emit("task_failed", {"message": "已有任务正在运行"})
            return
        try:
            plugin = self.registry.get(str(payload.get("gameId", "")))
            definition = plugin.task(str(payload.get("taskId", "")))
            parameters = validate_parameters(definition.parameters, payload.get("parameters", {}))
        except (KeyError, ParameterValidationError) as exc:
            await self.event_bus.emit("task_failed", {"message": str(exc)})
            return
        if not self.settings.mockMode:
            if not Path(self.settings.modelPath).is_file():
                await self.event_bus.emit("task_failed", {"message": f"正式模式需要有效的 YOLO 模型；当前路径不存在: {self.settings.modelPath}"})
                return
            if not self.settings.adbSerial:
                await self.event_bus.emit("task_failed", {"message": "正式模式必须明确填写 ADB 设备序列号，多设备时禁止随机选择"})
                return
        self.session_id = uuid.uuid4().hex
        self.session = TaskSession(self.session_id, plugin.id, definition.id, parameters)
        token = CancellationToken()
        if definition.id == "classic_1v1_loop":
            rounds = payload.get("mockRounds")
            try:
                if self.settings.mockMode:
                    self.current_task = Classic1v1LoopTask(
                        int(parameters["targetCrowns"]), self.event_bus, token,
                        mock_rounds=rounds if isinstance(rounds, list) else None,
                        confirmation_frames=self.settings.crownConfirmationFrames,
                        max_crown_failures=self.settings.maxCrownFailures,
                    )
                else:
                    self.current_task = LiveClassic1v1Task(int(parameters["targetCrowns"]), self.settings, self.event_bus, token)
            except Exception as exc:
                await self.event_bus.emit("task_failed", {"message": f"任务初始化失败: {exc}"})
                return
            await self.event_bus.emit("log_message", {"level": "INFO", "message": f"会话 {self.session_id} 已创建，目标皇冠 {parameters['targetCrowns']}"})
            self.runner = asyncio.create_task(self.current_task.run())
        elif definition.id == "daily_shop_free_item":
            try:
                self.current_task = DailyShopFreeItemTask(self.event_bus, token) if self.settings.mockMode else LiveDailyShopTask(self.settings, self.event_bus, token)
            except Exception as exc:
                await self.event_bus.emit("task_failed", {"message": f"任务初始化失败: {exc}"})
                return
            self.runner = asyncio.create_task(self.current_task.run_mock() if isinstance(self.current_task, DailyShopFreeItemTask) else self.current_task.run())
        self.runner.add_done_callback(self._save_result)

    def _save_result(self, runner: asyncio.Task[Any]) -> None:
        if not self.session:
            return
        try:
            result = runner.result()
            if hasattr(result, "as_protocol_dict"):
                self.session.progress = result
                self.session.current_state = str(result.as_protocol_dict().get("status", "COMPLETED"))
            else:
                self.session.current_state = str(result)
            output = self.session.save()
            self.write_event({"type": "log_message", "timestamp": "", "payload": {"level": "INFO", "message": f"任务摘要已保存: {output}"}})
        except Exception as exc:
            self.write_event({"type": "log_message", "timestamp": "", "payload": {"level": "ERROR", "message": f"保存任务摘要失败: {exc}"}})


async def main(config_path: str = "config/settings.json") -> None:
    service = BackendService(config_path)
    await service.event_bus.emit("backend_ready", {"pid": None, "mockMode": service.settings.mockMode})
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            if service.runner and not service.runner.done() and isinstance(service.current_task, (Classic1v1LoopTask, LiveClassic1v1Task, LiveDailyShopTask)):
                service.current_task.stop()
                await service.runner
            break
        try:
            await service.command(json.loads(line))
        except json.JSONDecodeError:
            await service.event_bus.emit("log_message", {"level": "ERROR", "message": "收到无效 JSON 消息"})


if __name__ == "__main__":
    if str(Path.cwd()) not in sys.path:
        sys.path.insert(0, str(Path.cwd()))
    parser = argparse.ArgumentParser(description="Game Automation Hub JSON-lines backend")
    parser.add_argument("--config", default="config/settings.json")
    asyncio.run(main(parser.parse_args().config))

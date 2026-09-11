from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from automation.core.workflow.cancellation import CancellationToken


class AdbCommandError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    stdout: bytes
    stderr: bytes
    returncode: int


def scale_point(point: tuple[int, int], source: tuple[int, int], target: tuple[int, int]) -> tuple[int, int]:
    if min(*source, *target) <= 0:
        raise ValueError("resolutions must be positive")
    return round(point[0] * target[0] / source[0]), round(point[1] * target[1] / source[1])


class AdbClient:
    def __init__(self, adb_path: str, serial: str, token: CancellationToken, timeout: float = 15) -> None:
        self.adb_path = str(Path(adb_path))
        self.serial = serial
        self.token = token
        self.timeout = timeout

    def _args(self, *args: str) -> list[str]:
        return [self.adb_path, "-s", self.serial, *args]

    async def run(self, *args: str, timeout: float | None = None) -> CommandResult:
        self.token.throw_if_cancelled()
        try:
            process = await asyncio.create_subprocess_exec(
                *self._args(*args), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout or self.timeout)
        except TimeoutError as exc:
            if process.returncode is None:
                process.kill()
            raise AdbCommandError(f"ADB 命令超时: {' '.join(args)}") from exc
        self.token.throw_if_cancelled()
        result = CommandResult(stdout, stderr, process.returncode or 0)
        if result.returncode != 0:
            raise AdbCommandError(stderr.decode(errors="replace").strip() or "ADB 命令失败")
        return result

    async def screenshot(self) -> bytes:
        return (await self.run("exec-out", "screencap", "-p", timeout=30)).stdout

    async def tap(self, x: int, y: int) -> None:
        await self.run("shell", "input", "tap", str(x), str(y))

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        await self.run("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))

    async def long_press(self, x: int, y: int, duration_ms: int = 800) -> None:
        await self.swipe(x, y, x, y, duration_ms)

    async def start_app(self, package: str, activity: str = "") -> None:
        if activity:
            await self.run("shell", "am", "start", "-n", f"{package}/{activity}")
        else:
            await self.run("shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")

    async def resolution(self) -> tuple[int, int]:
        text = (await self.run("shell", "wm", "size")).stdout.decode(errors="replace")
        matches = re.findall(r"(\d+)x(\d+)", text)
        if not matches:
            raise AdbCommandError("无法读取设备分辨率")
        width, height = matches[-1]
        return int(width), int(height)


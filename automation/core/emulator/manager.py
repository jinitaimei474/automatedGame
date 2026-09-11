from __future__ import annotations

import asyncio
import os
from pathlib import Path

from automation.core.workflow.cancellation import CancellationToken


class EmulatorManager:
    COMMON_MUMU_PATHS = (
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Netease/MuMuPlayer-12.0/shell/MuMuPlayer.exe",
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "MuMu/emulator/nemu/EmulatorShell/NemuPlayer.exe",
    )

    def __init__(self, token: CancellationToken) -> None:
        self.token = token
        self.started_by_app = False
        self.process: asyncio.subprocess.Process | None = None

    @classmethod
    def discover(cls) -> str | None:
        return next((str(path) for path in cls.COMMON_MUMU_PATHS if path.exists()), None)

    async def launch(self, executable: str, args: tuple[str, ...] = ()) -> None:
        self.token.throw_if_cancelled()
        path = Path(executable)
        if not path.is_file():
            raise FileNotFoundError(f"MuMu 可执行文件不存在: {path}")
        self.process = await asyncio.create_subprocess_exec(str(path), *args)
        self.started_by_app = True

    async def close_if_owned(self) -> None:
        if self.started_by_app and self.process and self.process.returncode is None:
            self.process.terminate()
            await self.process.wait()


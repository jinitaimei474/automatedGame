from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any


@dataclass
class AppSettings:
    mockMode: bool = True
    mumuExecutable: str = ""
    adbPath: str = "adb"
    adbSerial: str = "127.0.0.1:16384"
    clashRoyalePackage: str = "com.supercell.clashroyale"
    clashRoyaleActivity: str = ""
    modelPath: str = "automation/games/clash_royale/models/best.pt"
    screenshotIntervalMs: int = 500
    inferenceIntervalMs: int = 500
    yoloConfidence: float = 0.6
    crownConfidence: float = 0.75
    crownConfirmationFrames: int = 3
    stateTimeoutSeconds: int = 30
    maxRetries: int = 3
    maxCrownFailures: int = 5
    swipeDistance: int = 650
    swipeDurationMs: int = 450
    saveDebugScreenshots: bool = True
    debugScreenshotDirectory: str = "debug-screenshots"
    logLevel: str = "INFO"
    gameLaunchWaitSeconds: int = 10
    closeGameOnCompletion: bool = False
    closeEmulatorOnCompletion: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


def load_settings(path: str | Path) -> AppSettings:
    config_path = Path(path)
    if not config_path.exists():
        return AppSettings()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    allowed = {field.name for field in fields(AppSettings)}
    return AppSettings(**{key: value for key, value in raw.items() if key in allowed})


from __future__ import annotations

import json
import logging
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any


class RollingEventLogger:
    SENSITIVE = re.compile(r"(?i)(password|passwd|token|secret|账号密码)\s*[:=]\s*[^\s,]+")

    def __init__(self, directory: str | Path = "logs", level: str = "INFO", backup_days: int = 14) -> None:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"game_hub.{id(self)}")
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        handler = TimedRotatingFileHandler(
            target / "backend.log", when="midnight", interval=1, backupCount=backup_days, encoding="utf-8", utc=True
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        self.logger.addHandler(handler)
        self.logger.propagate = False

    def __call__(self, event: dict[str, Any]) -> None:
        if event.get("type") not in {"log_message", "task_failed", "task_paused", "task_completed"}:
            return
        payload = event.get("payload", {})
        level = str(payload.get("level", "INFO")).upper()
        message = str(payload.get("message") or json.dumps(payload, ensure_ascii=False))
        message = self.SENSITIVE.sub(lambda match: f"{match.group(1)}=[REDACTED]", message)
        self.logger.log(getattr(logging, level, logging.INFO), message)

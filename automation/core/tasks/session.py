from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .progress import CrownProgressTracker


@dataclass
class TaskSession:
    session_id: str
    game_id: str
    task_id: str
    parameters: dict[str, Any]
    current_state: str = "IDLE"
    progress: CrownProgressTracker | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        progress = self.progress.as_protocol_dict(self.current_state) if self.progress else {}
        return {
            "sessionId": self.session_id,
            "gameId": self.game_id,
            "taskId": self.task_id,
            "parameters": self.parameters,
            "currentState": self.current_state,
            **progress,
            "metadata": self.metadata,
        }

    def save(self, directory: str | Path = "task-results") -> Path:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        output = target / f"{self.session_id}.json"
        output.write_text(json.dumps(self.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return output

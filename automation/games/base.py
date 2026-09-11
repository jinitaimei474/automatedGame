from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from automation.core.tasks import TaskParameter


@dataclass(frozen=True)
class TaskDefinition:
    id: str
    name: str
    description: str
    parameters: tuple[TaskParameter, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameters": [item.as_dict() for item in self.parameters],
        }


class GamePlugin(Protocol):
    id: str
    name: str
    package_name: str
    tasks: tuple[TaskDefinition, ...]


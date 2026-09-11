from __future__ import annotations

import inspect
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

Listener = Callable[[dict[str, Any]], Awaitable[None] | None]


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)
        self._all: list[Listener] = []

    def on(self, event_type: str, listener: Listener) -> None:
        self._listeners[event_type].append(listener)

    def on_any(self, listener: Listener) -> None:
        self._all.append(listener)

    async def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        event = {"type": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), "payload": payload or {}}
        for listener in [*self._listeners[event_type], *self._all]:
            result = listener(event)
            if inspect.isawaitable(result):
                await result


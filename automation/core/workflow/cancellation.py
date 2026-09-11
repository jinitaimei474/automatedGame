from __future__ import annotations

import asyncio


class CancelledError(RuntimeError):
    pass


class CancellationToken:
    def __init__(self) -> None:
        self._event = asyncio.Event()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    def throw_if_cancelled(self) -> None:
        if self.cancelled:
            raise CancelledError("Task was cancelled")

    async def sleep(self, seconds: float) -> None:
        self.throw_if_cancelled()
        try:
            await asyncio.wait_for(self._event.wait(), timeout=seconds)
        except TimeoutError:
            return
        raise CancelledError("Task was cancelled")


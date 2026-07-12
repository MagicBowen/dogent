from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from typing import Callable

from rich.console import Console


class LLMWaitIndicator:
    def __init__(
        self,
        console: Console,
        label: str = "Waiting for LLM response",
        activity_callback: Callable[[str | None], None] | None = None,
    ) -> None:
        self.console = console
        self.label = label
        self.activity_callback = activity_callback
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if not self._running:
            return
        self._stop_event.set()
        if self._task:
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        self._running = False
        if self.activity_callback is not None:
            self.activity_callback(None)

    def _format_status(self, elapsed: float) -> str:
        return f"{self.label} ({elapsed:.1f}s)"

    async def _run(self) -> None:
        start = time.monotonic()
        if self.activity_callback is not None:
            self.activity_callback(self.label)
            await self._stop_event.wait()
            return
        with self.console.status(self._format_status(0.0), spinner="dots") as status:
            while not self._stop_event.is_set():
                elapsed = time.monotonic() - start
                status.update(self._format_status(elapsed))
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue

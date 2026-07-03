"""Async pub/sub bus for streaming pipeline events to the frontend via SSE.

One asyncio.Queue per subscriber, keyed by run_id. In-memory by design:
a pipeline run lives entirely inside one process, so no broker is needed.
(For multi-instance deployments this is the seam where Redis pub/sub
would slot in — the interface would not change.)
"""
import asyncio
from collections import defaultdict
from typing import AsyncIterator

import structlog

from app.schemas import AgentEvent

log = structlog.get_logger()


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, run_id: str, event: AgentEvent) -> None:
        async with self._lock:
            queues = list(self._subscribers.get(run_id, []))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                log.warning("event_bus_queue_full", run_id=run_id)

    async def subscribe(self, run_id: str) -> AsyncIterator[AgentEvent]:
        """Yield events for a run until the pipeline's terminal event arrives."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers[run_id].append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
                if event.agent_name == "__pipeline__" and event.status.value in (
                    "completed",
                    "failed",
                ):
                    break
        finally:
            async with self._lock:
                if queue in self._subscribers.get(run_id, []):
                    self._subscribers[run_id].remove(queue)
                if not self._subscribers[run_id]:
                    del self._subscribers[run_id]


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus

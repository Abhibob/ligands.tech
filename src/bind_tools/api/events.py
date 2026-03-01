"""Thread-safe event bus for streaming agent events to WebSocket clients.

The agent loop runs in a daemon thread and publishes events via `publish()`.
WebSocket handlers subscribe via `subscribe()` which returns an async generator.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class AgentEvent:
    """A single event from the agent loop."""

    agent_id: str
    event_type: str  # turn_start, tool_call, tool_result, thinking, nudge, assistant_text, done, error
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agentId": self.agent_id,
            "type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class AgentEventBus:
    """Singleton event bus for agent → WebSocket streaming.

    Thread-safe: publish() can be called from any thread.
    subscribe() returns an async generator for use in async WebSocket handlers.
    """

    _instance: AgentEventBus | None = None

    def __init__(self) -> None:
        self._lock = Lock()
        # agent_id -> list of asyncio.Queue (one per subscriber)
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        # agent_id -> list of past events (ring buffer for late joiners)
        self._history: dict[str, list[dict]] = defaultdict(list)
        self._max_history = 500

    @classmethod
    def get(cls) -> AgentEventBus:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def publish(self, event: AgentEvent) -> None:
        """Publish an event (called from agent thread — thread-safe)."""
        event_dict = event.to_dict()

        with self._lock:
            # Store in history
            history = self._history[event.agent_id]
            history.append(event_dict)
            if len(history) > self._max_history:
                self._history[event.agent_id] = history[-self._max_history :]

            queues = list(self._subscribers.get(event.agent_id, []))

        # Push to subscriber queues (non-blocking)
        for q in queues:
            try:
                q.put_nowait(event_dict)
            except asyncio.QueueFull:
                pass  # Drop if subscriber is too slow

    def subscribe(self, agent_id: str) -> tuple[asyncio.Queue, list[dict]]:
        """Subscribe to events for an agent. Returns (queue, history).

        Call unsubscribe() when done.
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        with self._lock:
            self._subscribers[agent_id].append(q)
            history = list(self._history.get(agent_id, []))
        return q, history

    def unsubscribe(self, agent_id: str, q: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        with self._lock:
            subs = self._subscribers.get(agent_id, [])
            if q in subs:
                subs.remove(q)
            if not subs and agent_id in self._subscribers:
                del self._subscribers[agent_id]

    def clear_history(self, agent_id: str) -> None:
        """Clear stored history for an agent (e.g., after it finishes)."""
        with self._lock:
            self._history.pop(agent_id, None)

"""In-process event bus with durable sink integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Event:
    type: str
    work_item_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    producer: str = "runtime"
    version: int = 1


class EventSink(Protocol):
    def append_event(self, event: Event) -> None: ...


class EventBus:
    """Publishes runtime events to subscribers and a durable sink."""

    def __init__(self, sink: EventSink | None = None) -> None:
        self.sink = sink
        self._subscribers: list[Callable[[Event], None]] = []

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        self._subscribers.append(handler)

    def emit(self, event_type: str, work_item_id: str | None = None, payload: dict[str, Any] | None = None, producer: str = "runtime") -> Event:
        event = Event(event_type, work_item_id, payload or {}, producer=producer)
        if self.sink is not None:
            self.sink.append_event(event)
        for subscriber in self._subscribers:
            subscriber(event)
        return event

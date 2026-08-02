"""Runtime event replay helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from awr.events import Event


@dataclass(slots=True)
class ReplayedWorkState:
    work_id: str
    status: str = "unknown"
    events: list[str] = field(default_factory=list)


class RuntimeReplay:
    """Reconstructs a lightweight state projection from immutable events."""

    STATUS_BY_EVENT = {
        "TaskCreated": "created",
        "TaskPlanned": "planned",
        "TaskReadied": "ready",
        "TaskStarted": "running",
        "TaskFinished": "completed",
        "TaskFailed": "failed",
        "TaskWaitingHuman": "waiting_human",
        "TaskPaused": "paused",
        "TaskResumed": "ready",
        "TaskCancelled": "cancelled",
        "TaskRetried": "retrying",
        "TaskApproved": "approved",
    }

    @classmethod
    def reconstruct(cls, events: list[Event]) -> dict[str, ReplayedWorkState]:
        state: dict[str, ReplayedWorkState] = {}
        for event in events:
            if event.work_item_id is None:
                continue
            item = state.setdefault(event.work_item_id, ReplayedWorkState(event.work_item_id))
            item.events.append(event.type)
            if event.type in cls.STATUS_BY_EVENT:
                item.status = cls.STATUS_BY_EVENT[event.type]
            if "to" in event.payload:
                item.status = str(event.payload["to"])
        return state

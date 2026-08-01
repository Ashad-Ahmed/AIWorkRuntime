"""Core domain objects for durable AI work."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class Status(StrEnum):
    CREATED = "created"
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    WAITING_HUMAN = "waiting_human"
    APPROVED = "approved"
    PAUSED = "paused"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.CREATED: {Status.PLANNED, Status.READY, Status.CANCELLED},
    Status.PLANNED: {Status.READY, Status.PAUSED, Status.CANCELLED},
    Status.READY: {Status.RUNNING, Status.PAUSED, Status.CANCELLED},
    Status.APPROVED: {Status.RUNNING, Status.PAUSED, Status.CANCELLED},
    Status.RUNNING: {Status.COMPLETED, Status.FAILED, Status.WAITING_HUMAN, Status.PAUSED, Status.CANCELLED},
    Status.FAILED: {Status.RETRYING, Status.CANCELLED},
    Status.RETRYING: {Status.READY, Status.RUNNING, Status.CANCELLED},
    Status.WAITING_HUMAN: {Status.APPROVED, Status.CANCELLED},
    Status.PAUSED: {Status.READY, Status.RUNNING, Status.CANCELLED},
    Status.COMPLETED: set(),
    Status.CANCELLED: set(),
}

RUNNABLE_STATUSES = {Status.READY, Status.APPROVED}
TERMINAL_STATUSES = {Status.COMPLETED, Status.CANCELLED}


@dataclass(slots=True)
class WorkItem:
    """A persistent, observable unit in the work graph."""

    title: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    status: Status = Status.CREATED
    priority: int = 0
    owner_agent: str | None = None
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)
    dependency_ids: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    confidence: float = 1.0
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    estimated_tokens: int = 0
    actual_tokens: int = 0
    retry_count: int = 0
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def transition_to(self, next_status: Status) -> None:
        if next_status == self.status:
            return
        if next_status not in ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"illegal work transition: {self.status} -> {next_status}")
        self.status = next_status
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    def add_artifact(self, kind: str, data: Any, metadata: dict[str, Any] | None = None) -> None:
        self.artifacts.append(
            {
                "kind": kind,
                "data": data,
                "metadata": metadata or {},
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        self.touch()

"""Core domain models for AI Work Runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class Status(StrEnum):
    """Supported lifecycle states for a work item."""

    CREATED = "created"
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    WAITING_HUMAN = "waiting_human"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    PAUSED = "paused"


TERMINAL_STATUSES = {Status.COMPLETED, Status.CANCELLED}


@dataclass(slots=True)
class WorkItem:
    """A durable unit of work owned by the runtime."""

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
    artifacts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def mark_updated(self) -> None:
        """Refresh the update timestamp after a mutation."""

        self.updated_at = datetime.now(UTC)

    def can_run(self, completed_dependencies: set[str]) -> bool:
        """Return true when this item can be scheduled for execution."""

        return self.status == Status.READY and set(self.dependency_ids) <= completed_dependencies

    def transition_to(self, status: Status) -> None:
        """Transition to a new lifecycle status."""

        if self.status in TERMINAL_STATUSES and self.status != status:
            raise ValueError(f"cannot transition terminal work item {self.id} from {self.status}")
        self.status = status
        self.mark_updated()

"""Dependency-aware scheduler for AI Work Runtime."""

from __future__ import annotations

from awr.models import WorkItem
from awr.registry import WorkRegistry


class Scheduler:
    """Selects runnable work without executing it."""

    def __init__(self, registry: WorkRegistry) -> None:
        self.registry = registry

    def ready(self) -> list[WorkItem]:
        completed = self.registry.completed_ids()
        candidates = [item for item in self.registry.list() if item.can_run(completed)]
        return sorted(candidates, key=lambda item: (-item.priority, item.created_at))

    def next(self) -> WorkItem | None:
        ready = self.ready()
        return ready[0] if ready else None

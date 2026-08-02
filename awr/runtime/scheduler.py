"""Scheduling policies and graph snapshots."""

from __future__ import annotations

from collections import Counter
from typing import Protocol

from awr.domain import RUNNABLE_STATUSES, WorkItem
from awr.runtime.dependency_manager import DependencyManager
from awr.storage.base import RuntimeStore


class SchedulingPolicy(Protocol):
    def sort(self, items: list[WorkItem]) -> list[WorkItem]: ...


class PriorityFirstPolicy:
    """Default policy: lower numeric priority first, then older work."""

    def sort(self, items: list[WorkItem]) -> list[WorkItem]:
        return sorted(items, key=lambda item: (item.priority, item.created_at))


class Scheduler:
    def __init__(
        self,
        store: RuntimeStore,
        dependency_manager: DependencyManager | None = None,
        policy: SchedulingPolicy | None = None,
    ) -> None:
        self.store = store
        self.dependency_manager = dependency_manager or DependencyManager(store)
        self.policy = policy or PriorityFirstPolicy()

    def runnable(self) -> list[WorkItem]:
        candidates = [item for item in self.store.list_work_items() if item.status in RUNNABLE_STATUSES]
        runnable = [item for item in candidates if self.dependency_manager.is_runnable(item)]
        return self.policy.sort(runnable)

    def next(self) -> WorkItem | None:
        runnable = self.runnable()
        return runnable[0] if runnable else None

    def stats(self) -> dict[str, int]:
        return dict(Counter(item.status.value for item in self.store.list_work_items()))

    def graph(self) -> dict[str, object]:
        items = self.store.list_work_items()
        return {
            "nodes": [
                {
                    "id": item.id,
                    "title": item.title,
                    "status": item.status.value,
                    "priority": item.priority,
                }
                for item in items
            ],
            "edges": [
                {"from": item.parent_id, "to": item.id, "type": "parent"}
                for item in items
                if item.parent_id
            ]
            + [
                {"from": dependency_id, "to": item.id, "type": "dependency"}
                for item in items
                for dependency_id in item.dependency_ids
            ],
        }

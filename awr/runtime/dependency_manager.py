"""Dependency and blocker resolution for work graph scheduling."""

from __future__ import annotations

from awr.domain import Status, WorkItem
from awr.storage.base import RuntimeStore


class DependencyManager:
    def __init__(self, store: RuntimeStore) -> None:
        self.store = store

    def unresolved_dependencies(self, item: WorkItem) -> list[str]:
        unresolved: list[str] = []
        for dependency_id in item.dependency_ids:
            dependency = self.store.get_work_item(dependency_id)
            if dependency.status != Status.COMPLETED:
                unresolved.append(dependency_id)
        return unresolved

    def active_blockers(self, item: WorkItem) -> list[str]:
        active: list[str] = []
        for blocker_id in item.blockers:
            blocker = self.store.get_work_item(blocker_id)
            if blocker.status not in {Status.COMPLETED, Status.CANCELLED}:
                active.append(blocker_id)
        return active

    def is_runnable(self, item: WorkItem) -> bool:
        return not self.unresolved_dependencies(item) and not self.active_blockers(item)

"""Lifecycle API for runtime-owned work management."""

from __future__ import annotations

from awr.domain import Status, WorkItem
from awr.events import EventBus
from awr.storage.base import RuntimeStore


class WorkRegistry:
    """Coordinates lifecycle mutations, lineage, and emitted events."""

    def __init__(self, store: RuntimeStore, event_bus: EventBus | None = None) -> None:
        self.store = store
        self.event_bus = event_bus or EventBus(store)

    def create(self, item: WorkItem) -> WorkItem:
        self.store.save_work_item(item)
        if item.parent_id:
            parent = self.store.get_work_item(item.parent_id)
            if item.id not in parent.child_ids:
                parent.child_ids.append(item.id)
                parent.touch()
                self.store.save_work_item(parent)
        self.event_bus.emit("TaskCreated", item.id, {"title": item.title, "parent_id": item.parent_id})
        return item

    def get(self, work_item_id: str) -> WorkItem:
        return self.store.get_work_item(work_item_id)

    def list(self) -> list[WorkItem]:
        return self.store.list_work_items()

    def mark_planned(self, work_item_id: str) -> WorkItem:
        return self._transition(work_item_id, Status.PLANNED, "TaskPlanned")

    def mark_ready(self, work_item_id: str) -> WorkItem:
        return self._transition(work_item_id, Status.READY, "TaskReadied")

    def mark_running(self, work_item_id: str) -> WorkItem:
        return self._transition(work_item_id, Status.RUNNING, "TaskStarted")

    def mark_completed(self, work_item_id: str, artifact: str | None = None) -> WorkItem:
        item = self.store.get_work_item(work_item_id)
        if artifact is not None:
            item.add_artifact("text", artifact)
            self.store.save_work_item(item)
        return self._transition(work_item_id, Status.COMPLETED, "TaskFinished")

    def mark_failed(self, work_item_id: str, error: str) -> WorkItem:
        return self._transition(work_item_id, Status.FAILED, "TaskFailed", {"error": error})

    def wait_for_human(self, work_item_id: str, reason: str) -> WorkItem:
        return self._transition(work_item_id, Status.WAITING_HUMAN, "TaskWaitingHuman", {"reason": reason})

    def pause(self, work_item_id: str) -> WorkItem:
        return self._transition(work_item_id, Status.PAUSED, "TaskPaused")

    def resume(self, work_item_id: str) -> WorkItem:
        item = self.store.get_work_item(work_item_id)
        next_status = Status.RUNNING if item.metadata.get("resume_to_running") else Status.READY
        return self._transition(work_item_id, next_status, "TaskResumed")

    def cancel(self, work_item_id: str) -> WorkItem:
        return self._transition(work_item_id, Status.CANCELLED, "TaskCancelled")

    def retry(self, work_item_id: str) -> WorkItem:
        item = self.store.get_work_item(work_item_id)
        item.transition_to(Status.RETRYING)
        item.retry_count += 1
        self.store.save_work_item(item)
        self.event_bus.emit("TaskRetried", item.id, {"retry_count": item.retry_count})
        item.transition_to(Status.READY)
        self.store.save_work_item(item)
        self.event_bus.emit("TaskReadied", item.id, {"from_retry": True})
        return item

    def approve(self, work_item_id: str) -> WorkItem:
        return self._transition(work_item_id, Status.APPROVED, "TaskApproved")

    def lineage(self, work_item_id: str) -> list[WorkItem]:
        chain = [self.store.get_work_item(work_item_id)]
        while chain[-1].parent_id:
            chain.append(self.store.get_work_item(chain[-1].parent_id))
        return list(reversed(chain))

    def _transition(
        self,
        work_item_id: str,
        status: Status,
        event_type: str,
        payload: dict[str, object] | None = None,
    ) -> WorkItem:
        item = self.store.get_work_item(work_item_id)
        previous = item.status
        item.transition_to(status)
        self.store.save_work_item(item)
        event_payload = {"from": previous.value, "to": status.value}
        event_payload.update(payload or {})
        self.event_bus.emit(event_type, item.id, event_payload)
        return item

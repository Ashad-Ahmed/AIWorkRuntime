"""Worker SDK, registration, health, and assignment."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from awr.domain import WorkItem


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    output: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    api_cost: float = 0.0


class WorkerStatus(StrEnum):
    AVAILABLE = "available"
    BUSY = "busy"
    UNHEALTHY = "unhealthy"


class Worker(Protocol):
    worker_id: str
    capabilities: set[str]
    max_concurrency: int

    def execute(self, work_item: WorkItem) -> ExecutionResult: ...


@dataclass(slots=True)
class BaseWorker:
    worker_id: str
    capabilities: set[str] = field(default_factory=lambda: {"default"})
    max_concurrency: int = 1

    def execute(self, work_item: WorkItem) -> ExecutionResult:
        return ExecutionResult(output=work_item.description or work_item.title)


class PythonWorker(BaseWorker):
    def __init__(self, worker_id: str = "python", max_concurrency: int = 1) -> None:
        super().__init__(worker_id=worker_id, capabilities={"python", "default"}, max_concurrency=max_concurrency)


class LLMWorker(BaseWorker):
    def __init__(self, worker_id: str = "llm", max_concurrency: int = 1) -> None:
        super().__init__(worker_id=worker_id, capabilities={"llm", "text", "default"}, max_concurrency=max_concurrency)


class HumanWorker(BaseWorker):
    def __init__(self, worker_id: str = "human", max_concurrency: int = 1) -> None:
        super().__init__(worker_id=worker_id, capabilities={"human", "approval"}, max_concurrency=max_concurrency)


@dataclass(frozen=True, slots=True)
class WorkerInfo:
    worker_id: str
    capabilities: set[str]
    status: WorkerStatus
    active: int
    max_concurrency: int


class WorkerManager:
    """Registers workers and tracks health, capacity, and reservations."""

    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}
        self._status: dict[str, WorkerStatus] = {}
        self._active: dict[str, int] = {}

    def register(self, worker: Worker) -> None:
        self._workers[worker.worker_id] = worker
        self._status[worker.worker_id] = WorkerStatus.AVAILABLE
        self._active[worker.worker_id] = 0

    def list_workers(self) -> list[WorkerInfo]:
        return [
            WorkerInfo(
                worker_id=worker.worker_id,
                capabilities=set(worker.capabilities),
                status=self._status[worker.worker_id],
                active=self._active[worker.worker_id],
                max_concurrency=worker.max_concurrency,
            )
            for worker in self._workers.values()
        ]

    def get(self, worker_id: str) -> Worker:
        return self._workers[worker_id]

    def set_health(self, worker_id: str, status: WorkerStatus) -> None:
        self._status[worker_id] = status

    def compatible(self, work_item: WorkItem) -> list[Worker]:
        required = str(work_item.metadata.get("work_type", "default"))
        return [
            worker
            for worker in self._workers.values()
            if required in worker.capabilities
            and self._status[worker.worker_id] == WorkerStatus.AVAILABLE
            and self._active[worker.worker_id] < worker.max_concurrency
        ]

    def reserve(self, worker_id: str) -> None:
        worker = self._workers[worker_id]
        if self._status[worker_id] != WorkerStatus.AVAILABLE:
            raise ValueError(f"worker is not available: {worker_id}")
        if self._active[worker_id] >= worker.max_concurrency:
            raise ValueError(f"worker capacity exhausted: {worker_id}")
        self._active[worker_id] += 1
        if self._active[worker_id] >= worker.max_concurrency:
            self._status[worker_id] = WorkerStatus.BUSY

    def release(self, worker_id: str) -> None:
        self._active[worker_id] = max(0, self._active[worker_id] - 1)
        if self._status[worker_id] == WorkerStatus.BUSY:
            self._status[worker_id] = WorkerStatus.AVAILABLE

    def utilization(self) -> dict[str, object]:
        return {
            info.worker_id: {"active": info.active, "max_concurrency": info.max_concurrency, "status": info.status.value}
            for info in self.list_workers()
        }


class AssignmentEngine:
    """Matches scheduled work to a compatible worker without executing it."""

    def __init__(self, workers: WorkerManager) -> None:
        self.workers = workers

    def assign(self, work_item: WorkItem) -> Worker:
        compatible = self.workers.compatible(work_item)
        if not compatible:
            raise ValueError(f"no compatible worker for work item {work_item.id}")
        worker = compatible[0]
        self.workers.reserve(worker.worker_id)
        return worker

    def release(self, worker_id: str) -> None:
        self.workers.release(worker_id)

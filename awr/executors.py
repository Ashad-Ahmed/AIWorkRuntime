"""Execution Adapter SDK, registration, health, and assignment.

Execution adapters are the boundary between AWR and any underlying execution
technology. They may wrap LangGraph, CrewAI, AutoGen, Python, Docker, a human
approval flow, or a remote job system, but the runtime only sees WorkItem in and
ExecutionResult out.
"""

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


class ExecutorStatus(StrEnum):
    AVAILABLE = "available"
    BUSY = "busy"
    UNHEALTHY = "unhealthy"


class ExecutionAdapter(Protocol):
    executor_id: str
    capabilities: set[str]
    max_concurrency: int

    def execute(self, work_item: WorkItem) -> ExecutionResult: ...


@dataclass(slots=True)
class BaseExecutionAdapter:
    executor_id: str
    capabilities: set[str] = field(default_factory=lambda: {"default"})
    max_concurrency: int = 1

    @property
    def worker_id(self) -> str:
        """Backward-compatible alias for older worker terminology."""

        return self.executor_id

    def execute(self, work_item: WorkItem) -> ExecutionResult:
        return ExecutionResult(output=work_item.description or work_item.title)


class PythonExecutionAdapter(BaseExecutionAdapter):
    def __init__(self, executor_id: str = "python", max_concurrency: int = 1) -> None:
        super().__init__(executor_id=executor_id, capabilities={"python", "default"}, max_concurrency=max_concurrency)


class LLMExecutionAdapter(BaseExecutionAdapter):
    def __init__(self, executor_id: str = "llm", max_concurrency: int = 1) -> None:
        super().__init__(executor_id=executor_id, capabilities={"llm", "text", "default"}, max_concurrency=max_concurrency)


class HumanExecutionAdapter(BaseExecutionAdapter):
    def __init__(self, executor_id: str = "human", max_concurrency: int = 1) -> None:
        super().__init__(executor_id=executor_id, capabilities={"human", "approval"}, max_concurrency=max_concurrency)


@dataclass(frozen=True, slots=True)
class ExecutorInfo:
    executor_id: str
    capabilities: set[str]
    status: ExecutorStatus
    active: int
    max_concurrency: int

    @property
    def worker_id(self) -> str:
        """Backward-compatible alias for older worker terminology."""

        return self.executor_id


class ExecutorManager:
    """Registers execution adapters and tracks health, capacity, and reservations."""

    def __init__(self) -> None:
        self._executors: dict[str, ExecutionAdapter] = {}
        self._status: dict[str, ExecutorStatus] = {}
        self._active: dict[str, int] = {}

    def register(self, executor: ExecutionAdapter) -> None:
        self._executors[executor.executor_id] = executor
        self._status[executor.executor_id] = ExecutorStatus.AVAILABLE
        self._active[executor.executor_id] = 0

    def list_executors(self) -> list[ExecutorInfo]:
        return [
            ExecutorInfo(
                executor_id=executor.executor_id,
                capabilities=set(executor.capabilities),
                status=self._status[executor.executor_id],
                active=self._active[executor.executor_id],
                max_concurrency=executor.max_concurrency,
            )
            for executor in self._executors.values()
        ]

    def get(self, executor_id: str) -> ExecutionAdapter:
        return self._executors[executor_id]

    def set_health(self, executor_id: str, status: ExecutorStatus) -> None:
        self._status[executor_id] = status

    def compatible(self, work_item: WorkItem) -> list[ExecutionAdapter]:
        required = str(work_item.metadata.get("work_type", "default"))
        return [
            executor
            for executor in self._executors.values()
            if required in executor.capabilities
            and self._status[executor.executor_id] == ExecutorStatus.AVAILABLE
            and self._active[executor.executor_id] < executor.max_concurrency
        ]

    def reserve(self, executor_id: str) -> None:
        executor = self._executors[executor_id]
        if self._status[executor_id] != ExecutorStatus.AVAILABLE:
            raise ValueError(f"executor is not available: {executor_id}")
        if self._active[executor_id] >= executor.max_concurrency:
            raise ValueError(f"executor capacity exhausted: {executor_id}")
        self._active[executor_id] += 1
        if self._active[executor_id] >= executor.max_concurrency:
            self._status[executor_id] = ExecutorStatus.BUSY

    def release(self, executor_id: str) -> None:
        self._active[executor_id] = max(0, self._active[executor_id] - 1)
        if self._status[executor_id] == ExecutorStatus.BUSY:
            self._status[executor_id] = ExecutorStatus.AVAILABLE

    def utilization(self) -> dict[str, object]:
        return {
            info.executor_id: {"active": info.active, "max_concurrency": info.max_concurrency, "status": info.status.value}
            for info in self.list_executors()
        }

    # Backward-compatible method name for the previous public API.
    def list_workers(self) -> list[ExecutorInfo]:
        return self.list_executors()


class ExecutionAssignmentEngine:
    """Matches scheduled work to a compatible execution adapter without executing it."""

    def __init__(self, executors: ExecutorManager) -> None:
        self.executors = executors

    def assign(self, work_item: WorkItem) -> ExecutionAdapter:
        compatible = self.executors.compatible(work_item)
        if not compatible:
            raise ValueError(f"no compatible executor for work item {work_item.id}")
        executor = compatible[0]
        self.executors.reserve(executor.executor_id)
        return executor

    def release(self, executor_id: str) -> None:
        self.executors.release(executor_id)

"""Runtime cost and metrics aggregation."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from awr.domain import Status, WorkItem


@dataclass(frozen=True, slots=True)
class CostRecord:
    work_id: str
    executor_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    api_cost: float = 0.0
    duration_ms: float = 0.0


class CostTracker:
    def __init__(self) -> None:
        self._records: list[CostRecord] = []

    def record(self, record: CostRecord) -> None:
        self._records.append(record)

    def summary(self) -> dict[str, object]:
        total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in self._records)
        total_cost = sum(r.api_cost for r in self._records)
        durations = [r.duration_ms for r in self._records]
        by_executor: dict[str, int] = defaultdict(int)
        for record in self._records:
            by_executor[record.executor_id] += 1
        return {
            "calls": len(self._records),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "average_latency_ms": sum(durations) / len(durations) if durations else 0.0,
            "per_executor_calls": dict(by_executor),
        }


class RuntimeMetrics:
    @staticmethod
    def from_items(items: list[WorkItem], executor_utilization: dict[str, object] | None = None) -> dict[str, object]:
        statuses = Counter(item.status.value for item in items)
        return {
            "queued_work": statuses[Status.READY.value] + statuses[Status.APPROVED.value],
            "running_work": statuses[Status.RUNNING.value],
            "completed": statuses[Status.COMPLETED.value],
            "failed": statuses[Status.FAILED.value],
            "retries": sum(item.retry_count for item in items),
            "waiting_human": statuses[Status.WAITING_HUMAN.value],
            "executor_utilization": executor_utilization or {},
        }

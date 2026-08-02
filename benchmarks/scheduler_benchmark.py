"""Simple scheduler benchmark for local development."""

from __future__ import annotations

from time import perf_counter

from awr.domain import Status, WorkItem
from awr.runtime import Scheduler, WorkRegistry
from awr.storage.sqlite_store import SQLiteRuntimeStore


def benchmark(count: int) -> float:
    store = SQLiteRuntimeStore()
    registry = WorkRegistry(store)
    for index in range(count):
        registry.create(WorkItem(title=f"work-{index}", status=Status.READY, priority=index % 10))
    start = perf_counter()
    Scheduler(store).runnable()
    return (perf_counter() - start) * 1000


if __name__ == "__main__":
    for size in (100, 1000, 10000):
        print(f"{size}: {benchmark(size):.2f} ms")

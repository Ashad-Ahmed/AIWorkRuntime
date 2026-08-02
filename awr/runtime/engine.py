"""Public runtime engine API."""

from __future__ import annotations

from time import perf_counter

from awr.artifacts import ArtifactStore
from awr.config import RuntimeConfig
from awr.domain import Status, WorkItem
from awr.metrics import CostRecord, CostTracker, RuntimeMetrics
from awr.replay import RuntimeReplay, ReplayedWorkState
from awr.runtime.registry import WorkRegistry
from awr.runtime.scheduler import Scheduler
from awr.storage.sqlite_store import SQLiteRuntimeStore
from awr.workers import AssignmentEngine, BaseWorker, ExecutionResult, WorkerManager


class RuntimeEngine:
    """Thin public API that composes storage, scheduling, assignment, and workers."""

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        *,
        store: SQLiteRuntimeStore | None = None,
        registry: WorkRegistry | None = None,
        scheduler: Scheduler | None = None,
        workers: WorkerManager | None = None,
        artifacts: ArtifactStore | None = None,
        costs: CostTracker | None = None,
    ) -> None:
        self.config = (config or RuntimeConfig()).validate()
        self.store = store or SQLiteRuntimeStore(self.config.storage.path)
        self.registry = registry or WorkRegistry(self.store)
        self.scheduler = scheduler or Scheduler(self.store)
        self.workers = workers or WorkerManager()
        if not self.workers.list_workers():
            self.workers.register(BaseWorker(worker_id=self.config.worker.default_worker, max_concurrency=self.config.worker.max_concurrency))
        self.assignment = AssignmentEngine(self.workers)
        self.artifacts = artifacts or ArtifactStore()
        self.costs = costs or CostTracker()
        self._shutdown = False

    def submit(self, title: str, description: str = "", **metadata: object) -> WorkItem:
        item = WorkItem(title=title, description=description, status=Status.READY, metadata=dict(metadata))
        return self.registry.create(item)

    def run_once(self) -> WorkItem | None:
        if self._shutdown:
            return None
        item = self.scheduler.next()
        if item is None:
            return None
        worker = self.assignment.assign(item)
        started = perf_counter()
        try:
            self.registry.mark_running(item.id)
            result = worker.execute(item)
            if isinstance(result, str):
                result = ExecutionResult(output=result)
            duration_ms = (perf_counter() - started) * 1000
            if result.output:
                artifact = self.artifacts.put_text(item.id, result.output, producer=worker.worker_id)
                item = self.registry.get(item.id)
                item.artifacts.append(self.artifacts.to_work_item_payload(artifact))
                self.store.save_work_item(item)
            completed = self.registry.mark_completed(item.id)
            self.costs.record(
                CostRecord(
                    work_id=item.id,
                    worker_id=worker.worker_id,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    api_cost=result.api_cost,
                    duration_ms=duration_ms,
                )
            )
            return completed
        except Exception as error:
            self.registry.mark_failed(item.id, str(error))
            raise
        finally:
            self.assignment.release(worker.worker_id)

    def run_until_idle(self, limit: int | None = None) -> int:
        ran = 0
        while limit is None or ran < limit:
            item = self.run_once()
            if item is None:
                return ran
            ran += 1
        return ran

    def pause(self, work_id: str) -> WorkItem:
        return self.registry.pause(work_id)

    def resume(self, work_id: str) -> WorkItem:
        return self.registry.resume(work_id)

    def retry(self, work_id: str) -> WorkItem:
        return self.registry.retry(work_id)

    def cancel(self, work_id: str) -> WorkItem:
        return self.registry.cancel(work_id)

    def approve(self, work_id: str) -> WorkItem:
        return self.registry.approve(work_id)

    def graph(self) -> dict[str, object]:
        graph = self.scheduler.graph()
        artifact_edges = []
        for item in self.registry.list():
            for artifact in item.artifacts:
                artifact_edges.append({"from": item.id, "to": artifact.get("artifact_id"), "type": "artifact"})
        graph["edges"] = [*graph["edges"], *artifact_edges]
        return graph

    def events(self) -> list[object]:
        return self.store.list_events()

    def metrics(self) -> dict[str, object]:
        metrics = RuntimeMetrics.from_items(self.registry.list(), self.workers.utilization())
        metrics["costs"] = self.costs.summary()
        return metrics

    def workers_status(self) -> list[object]:
        return self.workers.list_workers()

    def replay(self) -> dict[str, ReplayedWorkState]:
        return RuntimeReplay.reconstruct(self.store.list_events())

    def recover(self) -> dict[str, object]:
        return {"work_items": len(self.registry.list()), "events": len(self.store.list_events()), "metrics": self.metrics()}

    def shutdown(self) -> None:
        self._shutdown = True
        self.store.close()

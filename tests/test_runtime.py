import pytest

from awr.agents import LLMGatewayAgent
from awr.domain import Status, WorkItem
from awr.runtime import DependencyManager, Scheduler, WorkRegistry
from awr.storage.sqlite_store import SQLiteRuntimeStore


def test_scheduler_respects_dependencies_and_lower_priority_first():
    store = SQLiteRuntimeStore()
    registry = WorkRegistry(store)
    first = registry.create(WorkItem(title="Clean CSV", status=Status.READY, priority=5))
    second = registry.create(
        WorkItem(title="Generate dashboard", status=Status.READY, priority=1, dependency_ids=[first.id])
    )

    assert [item.id for item in Scheduler(store).runnable()] == [first.id]

    registry.mark_running(first.id)
    registry.mark_completed(first.id)

    assert Scheduler(store).next().id == second.id


def test_active_blockers_prevent_scheduling_until_cancelled():
    store = SQLiteRuntimeStore()
    registry = WorkRegistry(store)
    blocker = registry.create(WorkItem(title="Approval", status=Status.READY))
    blocked = registry.create(WorkItem(title="Deploy", status=Status.READY, blockers=[blocker.id]))

    manager = DependencyManager(store)

    assert manager.active_blockers(blocked) == [blocker.id]
    assert Scheduler(store).runnable() == [blocker]

    registry.cancel(blocker.id)

    assert Scheduler(store).next().id == blocked.id


def test_registry_records_lineage_and_events():
    store = SQLiteRuntimeStore()
    registry = WorkRegistry(store)
    parent = registry.create(WorkItem(title="Research competitors"))
    child = registry.create(WorkItem(title="Search companies", parent_id=parent.id))

    assert child.id in registry.get(parent.id).child_ids
    assert [item.id for item in registry.lineage(child.id)] == [parent.id, child.id]
    assert [event.type for event in store.list_events()] == ["TaskCreated", "TaskCreated"]


def test_strict_lifecycle_rejects_illegal_transitions():
    item = WorkItem(title="Deploy application", status=Status.COMPLETED)

    with pytest.raises(ValueError, match="illegal work transition"):
        item.transition_to(Status.RUNNING)


def test_retry_increments_retry_count_and_returns_ready():
    store = SQLiteRuntimeStore()
    registry = WorkRegistry(store)
    item = registry.create(WorkItem(title="Call API", status=Status.READY))
    registry.mark_running(item.id)
    registry.mark_failed(item.id, "timeout")

    retried = registry.retry(item.id)

    assert retried.status == Status.READY
    assert retried.retry_count == 1
    assert [event.type for event in store.list_events()][-2:] == ["TaskRetried", "TaskReadied"]


def test_event_persistence_survives_reopen(tmp_path):
    database = tmp_path / "runtime.sqlite"
    store = SQLiteRuntimeStore(database)
    registry = WorkRegistry(store)
    item = registry.create(WorkItem(title="Persist me"))
    store.close()

    reopened = SQLiteRuntimeStore(database)

    assert reopened.get_work_item(item.id).title == "Persist me"
    assert reopened.list_events()[0].type == "TaskCreated"


def test_llm_gateway_without_endpoint_returns_deterministic_smoke_response(monkeypatch):
    monkeypatch.delenv("AWR_LLM_GATEWAY_URL", raising=False)

    response = LLMGatewayAgent().execute(WorkItem(title="Smoke", description="hello"))

    assert response == "LLM gateway not configured; smoke prompt: hello"

from awr.config import RuntimeConfig, StorageConfig
from awr.runtime import RuntimeEngine
from awr.workers import BaseWorker, ExecutionResult, WorkerManager


class TextWorker(BaseWorker):
    def __init__(self):
        super().__init__(worker_id="text-worker", capabilities={"text"})

    def execute(self, work_item):
        return ExecutionResult(output=f"done: {work_item.title}", prompt_tokens=2, completion_tokens=3, api_cost=0.01)


def test_runtime_engine_assigns_worker_records_artifact_metrics_and_replay(tmp_path):
    workers = WorkerManager()
    workers.register(TextWorker())
    engine = RuntimeEngine(
        RuntimeConfig(storage=StorageConfig(path=str(tmp_path / "runtime.sqlite"))),
        workers=workers,
    )
    item = engine.submit("Summarize", work_type="text")

    completed = engine.run_once()

    assert completed.id == item.id
    assert completed.status == Status.COMPLETED
    assert engine.registry.get(item.id).artifacts[0]["producer"] == "text-worker"
    assert engine.metrics()["costs"]["total_tokens"] == 5
    assert engine.replay()[item.id].status == "completed"
    engine.shutdown()


def test_assignment_rejects_incompatible_workers(tmp_path):
    engine = RuntimeEngine(RuntimeConfig(storage=StorageConfig(path=str(tmp_path / "runtime.sqlite"))))
    engine.submit("Needs browser", work_type="browser")

    with pytest.raises(ValueError, match="no compatible worker"):
        engine.run_once()

    engine.shutdown()


def test_runtime_config_validation_rejects_invalid_storage():
    with pytest.raises(ValueError, match="unsupported storage backend"):
        RuntimeConfig(storage=StorageConfig(backend="postgres")).validate()

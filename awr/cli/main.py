"""Operational command surface for AI Work Runtime."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict

from awr.agents import LLMGatewayAgent
from awr.config import RuntimeConfig, StorageConfig
from awr.domain import Status, WorkItem
from awr.formatting import human_graph, mermaid_graph, panel, status_dashboard, timeline, work_summary
from awr.runtime import RuntimeEngine, Scheduler, WorkRegistry
from awr.storage.sqlite_store import SQLiteRuntimeStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="awr")
    parser.add_argument("--db", default="awr.sqlite", help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("title")
    create.add_argument("--description", default="")
    create.add_argument("--priority", type=int, default=0)
    create.add_argument("--parent-id")
    create.add_argument("--depends-on", action="append", default=[])
    create.add_argument("--blocker", action="append", default=[])
    create.add_argument("--ready", action="store_true")

    start = subparsers.add_parser("start")
    start.add_argument("--interval", type=float, default=1.0)
    start.add_argument("--max-iterations", type=int)
    start.add_argument("--once", action="store_true")

    watch = subparsers.add_parser("watch")
    watch.add_argument("--interval", type=float, default=1.0)
    watch.add_argument("--once", action="store_true")

    graph = subparsers.add_parser("graph")
    graph.add_argument("--json", action="store_true")
    graph.add_argument("--mermaid", action="store_true")

    events = subparsers.add_parser("events")
    events.add_argument("--follow", action="store_true")
    events.add_argument("--interval", type=float, default=1.0)

    demo = subparsers.add_parser("demo")
    demo.add_argument("name", choices=["supplier-research"])

    for command in ("list", "run", "status", "metrics", "workers", "replay", "recover", "timeline"):
        subparsers.add_parser(command)
    for command in ("pause", "resume", "cancel", "retry", "approve", "lineage"):
        sub = subparsers.add_parser(command)
        sub.add_argument("id")

    smoke = subparsers.add_parser("gateway-smoke")
    smoke.add_argument("--prompt", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = SQLiteRuntimeStore(args.db)
    registry = WorkRegistry(store)
    try:
        return _dispatch(args, registry, store)
    finally:
        store.close()


def _engine(store: SQLiteRuntimeStore, registry: WorkRegistry) -> RuntimeEngine:
    return RuntimeEngine(RuntimeConfig(storage=StorageConfig(path=store.database_path)), store=store, registry=registry)


def _dispatch(args: argparse.Namespace, registry: WorkRegistry, store: SQLiteRuntimeStore) -> int:
    engine = _engine(store, registry)
    if args.command == "create":
        item = WorkItem(
            title=args.title,
            description=args.description,
            priority=args.priority,
            parent_id=args.parent_id,
            dependency_ids=args.depends_on,
            blockers=args.blocker,
            status=Status.READY if args.ready else Status.CREATED,
        )
        registry.create(item)
        queue = [work.id for work in Scheduler(store).runnable()]
        queue_position = queue.index(item.id) + 1 if item.id in queue else None
        print(work_summary(item, queue_position))
        return 0
    if args.command == "start":
        return _start(engine, interval=args.interval, max_iterations=1 if args.once else args.max_iterations)
    if args.command == "watch":
        return _watch(engine, interval=args.interval, once=args.once)
    if args.command == "status":
        print(status_dashboard(engine.metrics(), len(engine.workers_status()), "SQLite connected", "Priority Scheduler"))
        return 0
    if args.command == "metrics":
        print(json.dumps(engine.metrics(), indent=2))
        return 0
    if args.command == "workers":
        print(json.dumps([asdict(worker) for worker in engine.workers_status()], default=list, indent=2))
        return 0
    if args.command == "replay":
        print(json.dumps({key: asdict(value) for key, value in engine.replay().items()}, indent=2))
        return 0
    if args.command == "recover":
        print(json.dumps(engine.recover(), indent=2))
        return 0
    if args.command == "timeline":
        print(timeline(store.list_events()))
        return 0
    if args.command == "list":
        for item in registry.list():
            print(panel(item.title, [("ID", item.id), ("Status", item.status.value.upper()), ("Priority", item.priority), ("Worker", item.owner_agent or "unassigned")]))
        return 0
    if args.command == "graph":
        graph = Scheduler(store).graph()
        if args.json:
            print(json.dumps(graph, indent=2))
        elif args.mermaid:
            print(mermaid_graph(graph))
        else:
            print(human_graph(graph))
        return 0
    if args.command == "events":
        return _events(store, follow=args.follow, interval=args.interval)
    if args.command == "run":
        completed = engine.run_once()
        print("No runnable work." if completed is None else panel("✓ Work Executed", [("ID", completed.id), ("Title", completed.title), ("Status", completed.status.value.upper()), ("Worker", completed.owner_agent or "unassigned")]))
        return 0
    if args.command == "demo":
        return _demo_supplier_research(engine)
    if args.command == "pause":
        print(registry.pause(args.id).status.value)
        return 0
    if args.command == "resume":
        print(registry.resume(args.id).status.value)
        return 0
    if args.command == "cancel":
        print(registry.cancel(args.id).status.value)
        return 0
    if args.command == "retry":
        print(registry.retry(args.id).status.value)
        return 0
    if args.command == "approve":
        print(registry.approve(args.id).status.value)
        return 0
    if args.command == "lineage":
        for item in registry.lineage(args.id):
            print(f"{item.id}\t{item.status.value}\t{item.title}")
        return 0
    if args.command == "gateway-smoke":
        item = registry.create(WorkItem(title="LLM gateway smoke", description=args.prompt, status=Status.READY))
        registry.mark_running(item.id)
        try:
            response = LLMGatewayAgent().execute(item)
            registry.mark_completed(item.id, artifact=response)
            print(response)
            return 0
        except Exception as error:
            registry.mark_failed(item.id, str(error))
            raise
    return 1


def _start(engine: RuntimeEngine, interval: float, max_iterations: int | None) -> int:
    print(panel("AI Work Runtime v1.0", [("Storage", "SQLite"), ("Scheduler", "Priority Scheduler"), ("Workers", len(engine.workers_status())), ("Status", "Running"), ("Mode", "Watching for new work...")]))
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        completed = engine.run_once()
        if completed is not None:
            print(f"✓ completed {completed.title} ({completed.id})")
        iterations += 1
        if max_iterations is None:
            time.sleep(interval)
    return 0


def _watch(engine: RuntimeEngine, interval: float, once: bool) -> int:
    while True:
        print(status_dashboard(engine.metrics(), len(engine.workers_status()), "SQLite connected", "Priority Scheduler"))
        print(human_graph(engine.graph()))
        if once:
            return 0
        time.sleep(interval)


def _events(store: SQLiteRuntimeStore, follow: bool, interval: float) -> int:
    seen = 0
    while True:
        events = store.list_events()
        print(timeline(events[seen:]))
        seen = len(events)
        if not follow:
            return 0
        time.sleep(interval)


def _demo_supplier_research(engine: RuntimeEngine) -> int:
    root = engine.submit("Supplier research", "Create a supplier profile", work_type="default")
    website = engine.registry.create(WorkItem(title="Extract supplier website", parent_id=root.id, status=Status.READY, priority=1, metadata={"work_type": "default"}))
    report = engine.registry.create(WorkItem(title="Generate supplier report", parent_id=root.id, status=Status.READY, priority=2, dependency_ids=[website.id], metadata={"work_type": "default"}))
    engine.run_until_idle(limit=3)
    print(panel("✓ Demo Complete", [("Scenario", "supplier-research"), ("Root Work", root.id), ("Completed", engine.metrics().get("completed", 0)), ("Events", len(engine.events()))]))
    print("\nTimeline\n")
    print(timeline(engine.events()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

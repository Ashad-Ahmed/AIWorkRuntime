"""Operational command surface for AI Work Runtime."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from awr.agents import LLMGatewayAgent
from awr.config import RuntimeConfig, StorageConfig
from awr.domain import Status, WorkItem
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

    for command in ("list", "graph", "events", "run", "status", "metrics", "workers", "replay", "recover"):
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


def _dispatch(args: argparse.Namespace, registry: WorkRegistry, store: SQLiteRuntimeStore) -> int:
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
        print(item.id)
        return 0
    if args.command == "status":
        engine = RuntimeEngine(RuntimeConfig(storage=StorageConfig(path=store.database_path)), store=store, registry=registry)
        print(json.dumps(engine.metrics(), indent=2))
        return 0
    if args.command == "metrics":
        engine = RuntimeEngine(RuntimeConfig(storage=StorageConfig(path=store.database_path)), store=store, registry=registry)
        print(json.dumps(engine.metrics(), indent=2))
        return 0
    if args.command == "workers":
        engine = RuntimeEngine(RuntimeConfig(storage=StorageConfig(path=store.database_path)), store=store, registry=registry)
        print(json.dumps([asdict(worker) for worker in engine.workers_status()], default=list, indent=2))
        return 0
    if args.command == "replay":
        engine = RuntimeEngine(RuntimeConfig(storage=StorageConfig(path=store.database_path)), store=store, registry=registry)
        print(json.dumps({key: asdict(value) for key, value in engine.replay().items()}, indent=2))
        return 0
    if args.command == "recover":
        engine = RuntimeEngine(RuntimeConfig(storage=StorageConfig(path=store.database_path)), store=store, registry=registry)
        print(json.dumps(engine.recover(), indent=2))
        return 0
    if args.command == "list":
        for item in registry.list():
            print(f"{item.id}\t{item.status.value}\t{item.priority}\t{item.title}")
        return 0
    if args.command == "graph":
        print(json.dumps(Scheduler(store).graph(), indent=2))
        return 0
    if args.command == "events":
        for event in store.list_events():
            print(json.dumps({"id": event.id, "type": event.type, "work_item_id": event.work_item_id, "payload": event.payload}))
        return 0
    if args.command == "run":
        item = Scheduler(store).next()
        if item is None:
            print("no runnable work")
            return 0
        registry.mark_running(item.id)
        registry.mark_completed(item.id)
        print(item.id)
        return 0
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


if __name__ == "__main__":
    raise SystemExit(main())

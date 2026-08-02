"""Command-line interface for the foundational AWR runtime."""

from __future__ import annotations

import argparse

from awr.models import Status, WorkItem
from awr.registry import WorkRegistry
from awr.scheduler import Scheduler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="awr")
    parser.add_argument("--db", default="awr.sqlite", help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a work item")
    create.add_argument("title")
    create.add_argument("--description", default="")
    create.add_argument("--priority", type=int, default=0)
    create.add_argument("--parent-id")
    create.add_argument("--depends-on", action="append", default=[])
    create.add_argument("--ready", action="store_true", help="Create in ready state")

    subparsers.add_parser("list", help="List work items")
    subparsers.add_parser("ready", help="List schedulable work items")

    status = subparsers.add_parser("status", help="Update work item status")
    status.add_argument("id")
    status.add_argument("status", choices=[status.value for status in Status])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = WorkRegistry(args.db)
    try:
        if args.command == "create":
            item = WorkItem(
                title=args.title,
                description=args.description,
                priority=args.priority,
                parent_id=args.parent_id,
                dependency_ids=args.depends_on,
                status=Status.READY if args.ready else Status.CREATED,
            )
            registry.add(item)
            print(item.id)
            return 0
        if args.command == "list":
            for item in registry.list():
                print(f"{item.id}\t{item.status}\t{item.priority}\t{item.title}")
            return 0
        if args.command == "ready":
            for item in Scheduler(registry).ready():
                print(f"{item.id}\t{item.priority}\t{item.title}")
            return 0
        if args.command == "status":
            item = registry.update_status(args.id, Status(args.status))
            print(f"{item.id}\t{item.status}")
            return 0
    finally:
        registry.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

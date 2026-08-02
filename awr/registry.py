"""SQLite-backed registry for durable work and event state."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from awr.events import Event
from awr.models import Status, WorkItem


class WorkRegistry:
    """Runtime-owned persistence boundary for work items."""

    def __init__(self, database_path: str | Path = ":memory:") -> None:
        self.database_path = str(database_path)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self._migrate()

    def close(self) -> None:
        self.connection.close()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS work_items (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL,
                owner_agent TEXT,
                parent_id TEXT,
                child_ids TEXT NOT NULL,
                dependency_ids TEXT NOT NULL,
                blockers TEXT NOT NULL,
                confidence REAL NOT NULL,
                estimated_cost REAL NOT NULL,
                actual_cost REAL NOT NULL,
                estimated_tokens INTEGER NOT NULL,
                actual_tokens INTEGER NOT NULL,
                retry_count INTEGER NOT NULL,
                artifacts TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                work_item_id TEXT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def add(self, item: WorkItem) -> WorkItem:
        self._upsert(item)
        self.record_event(Event("TaskCreated", item.id, {"title": item.title}))
        if item.parent_id:
            parent = self.get(item.parent_id)
            parent.child_ids.append(item.id)
            self._upsert(parent)
        return item

    def get(self, work_item_id: str) -> WorkItem:
        row = self.connection.execute("SELECT * FROM work_items WHERE id = ?", (work_item_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown work item: {work_item_id}")
        return self._from_row(row)

    def list(self) -> list[WorkItem]:
        rows = self.connection.execute(
            "SELECT * FROM work_items ORDER BY priority DESC, created_at ASC"
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def completed_ids(self) -> set[str]:
        rows = self.connection.execute("SELECT id FROM work_items WHERE status = ?", (Status.COMPLETED,)).fetchall()
        return {row["id"] for row in rows}

    def update_status(self, work_item_id: str, status: Status) -> WorkItem:
        item = self.get(work_item_id)
        previous = item.status
        item.transition_to(status)
        self._upsert(item)
        self.record_event(Event("TaskStatusChanged", item.id, {"from": previous, "to": status}))
        return item

    def events(self) -> list[Event]:
        rows = self.connection.execute("SELECT * FROM events ORDER BY created_at ASC").fetchall()
        return [Event(row["type"], row["work_item_id"], json.loads(row["payload"]), row["id"], datetime.fromisoformat(row["created_at"])) for row in rows]

    def record_event(self, event: Event) -> None:
        self.connection.execute(
            "INSERT INTO events (id, type, work_item_id, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (event.id, event.type, event.work_item_id, json.dumps(event.payload), event.created_at.isoformat()),
        )
        self.connection.commit()

    def _upsert(self, item: WorkItem) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO work_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._to_record(item),
        )
        self.connection.commit()

    def _to_record(self, item: WorkItem) -> tuple[Any, ...]:
        return (
            item.id, item.title, item.description, item.status, item.priority, item.owner_agent,
            item.parent_id, json.dumps(item.child_ids), json.dumps(item.dependency_ids), json.dumps(item.blockers),
            item.confidence, item.estimated_cost, item.actual_cost, item.estimated_tokens, item.actual_tokens,
            item.retry_count, json.dumps(item.artifacts), json.dumps(item.metadata), item.created_at.isoformat(),
            item.updated_at.isoformat(),
        )

    def _from_row(self, row: sqlite3.Row) -> WorkItem:
        return WorkItem(
            id=row["id"], title=row["title"], description=row["description"], status=Status(row["status"]),
            priority=row["priority"], owner_agent=row["owner_agent"], parent_id=row["parent_id"],
            child_ids=json.loads(row["child_ids"]), dependency_ids=json.loads(row["dependency_ids"]),
            blockers=json.loads(row["blockers"]), confidence=row["confidence"], estimated_cost=row["estimated_cost"],
            actual_cost=row["actual_cost"], estimated_tokens=row["estimated_tokens"], actual_tokens=row["actual_tokens"],
            retry_count=row["retry_count"], artifacts=json.loads(row["artifacts"]), metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def add_many(self, items: Iterable[WorkItem]) -> list[WorkItem]:
        return [self.add(item) for item in items]

"""SQLite implementation of the runtime store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from awr.domain import Status, WorkItem
from awr.events import Event


class SQLiteRuntimeStore:
    """Durable SQLite backend for work items and immutable runtime events."""

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
            CREATE TABLE IF NOT EXISTS runtime_events (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                work_item_id TEXT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def save_work_item(self, item: WorkItem) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO work_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._to_record(item),
        )
        self.connection.commit()

    def get_work_item(self, work_item_id: str) -> WorkItem:
        row = self.connection.execute("SELECT * FROM work_items WHERE id = ?", (work_item_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown work item: {work_item_id}")
        return self._from_row(row)

    def list_work_items(self) -> list[WorkItem]:
        rows = self.connection.execute("SELECT * FROM work_items ORDER BY priority ASC, created_at ASC").fetchall()
        return [self._from_row(row) for row in rows]

    def update_status(self, work_item_id: str, status: Status) -> WorkItem:
        item = self.get_work_item(work_item_id)
        item.transition_to(status)
        self.save_work_item(item)
        return item

    def append_event(self, event: Event) -> None:
        self.connection.execute(
            "INSERT INTO runtime_events (id, type, work_item_id, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (event.id, event.type, event.work_item_id, json.dumps(event.payload), event.created_at.isoformat()),
        )
        self.connection.commit()

    def list_events(self) -> list[Event]:
        rows = self.connection.execute("SELECT * FROM runtime_events ORDER BY created_at ASC").fetchall()
        return [
            Event(
                type=row["type"],
                work_item_id=row["work_item_id"],
                payload=json.loads(row["payload"]),
                id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def _to_record(self, item: WorkItem) -> tuple[Any, ...]:
        return (
            item.id,
            item.title,
            item.description,
            item.status.value,
            item.priority,
            item.owner_agent,
            item.parent_id,
            json.dumps(item.child_ids),
            json.dumps(item.dependency_ids),
            json.dumps(item.blockers),
            item.confidence,
            item.estimated_cost,
            item.actual_cost,
            item.estimated_tokens,
            item.actual_tokens,
            item.retry_count,
            json.dumps(item.artifacts),
            json.dumps(item.metadata),
            item.created_at.isoformat(),
            item.updated_at.isoformat(),
        )

    def _from_row(self, row: sqlite3.Row) -> WorkItem:
        return WorkItem(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=Status(row["status"]),
            priority=row["priority"],
            owner_agent=row["owner_agent"],
            parent_id=row["parent_id"],
            child_ids=json.loads(row["child_ids"]),
            dependency_ids=json.loads(row["dependency_ids"]),
            blockers=json.loads(row["blockers"]),
            confidence=row["confidence"],
            estimated_cost=row["estimated_cost"],
            actual_cost=row["actual_cost"],
            estimated_tokens=row["estimated_tokens"],
            actual_tokens=row["actual_tokens"],
            retry_count=row["retry_count"],
            artifacts=json.loads(row["artifacts"]),
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

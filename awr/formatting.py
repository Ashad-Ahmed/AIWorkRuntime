"""Human-friendly terminal rendering helpers for the AWR CLI."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from awr.domain import WorkItem
from awr.events import Event

CHECK = "✓"
DIVIDER = "─" * 52


def panel(title: str, rows: Iterable[tuple[str, object]]) -> str:
    lines = [DIVIDER, title.upper(), DIVIDER]
    for key, value in rows:
        lines.append(f"{key:<18} {value}")
    lines.append(DIVIDER)
    return "\n".join(lines)


def work_summary(item: WorkItem, queue_position: int | None = None) -> str:
    rows: list[tuple[str, object]] = [
        ("Title", item.title),
        ("ID", item.id),
        ("Priority", item.priority),
        ("Status", item.status.value.upper()),
        ("Assigned Worker", item.owner_agent or "unassigned"),
    ]
    if queue_position is not None:
        rows.append(("Queue Position", queue_position))
    return panel(f"{CHECK} Work Created", rows)


def status_dashboard(metrics: dict[str, object], worker_count: int, storage: str, scheduler: str) -> str:
    return panel(
        "AI Work Runtime",
        [
            ("Status", "Running"),
            ("Workers", worker_count),
            ("Queued", metrics.get("queued_work", 0)),
            ("Running", metrics.get("running_work", 0)),
            ("Completed", metrics.get("completed", 0)),
            ("Failed", metrics.get("failed", 0)),
            ("Waiting Human", metrics.get("waiting_human", 0)),
            ("Storage", storage),
            ("Scheduler", scheduler),
        ],
    )


def human_graph(graph: dict[str, object]) -> str:
    nodes = {str(node["id"]): node for node in graph.get("nodes", [])}  # type: ignore[index]
    dependency_edges = [edge for edge in graph.get("edges", []) if edge.get("type") == "dependency"]  # type: ignore[union-attr]
    if not nodes:
        return "No work graph yet. Create work with `awr create ...`."
    children = {str(edge["from"]): str(edge["to"]) for edge in dependency_edges}
    roots = [node_id for node_id in nodes if node_id not in children.values()]
    start = roots[0] if roots else next(iter(nodes))
    lines: list[str] = []
    current: str | None = start
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        node = nodes[current]
        lines.append(f"{node['title']} [{str(node['status']).upper()}]")
        current = children.get(current)
        if current:
            lines.append("↓")
    remaining = [node for node_id, node in nodes.items() if node_id not in seen]
    for node in remaining:
        lines.extend(["", f"{node['title']} [{str(node['status']).upper()}]"])
    return "\n".join(lines)


def mermaid_graph(graph: dict[str, object]) -> str:
    lines = ["flowchart TD"]
    for node in graph.get("nodes", []):
        node_id = _safe_id(str(node["id"]))  # type: ignore[index]
        label = f"{node['title']}\\n{str(node['status']).upper()}"  # type: ignore[index]
        lines.append(f'  {node_id}["{label}"]')
    for edge in graph.get("edges", []):
        source = _safe_id(str(edge["from"]))  # type: ignore[index]
        target = _safe_id(str(edge["to"]))  # type: ignore[index]
        lines.append(f"  {source} -->|{edge['type']}| {target}")  # type: ignore[index]
    return "\n".join(lines)


def timeline(events: list[Event]) -> str:
    if not events:
        return "No events yet."
    lines = [DIVIDER, "TIMELINE", DIVIDER]
    for event in events:
        timestamp = _time(event.created_at)
        work = event.work_item_id or "runtime"
        lines.append(f"{timestamp}  {event.type:<18} {work}  {event.payload}")
    lines.append(DIVIDER)
    return "\n".join(lines)


def _time(value: datetime) -> str:
    return value.strftime("%H:%M:%S")


def _safe_id(value: str) -> str:
    return "n" + "".join(character if character.isalnum() else "_" for character in value)

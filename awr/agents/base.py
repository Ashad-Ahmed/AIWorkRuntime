"""Minimal agent contract."""

from __future__ import annotations

from typing import Protocol

from awr.domain import WorkItem


class Agent(Protocol):
    def execute(self, work_item: WorkItem) -> str: ...

"""First-class artifact records and local artifact store."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Artifact:
    artifact_id: str
    work_id: str
    type: str
    mime_type: str
    path: str
    created_at: datetime
    size: int
    producer: str
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


class ArtifactStore:
    """Stores artifact payloads on disk and returns immutable metadata records."""

    def __init__(self, root: str | Path = ".awr/artifacts") -> None:
        self.root = Path(root)

    def put_text(
        self,
        work_id: str,
        content: str,
        *,
        artifact_type: str = "text",
        mime_type: str = "text/plain",
        producer: str = "runtime",
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        artifact_id = str(uuid4())
        path = self.root / work_id / f"{artifact_id}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return Artifact(
            artifact_id=artifact_id,
            work_id=work_id,
            type=artifact_type,
            mime_type=mime_type,
            path=str(path),
            created_at=datetime.now(UTC),
            size=path.stat().st_size,
            producer=producer,
            metadata=metadata or {},
        )

    @staticmethod
    def to_work_item_payload(artifact: Artifact) -> dict[str, Any]:
        payload = {
            "artifact_id": artifact.artifact_id,
            "work_id": artifact.work_id,
            "type": artifact.type,
            "mime_type": artifact.mime_type,
            "path": artifact.path,
            "created_at": artifact.created_at.isoformat(),
            "size": artifact.size,
            "producer": artifact.producer,
            "version": artifact.version,
            "metadata": artifact.metadata,
        }
        json.dumps(payload)
        return payload

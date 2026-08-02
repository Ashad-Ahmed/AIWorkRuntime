"""Validated runtime configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StorageConfig:
    backend: str = "sqlite"
    path: str = "awr.sqlite"

    def validate(self) -> None:
        if self.backend != "sqlite":
            raise ValueError(f"unsupported storage backend: {self.backend}")
        if not self.path:
            raise ValueError("storage path is required")


@dataclass(frozen=True, slots=True)
class SchedulerConfig:
    policy: str = "priority_first"

    def validate(self) -> None:
        if self.policy != "priority_first":
            raise ValueError(f"unsupported scheduler policy: {self.policy}")


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    url: str | None = None
    api_key: str | None = None

    def validate(self) -> None:
        if self.url is not None and not self.url.startswith(("http://", "https://")):
            raise ValueError("gateway url must be http(s)")


@dataclass(frozen=True, slots=True)
class ExecutorConfig:
    default_executor: str = "echo"
    max_concurrency: int = 1

    @property
    def default_worker(self) -> str:
        """Backward-compatible alias for older worker terminology."""

        return self.default_executor

    def validate(self) -> None:
        if self.max_concurrency < 1:
            raise ValueError("executor max_concurrency must be >= 1")


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    storage: StorageConfig = field(default_factory=StorageConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)

    def validate(self) -> "RuntimeConfig":
        self.storage.validate()
        self.scheduler.validate()
        self.gateway.validate()
        self.executor.validate()
        if self.storage.backend == "sqlite" and self.storage.path != ":memory:":
            Path(self.storage.path).parent.mkdir(parents=True, exist_ok=True)
        return self


# Backward-compatible alias for the previous public name.
WorkerConfig = ExecutorConfig

"""Backward-compatible aliases for the Execution Adapter SDK.

Public documentation now uses executor / execution adapter terminology. These
aliases preserve the previous worker imports while downstream code migrates.
"""

from awr.executors import (
    BaseExecutionAdapter as BaseWorker,
    ExecutionAdapter as Worker,
    ExecutionAssignmentEngine as AssignmentEngine,
    ExecutionResult,
    ExecutorInfo as WorkerInfo,
    ExecutorManager as WorkerManager,
    ExecutorStatus as WorkerStatus,
    HumanExecutionAdapter as HumanWorker,
    LLMExecutionAdapter as LLMWorker,
    PythonExecutionAdapter as PythonWorker,
)

__all__ = [
    "AssignmentEngine",
    "BaseWorker",
    "ExecutionResult",
    "HumanWorker",
    "LLMWorker",
    "PythonWorker",
    "Worker",
    "WorkerInfo",
    "WorkerManager",
    "WorkerStatus",
]

# AI Work Runtime (AWR)

AI Work Runtime is an early foundation for managing autonomous AI work as durable, observable work items instead of transient chains or conversations.

The runtime owns lifecycle, scheduling, dependency management, lineage, persistence, and events. Agents remain simple stateless workers that execute assigned work.

## MVP scope

This repository starts Phase 1 of the roadmap:

- `WorkItem` domain model with statuses and lifecycle validation.
- Durable SQLite-backed work registry.
- Dependency-aware scheduler that only selects ready work.
- Event log for observable lifecycle changes.
- Basic CLI for creating, listing, and advancing work.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
awr create "Research competitors" --description "Find market alternatives"
awr list
awr ready
```

By default the CLI stores runtime state in `awr.sqlite` in the current directory. Override it with `--db path/to/runtime.sqlite`.

## Design principles

1. Work is durable.
2. Every task is observable.
3. Every action is recoverable.
4. Every artifact has lineage.
5. Agents are stateless workers whenever possible.
6. The runtime is the single source of truth.

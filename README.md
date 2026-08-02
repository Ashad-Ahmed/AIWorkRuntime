# AI Work Runtime (AWR)

Today's AI frameworks are excellent at orchestrating intelligence, but they leave runtime concerns—work lifecycle, scheduling, recovery, persistence, observability, approvals, and execution management—to application developers. AI Work Runtime (AWR) explores what an operating system for AI work could look like.

Every task is a persistent `WorkItem` in a work graph, not a transient function call, prompt chain, or chat turn.

AWR is meant to answer operational questions such as what is running now, why it exists, what it depends on, whether it can be paused/resumed/retried/cancelled, and what happened over time.

This repository is intentionally focused on runtime engineering first, with AI workers treated as replaceable execution plugins.

## Current MVP architecture

At runtime, components are composed as a small local control plane:

1. CLI receives operational commands such as `create`, `run`, `pause`, and `lineage`.
2. `WorkRegistry` creates and updates work while enforcing lifecycle transitions.
3. `DependencyManager` checks unresolved dependencies and active blockers.
4. `Scheduler` picks runnable work using the default priority-first policy.
5. `EventBus` emits every significant action and writes it to durable storage.
6. `SQLiteRuntimeStore` stores work items and immutable events.
7. Optional agent adapters execute external work, starting with the LLM gateway smoke adapter.

## Core modules

- `awr/domain/`: `WorkItem`, `Status`, lifecycle transition guards, artifacts, metadata, lineage fields, costs, tokens, dependencies, blockers, and timestamps.
- `awr/runtime/`: lifecycle registry, dependency manager, scheduler policy, stats, and graph snapshots.
- `awr/storage/`: storage protocols and the SQLite backend.
- `awr/events/`: in-process pub/sub event bus with durable sink integration.
- `awr/agents/`: minimal `execute(work_item)` agent contract and LLM gateway adapter.
- `awr/cli/`: local operational command surface.

## Implemented today

- Durable SQLite-backed work registry.
- Guarded lifecycle state machine for created, planned, ready, running, completed, failed, retrying, waiting-human, approved, paused, and cancelled work.
- Dependency-aware scheduling that only considers ready/approved work with completed dependencies and inactive blockers.
- Default scheduler policy: lower numeric priority first, then older work.
- Control operations for pause, resume, cancel, retry, approve, and run.
- Parent-child lineage queries for answering why a task exists.
- Immutable event log in `runtime_events` for baseline observability.
- Artifact and metadata capture on `WorkItem`.
- LLM gateway smoke command using environment-configured credentials.

## Phase 2 additions

- `RuntimeEngine` is the public SDK surface for submit/run/control/graph/events/metrics/replay/recovery.
- `WorkerManager` and `AssignmentEngine` separate worker capability matching from scheduling.
- Strongly typed runtime, storage, scheduler, gateway, and worker configuration centralize validation.
- First-class artifacts, cost tracking, runtime metrics, and replay projections strengthen observability and recovery.
- `docs/` and `benchmarks/` capture architecture and performance expectations as production assets.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
awr create "Research competitors" --description "Find market alternatives" --ready
awr list
awr graph
awr run
awr events
```

By default the CLI stores runtime state in `awr.sqlite` in the current directory. Override it with `--db path/to/runtime.sqlite`.

## CLI surface

```text
create, list, graph, events, run
pause, resume, cancel, retry, approve, lineage
gateway-smoke --prompt "..."
```

## LLM gateway smoke setup

Copy `.env.example` if you want a local place to track gateway configuration. The runtime reads environment variables directly:

```bash
export AWR_LLM_GATEWAY_URL="https://example.com/gateway"
export AWR_LLM_GATEWAY_API_KEY="..."
awr gateway-smoke --prompt "Say hello"
```

If `AWR_LLM_GATEWAY_URL` is not set, the smoke adapter returns a deterministic local message and still exercises lifecycle, event, and artifact capture.

## Not implemented yet

- REST API server.
- Dashboard UI.
- Distributed workers and multi-user execution.
- LangGraph, CrewAI, AutoGen, Temporal, Airflow, and MCP adapters.
- Deadline/cost/agent-capacity-aware scheduling policies.

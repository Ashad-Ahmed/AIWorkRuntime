# Architecture

```mermaid
flowchart TD
  Planner[Planner / Application] --> Engine[RuntimeEngine]
  Engine --> Registry[WorkRegistry]
  Engine --> Scheduler[Scheduler]
  Engine --> Assign[ExecutionAssignmentEngine]
  Assign --> Executors[ExecutorManager / Execution Adapters]
  Executors --> Frameworks[LangGraph / CrewAI / AutoGen / Python / Human / Docker]
  Registry --> Events[EventBus]
  Registry --> Store[SQLiteRuntimeStore]
  Events --> Store
  Engine --> Artifacts[ArtifactStore]
  Engine --> Metrics[CostTracker / RuntimeMetrics]
```

AWR treats work as durable runtime state. Execution adapters execute assigned work and return results; the runtime owns lifecycle, events, scheduling, assignment, artifacts, metrics, replay, and recovery.

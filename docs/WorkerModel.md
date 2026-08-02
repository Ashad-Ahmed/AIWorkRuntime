# Execution Adapter Model

The original code used the term “worker.” Public documentation now uses **execution adapter** because many AI frameworks do not run as persistent workers. They instantiate a graph, crew, conversation, job, or function for one execution and then disappear.

```mermaid
sequenceDiagram
  RuntimeEngine->>ExecutionAssignmentEngine: assign(work)
  ExecutionAssignmentEngine->>ExecutorManager: reserve compatible adapter
  RuntimeEngine->>ExecutionAdapter: execute(work)
  ExecutionAdapter-->>RuntimeEngine: ExecutionResult
  RuntimeEngine->>WorkRegistry: mark completed or failed
```

The runtime manages work. Execution adapters execute work.

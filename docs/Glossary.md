# Glossary

- WorkItem: durable unit of AI work.
- RuntimeEngine: public SDK and composition root.
- Execution Adapter: plugin that executes work using any framework and returns `ExecutionResult`.
- ExecutorManager: registry for execution adapters, health, capacity, and reservations.
- ExecutionAssignmentEngine: matches runnable work to a compatible execution adapter.
- Event replay: reconstructs lifecycle state from immutable events.

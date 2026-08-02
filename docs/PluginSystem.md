# Plugin System

Plugins will cover execution adapters, schedulers, storage, event sinks, approval providers, and LLM gateways. The first plugin boundary is the execution adapter interface: `WorkItem -> execute() -> ExecutionResult`.

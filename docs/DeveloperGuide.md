# Developer Guide

Start with the runtime loop:

```bash
awr create "Research NVIDIA" --ready
awr start --once
awr watch --once
awr timeline
```

Execution adapters are replaceable execution plugins. Runtime code owns lifecycle mutations, events, retries, artifacts, and metrics.

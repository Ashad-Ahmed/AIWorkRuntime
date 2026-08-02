# Contributing

AWR is runtime infrastructure. Keep lifecycle, scheduling, events, persistence, and recovery in runtime modules. Workers should only execute assigned work and return results.

Before opening a PR:

```bash
python -m pytest
python -m compileall awr tests docs benchmarks
```

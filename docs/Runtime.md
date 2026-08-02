# Runtime

`RuntimeEngine` is the public SDK surface. It composes storage, registry, scheduler, execution adapter assignment, artifact capture, cost tracking, metrics, replay, and recovery helpers.

```python
runtime.submit("Summarize report", work_type="text")
runtime.run_once()
runtime.run_until_idle()
runtime.metrics()
```

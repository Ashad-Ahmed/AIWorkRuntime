# Human Approval Example

```bash
awr create "Deploy report" --ready
awr pause <work-id>
awr approve <work-id>
awr resume <work-id>
```

This demonstrates lifecycle control without workers mutating runtime state directly.

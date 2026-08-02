# Dependency Graph Example

```bash
awr create "Extract data" --ready
awr create "Analyze data" --ready --depends-on <extract-id>
awr graph
awr graph --mermaid
```

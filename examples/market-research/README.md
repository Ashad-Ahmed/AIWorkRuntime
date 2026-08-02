# Market Research Example

Create research work and watch the daemon process it:

```bash
awr --db market.sqlite create "Research NVIDIA" --description "Create a short market brief" --ready
awr --db market.sqlite start --once
awr --db market.sqlite timeline
```

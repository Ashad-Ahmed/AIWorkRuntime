# API

The SDK should favor `RuntimeEngine`: `submit`, `run_once`, `run_until_idle`, `pause`, `resume`, `retry`, `cancel`, `approve`, `graph`, `events`, `metrics`, `replay`, `recover`, and `shutdown`.

Execution integrations should implement the `ExecutionAdapter` protocol and return `ExecutionResult`. Previous worker aliases remain temporarily for compatibility.

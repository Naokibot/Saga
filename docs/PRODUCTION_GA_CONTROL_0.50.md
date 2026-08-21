# Using Saga 0.50 for production machine control

Use ordinary Saga for supervisory logic, communication, UI and vision. Keep the hard periodic kernel small and explicit:

```saga
use machine

@control_safe
fn current_error(target: decimal, measured: decimal) -> decimal {
    return target - measured
}

@control_tick(20000, 35)
fn current_tick(target: decimal, measured: decimal) -> decimal {
    let error = current_error(target, measured)
    return max(-1.0, min(1.0, error * 0.5))
}
```

Do not read a socket, wait for CAN, allocate a list, call vision inference, obtain a clock timestamp, or mutate shared application state from the control kernel. Acquire input outside the kernel, timestamp it, verify freshness, then pass scalar/preallocated state into the tick.

For a deployable project, run:

```text
saga production-check . --native --machine
```

The command fails until the project has a locked/reproducible build and a source-bound machine safety case. See `spec/SAGA_PRODUCTION_GA_CONTROL_0.50.md` for the evidence contract.

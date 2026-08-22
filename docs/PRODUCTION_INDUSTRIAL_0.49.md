# Saga 0.49 — production and industrial use

Saga 0.49 treats production delivery and machine control as language-toolchain concerns rather than application conventions.

For large systems, `saga-workspace.toml` groups independently locked projects without flattening their package identities. `saga production-check --native` combines compilation, Standard lint, lock verification, deterministic package creation, capability reporting and a two-build native reproducibility check. This gives CI one fail-closed gate instead of a collection of optional scripts.

For machine control, `@control_tick(rate_hz, budget_us)` makes the intended periodic contract reviewable in source. `machine.control_guard` consumes caller-provided timestamps so hardware/PHC/RTOS timestamps can be used without pretending host `monotonic_ns` is hardware time. It records stale samples, period jitter and execution-budget misses while leaving stop/hold/degrade policy explicit.

The intended specialization is therefore: **ordinary application code stays low-ceremony; code that can affect physical motion carries explicit time, authority and bounded-execution contracts.**

This profile strengthens production candidacy but does not manufacture ecosystem age, third-party audit results, hardware certification or multi-year field evidence. Those remain release gates.

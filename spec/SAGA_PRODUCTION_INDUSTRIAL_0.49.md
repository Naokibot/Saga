# Saga Production & Industrial Profile 0.49

## Status

This profile promotes two concerns to first-class language/tooling contracts: large multi-project production delivery and deterministic industrial-control execution boundaries. It does **not** redefine external platform, security-audit, hardware-safety, or long-term adoption evidence as software tests.

## 1. Workspace contract

A workspace is rooted by `saga-workspace.toml`:

```toml
[workspace]
members = ["libs/core", "services/api", "control/servo"]
```

Members are explicit, remain within the workspace root, may not be symlink aliases, and must have unique project names. Every member retains its own `saga.toml` and `saga.lock`.

## 2. Production project gate

`saga production-check [PATH]` validates every project in a project/workspace:

1. all Saga source compiles;
2. Standard profile lint has no errors;
3. `saga.lock` exactly matches current project inputs;
4. two independently-created `.sagapkg` files are byte-identical;
5. the static minimum capability set is reported.

`--native` additionally builds the Standard native artifact twice from independent temporary build roots and requires byte-identical outputs. The gate emits deterministic JSON and returns a conformance-failure exit code when any gate fails.

A passing project gate is necessary production hygiene. It is not evidence of independent security audit, platform execution, load testing, or functional-safety certification.

## 3. Periodic control contract

`@control_tick` remains valid without arguments for 0.47 compatibility. 0.49 adds an optional explicit contract:

```saga
@control_tick(20000, 35)
fn current_loop(error: decimal) -> decimal {
    return error * 0.5
}
```

The two positional integer literals are `(rate_hz, budget_us)`.

- `rate_hz` must be in `1..1_000_000`;
- `budget_us` must be positive;
- `budget_us * rate_hz <= 1_000_000`;
- the pre-existing allocation/task/exception/unbounded-loop/blocking-I/O restrictions still apply.

Both the Python reference checker and independent Go checker enforce the same contract and diagnostic IDs (`SAGA-C480`..`SAGA-C483`).

## 4. Timestamped control guard

`machine.control_guard(rate_hz, budget_us, stale_input_us, max_jitter_us)` creates a deterministic observation state. The caller supplies timestamps from one monotonic clock domain:

- `machine.control_guard_begin(guard, input_timestamp_ns, cycle_timestamp_ns)` checks input age and start-to-start jitter;
- `machine.control_guard_end(guard, end_timestamp_ns)` checks execution budget;
- `machine.control_guard_ok(guard)` and `machine.control_guard_stats_json(guard)` expose state;
- `machine.control_guard_reset(guard)` clears evidence without altering application safety policy.

The guard never sleeps, stops an actuator, changes a setpoint, or silently degrades a controller. Safety policy remains explicit Saga source or external safety hardware.

## 5. Production compatibility rule

0.49 does not weaken the 1.0 stability candidate: stable diagnostics, deterministic Standard Core behavior, edition-pinned Unicode, public module ABI hashes, resource ownership, package locking/signing, and fail-closed host error translation remain mandatory.

## 6. Qualification boundary

A project may pass `production-check` while the language release is still not unconditionally qualified for arbitrary commercial deployment. A release-level claim additionally requires the existing GA gates: physical Windows/macOS/Linux host execution, independent third-party security audit, signed live registry interoperability, self-host fixed point, second-implementation conformance, and any applicable physical machine/safety qualification.

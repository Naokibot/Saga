# Saga 0.49.0 — Production & Industrial Profile

- Added explicit multi-project `saga-workspace.toml` loading with root confinement, symlink rejection and unique project identity.
- Added `saga production-check` for compile/Standard-lint/lock/reproducible-package/capability gates across a project or workspace.
- Added `saga production-check --native` for byte-reproducible Standard native builds from independent build roots.
- Extended `@control_tick` with optional `(rate_hz, budget_us)` compile-time contracts and shared Python/Go diagnostics.
- Added `machine.control_guard` for timestamped input freshness, start jitter and execution-budget observation without hidden motion policy.
- Preserved existing FOC, encoder, online identification, MPC, disturbance/friction compensation, multi-axis synchronization, CAN-FD/EtherCAT and allocation-free source profile.
- Kept external production/security/platform/hardware qualification gates explicit; 0.49 does not equate local regression success with unconditional commercial certification.

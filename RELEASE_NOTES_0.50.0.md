# Saga 0.50.0 — Production GA Control Hardening

## Added

- `@control_safe` for transitive, statically checked control helpers.
- Whole-call-graph control validation shared by the Python reference implementation and independent Go implementation.
- Compile-time rejection of hidden unverified helpers, recursion, indirect calls, unapproved builtins/external modules, shared/global mutation and direct arbitrary field mutation in the production control surface.
- 4096-iteration static ceiling for literal range loops in production control code.
- `saga production-check --machine` with source-bound machine safety-case evidence.
- Release-specific machine safety profile requiring explicit control timing contracts, external E-stop, STO/interlock, hardware watchdog, deterministic target class, hazard analysis, WCET evidence and HIL evidence.
- Contextual-keyword parser fix: names such as `move` remain valid before comparison/logical/range operators in both Python and Go parsers.
- HTTP redirect/error response ownership fix: rejected redirects and HTTP error responses now close their response objects explicitly, preventing socket/resource accumulation in long-running hosts.
- Resumable source-bound Production GA qualification: passing checks are checkpointed against the exact source-manifest/tree hashes and automatically invalidated after any source change.

## Retained

- 0.49 workspaces, deterministic packaging/native reproducibility and ControlGuard.
- 0.47 FOC/encoder/RLS/MPC/disturbance/friction/electronic gearing/CAN-FD/EtherCAT stack.
- 0.46 precision-control primitives.
- 0.45 async/await/taskgroup/defer/using/move resource model.
- 0.44 hosted 4 kHz logical-cycle profile.

## Scope of the GA designation

0.50 is intended as a Production GA language/toolchain release for machine-control development. It is not a functional-safety certificate for a machine. Hardware-specific hard real time, WCET, HIL, fieldbus, motor/drive and SIL/PL evidence remain deployment-specific and are deliberately fail-closed by the machine-production gate when absent.

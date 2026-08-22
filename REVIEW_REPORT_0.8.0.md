# Saga 0.8.0 review report

Date: 2026-08-07

## Scope

Reviewed the Saga 0.7 reference implementation, Go Portable Core implementation, standard-library task APIs, numeric model, parser/compiler resource handling, package tooling, installers, conformance material, and the ISO/IEC candidate working draft.

## Findings and corrections

| Severity | Finding | Correction in 0.8.0 |
|---|---|---|
| High | Fixed numeric ceilings (8 MiB source, 1,000,000 tokens/AST nodes, nesting 512, module/package ceilings, exact-integer/exponent ceilings) had become de-facto language restrictions. | Removed them from language semantics and reference implementation rejection paths. Host exhaustion is now an implementation resource condition. |
| High | Removing the explicit nesting limit alone exposed Python's default recursion setting as an accidental replacement limit. | Added adaptive compilation recursion capacity proportional to token/AST work. Verified 3,000 nested parentheses, above the former 512 limit. |
| High | Existing `parallel_map` used Python threads, so CPU-bound work was not reliably multi-core parallel because of the Python GIL. | Added process-based `task.cpu_map`, `task.cpu_filter`, and `task.cpu_reduce` using the spawn model and fresh Saga worker interpreters. |
| High | CPU workers could become unsafe if native resources/capabilities were inherited. | Added Process-Send validation. Workers inherit no file, network, DB, GUI, process, plugin, environment, or cloud capabilities. |
| Medium | Worker counts had a Saga-specific ceiling of 256. | Removed the Saga ceiling. Positive counts are delegated to the host; `0` requests automatic scheduling based on available CPUs and job count. |
| Medium | Function definitions/calls were capped at 64 parameters/arguments. | Removed the fixed arity ceiling. Verified an 80-parameter/80-argument function. |
| Medium | Decimal precision was capped at 10,000 digits. | Removed Saga's maximum; any positive host-supported precision is accepted. Verified precision 20,000. |
| Medium | `repeat`, random-byte generation, sleep/UI delays, process timeout/output, HTTP request/response size, JSON depth, and package size contained arbitrary fixed resource ceilings. | Removed Saga-defined maxima. Semantic/protocol constraints remain (for example non-negative delay and valid HTTP status). Physical-host exhaustion remains possible. |
| Medium | Go range evaluation narrowed arbitrary-precision integers to `int64`. | Reworked range iteration to stay on `big.Int`; list bounds are compared as arbitrary-precision integers before host indexing. |
| Medium | Unlimited-by-spec parser behavior could leak host recursion errors in compile/session paths. | Added controlled resource diagnostics and adaptive recursion handling to parse, type-check, source-unit compilation, and REPL sessions. |
| Low | Documentation still described former fixed limits and concurrency as thread-only. | Added Saga 0.8 resource model and CPU parallel execution clauses and migration guide. |

## Security note

"No fixed normative ceiling" does not mean infinite physical resources. A host may still reject allocations, process counts, stack growth, files, or network bodies because physical or administrator resources are exhausted. `--step-limit` remains available as an optional caller-selected watchdog and is disabled by default. Deployments handling hostile input should use OS/container quotas, reverse-proxy body limits, process quotas, and explicit Saga capabilities.

## Parallel semantics

- `task.spawn`, `task.pool`, `task.submit`, `task.parallel_map`: isolated concurrent tasks using threads in the Python reference implementation.
- `task.cpu_map`, `task.cpu_filter`, `task.cpu_reduce`: OS-process CPU parallelism.
- CPU functions must be top-level Saga functions.
- Process-Send values are copied; native resources and object identity do not cross process boundaries.
- CPU worker output is not merged; result values are the communication channel.
- `cpu_reduce` uses tree reduction; associative reducers are required for worker-count-independent results.

## Remaining limitations

- Physical host resources are finite even though Saga no longer prescribes fixed numeric ceilings.
- Python reference parser/type checker still depends on host memory and Python execution machinery, though its former fixed nesting ceiling is removed and recursion capacity is adaptive.
- CPU process startup has nontrivial overhead; it is intended for CPU-bound work rather than tiny tasks.
- Windows installer binaries were cross-built and format-checked in this environment but not executed on a Windows machine.
- Go remains Portable Core Level 1 rather than a complete Hosted Standard implementation.
- Saga is not an ISO/IEC International Standard until external standardization procedures are completed.

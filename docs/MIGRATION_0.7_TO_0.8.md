# Migrating Saga 0.7 projects to 0.8

1. Change `project.language` in `saga.toml` from `0.7` to `0.8`.
2. Fixed language-prescribed resource ceilings have been removed. `--step-limit` remains as an optional caller-selected watchdog and has no default.
3. Decimal `precision(n)` accepts any positive precision supported by the host decimal provider; Saga itself defines no maximum.
4. Function/call argument counts are no longer capped at 64 by the language.
5. `task.pool` and `task.parallel_map` no longer impose Saga's former 256-worker ceiling. The operating system/runtime may still reject an unavailable worker count.
6. Use `task.cpu_map`, `task.cpu_filter`, or `task.cpu_reduce` for CPU-bound parallel execution across operating-system processes. Their functions must be top-level Saga functions and values must satisfy Process-Send.
7. `task.cpu_reduce` should use an associative reducer if results must be independent of worker count.

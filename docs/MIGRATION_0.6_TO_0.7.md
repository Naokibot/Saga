# Migrating Saga 0.6 projects to 0.7

1. Add `language = "0.8"` under `[project]` in `saga.toml`.
2. Use `use "relative.saga"` for project source inclusion. Standard module imports remain `use module`.
3. Re-run `saga check --standard` and `saga test`.
4. Generate `saga.lock` with `saga lock` and verify it with `saga verify`.
5. Do not depend on structural equality for class instances. Class equality is identity equality in 0.7.
6. Update automation to use stable exit statuses and, where needed, `--diagnostic-format json`.
7. Task pool and parallel-map inputs must satisfy the same Send rules as `task.spawn`.
8. Very large syntax and numeric operations now produce controlled resource diagnostics rather than host exceptions.

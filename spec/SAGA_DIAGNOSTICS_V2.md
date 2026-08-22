# Saga Diagnostic Schema 2

A diagnostic has a stable `id` independent of translation. JSON output uses `schema: "saga.diagnostic.v2"` and carries `code`, `id`, `message`, source coordinates, `primary`, `summary`, `notes`, `fixes`, and `suppressed_dependent_errors`.

Human output should answer, in order: what happened; where; why; a safe correction when one is known; and where to learn more. Fixes are suggestions, not semantic authority. Tooling must not determine compiler behavior by matching translated strings.

Compilers should report a root cause instead of cascading dependent errors. The current Native checker is intentionally fail-fast and therefore normally reports one primary error with zero dependent errors; future multi-error recovery shall preserve causal grouping.

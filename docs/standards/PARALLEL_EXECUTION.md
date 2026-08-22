# Saga 0.8 parallel execution model

Saga distinguishes concurrency from CPU parallelism.

- `task.spawn`, `task.pool`, `task.submit`, and `task.parallel_map` use isolated interpreter tasks and are suitable for asynchronous/concurrent work.
- `task.cpu_map`, `task.cpu_filter`, and `task.cpu_reduce` use independent OS processes in the Python reference implementation and can execute CPU-bound Saga code simultaneously on multiple CPU cores.
- `task.cpu_count()` reports the host logical CPU count; `task.process_id()` exposes the current worker process identifier for diagnostics.
- Passing worker count `0` selects the host/runtime default. Positive worker counts have no Saga-defined maximum; the host may reject counts it cannot support.

CPU workers receive only Process-Send values. They do not inherit filesystem, DB, socket, GUI, process, plugin, environment-variable, or cloud capabilities. Top-level Saga functions are reconstructed from the checked program in each worker. Output from worker code is intentionally not merged into the caller; return values are the communication channel.

`cpu_reduce` is a tree reduction. Use an associative reducer when results must not depend on worker count or reduction tree shape.


## Saga 0.45 structured async syntax

Saga 0.45 adds language-level `async fn` / `await` and lexical `taskgroup` to the common hosted surface. Calling an async Saga function returns `future[T]`; `await` unwraps it to `T`. Async calls created inside the innermost `taskgroup` are joined before that lexical group exits. A failing group requests cancellation of pending futures before propagating the failure.

These constructs use the existing isolated-task model rather than adding implicit shared mutable Saga memory. They are hosted concurrency facilities and do not provide a hard-real-time scheduling guarantee.

# Saga 0.45.0 — Language Synthesis Profile

Saga 0.45 promotes a focused set of advanced language features into one common surface shared by the Python reference implementation and the independent Go implementation.

The release adds common `async fn` / `await`, lexical `taskgroup`, LIFO `defer`, deterministic `using`, resource-focused `move`, and a common hosted `task.pool` / `task.submit` / `task.shutdown` API. Public async module APIs are represented as `future[T]` in the deterministic `.smi.json` ABI.

```saga
use task

async fn double(value: int) -> int {
    return value * 2
}

fn answer() -> int {
    defer print("cleanup")
    return await double(21)
}

print(answer())

using pool = task.pool(1) {
    let pending = task.submit(pool, answer)
    print(task.await(pending))
}
```

The new words are contextual rather than unconditional hard keywords. Existing code can still use names such as `await`, `move`, `defer`, `using`, `taskgroup`, and `async` where the spelling is not being used as the corresponding 0.45 construct. `move` is intentionally limited to move-only resources; Saga remains a managed-memory language rather than adopting a general borrow checker.

## Design synthesis

The implementation takes useful ideas from established languages without turning Saga into a compatibility dialect:

- Python-like low ceremony;
- Ruby-like readable scoped code;
- Go-like structured cleanup/concurrency boundaries;
- Rust-inspired explicit transfer for external/native resources;
- Swift/Kotlin-style async source structure;
- Saga's existing exact values, static contracts, capability security, `option` / `result`, modules, and native ABI remain intact.

Raw C/C++ pointer semantics, JavaScript null/undefined semantics, unrestricted runtime metaprogramming, and implicit shared mutable async state are deliberately not added.

## Qualification

Frozen reviewed Saga 0.45 full source tree SHA-256:

`cb06d5ac6e6ff7532c37499e3d38b51753a573d9110a42b5fcfabfba4729e804`

Full reviewed source ZIP SHA-256:

`bcb6fb350d20befea983dabf4458381e95b21d71bdc3361ccf518bb14c22f97b`

Canonical 0.44→0.45 focused patch SHA-256:

`73d60309157fab0cf212d115444cad972f2b01e4415b6538a1c5350b55dc08ff`

Executed software evidence:

- dedicated Language Synthesis 0.45 Python/Go qualification: **6/6 PASS**
- `tests.test_language_synthesis_045`: **12/12 PASS**
- core + Natural language + module + 0.45 selection: **82/82 PASS**
- common module conformance: **14/14 PASS**
- Python↔Go Standard Core differential conformance: **48/48 PASS**
- Python self-conformance: **48/48 PASS**
- Go self-conformance: **48/48 PASS**
- broader Python language/runtime/native regression group: **78/78 PASS**
- Native Object/GC + machine/drone/vision/fine-control/4 kHz regression group: **70/70 PASS**
- Go `go test ./...`: **PASS**
- Go `go vet ./...`: **PASS**
- Go Race Detector on the changed concurrency/resource paths: **PASS**
- project-internal automated security audit: **PASS, 0 issues reported**

A monolithic Python `unittest discover` run was also attempted but exceeded the execution window after only passing progress markers. It is intentionally **not** claimed as a full-suite PASS; the completed explicit groups above are the release evidence.

See `spec/SAGA_LANGUAGE_SYNTHESIS_0.45.md`, `docs/LANGUAGE_SYNTHESIS_0.45.md`, `RELEASE_NOTES_0.45.0.md`, `saga-REVIEW_REPORT-0.45.0.md`, and `saga-VALIDATION-0.45.0.md`.

## Retained 4 kHz hosted control profile

Saga 0.44's hosted **4,000 logical control-state updates per second** profile remains available. On Linux, the Python reference runtime uses kernel `timerfd`; `machine.cycle_wait_due(clock)` reports the logical ticks that became due so temporary scheduler pre-emption does not silently erase state updates.

The profile remains **hosted soft real-time**. Neither the 0.44 timing evidence nor the new 0.45 async/task-pool semantics prove that a physical PWM/GPIO/CAN/EtherCAT edge occurs on every exact 250 us deadline. Hard-deadline current/FOC loops, deterministic fieldbus timing, hardware-timed waveforms, and certified safety motion still require qualified RTOS/driver/drive/FPGA/hardware paths. Physical E-stop/STO/interlocks remain external.

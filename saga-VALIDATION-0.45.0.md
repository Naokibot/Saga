# Saga 0.45.0 validation

Validation distinguishes executed software evidence from claims that require external hardware or a different host scheduler.

## Language Synthesis 0.45

Executed on the release source candidate:

- dedicated 0.45 Python/Go synthesis qualification: **6/6 PASS**;
- `tests.test_language_synthesis_045`: **12/12 PASS**;
- core + Natural language + modules + 0.45 synthesis selection: **82/82 PASS**;
- common module conformance: **14/14 PASS**;
- Python↔Go Standard Core differential conformance: **48/48 PASS**;
- Python Standard Core self-conformance: **48/48 PASS**;
- Go Standard Core self-conformance: **48/48 PASS**;
- Go full `go test ./...`: **PASS**;
- Go `go vet ./...`: **PASS**;
- Go Race Detector on resource/move/using and structured-concurrency regressions: **PASS**.

The dedicated cross-implementation cases execute:

- `async fn` + `await` + LIFO `defer`;
- contextual-word compatibility;
- lexical `taskgroup` joining;
- common `task.pool` / `task.submit` / `task.shutdown` with `using` and `move`;
- static use-after-move rejection (`SAGA-T180`);
- public async `.smi.json` export and ABI-hash equality.

## Broader regression

Additional executed Python regression groups:

- standard language, generic relations, ecosystem, full stack, runtime safety/scale, security profile, Native Runtime and Native Codegen: **78/78 PASS**;
- Native Object, Native Aggregate/GC, machine control, drone control, vision/communications, integrated autonomy/machine, fine control and retained 4 kHz profile: **70/70 PASS**.

The complete monolithic Python `unittest discover` command was also attempted, but exceeded the execution window after producing only passing progress markers up to that point. It is **not counted as a full-suite PASS**. The release evidence therefore uses the explicit completed groups above rather than relabeling a timeout as success.

## Review and security checks

- source manifest exact-tree verification: PASS after final documentation freeze;
- specification final-candidate lint: PASS;
- project-internal automated security audit: PASS, 0 issues in the audit output.

The internal audit is not an independent penetration test or third-party certification.

## Retained external boundaries

Saga 0.45 changes language semantics and hosted concurrency/resource handling; it does not change the external qualification boundary for physical systems.

- Hosted `async`, `taskgroup` and task pools do not provide a hard-real-time scheduling guarantee.
- The Saga 0.44 4 kHz profile remains hosted soft real-time; a physical 250 us I/O deadline still requires target RTOS/driver/hardware qualification.
- Physical aircraft, cameras, PLC/servo/CAN devices and certified safety functions are not newly qualified by this language release.
- Cancellation of host work remains cooperative/best-effort where the host operation itself is not interruptible.
- Finite Python/Go conformance is strong regression evidence, not a proof that every possible program has identical behavior.

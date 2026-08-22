# Saga 0.37.0 Validation Report

## Evidence boundary

This report deliberately separates executed native/Linux tests, cross-target compile simulation, synthetic package scale, and accelerated industrial digital-twin testing. A simulated or cross-compiled target is never relabeled as physical execution.

## Runtime/compiler regressions executed

- New `tests.test_runtime_scale_037`: **5 / 5 PASS**.
  - cross-module generic function/class specialization;
  - external open-world subtype registration after base compilation;
  - concurrent idempotent dispatch registration;
  - bounded low-pause major mark/sweep polling;
  - debugger watch/record/profile behavior.
- Native Runtime 0.35 regression: **10 / 10 PASS**.
- Native Aggregate/GC regression: **14 / 14 PASS**.
- Native Codegen regression: **8 / 8 PASS**.
- Module/generic/machine group: **45 tests PASS**.
- Core language / Natural / Standard / full-stack group: **84 tests PASS**.
- Existing ecosystem regression: **15 / 15 PASS**, with `ResourceWarning` promoted to error after registry connection-lifetime fixes.
- Independent Go full tests: PASS.
- Independent Go `go vet ./...`: PASS.

Long combined Python invocations can exceed the execution harness wall-clock limit. The release does not claim a new repository-wide all-tests count from a timed-out aggregate command; completed suites are reported individually.

## Low-pause GC direct runtime evidence

A direct C runtime harness creates 50 unreachable managed objects plus one rooted object and runs low-pause major collection with an object budget of 7.

Observed behavior in review:

- collection polls: 9;
- maximum reported pause work: 7 objects;
- incremental sweep count: 1;
- final live object count: 1.

An ASan/UBSan runtime harness combining low-pause GC and concurrent dispatch registration completed without detected AddressSanitizer or UndefinedBehaviorSanitizer faults. Source-bound Native Runtime qualification also exercises the legacy zero-budget incremental-start contract after the compatibility fix.

## Package ecosystem scale simulation

`tools/ecosystem_scale_qualification.py` executes a synthetic metadata corpus:

- package names: 20,000;
- versions per name: 5;
- package-version rows: **100,000**;
- search backend: **FTS5 trigram** on this host;
- 200 sequential searches;
- 8 concurrent readers × 40 searches = 320 concurrent searches;
- SQLite `integrity_check`: **ok**;
- indexed rows: **100,000**;
- qualification result: PASS.

A representative final pre-freeze run measured mean sequential search latency around 3.3 ms, p95 around 6.2 ms, and worst concurrent query around 91 ms. These are host-specific measurements, not service-level guarantees.

## Windows/macOS simulated qualification

No Windows or macOS machine is available on the review host. The replacement evidence is cross-target compile and binary-structure verification:

### Windows amd64
- CLI cross-build: PASS;
- standalone runtime cross-build: PASS;
- target test binary compilation: PASS;
- PE32+ magic/format inspection: PASS;
- physical execution: **UNEXECUTED**.

### macOS amd64
- CLI cross-build: PASS;
- standalone runtime cross-build: PASS;
- target test binary compilation: PASS;
- Mach-O 64-bit magic/format inspection: PASS;
- physical execution: **UNEXECUTED**.

This does not validate Win32/macOS process startup, filesystem semantics, GUI behavior, code signing/notarization, device drivers, installer behavior, Gatekeeper/SmartScreen, or physical hardware access.

## Seven-day industrial digital-twin endurance

`tools/industrial_endurance_simulation_037.py` was run for **168 simulated hours** with a 100 ms supervisory period:

- control cycles: **6,048,000**;
- accelerated wall time: about 27 seconds on this host;
- Modbus RTU transactions: **10,082**;
- normal periodic Modbus reads: 10,080;
- expected injected Modbus failures: 2;
- unexpected failures: **0**.

Injected faults all passed their fail-safe checks:

- following error -> safety latch trips;
- soft limit -> safety latch trips;
- emergency stop -> output forced to zero;
- corrupt Modbus CRC -> rejected;
- dropped Modbus response -> timeout/short-response rejection;
- recovery remains explicit rather than automatic.

Physical PLC/drive/motor/CAN/encoder/fieldbus hardware was **not attached**. This endurance run therefore does not establish mechanical durability, EMI immunity, deterministic timing, hardware watchdog behavior, certified safety, or field reliability.

## Source-bound release validation

The distribution includes `release/source-manifest-0.37.0.json`. Final qualification tools verify that manifest before emitting source-bound evidence for cross-implementation, modules, native runtime/codegen, machine-control, security, and runtime-0.37 behavior. Validation JSON is intentionally excluded from the source-tree digest so evidence can be regenerated without mutating the source identity.

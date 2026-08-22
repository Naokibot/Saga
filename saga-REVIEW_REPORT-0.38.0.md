# Saga 0.38.0 review report

## Scope

0.38 addresses the remaining 0.37 qualification gaps that can be addressed inside this environment: the minor/nursery collector is no longer forced into a whole-cycle STW path when low-pause mode is enabled; simulated OS/HIL/public-registry/safety-assessment harnesses are expanded and evidence-labeled.

## Code changes reviewed

### Incremental minor GC
- Added `SAGA_GC_MINOR_MARKING` and `SAGA_GC_MINOR_SWEEPING` phases.
- Added `saga_gc_minor_step(budget)`, `saga_gc_incremental_minor_collections()` and `saga_gc_incremental_minor_available()`.
- Low-pause allocation pressure now starts/advances the nursery cycle instead of calling the synchronous whole-cycle minor collector.
- Root rescanning and a minor write barrier preserve mutations during incremental marking.
- Remembered old objects are queued to discover old->young edges.
- Objects allocated during minor marking/sweeping are protected by the allocation barrier.
- Promotion recomputes whether the promoted object must remain remembered.
- Existing `saga_gc_collect_minor()` remains a synchronous compatibility wrapper.

Review boundary: the budget is measured in objects, not microseconds. A single very large object's slot scan can still exceed a real-time latency target. 0.38 therefore claims lower-pause/incremental nursery collection, not hard-real-time or pauseless GC.

### External-gate simulation
- Windows/macOS: cross-build CLI/runtime/target test binary and parse PE/Mach-O structure; physical execution remains `UNEXECUTED`.
- Industrial HIL: PTY/termios is used by Saga's real `UARTDevice` and `ModbusRTUMaster`; CAN is represented by OS datagram sockets because `vcan0` cannot be created without `CAP_NET_ADMIN`; PLC/servo/motor/encoder remain simulated.
- Registry: actual Saga HTTP registry, immutable signed publish, search, download and digest checks are exercised under concurrent virtual-user load; no public Internet endpoint or real adoption is claimed.
- Safety: software safety semantics and fault injection are assessed, but SIL/PL targets are not invented and status stays `NOT_CERTIFIED`.

## Defects found during this pass

1. Incremental-minor write barrier initially referenced the minor mark helper before its C declaration. Fixed with an explicit forward declaration and compiler regression.
2. PTY PLC simulator initially closed the only slave descriptor before Saga opened the UART, allowing the master-side worker to exit with `EIO`. Fixed by retaining a guard slave descriptor for the simulator lifetime.
3. Registry load project names used a numeric-only hyphen segment rejected by Saga's project-name grammar. Fixed by generating valid Saga identifiers.
4. Source-bound Native Runtime qualification initially hard-coded runtime feature level 0.37 and rejected the correct 0.38 metadata. Fixed the qualification expectation before refreezing the source.
5. Four-way Windows/macOS x64/arm64 parallel cross-build exceeded the execution window. The current qualification is narrowed to the requested desktop x64 targets and explicitly records arm64 as outside this pass rather than silently treating timeout as PASS.

## Regression evidence before source freeze

- Core/general/module/machine group: 129/129 PASS.
- Runtime/GC group: 30/30 PASS.
- Native codegen/object/human-value group: 22/22 PASS.
- Security/ecosystem group: 27/27 PASS.
- Go implementation: `go test ./...` PASS and `go vet ./...` PASS.
- Full `unittest discover` was attempted but exceeded the command execution window; no all-suite aggregate PASS is claimed from that run.

## External evidence boundary

A physical Windows/macOS machine, physical PLC/servo/CAN/encoder/motor rig, inbound public Internet service with real users, and an accredited/independent functional-safety certification process are not available inside this execution environment. The corresponding 0.38 results are simulation/pre-certification evidence only and must not be relabeled.

## Source-bound qualification after freeze candidate

The 0.38 source-bound tools were run against a generated 0.38 manifest and passed after correcting the stale 0.37 feature-level expectation in the qualification harness:
- runtime 0.38 qualification: 6/6;
- Python↔Go differential: 48/48;
- module conformance: 14/14;
- Native Runtime qualification: 10/10;
- Native Codegen qualification: 17/17;
- machine-control qualification: PASS (23 Python machine tests plus Go regression/vet and example checks);
- internal automated security review: 0 issues;
- specification review lint: PASS.

The final distribution is refrozen after this report change and the source-bound set is rerun against the final manifest.

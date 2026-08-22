# Saga 0.37 General-Purpose Readiness

Saga 0.37 is a serious general-purpose/runtime engineering preview. It does not claim safety certification, universal production readiness, or physical-platform qualification that was not actually executed.

## Added in 0.37

- low-pause major GC mode: incremental mark **and** incremental sweep, each bounded by an object-work budget per `saga_gc_poll()`; minor/nursery GC remains stop-the-world;
- open-world native dispatch registry with stable public type/slot constants, base/interface registration, externally registered method thunks and synchronized concurrent registration;
- cross-module native specialization of public generic functions and generic aggregate templates in the caller object;
- bounded debugger execution recording with lexical watches, plus statement elapsed-time/heap profilers in both Python and Go implementations;
- indexed signed registry search using SQLite FTS5 trigram when available, with plain-SQL fallback;
- scale qualification against 100,000 synthetic package versions and concurrent readers;
- Windows/macOS target build + target-test compilation evidence, explicitly separated from physical execution;
- accelerated 168-hour industrial digital-twin endurance qualification using Saga axis/safety logic and the real Modbus RTU master parser/transaction path.

## Evidence boundary

| Area | 0.37 evidence |
|---|---|
| Linux native runtime | Executed on the current Linux host |
| Windows x64 | Cross-build + target test-binary compile + PE structural check; physical run UNEXECUTED |
| macOS x64 | Cross-build + target test-binary compile + Mach-O structural check; physical run UNEXECUTED |
| package scale | 100k synthetic package-version index; not 100k real community packages |
| industrial endurance | 7-day accelerated digital twin; no physical PLC/drive/motor rig attached |
| hard real time | Not claimed |
| SIL/PL / machinery safety certification | Not claimed |

## Remaining 1.0 work

Physical Windows/macOS execution, hardware-in-the-loop industrial endurance, independent external security review, long-term public package governance, bounded-time minor collection or a moving/region collector where appropriate, and broader real-world deployment evidence remain external gates. Open-world dispatch now exists, but stable long-term plugin ABI governance still needs ecosystem experience.

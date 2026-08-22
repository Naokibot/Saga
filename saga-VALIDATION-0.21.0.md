# Saga 0.21.0 Validation Report

Validation host: Linux x86-64. Release focus: application-use expansion while retaining Standard Core, Edition 2027 and official SH-3 qualification.

## Core regression

| Check | Result |
|---|---:|
| Go reference unit tests | PASS |
| Go `vet` | PASS |
| Go Race Detector | PASS |
| Python reference | **155/155 PASS + 4 subtests** |
| Native game checker/runtime/manifest | **101/101 aligned** |
| Hosted API reference validator | **149/149 registered Python reference entry points exercised** |
| Parser fuzz | **100,000 cases; 0 unexpected host exceptions** |
| Expression fuzz | **25,000 cases; 0 unexpected host exceptions** |
| Internal automated security review | PASS, 0 unresolved findings |

## Official SH-3

`tools/sh3_validate.py` was rerun after the browser-host bootstrap changes.

- bootstrap VM strict C11 build: PASS
- Stage1 -> Stage2 -> Stage3: PASS
- compiler Stage2 == Stage3: PASS
- compiler fixed-point SHA-256: `2c754d21da7740b5d1be341f5fca83f9e6c8d65e93371e7514fd119c86480e78`
- canonical kernel deterministic SHA-256: `88d16d709dae09c82662e8ea0cc0273d174458bff0382362ac524560dc71b5dd`
- Standard Core success: **23/23**
- Standard Core diagnostics: **11/11**
- Edition 2027: **14/14**
- source loader/lowering: PASS
- empty-PATH `saga` / `sagac`: PASS
- source-boundary audit: PASS, 0 problems

The C11 seed adds only generic `host_available`/`host_call` bootstrap primitives. Saga module/DOM semantics remain in canonical Saga source or optional browser host adapters; the SH-3 source-boundary audit remains green.

## Web / PWA

- `saga build ... --target web`: PASS in Go tests.
- `--target pwa`: PASS; generated 8-file offline bundle for `examples/web/pwa_counter.saga`.
- embedded browser VM syntax (`node --check`): PASS.
- embedded application JavaScript syntax: PASS.
- canonical SH-3 kernel executes through the JavaScript language-neutral VM: PASS (`42`).
- DOM host integration: PASS for text/value/attribute updates.
- localStorage set/get host path: PASS.
- click dispatch path: PASS.
- browser-unavailable fail-closed path in Native Hosted: covered by implementation/tests.

A Chromium executable existed on the host, but even a trivial headless data-URL page hung in the host D-Bus/zygote environment and timed out. Therefore a real Chromium page run is **not** counted as PASS; Node-based browser-host integration is the executed browser-runtime evidence for this release.

## HTTP server

- real localhost listen with ephemeral port: PASS.
- external `curl` -> Saga source server -> HTTP 200 body `Hello from Saga`: PASS.
- method/path/body/header/query accessors: PASS.
- one-response rule: PASS.
- 8 MiB request-body guard: implemented.
- outstanding `accept` unblocks on close: PASS.
- response write acknowledgement before `respond()` returns: PASS.

An initial E2E run exposed a race where `server_close()` could cancel the host handler after Saga enqueued a response but before bytes were written. The implementation was changed to wait for a host write acknowledgement and the E2E was rerun successfully.

## Database transactions

- begin/snapshot: PASS.
- commit: PASS.
- rollback: PASS.
- optimistic same-handle conflict: PASS.
- normalized path-level write mutex: PASS.
- write-new-then-rename persistence: PASS.
- Saga source E2E persisted `{"name":"Saga","version":21}`: PASS.

This is not a claim of multi-process PostgreSQL/SQLite-class ACID isolation.

## Portable 3D

- custom triangle mesh: PASS.
- cube mesh: PASS.
- Wavefront OBJ vertices/faces + quad triangulation: PASS.
- transforms and perspective camera: PASS.
- reciprocal-depth rasterization and per-pixel depth buffer: PASS.
- wireframe path: covered by checker/runtime and unit surface.
- Saga source cube example: PASS; reported 10 rasterized visible triangles on the test view.

No claim is made for PBR, skeletal animation, scene graphs, GPU mesh rendering or an AAA engine.

## Mobile/system boundary

PWA output is installable/offline web-app infrastructure and materially improves mobile deployment, but native Android/iOS App Store binaries were not built or executed in this validation. Systems introspection adds platform/architecture/CPU/page-size without exposing ambient environment variables.

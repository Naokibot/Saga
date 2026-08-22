# Saga 0.24.1 source review report

## Scope

The review covered language/runtime type consistency, task/process value boundaries, DB persistence and concurrency, HTTP/network boundaries, process execution, Universal App actions, package registry/install paths, defensive cryptography, release validators and cross-platform build surfaces.

## Findings fixed

### High — DB symlink persistence could split one logical database

0.24.0 canonicalized the lock identity but retained the caller's symlink path as the persistence path. Atomic rename through that path could replace the symlink rather than the target, causing the alias and real database to diverge. `db.open` now stores and persists to the canonical target path. A regression test verifies that writing through a symlink preserves the symlink and updates the real database.

### High — Python security API violated its declared `result[T,E]` contract

Four defensive APIs were statically declared as `result[...]` in Native but the Python reference exposed raw text/bool values or raised host exceptions. They now return `ResultValue` consistently. This exposed a deeper interpreter defect: native return validation, Send/Process-Send checks and isolated-task snapshots did not fully support ResultValue. Those paths were fixed and a task-boundary regression was added.

### Medium/high — Registry identity and archive exhaustion hardening

The Go registry add path did not strongly bind the returned package name/version to the requested `name@version`, and extraction had no explicit archive-shape defenses. Registry requests now validate project-name + SemVer identity, require exact requested/returned identity, escape query/path components, use an explicit client, bound registry protocol payloads, reject duplicate/unsafe/non-regular archive entries, and enforce deployment-profile extraction limits. Python reference registry received corresponding name/version, wire-size, archive traversal/symlink/file-count/expanded-size and cleanup hardening.

### Medium/high — Universal App JSON ambiguity

Host action payload decoding previously used ordinary JSON last-key-wins behavior. Duplicate keys are now rejected through Saga's strict JSON decoder before host conversion.

### Medium — Text/network boundary validation

Universal App file reads now use bounded UTF-8 decoding. HTTP server request bodies reject invalid UTF-8, and response Content-Type rejects CR/LF to prevent header injection. The standard HTTP API keeps explicit proxy/redirect behavior and gains optional administrator timeout/body policies rather than a new language-level fixed ceiling.

### Medium — Process resource policy without semantic regression

A first hardening attempt imposed a fixed 8 MiB process-output ceiling. The existing 17 MiB regression correctly failed. Saga's no-fixed-normative-ceiling rule was restored; deployments can opt into `SAGA_PROCESS_OUTPUT_LIMIT_BYTES`. `process.run` remains argv-only/no-shell and its caller-supplied positive timeout remains uncapped by an arbitrary Saga maximum.

### Medium — Hosted validator contract drift

The Hosted validator still asserted raw values for security functions after the API moved to `result[T,E]`. The validator now unwraps successful ResultValue instances and again covers all 160 registered entry points.

### Low — Duplicate verification branch

The Python registry server repeated the same publisher-fingerprint mismatch condition twice. The duplicate branch was removed.

## Review result

No unresolved defect found by this project-internal review remains in the changed areas. Static review and automated testing cannot prove defect absence. The project-internal security audit is not an independent penetration test or external certification.

## Remaining boundaries / non-claims

- The built-in JSON application DB is not PostgreSQL/SQLite-class distributed or multi-host ACID storage. Cross-process safety is tested on one host and lock semantics remain OS/filesystem dependent.
- Public registry limits are deployment/profile controls, not language semantic ceilings.
- Vulkan probing succeeds as a fail-closed capability check on this host, but a usable Vulkan instance/device is not present, so a real Vulkan present/render path is unverified here.
- Windows/macOS/ARM64 binaries are cross-built/format-checked unless explicitly stated; target-host execution is not inferred.
- AWS, physical GPIO, Spark, pygame, mobile entitlements/devices and third-party lab/security validation require their actual external environments.

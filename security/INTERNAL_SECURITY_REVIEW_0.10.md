# Saga 0.10.0 internal security review

Status: project-internal review, **not an independent third-party audit**.

## Changes reviewed

- Python plugins moved out of process and communicate through a serialized value boundary.
- Linux strict plugin mode uses user/mount/PID/IPC/UTS/network namespaces, `no_new_privs`, path masking, minimal environment and resource controls.
- plugin/processor AST policy rejects imports and dunder/object-graph introspection paths; exposed standard-library helpers are narrow facades rather than raw module objects.
- strict sandboxing is fail-closed on unsupported platforms.
- diagnostic identity no longer depends on parsing Japanese/localized text.
- task Send/snapshot boundaries, WebSocket proxy/redirect behavior, process execution, private display/serialization and package/symlink boundaries were re-reviewed.
- Go Standard Core implementation was reviewed with `go test`, `go vet`, Race Detector and cross-implementation tests.

## Automated internal scan

`tools/internal_security_audit.py` reported zero unreviewed findings. `shell=True`, `os.system`, unisolated `eval`, and localized-message compatibility classifiers were not found. Two uses of `exec` remain in the dedicated isolated plugin/processor workers after AST policy validation and are explicitly recorded as reviewed exceptions.

## Attack-oriented regression evidence

The regression suite verifies that secure plugins cannot use `open`, cannot import `os`, cannot use dunder subclass introspection, and cannot escape through raw `statistics` module state. A permitted pure-computation plugin continues to work. Linux strict whole-program sandbox tests show that a network capability granted by Saga still cannot cross the separate network namespace.

## Dependency observation

Saga Standard Core itself declares no third-party Python runtime dependency, and Saga Go lists no third-party Go modules. The host test environment has an unrelated `moviepy 2.2.1` / `Pillow 12.2.0` dependency conflict; it is recorded separately and is not introduced by Saga Core.

## Residual risk

Python is not a security boundary by itself; strict plugin security relies on the Linux kernel namespace boundary plus language-level restrictions. A kernel vulnerability may defeat it. Windows AppContainer/Job Object and macOS sandbox equivalents are not implemented in this release, so strict mode refuses to claim strong sandboxing there. Optional hosted libraries have their own vulnerability surface.

## Independence

This report cannot satisfy the requested third-party audit requirement because it was produced by the same project/work environment. `security/THIRD_PARTY_AUDIT_SCOPE_0.10.md` and the external audit handoff archive are provided for an unrelated assessor.

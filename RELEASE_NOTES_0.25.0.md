# Saga 0.25.0 release notes

## Theme: platform qualification and GA readiness

Saga 0.25.0 converts the remaining external platform gaps from informal caveats into explicit implementation profiles, live qualification tools and fail-closed release gates. It does not relabel mocks, cross-builds, simulators or software renderers as physical-hardware evidence.

## Implemented platform work

- Vulkan: the production SDL/Vulkan backend is exercised through instance/device/surface/swapchain/acquire/submit/`vkQueuePresentKHR`. The current Linux host passes on Chromium SwiftShader, recorded as `PASS_SOFTWARE_DEVICE`; physical-GPU qualification remains a separate gate.
- AWS: live STS `GetCallerIdentity` qualification through Saga is available with explicit `--allow-cloud` and authorized credentials/OIDC. Generic cloud calls reject private/underscore SDK methods.
- GPIO: input, output, PWM, read, write, on/off and close are available. Physical-device access now requires the dedicated `--allow-device` capability.
- Spark: local sessions, SQL and range-count processing are supported; creating Spark/Py4J sessions requires `--allow-process`.
- pygame: a finite-frame `game.run_frames` path makes real pygame execution CI-qualifiable without an infinite demo loop.
- Android/iOS: StandardCoreRuntime generation is build/vet/execution-tested. Android Gradle generation was repaired and mobile runtime dependency closure was completed. Device validation scripts and CI jobs are included.
- Native desktop OSes: Linux/Windows/macOS native-host qualification jobs build and execute the current Saga Native release on the actual host. Cross-build artifacts do not satisfy these gates.
- Physical gamepads/GPIO: self-hosted hardware-lab gates are included and require explicit operator opt-in.
- Third-party security: an Ed25519-signed independent-audit attestation verifier is included. It refuses GA evidence with open critical/high findings or invalid/non-independent attestations.

## Language/tooling hardening

- Hosted API coverage is now 168/168 across 28 modules.
- Added current-release Python↔Go differential conformance evidence.
- Fixed a Native HTTP response lifecycle race where request-context cancellation could beat an already-buffered successful write acknowledgement.
- Added `python -m saga` as a first-class module entry point.
- Added a Python `saga debug` command with statement trace and line breakpoints, aligned in purpose with Saga Native's debugger.
- Added `tools/ga_readiness.py` and `docs/GA_READINESS_1.0.md` so “generally usable” is a machine-verifiable project state rather than a marketing claim.
- Added Language Specification 1.0 RC2, repairing duplicate/out-of-order clause and annex structure found during review. RC2 is deliberately not called Final.

## Package/registry hardening

- Registry installs now verify the package's internal project/lock identity against the requested name/version.
- Installation uses staging and rollback instead of extracting directly over the destination.
- Signed live HTTPS publish/search/install qualification is available as a dedicated GA gate.
- Existing archive traversal, duplicate-path, symlink, download and extraction-size protections remain in force.

## Qualification summary on the current host

Internal/current-host release qualification passes, including 174 Python tests plus 4 subtests, Go full/vet/race, optional FFI/JIT/Desktop/Vulkan-tagged suites, Hosted 168/168, security, game/web/app API alignment, real Chromium, machine smoke, 100,000 parser fuzz cases, 25,000 expression fuzz cases, cross-implementation conformance and SH-3 fixed-point qualification.

Saga 0.25.0 is **not yet Core GA 1.0**. The current GA blockers are a final Language Specification 1.0, native execution evidence on Windows and macOS, a live external signed HTTPS registry roundtrip, and an independent signed security audit. Optional physical/service profiles have separate evidence gates and do not block the core language GA definition.

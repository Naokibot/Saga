# Saga 0.21.0 Release Notes

Saga 0.21.0 is the **Application Expansion** release. It keeps Standard Core 1.0 RC1, Edition 2027 Preview and the official SH-3 implementation while strengthening previously weak application areas.

## Added

- Browser SH-3 target: `--target web`.
- Offline/installable PWA target: `--target pwa`.
- Browser-hosted DOM, form value, localStorage and click-dispatch APIs.
- Native Hosted HTTP listen/accept/respond server API with close-safe acceptance and an 8 MiB body limit.
- Persistent DB optimistic transactions with rollback/conflict detection and atomic replacement.
- Portable CPU 3D renderer: perspective camera, mesh transforms, depth buffer, filled/wireframe triangles.
- Wavefront OBJ vertex/face loading with polygon triangulation.
- `sys.platform`, `sys.arch`, `sys.cpu_count`, and `sys.page_size`.
- Native game API inventory grows from 92 to **101** functions.

## Preserved

- SH-3 all-source self-hosting qualification.
- Standard Core and Edition 2027 behavior.
- C ABI Profile 2, bare-metal Cortex-M0/STM32, SIR1 and Desktop graphics profiles.

## Explicit non-claims

0.21 does not claim a native Android/iOS SDK, AAA 3D engine, production distributed database, or complete OS kernel environment. The PWA target is the mobile deployment improvement in this release; the 3D renderer is a CPU baseline rather than a replacement for a full GPU scene engine.

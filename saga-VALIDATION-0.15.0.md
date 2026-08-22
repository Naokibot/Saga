# Saga 0.15.0 validation report

Validation date: 2026-08-09
Validation host: Debian GNU/Linux 13 x86-64 container

| Validation | Result |
|---|---:|
| Python reference test suite | 154/154 PASS, plus 4 subtests |
| Go default tests | PASS |
| Go vet | PASS |
| Go Race Detector | PASS |
| Native Standard Core self-conformance | 17/17 PASS |
| Python Hosted API validator | 149/149 entry points exercised; PASS with documented external test doubles |
| Internal automated security review | PASS, 0 unresolved issues; project-internal only |
| Portable game pipeline Saga source | PASS (`PORTABLE_GAME_OK 64x48 tex=64x16 particles=1 frame=2`) |
| PNG native decode test | PASS |
| JPEG native decode test | PASS |
| RGBA primitives/blending tests | PASS |
| Animation/tilemap/particle tests | PASS |
| AABB physics tests | PASS |
| WAV PCM + asset-cache tests | PASS |
| Desktop-tag Go tests | PASS |
| SDL2/OpenGL/Xvfb integration | PASS |
| Native window creation | PASS under Xvfb |
| OpenGL context + RGBA presentation | PASS |
| GLSL fragment shader | PASS |
| Explicit vertex+fragment shader program | PASS |
| Keyboard/mouse state query paths | PASS (API/query path; no physical user input injected) |
| SDL audio queue with dummy audio driver | PASS |
| Saga desktop smoke source | PASS |
| Standards evidence chain/tamper regression | PASS |
| Standards 4/5 P-member threshold regression | PASS |
| Game checker/runtime/manifest API alignment | PASS (85/85 names aligned) |
| Linux x86-64 portable binary | static ELF, PASS |
| Linux ARM64 portable output | AArch64 ELF format PASS; target hardware not executed |
| Windows x86-64 portable output | PE32+ x86-64 format PASS; Windows host not executed |
| Windows ARM64 portable output | PE32+ ARM64 format PASS; target hardware not executed |

## Desktop renderer evidence

The real Saga source `examples/game/desktop_smoke.saga` reported:

```text
SDL2/x11 vendor=Mesa renderer=llvmpipe (LLVM 19.1.7, 256 bits) OpenGL=4.5 (Compatibility Profile) Mesa 25.0.7-2 GLSL=4.50
GAMEPAD_COUNT=0
SAGA_DESKTOP_GAME_SMOKE_OK
```

This validates a real OpenGL/GLSL execution path. The renderer in this environment is Mesa llvmpipe, which is software rendering. Therefore physical GPU acceleration is **not** claimed as hardware-validated.

## Validation gaps

- no physical GPU was exposed to the container;
- no physical gamepad was attached (`GAMEPAD_COUNT=0`);
- Windows/macOS Desktop Game builds and device tests were not executed;
- Linux ARM64/Windows portable binaries were cross-built/format-checked, not run on target hardware;
- macOS portable cross-build attempt did not complete within the execution limit and is not marked passed;
- no independent third-party security audit or independent conformance laboratory executed this release;
- no ISO/IEC or National Body has approved Saga;
- public ecosystem/adoption remains an external community/operations requirement.

## Test-run qualification

The Python 154-test suite exceeded a single 120-second execution window when run monolithically. It was re-run in exhaustive file groups: 90 tests + 4 subtests, 23 tests, 27 tests, and 14 tests, totaling all 154 collected tests, all passing.

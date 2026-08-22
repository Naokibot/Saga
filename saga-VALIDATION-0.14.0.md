# Saga 0.14.0 validation report

Validation date: 2026-08-08  
Host: Debian GNU/Linux 13 x86-64

| Validation | Result |
|---|---:|
| Python reference regression | 154/154 PASS |
| Python reference self-conformance | 13/13 PASS |
| Python Standard Core regression | 154/154 PASS |
| Saga Native Go unit tests | PASS |
| `go vet` | PASS |
| Go Race Detector | PASS after concurrency defect fix |
| Installer Go tests / vet | PASS |
| Saga Native self-conformance | 17/17 PASS |
| Python ↔ Native cross-implementation | 35/35 PASS |
| Native Hosted API inventory | 52/52 PASS after game API expansion |
| Parser fuzz | 100,000 cases; unexpected host exceptions 0 |
| Expression fuzz | 25,000 cases; unexpected host exceptions 0 |
| Internal automated security review | detected unresolved issues 0; not third-party certification |
| Strict JSON runtime + codegen regression | PASS |
| Registry signed publisher + trust-store regression | PASS |
| DB failed-persist rollback regression | PASS |
| HTTP redirect/proxy determinism regression | PASS |
| Task snapshot isolation + Race Detector | PASS |
| New enum/record/match/result/interpolation execution | PASS |
| Native standard `test` declarations | 2/2 sample PASS |
| Formatter idempotence / lint / check smoke | PASS |
| Native debugger smoke | PASS |
| Native LSP initialize/UTF-16 capability | PASS |
| Native direct WASM build + Node execution | PASS (`42`) |
| Native standalone deterministic rebuild | identical SHA-256 on repeated input |
| Empty-PATH standalone execution | PASS |
| Dependency-free mini game | PASS |
| Linux x86-64 CLI static-link check | `not a dynamic executable` |
| Linux x86-64 runtime static-link check | `not a dynamic executable` |
| Fixed-point self-host Stage2/Stage3 | PASS |
| Stage2/Stage3 SHA-256 | `300585094188ee3fa8a59571522c039acaecfea300536df65b7da06be9f4efc4` |
| Linux x86-64 final installer | install / self-host / conformance / build / empty-PATH run / uninstall PASS |
| Linux ARM64 output format | ELF 64-bit AArch64; real target hardware not available |
| Windows x86-64 output format | PE32+ x86-64; real Windows host not available |
| Windows ARM64 output format | PE32+ ARM64; real target hardware not available |

## Lightweight measurements

Final Linux x86-64 release build:

- Developer CLI: **7,757,959 bytes**
- Minimal application runtime: **6,959,239 bytes**
- Minimal standalone sample: **6,959,362 bytes**
- `saga --version` 60-run median startup: **~1.64 ms**
- standalone `print(42)` 60-run median startup: **~1.53 ms**

Measurements are specific to this container/host and are not portable performance guarantees.

## External validation gaps

No Windows/ARM64 target machine was available. No independent third-party audit organization executed this release. No independent conformance lab signed the results. No ISO/IEC committee has approved or published Saga. A public Internet package service and a large external library/community ecosystem require ongoing external operations and participation rather than source code alone.


## 2026-08-09 game-capability expansion revalidation

- Corrected the game guide's invalid three-argument `game.canvas` example.
- Added `game.fill_rect`, `game.line`, `game.circle`, `game.sprite`, and `game.point_in_rect`.
- Native game-focused regression tests: PASS.
- Complete Saga Native Go test suite: PASS.
- `go vet ./...`: PASS.
- Complete Go Race Detector suite: PASS.
- `examples/game/shape_arena.saga`: static check PASS and execution PASS.
- `examples/game/mini_dodge.saga`: execution PASS with scripted quit input.
- Scope remains terminal/text-cell 2D. Hardware-accelerated windows, bitmap textures, audio, gamepads, shaders, and raw non-blocking keyboard input are not claimed.

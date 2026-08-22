# Saga 0.19.0 validation report

Validation host: Linux x86-64. Release scope: C ABI Profile 2, Bare-Metal Profile 1, and SH-3 qualification review on top of Saga Language Edition 1.0 RC1 / Edition 2027 Preview.

## Regression and conformance

| Validation | Result |
|---|---:|
| Python reference regression | **155/155 PASS + 4 subtests** |
| Saga Native Go tests | **PASS** |
| `go vet ./...` | **PASS** |
| Go Race Detector | **PASS** |
| Native Standard Core | **17/17 PASS** |
| Edition 2027 Preview | **14/14 PASS** |
| Python ↔ Native Standard Core | **35/35 PASS** |
| Native game API checker/runtime/manifest | **92/92 PASS** |
| parser fuzz | **100,000 cases; 0 unexpected host exceptions** |
| expression fuzz | **25,000 cases; 0 unexpected host exceptions** |
| project-internal automated security review | **PASS; 0 findings** |

## C ABI Profile 2

Reference backend: Linux x86-64, `sagaffi`, libffi 3.x ABI.

Executed validation:

- real C shared library build and `dlopen`/symbol resolution: **PASS**;
- C aggregate `struct { int32_t x; double y; }` by-value argument: **PASS**;
- same aggregate by-value return: **PASS**;
- platform layout size/alignment (`size=16` on validation ABI): **PASS**;
- C pointer argument: **PASS**;
- Saga callable -> native C function pointer callback -> C -> Saga round trip: **PASS** (`32 -> 42 -> 43`);
- C-returned raw allocation -> explicit Saga `ffi.adopt` ownership transfer: **PASS**;
- owned raw pointer load/store -> explicit release: **PASS** (`99` round trip);
- borrowed-pointer free rejection: **PASS**;
- owner double-free rejection: **PASS**;
- derived pointer invalidated after owner release: **PASS**;
- callback code pointer invalidated with callback lifetime: **PASS by lifetime model and regression coverage**;
- nested aggregate storage/access primitives: **PASS**;
- fixed-size C array fields inside by-value structs: **PASS** (`int32_t v[3]` + nested struct integration);
- runtime defense-in-depth rejects FFI outside `unsafe`: **PASS**;
- `go vet -tags sagaffi`: **PASS** after uintptr/C-shim hardening;
- tagged FFI/bare-metal Race Detector tests: **PASS**.

Reference-profile limitation: the implemented Profile 2 backend is qualified on Linux x86-64. Unsupported targets fail closed. The normative C ABI Profile 2 semantics are backend-neutral, but this report does not claim Windows/macOS Profile 2 execution.

## Bare-Metal Profile 1

Targets validated:

- generic ARM Cortex-M0 (`armv6m-none-eabi`): **PASS build/vector test**;
- STM32F030K6 board profile: **PASS build/vector/memory-manifest test**.

The backend generated a freestanding ARM EABI5 ELF and raw BIN. Validation directly inspected the binary/vector data and ELF sections.

STM32F030K6 sample evidence:

- `.isr_vector` address: `0x08000000`;
- initial stack pointer in raw image: `0x20001000`;
- Reset vector: nonzero Thumb target in Flash;
- SysTick vector: nonzero Thumb target in Flash;
- board manifest Flash origin/size: `0x08000000`, 32768;
- board manifest RAM origin/size: `0x20000000`, 4096;
- `.data` copy symbols and `.bss` zero-initialization startup path: **PASS**;
- Saga-source GPIO/SysTick BSP example: **check/build PASS**;
- volatile MMIO, bit set/clear, IRQ/NVIC, critical-section, tick/yield/delay/reset/panic code generation: **PASS compile**.

The reference bare-metal machine-code backend invokes LLVM clang/lld and llvm-objcopy at build time. The resulting flashed firmware is freestanding. Physical STM32 execution was not available in this validation host and is **not** claimed.

## Self-hosting

SH-1 operational independence: **PASS (retained)**.

SH-2 Saga compiler-driver fixed point: **PASS**.

0.19 fixed-point evidence:

- Stage1 produced from `selfhost/sagac.saga`: PASS;
- Stage1 -> Stage2: PASS;
- Stage2 -> Stage3: PASS;
- Stage2 SHA-256 = Stage3 SHA-256: `2b54169eb48c50ed41e3fd4eb24bf10de4358b9aefa13fd591deb7dc34442d05`.

SH-3 all-source self-hosting: **NOT QUALIFIED**.

Strict source audit found 49 non-test Go files in the official Native kernel source set. Core blockers include the official lexer, parser, checker, runtime/builtins and loader. `tools/sh3_audit.py` intentionally exits non-zero while any official non-test Native kernel source remains non-Saga.

This release does not rename the current Go semantic kernel as a “minimal seed”; doing so would weaken the SH-3 definition and would be misleading.

## Deterministic release binary check

The official Native release build uses `-trimpath` and an empty Go build ID. The
same 0.19.0 Go source built from two different checkout paths produced
byte-identical Saga Native binaries with SHA-256
`e7dedaa3d7e43df8bc6824bf485ae5e3b4dfe6cd95d283a048b6f7a43f7135f3`.
Using that deterministic Native prefix, SH-2 Stage2 and Stage3 were byte-identical
with SHA-256
`2b54169eb48c50ed41e3fd4eb24bf10de4358b9aefa13fd591deb7dc34442d05`.

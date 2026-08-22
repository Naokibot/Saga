# Saga 0.19.0 feature audit

## Retained language/toolchain

Saga 1.0 RC1 / Edition 2027 Preview retain static typing/inference, exact numbers and floats, collections, functions/closures, modules/namespaces, OOP/interfaces/generics/constraints/associated types, exceptions, option/result, enum/record/match, resource/move safety, structured concurrency, diagnostics v2, LSP/debugger, package trust, deterministic builds, graphics/game profiles, SIR1, JIT and Embedded WASM.

## C ABI Profile 2

Added and validated on Linux x86-64:

- scalar ABI types;
- supported nested C struct layouts including fixed-size array fields;
- by-value struct arguments and return values;
- explicit owned and borrowed raw pointers;
- raw-pointer extent tracking;
- explicit adoption of a foreign allocation;
- derived-pointer parent lifetime;
- native callbacks invoking Saga callables;
- callback code-pointer lifetime;
- bounds checks where an extent is known;
- fail-closed unsupported host behavior;
- unsafe-block requirement in both checker and runtime.

## Bare-Metal Profile 1

Added:

- generic Cortex-M0 target;
- STM32F030K6 target/BSP memory profile;
- vector table and Reset handler;
- SysTick/core exception and IRQ0..IRQ31 binding;
- volatile MMIO 8/16/32;
- 32-bit MMIO set/clear;
- global IRQ and NVIC operations;
- critical-section state save/restore;
- tick/yield/delay minimal kernel substrate;
- system reset and panic;
- startup `.data` copy and `.bss` zeroing;
- ELF, BIN, linker script, generated C and JSON manifest;
- Saga-source STM32 GPIO/SysTick example.

## Self-hosting status

- SH-1: supported.
- SH-2: supported; Stage2/Stage3 fixed-point still passes.
- SH-3: **not supported yet**. Strict audit finds non-Saga official Native kernel sources. No all-source claim is made.

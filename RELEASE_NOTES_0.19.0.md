# Saga 0.19.0 release notes

Saga 0.19.0 focuses on low-level interoperability and embedded execution.

The optional C ABI Profile 2 extends Saga FFI with C-compatible aggregate layout, by-value structs, callback trampolines and explicit raw-pointer ownership/lifetime. The Linux x86-64 reference backend is implemented using libffi and fails closed on unsupported builds.

Bare-Metal Profile 1 adds freestanding Cortex-M0 firmware generation and an STM32F030K6 board profile with vector-table generation, MMIO, interrupts/NVIC, critical sections, a minimal tick/WFI kernel substrate, correct data/BSS startup, and ELF/BIN output.

The release also strengthens self-hosting terminology. SH-1 and SH-2 remain valid. SH-3 is still not claimed: a strict audit now fails while any official Native kernel source remains non-Saga. This is deliberate; 0.19 does not convert the existing full Go semantic kernel into a “minimal bootstrap seed” by definition alone.

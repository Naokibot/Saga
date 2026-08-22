# Saga Bare-Metal Profile 1

Saga 0.19.0 can emit freestanding ARM Cortex-M0 firmware in addition to the
portable no-import WebAssembly embedded target.

```sh
saga build examples/embedded/cortex_m0_blink.saga --target cortex-m0 --output build/fw
saga build examples/embedded/stm32f030k6_pa5.saga --target stm32f030k6 --output build/stm32
```

Each build emits `.elf`, `.bin`, generated `.c`, linker `.ld`, and a JSON target
manifest. The reference machine-code backend uses LLVM clang/lld and
llvm-objcopy; the flashed image itself is freestanding and has no hosted runtime.

The `embedded` module provides volatile MMIO, set/clear-bit operations, IRQ and
NVIC control, critical sections, a tick counter, WFI-based cooperative delay,
reset and panic primitives. Interrupt functions use `@interrupt("...")` and are
installed in the Cortex-M vector table.

Hosted execution of `embedded` intrinsics is rejected intentionally.

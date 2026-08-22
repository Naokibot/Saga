# Saga Bare-Metal Profile 1 — 2027 Preview

Status: normative preview for Saga implementation 0.19.0.

## 1. Purpose

Bare-Metal Profile 1 defines a freestanding Saga environment for microcontrollers
without a hosted operating system. It is separate from Standard Core and from the
no-import Portable Embedded WebAssembly target.

## 2. Initial targets

The reference backend provides:

- generic ARM Cortex-M0 (`armv6m-none-eabi`);
- STM32F030K6 board/memory profile.

A target profile specifies CPU, instruction-set mode, Flash origin/extent, RAM
origin/extent, stack-top rule and interrupt-vector format.

## 3. Program model

A firmware program supplies `fn reset() -> unit`. Bare-metal compilation emits a
startup `Reset_Handler`, a vector table and a default fault/interrupt handler.
Functions annotated `@interrupt("SysTick")`, `@interrupt("NMI")`,
`@interrupt("HardFault")`, `@interrupt("SVC")`, `@interrupt("PendSV")` or
`@interrupt("IRQ0".."IRQ31")` are placed into the corresponding vector entry.
Duplicate vector ownership is a build error.

## 4. MMIO and interrupt facilities

The `embedded` module provides volatile 8/16/32-bit MMIO reads/writes,
32-bit set/clear bit operations, global interrupt enable/disable, memory barrier,
wait-for-interrupt, NVIC enable/disable/priority functions, critical-section state
save/restore, tick accounting, cooperative yield/delay, system reset and panic.

Hosted execution of these intrinsics shall fail closed. They are meaningful only
under a declared bare-metal target.

## 5. Minimal kernel contract

The profile contains a minimal non-preemptive kernel substrate:

- interrupt-safe critical sections;
- monotonic 32-bit tick counter advanced by explicit `embedded.os_tick()` from a
  timer/SysTick ISR;
- WFI-based cooperative yield and tick delay;
- NVIC control;
- reset and fail-stop panic paths.

This is intentionally smaller than a POSIX/RTOS environment. Dynamic processes,
virtual memory and ambient filesystem/network services are not implied.

## 6. Drivers and BSP

Board-specific drivers are built on volatile MMIO plus target memory/BSP metadata.
The STM32F030K6 example configures GPIO and SysTick entirely from Saga source and
is linked with an MCU-specific Flash/RAM layout. Hardware register constants are
part of the BSP/application source rather than Standard Core.

## 7. Build artifacts and qualification

A successful reference build emits:

- freestanding ARM ELF;
- raw binary image;
- generated C translation unit;
- linker script;
- machine-readable manifest containing board/memory/vector metadata.

Saga Native 0.19.0 uses LLVM clang/lld and llvm-objcopy as the reference
machine-code backend for these targets. This is a build-tool dependency of the
bare-metal target, not a runtime dependency of the flashed firmware.

Physical-device execution is a separate qualification gate. ELF/BIN generation
and vector-layout inspection shall not be relabeled as physical-board validation.

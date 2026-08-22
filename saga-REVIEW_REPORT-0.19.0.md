# Saga 0.19.0 source review

## Scope

Reviewed the 0.18.0 codebase and 0.19 low-level changes across FFI, pointer ownership, callbacks, aggregate ABI layout, bare-metal code generation, startup/linker behavior, BSP metadata and self-hosting claims.

## Problems found and repaired

### 1. FFI Profile 2 used Go uintptr -> unsafe.Pointer conversions throughout the bridge

The first implementation worked in tests but `go vet -tags sagaffi` reported many possible unsafe-pointer misuse locations. Raw-address access/copy/load/store and callback handle conversion were moved behind C `uintptr_t` shims. Tagged `go vet` now passes.

### 2. Derived raw pointers could survive owner release

A borrowed pointer created from an owned allocation tracked its own `Freed` bit but originally did not invalidate itself when its parent owner was released. Pointer validity now follows the parent ownership chain. Use-after-free is rejected.

### 3. Callback code pointers did not carry callback lifetime

A borrowed native function pointer could retain the old code address after `callback_close`. It now references the callback lifetime state and is rejected once the callback is closed.

### 4. Struct return allocation was copied twice

The libffi return bridge copied a transient ABI aggregate into a Saga-owned allocation, then the common marshaller allocated a second buffer and copied it again, leaving the first allocation unreleased. The common marshaller now adopts the already-owned copy exactly once.

### 5. FFI Profile 2 dispatch preceded runtime unsafe enforcement

Static checking already rejected normal source use outside `unsafe`, but the runtime dispatcher called Profile 2 before the defense-in-depth unsafe gate. Dispatch order is corrected and a direct runtime regression test verifies `SAGA-R188`.

### 6. Unsupported FFI builds could enter Profile 2 common code

Profile 2 common operations are now guarded by platform/backend availability and fail closed on unsupported builds rather than returning misleading zero/null behavior.

### 7. Initial bare-metal generated C contained escaped newline text

The first emitter revision wrote `\\n` text in a generated header path instead of a real newline. It was detected by actually invoking Clang and corrected.

### 8. Initial linker MEMORY syntax was invalid for lld

The first linker script formatting failed at real ARM link time. The syntax was corrected and both generic Cortex-M0 and STM32F030K6 builds are regression-tested.

### 9. Board manifest stayed on generic Cortex-M0 values

The board-specific ELF used STM32 placement correctly, but the first JSON manifest was hard-coded to generic Flash/RAM values. Manifest generation now derives all values from the selected board profile.

### 10. Bare-metal startup omitted `.data` copy / `.bss` clear

This was a functional firmware defect: static state such as the tick counter could start with undefined SRAM contents. Reset startup now copies initialized data from Flash, zeros BSS, issues a barrier and only then enters Saga `reset`.

## Self-host review finding

The requested SH-3 all-source condition is **not repaired in 0.19.0**. The official Native implementation still contains non-test Go semantic-kernel source. The release now has a strict machine-readable audit and cannot claim SH-3 while this remains true.

This is not treated as a documentation-only issue: replacing approximately the semantic kernel with Saga source and proving it runs without invoking those Go semantics is a separate compiler/runtime rewrite, not a flag or packaging change.

# Saga Embedded Portable Profile 2027 — Preview

A conforming `embedded-wasm` artifact:

- is a WebAssembly module with no import section;
- uses the declared scalar subset (`int`, `bool`, `unit`, control flow and supported pure functions);
- exports only explicitly `public` Saga functions;
- rejects hosted modules, output, async/FFI and unsupported heap/object semantics;
- has deterministic code generation for identical canonical source;
- does not imply any particular RTOS, MCU ABI, linker script, interrupt model or board support package.

This profile is the portable embedded foundation. Bare-metal/native MCU profiles must separately specify integer widths, endianness, alignment, interrupt/volatile semantics, atomics, memory-mapped I/O and ABI.

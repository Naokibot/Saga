# Saga 0.38 general-purpose / industrial readiness

Saga 0.38 adds incremental nursery collection to the existing incremental major collector. Both mark and sweep can now be advanced through object-budget polling in low-pause mode. This reduces whole-cycle stop-the-world work but does not make Saga a hard-real-time runtime: a single object scan, allocator/OS behavior, scheduler latency, and synchronous compatibility APIs remain unbounded by a certified time deadline.

Qualification layers are separated:

- **executed on this Linux host:** compiler/runtime regression, C native runtime, Go implementation tests, PTY/termios Modbus RTU path, loopback HTTP registry, virtual CAN socket transport;
- **simulated/static:** Windows amd64 PE and macOS amd64 Mach-O target build/test-binary inspection;
- **digital/HIL simulation:** PLC/servo/motor/encoder/CAN plant and injected field faults;
- **external-only:** physical Windows/macOS execution, physical industrial HIL, public-Internet operation and real adoption, SIL/PL certification.

A PASS in a simulated layer is never promoted to a physical or certification PASS.

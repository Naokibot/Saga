# Saga 0.38.0 validation

## Executed regression

- Python compileall: PASS.
- Core/general/module/machine: 129 tests PASS.
- Runtime/open-world/GC: 30 tests PASS, including the new incremental nursery mutation/promotion/remembered-edge test.
- Native codegen/object/human-value: 22 tests PASS.
- Security/ecosystem: 27 tests PASS.
- Go reference implementation: all packages PASS; `go vet` PASS.

## Simulated external qualification

### Industrial HIL
`tools/industrial_hil_simulation_038.py`:
- 72 simulated hours;
- 2,592,000 control cycles at 100 ms;
- 2,592,000 virtual CAN command frames and feedback frames;
- 4,322 Modbus RTU transactions through Linux PTY/termios and Saga `UARTDevice`/`ModbusRTUMaster`;
- E-stop, CAN command loss, CRC corruption and response timeout detected as required;
- unexpected failures: 0;
- PASS;
- physical hardware: UNEXECUTED.

### Long deterministic plant endurance
`tools/industrial_endurance_simulation_038.py`:
- 168 simulated hours;
- 6,048,000 cycles;
- 10,082 Modbus RTU transactions;
- following error, soft limit, E-stop, CRC and timeout fault checks PASS;
- unexpected failures: 0.

### Windows/macOS
`tools/desktop_virtual_qualification_038.py`:
- windows/amd64 CLI, standalone runtime and target test binary cross-build PASS; PE32+ parsed PASS;
- darwin/amd64 CLI, standalone runtime and target test binary cross-build PASS; Mach-O 64-bit parsed PASS;
- Go build info readable PASS;
- physical execution: UNEXECUTED for both platforms.

### Registry network/load
`tools/public_registry_load_simulation_038.py`:
- real Saga HTTP registry code over loopback;
- 48 signed package versions published through the immutable publish endpoint;
- 256 virtual users;
- 2,048 concurrent search/download requests;
- 0 failures;
- public Internet endpoint: UNAVAILABLE;
- real human users: UNAVAILABLE.

### Functional-safety pre-certification
`tools/functional_safety_prequalification_038.py`:
- 100,000 deterministic seeded modeled fault cases;
- modeled categories: E-stop, soft limit, following error, communication loss, encoder stuck, watchdog;
- 100,000 detected, 100,000 safe-zero outcomes, 100,000 explicit resets;
- internal prequalification PASS;
- certification status: NOT_CERTIFIED;
- SIL target: NOT_ASSIGNED; PL target: NOT_ASSIGNED.

## Important interpretation

Simulation PASS is not physical PASS. Internal safety prequalification is not SIL/PL certification. The runtime's object budget is not a certified microsecond deadline. These boundaries are part of the 0.38 release evidence rather than informal caveats.

## Source-bound conformance set

A source manifest is generated only after implementation/review artifacts are complete. The final distribution reruns runtime 0.38 qualification, Python↔Go differential, module conformance, Native Runtime, Native Codegen, machine qualification, security audit and specification lint against that manifest. The machine-readable validation directory contains the exact reports.

# Saga Advanced Motion — Virtual HIL Qualification 0.48

This qualification responds to the remaining physical-control gaps after Saga 0.47. No physical motor, inverter, encoder, CAN-FD controller, EtherCAT ESC, PTP-capable NIC, safety relay or STO-capable drive is attached to this execution environment. Therefore **no physical qualification or functional-safety certification is claimed**.

The package instead runs a reproducible virtual-HIL campaign using the real Saga 0.47 control classes and Linux kernel facilities where available.

## Campaign

1. **High-bandwidth FOC:** 20 kHz Saga `FOCCurrentLoop` against a d/q PMSM + inverter-delay/dead-time/bus-sag model, including 100 parameter-variation cases.
2. **Absolute encoder:** 17-bit modulo encoder at 3000 rpm, 10 kHz sampling, wrap, count noise, timestamp jitter and dropped-sample injection.
3. **CAN-FD BRS:** Saga SocketCAN ABI packing with BRS flag plus a deterministic nominal/data-phase wire-time model. The sandbox cannot create a `vcan` device because network-administration capability is denied.
4. **EtherCAT Distributed Clocks:** Saga EtherCAT datagrams for DC registers 0x0900, 0x0910 and 0x092C plus a four-slave drift/propagation/servo simulation. This models ESC clock behavior; it is not ETG conformance testing.
5. **Timestamping:** synthetic `SCM_TIMESTAMPING` hardware provenance tests, actual Linux loopback software RX timestamps, and an 8 ns virtual-PHC model. No `/dev/ptp*` device is present, so physical NIC timestamp precision is unexecuted.
6. **MCU zero-allocation:** a restricted `@control_tick` Saga function is compiled by the qualification backend to freestanding C and then to an ARM Cortex-M4F object. The object is scanned for allocator symbols and subroutine calls. The emitted function is acyclic, allowing a finite static instruction bound. A deliberately pessimistic 16-cycles-per-instruction virtual timing envelope is reported separately from formal WCET.
7. **STO / E-stop:** dual-channel external-STO model with discrepancy and welded-channel fault injection, combined with Saga `SafetyLatch`. It tests logic/restart behavior only and is not SIL/PL certification.

## Critical boundaries

- The Python/Go hosted runtime is not hard real-time.
- The Cortex-M4F proof is for **one restricted generated control kernel**, not every Saga program or the general native backend.
- The reported virtual timing envelope is **not formal target WCET**. Formal WCET requires the actual MCU, memory system, compiler/linker configuration, interrupt model and measurement/static-analysis method.
- A software safety latch is not STO. Physical STO must remain implemented by a qualified drive/safety circuit independent of Saga software.

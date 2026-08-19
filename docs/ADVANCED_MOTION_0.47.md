# Saga 0.47 Advanced Motion Control

Saga 0.47 applies the language's core design rule to motion control: **control mathematics stays easy to compose; authority to affect physical equipment stays explicit.**

The common Python/Go surface now includes FOC current control, integrated incremental/absolute encoder tracking, fixed-size RLS identification, bounded MPC, disturbance observation, Stribeck friction compensation, electronic gearing/multi-axis synchronization, EtherCAT framing/raw transport, CAN-FD metadata and timestamp provenance, and the `@control_tick` MCU/RTOS source profile.

FOC/MPC/observer/filter/state objects are ordinary managed Saga values. Raw CAN/EtherCAT/device handles remain capability-gated resources and participate in `using`/`move` lifetime rules. This keeps simulation and offline control design free of hardware ceremony while making the transition to real I/O visible in source.

`@control_tick` rejects dynamic list construction, closures/nested functions, async/task-pool work, resource lifetime changes, exception control flow, unbounded `while`, non-literal loop bounds, and known blocking I/O. It is a source-level allocation-free profile; a target MCU/RTOS backend must still prove allocator-free lowering and WCET on the actual target.

Hardware timestamp APIs report provenance (`hardware`, `software`, `host`, or `none`) instead of silently claiming hardware timing when the OS/NIC falls back.

Physical motor/inverter/encoder/CAN-FD/EtherCAT operation and functional-safety qualification remain separate hardware-lab work.

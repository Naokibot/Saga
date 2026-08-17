# Saga 0.43.0 control review

Review fixes:
1. Cached the topology-dependent multirotor allocation projection instead of solving a 4x4 system every update.
2. Added explicit per-actuator target/range/deadband/slew and batch operations.
3. Added independent XYZ trajectory limits and lower-level MAVLink attitude/batch/timeout APIs.
4. Added cyclic jitter/overrun telemetry and an optional compact state-space hot path.
5. Reworked GStreamer detection so installed shared libraries/plugins can execute without CLI utilities.
6. Separated `webrtcbin` plugin loading from full ICE readiness; the current environment lacks the GStreamer nice source/sink plugin.
7. Kept automatic drone RTL/LAND/DISARM out of the standard module.

Hardware review: no physical video, USB serial/CAN, drone, drive, PLC, or fieldbus adapters are exposed to the execution container. Physical qualification is therefore not claimed. The 0.43 HIL path uses real OS sockets plus a six-axis cyclic plant and keeps HIL status separate from physical hardware status.

Hosted Saga remains soft real-time and does not replace external E-stop/STO/interlocks or deterministic RTOS/driver layers.
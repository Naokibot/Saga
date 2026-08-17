# Saga 0.43.0 — Fine-Grained Control + Lightweight Runtime Paths

## Added
- Per-actuator explicit target/range/deadband/slew control and batch commands.
- Hosted cyclic clock with jitter/overrun telemetry.
- Per-axis XYZ velocity/acceleration/jerk limits for drone trajectories.
- MAVLink attitude setpoints, position batches, and runtime timeout control.
- Compact state-space hot path for larger hosted controllers.
- GStreamer C-API fallback when CLI tools are absent.
- Real GStreamer runtime probe and VP8/RTP test sender.
- `tools/real_sitl_e2e_043.py` for real PX4/ArduPilot MAVLink endpoints.

## Optimized
The multirotor allocator now caches its topology-dependent projection matrix. In the reviewed environment the Quad-X allocation benchmark improved from roughly 30–32 us/call to about 5 us/call, around 6x faster.

## Qualification boundary
Real GStreamer VP8/RTP and `webrtcbin` plugin loading were executed. Full GStreamer ICE, official PX4/ArduPilot SITL, pretrained OpenCV Zoo YOLOX, and physical camera/drone/servo/PLC/fieldbus remain unexecuted in this container because required plugins, external binary download access, or hardware are absent. HIL/loopback results are labeled separately.

Automatic drone RTL/LAND/DISARM policy remains intentionally absent.
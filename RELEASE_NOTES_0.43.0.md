# Saga 0.43.0 — Fine-Grained Control + Lightweight Runtime Paths

## Added

- Fine-grained actuator bank with explicit per-channel targets, limits, deadband and slew rate.
- Hosted cyclic clock with jitter and overrun telemetry.
- Per-axis XYZ velocity/acceleration/jerk limits for 3D drone trajectories.
- MAVLink offboard attitude setpoints, position-setpoint batches and runtime receive timeout changes.
- Compact state-space hot path for larger hosted controllers.
- GStreamer C-API fallback when `gst-launch-1.0` is unavailable.
- Real GStreamer runtime probe and synthetic VP8/RTP sender.
- `tools/real_sitl_e2e_043.py` for direct PX4/ArduPilot endpoints.
- `tools/release_043_qualification.py` separating physical, official-runtime and HIL evidence.

## Optimized

- Control allocation now caches the topology-dependent projection matrix. In the qualification environment the cyclic allocation path improved from roughly 30–32 microseconds to about 5 microseconds per call for the Quad-X benchmark (around 6x), without changing the demand/result semantics.
- The 8-state compact state-space path showed a smaller but measurable improvement in the hosted Python reference implementation.

## Evidence boundary

The GStreamer VP8/RTP path and `webrtcbin` plugin load were actually executed. Full GStreamer WebRTC ICE was not executed because `nicesrc/nicesink` are absent. Official PX4/ArduPilot SITL, pretrained OpenCV Zoo YOLOX and physical devices could not be executed in this container because the required external artifacts/hardware are unavailable. Those cases remain `UNEXECUTED`; loopback/HIL evidence is labeled separately.

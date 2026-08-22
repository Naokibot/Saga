# Saga 0.43.0 review report

## Findings addressed

1. **Allocator cyclic cost:** 0.42 recomputed and solved a four-axis Gram system on every allocation. 0.43 caches the projection until the actuator topology changes.
2. **Fine actuator control:** added explicit per-channel targets, range/deadband/slew and batch operations.
3. **Trajectory granularity:** added independent XYZ speed/acceleration/jerk limits.
4. **Offboard granularity:** added attitude target, batch position targets and timeout adjustment.
5. **Hosted loop observability:** added a cyclic clock with jitter/overrun statistics.
6. **GStreamer false-negative:** 0.42 considered GStreamer absent when CLI tools were missing even though the libraries/plugins were installed. 0.43 can execute through the C ABI directly.
7. **WebRTC evidence clarity:** `webrtcbin` presence is no longer conflated with full ICE readiness; missing `nicesrc/nicesink` is reported separately.

## Runtime/hardware review

- Real GStreamer VP8/RTP pipeline: executed.
- Real `webrtcbin` plugin: loaded.
- Full GStreamer WebRTC ICE peer: unexecuted (GStreamer libnice plugin absent).
- Official PX4 SITL process: unexecuted (binary/image absent and outbound binary download blocked).
- Official ArduPilot SITL process: unexecuted for the same environment reason.
- Official pretrained OpenCV Zoo YOLOX: unexecuted; backend remains compatible with a locally supplied asset.
- Physical camera/drone/servo/PLC/fieldbus: no devices are attached to the execution container.
- Modbus TCP, CANopen/CiA-402 framing and six-axis servo/PLC cyclic behavior: HIL/OS loopback executed.

## Safety/timing boundary

No automatic drone RTL/LAND/DISARM policy was added. Hosted Saga remains soft real-time. Physical STO/E-stop/interlocks and certified/deterministic low-level loops remain outside this release qualification.

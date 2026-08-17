# Saga 0.40 Drone Control Profile

## Intended practical use

The production-oriented path for Saga 0.40 is a companion/offboard process connected to an established autopilot such as PX4 or ArduPilot over MAVLink. Saga can compute high-level position, velocity, attitude, body-rate, mission or perception-derived setpoints, serialize standard MAVLink messages, and send them through the existing guarded UDP or UART APIs.

The language runtime does not automatically choose RTL, LAND or DISARM. Battery/link/estimator/position/geofence state can be observed by the application, but mode policy belongs to application code or the external autopilot.

## Included control primitives

- quaternion attitude controller;
- angular-rate PID controller;
- local position/velocity controller;
- Quad-X mixer/reference allocation;
- mission, geofence, explicit RTL and landing helpers;
- MAVLink 2 framing/signing, common offboard messages, telemetry decoder and streaming parser;
- DroneCAN single- and multi-frame transport helpers;
- DShot 16-bit command-word encoding and PWM ESC duty conversion.

## What is not claimed

Saga 0.40 is not a replacement for a flight-controller firmware stack. The hosted runtime is soft real-time. The built-in estimator is a deterministic complementary estimator rather than a production EKF. DShot support creates the protocol word but does not generate DMA/timer waveforms. There is no physical flight qualification for an IMU/GNSS/barometer/ESC/motor/propeller airframe in this environment.

## Recommended architecture

```text
Camera / AI / mission / user logic
             |
          Saga 0.40
   setpoint + MAVLink stream
             |
      PX4 / ArduPilot FC
 estimator + hard inner loops
             |
        ESC / motors
```

For PX4 Offboard, the application must stream supported setpoints continuously before and during Offboard mode. For ArduPilot Copter Guided, use the command/message subset supported by that vehicle and mode. Type masks and coordinate-frame semantics are autopilot-specific even when the packet is valid MAVLink.

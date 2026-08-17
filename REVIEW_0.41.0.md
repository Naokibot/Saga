# Saga 0.41.0 review

## Assessment

Saga 0.41 can support advanced drone **companion/offboard** work: smooth trajectory generation, redundant-airframe allocation, camera/video recognition, target tracking and coordinate projection, plus robust MAVLink/DroneCAN communications. It is not qualified as a sole inner-loop flight controller.

## Review fixes

1. Added the missing camera-frame -> DNN/region recognition -> NMS -> tracking -> ray-geometry pipeline.
2. Replaced fixed-only allocation as the advanced path with generic 4/6/8-rotor allocation and explicit failed-rotor handling.
3. Fixed a review bug where a disabled rotor inherited the configured idle command; disabled output is now exactly zero.
4. Added MAVLink sequence-loss observation, redundant-link de-duplication and token-bucket traffic shaping.
5. Added MAVLink TIMESYNC so camera/companion timing can use the standard protocol path.
6. Added real generated-ONNX forward execution through OpenCV rather than claiming DNN capability from API presence alone.
7. Kept the independent Go implementation honest: it supplies portable geometry/tracking but camera/DNN calls fail closed without an OpenCV host adapter.

Automatic RTL/LAND/DISARM policy remains outside the standard module, as requested. Source tree SHA-256: `af73721b17e2f18b5a60b7c7e88ac925f7c5329416bfe30d87c768ac4e0befe9`.
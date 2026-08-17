# Saga 0.44.0 control review

Review focus: make 4 kHz hosted control meaningful rather than merely accepting `4000` as an input value.

Key changes:
1. Replaced Linux sub-millisecond `time.sleep()` scheduling with periodic kernel `timerfd` expirations.
2. Added `cycle_wait_due()` so missed host slots are visible and logical state updates can catch up deterministically.
3. Fixed timerfd accounting so authoritative kernel expiration counts are never double-counted by user-space lateness logic.
4. Added a portable absolute-deadline sleep/spin fallback.
5. Added the same frequency/due-count model to the independent Go runtime and checker.
6. Preserved the existing cached allocator, compact state-space and actuator-conditioning hot paths.
7. Kept all automatic arm/RTL/LAND/DISARM and machinery stop policy out of the timing primitive.

The reviewed source tree SHA-256 is `cc58a362d0118f1b489f339cb90920e2423cfbf76a5ea3ad6dd44d05c5b07eb0`.

The hosted runtime can execute 4,000 logical updates per second in the qualification environment, but it is not a hard-real-time certification. Physical 250 us edge timing still requires a qualified OS/driver/hardware backend.
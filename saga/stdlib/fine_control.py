from __future__ import annotations

import json
import math
import os
import struct
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable

from .machine_control import MachineControlError

D0 = Decimal(0)


def _d(name: str, value: object) -> Decimal:
    out = value if isinstance(value, Decimal) else Decimal(str(value))
    if not out.is_finite():
        raise MachineControlError(f"{name} must be finite")
    return out


@dataclass(slots=True)
class FineActuatorBank:
    """Explicit per-actuator setpoint conditioning for cyclic machine/drone loops.

    This class never changes mode or performs an automatic stop. It only applies the
    limits requested by the Saga program: min/max, optional deadband, and slew rate.
    The caller owns policy and may explicitly call ``zero`` when desired.
    """

    count: int
    minimum: Decimal
    maximum: Decimal
    neutral: Decimal
    max_slew_per_s: Decimal
    deadband: Decimal = D0
    target: list[Decimal] = field(init=False)
    output: list[Decimal] = field(init=False)

    def __post_init__(self) -> None:
        if self.count < 1 or self.count > 1024:
            raise MachineControlError("actuator count must be 1..1024")
        self.minimum = _d("minimum", self.minimum)
        self.maximum = _d("maximum", self.maximum)
        self.neutral = _d("neutral", self.neutral)
        self.max_slew_per_s = _d("max_slew_per_s", self.max_slew_per_s)
        self.deadband = _d("deadband", self.deadband)
        if self.maximum <= self.minimum:
            raise MachineControlError("maximum must be > minimum")
        if not self.minimum <= self.neutral <= self.maximum:
            raise MachineControlError("neutral must be within min/max")
        if self.max_slew_per_s <= 0 or self.deadband < 0:
            raise MachineControlError("slew must be > 0 and deadband >= 0")
        self.target = [self.neutral] * self.count
        self.output = [self.neutral] * self.count

    def _limit(self, value: object) -> Decimal:
        v = _d("actuator command", value)
        if abs(v - self.neutral) <= self.deadband:
            v = self.neutral
        return min(self.maximum, max(self.minimum, v))

    def set(self, index: int, value: object) -> None:
        if not 0 <= index < self.count:
            raise MachineControlError("actuator index outside bank")
        self.target[index] = self._limit(value)

    def set_all(self, values: Iterable[object]) -> None:
        vals = list(values)
        if len(vals) != self.count:
            raise MachineControlError("actuator command count mismatch")
        self.target = [self._limit(v) for v in vals]

    def zero(self) -> None:
        self.target = [self.neutral] * self.count

    def step(self, dt_seconds: object) -> list[Decimal]:
        dt = _d("dt_seconds", dt_seconds)
        if dt <= 0 or dt > Decimal("10"):
            raise MachineControlError("dt_seconds must be in (0,10]")
        max_delta = self.max_slew_per_s * dt
        for i, wanted in enumerate(self.target):
            delta = wanted - self.output[i]
            if delta > max_delta:
                delta = max_delta
            elif delta < -max_delta:
                delta = -max_delta
            self.output[i] += delta
        return list(self.output)

    def state_json(self) -> str:
        return json.dumps({
            "target": [str(v) for v in self.target],
            "output": [str(v) for v in self.output],
        }, separators=(",", ":"))


@dataclass(slots=True)
class CyclicClock:
    """Hosted cyclic scheduler with a 4 kHz-capable Linux timer backend.

    Linux uses ``timerfd`` when available. The kernel counts every periodic
    expiration, so a temporarily pre-empted Saga process can observe how many
    logical control ticks became due instead of silently losing them. Other
    platforms use an absolute-deadline sleep/spin fallback. This is still
    hosted soft real-time: it does not promise that physical I/O happened at
    every 250 us boundary.
    """

    frequency_hz: int
    period_ns: int = field(init=False)
    period_s: float = field(init=False)
    next_deadline_ns: int = field(init=False)
    cycles: int = 0
    wait_calls: int = 0
    overruns: int = 0
    max_late_us: float = 0.0
    sum_abs_jitter_us: float = 0.0
    last_late_us: float = 0.0
    last_due: int = 0
    max_due: int = 0
    backend: str = field(init=False, default="hybrid-sleep-spin")
    _timer_fd: int = field(init=False, default=-1, repr=False)
    _spin_guard_ns: int = field(init=False, default=0, repr=False)

    def __post_init__(self) -> None:
        if self.frequency_hz < 1 or self.frequency_hz > 100_000:
            raise MachineControlError("cycle frequency must be 1..100000 Hz")
        self.period_ns = max(1, round(1_000_000_000 / self.frequency_hz))
        self.period_s = self.period_ns / 1_000_000_000.0
        self._spin_guard_ns = min(80_000, max(2_000, self.period_ns // 3))
        self.next_deadline_ns = time.monotonic_ns() + self.period_ns
        if all(hasattr(os, name) for name in ("timerfd_create", "timerfd_settime_ns")):
            try:
                self._timer_fd = os.timerfd_create(time.CLOCK_MONOTONIC, flags=getattr(os, "TFD_CLOEXEC", 0))
                os.timerfd_settime_ns(self._timer_fd, initial=self.period_ns, interval=self.period_ns)
                self.backend = "linux-timerfd"
            except OSError:
                self._timer_fd = -1

    def _record(self, due: int, actual_ns: int) -> int:
        due = max(1, int(due))
        expected_latest_ns = self.next_deadline_ns + (due - 1) * self.period_ns
        late_ns = actual_ns - expected_latest_ns
        late_us = late_ns / 1_000.0
        self.last_late_us = late_us
        self.last_due = due
        self.max_due = max(self.max_due, due)
        self.wait_calls += 1
        self.cycles += due
        if due > 1:
            self.overruns += due - 1
        if self._timer_fd < 0 and late_ns > self.period_ns:
            # The portable fallback has no kernel expiration counter, so derive
            # missed periods from the absolute deadline. timerfd counts are
            # authoritative and must never be double-counted here.
            extra = late_ns // self.period_ns
            due += extra
            self.cycles += extra
            self.overruns += extra
            self.last_due += extra
            self.max_due = max(self.max_due, self.last_due)
            expected_latest_ns += extra * self.period_ns
            late_us = (actual_ns - expected_latest_ns) / 1_000.0
            self.last_late_us = late_us
        self.max_late_us = max(self.max_late_us, max(0.0, self.last_late_us))
        self.sum_abs_jitter_us += abs(self.last_late_us)
        self.next_deadline_ns += self.last_due * self.period_ns
        return self.last_due

    def wait_due(self) -> int:
        """Block until the next tick and return the number of due control ticks.

        At 4 kHz a return value of 1 means the process kept up with the 250 us
        cadence. A value greater than 1 means the kernel observed missed host
        scheduling slots; callers may run deterministic catch-up state updates,
        while physical output should still be treated as late.
        """
        if self._timer_fd >= 0:
            raw = os.read(self._timer_fd, 8)
            if len(raw) != 8:
                raise MachineControlError("timerfd returned an invalid expiration record")
            due = struct.unpack("=Q", raw)[0]
            return self._record(due, time.monotonic_ns())

        while True:
            now = time.monotonic_ns()
            remaining = self.next_deadline_ns - now
            if remaining <= 0:
                break
            if remaining > self._spin_guard_ns:
                time.sleep((remaining - self._spin_guard_ns) / 1_000_000_000.0)
            # Final short interval intentionally spins to avoid sub-ms sleep
            # quantisation on platforms without timerfd.
        actual = time.monotonic_ns()
        due = 1 + max(0, (actual - self.next_deadline_ns) // self.period_ns)
        return self._record(due, actual)

    def wait(self) -> Decimal:
        self.wait_due()
        return Decimal(str(max(0.0, self.last_late_us)))

    def reset(self) -> None:
        self.cycles = self.wait_calls = self.overruns = 0
        self.max_late_us = self.sum_abs_jitter_us = self.last_late_us = 0.0
        self.last_due = self.max_due = 0
        self.next_deadline_ns = time.monotonic_ns() + self.period_ns
        if self._timer_fd >= 0:
            os.timerfd_settime_ns(self._timer_fd, initial=self.period_ns, interval=self.period_ns)

    def close(self) -> None:
        if self._timer_fd >= 0:
            fd, self._timer_fd = self._timer_fd, -1
            try:
                os.close(fd)
            except OSError:
                pass

    def stats_json(self) -> str:
        avg = self.sum_abs_jitter_us / self.wait_calls if self.wait_calls else 0.0
        return json.dumps({
            "frequency_hz": self.frequency_hz,
            "period_us": self.period_ns / 1_000.0,
            "cycles": self.cycles,
            "wait_calls": self.wait_calls,
            "overruns": self.overruns,
            "last_due": self.last_due,
            "max_due": self.max_due,
            "max_late_us": self.max_late_us,
            "mean_abs_jitter_us": avg,
            "backend": self.backend,
            "timing_class": "hosted-soft-realtime",
        }, separators=(",", ":"))

    def __del__(self) -> None:
        self.close()


@dataclass(slots=True)
class FastStateSpace:
    """Allocation-light float hot path for high-rate hosted supervisory control.

    The public Saga API still accepts/returns exact Decimal values. Matrices are
    converted once at construction and reused as compact Python float tuples.
    """

    A: tuple[tuple[float, ...], ...]
    B: tuple[tuple[float, ...], ...]
    K: tuple[tuple[float, ...], ...]
    N: tuple[tuple[float, ...], ...]
    state: list[float]
    minimum: tuple[float, ...]
    maximum: tuple[float, ...]

    @classmethod
    def create(cls, A, B, K, N, initial_state, minimum, maximum) -> "FastStateSpace":
        def mat(name, value):
            rows = tuple(tuple(float(_d(name, x)) for x in row) for row in value)
            if not rows or not rows[0] or any(len(r) != len(rows[0]) for r in rows):
                raise MachineControlError(f"{name} must be a non-empty rectangular matrix")
            return rows
        aa, bb, kk, nn = mat("A", A), mat("B", B), mat("K", K), mat("N", N)
        n = len(aa); m = len(bb[0])
        if len(aa[0]) != n or len(bb) != n or len(kk) != m or any(len(r) != n for r in kk) or len(nn) != m:
            raise MachineControlError("fast state-space dimensions do not align")
        state = [float(_d("state", x)) for x in initial_state]
        lo = tuple(float(_d("minimum", x)) for x in minimum)
        hi = tuple(float(_d("maximum", x)) for x in maximum)
        if len(state) != n or len(lo) != m or len(hi) != m or any(lo[i] > hi[i] for i in range(m)):
            raise MachineControlError("fast state-space vector dimensions do not align")
        return cls(aa, bb, kk, nn, state, lo, hi)

    @staticmethod
    def _mv(a: tuple[tuple[float, ...], ...], x: list[float] | tuple[float, ...]) -> list[float]:
        return [sum(row[j] * x[j] for j in range(len(row))) for row in a]

    def command(self, reference: Iterable[object], measured_state: Iterable[object] | None = None) -> list[Decimal]:
        x = self.state if measured_state is None else [float(_d("measured_state", v)) for v in measured_state]
        r = [float(_d("reference", v)) for v in reference]
        if len(x) != len(self.state) or len(r) != len(self.N[0]):
            raise MachineControlError("fast state-space command dimensions do not align")
        ff, fb = self._mv(self.N, r), self._mv(self.K, x)
        return [Decimal(str(min(self.maximum[i], max(self.minimum[i], ff[i] - fb[i])))) for i in range(len(ff))]

    def predict(self, command: Iterable[object]) -> list[Decimal]:
        u = [float(_d("command", v)) for v in command]
        if len(u) != len(self.B[0]):
            raise MachineControlError("fast state-space command dimensions do not align")
        ax, bu = self._mv(self.A, self.state), self._mv(self.B, u)
        self.state[:] = [ax[i] + bu[i] for i in range(len(ax))]
        return [Decimal(str(v)) for v in self.state]

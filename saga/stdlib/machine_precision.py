from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable

from .machine_control import MachineControlError

D0 = Decimal(0)
D1 = Decimal(1)
D2 = Decimal(2)


def _d(name: str, value: object) -> Decimal:
    out = value if isinstance(value, Decimal) else Decimal(str(value))
    if not out.is_finite():
        raise MachineControlError(f"{name} must be finite")
    return out


def _positive(name: str, value: object) -> Decimal:
    out = _d(name, value)
    if out <= 0:
        raise MachineControlError(f"{name} must be > 0")
    return out


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(high, max(low, value))


def _decimal_from_float(value: float, name: str) -> Decimal:
    if not math.isfinite(value):
        raise MachineControlError(f"{name} became non-finite")
    return Decimal(str(value))


@dataclass(slots=True)
class TwoDOFPID:
    """Industrial-style 2-DOF PID with derivative on measurement.

    The proportional path may weight the setpoint with ``beta``. The derivative
    path intentionally observes the measurement rather than the error, avoiding
    derivative kick on setpoint changes. ``derivative_tau`` is the time constant
    of a first-order derivative low-pass. ``antiwindup_gain`` back-calculates the
    integrator when the commanded output saturates.
    """

    kp: Decimal
    ki: Decimal
    kd: Decimal
    beta: Decimal
    derivative_tau: Decimal
    antiwindup_gain: Decimal
    output_min: Decimal
    output_max: Decimal
    integral: Decimal = D0
    previous_measurement: Decimal | None = None
    derivative_state: Decimal = D0

    def __post_init__(self) -> None:
        self.kp = _d("kp", self.kp)
        self.ki = _d("ki", self.ki)
        self.kd = _d("kd", self.kd)
        self.beta = _d("beta", self.beta)
        self.derivative_tau = _d("derivative_tau", self.derivative_tau)
        self.antiwindup_gain = _d("antiwindup_gain", self.antiwindup_gain)
        self.output_min = _d("output_min", self.output_min)
        self.output_max = _d("output_max", self.output_max)
        if not D0 <= self.beta <= D1:
            raise MachineControlError("PID beta must be in 0..1")
        if self.derivative_tau < 0:
            raise MachineControlError("PID derivative_tau must be >= 0")
        if self.antiwindup_gain < 0:
            raise MachineControlError("PID antiwindup_gain must be >= 0")
        if self.output_min >= self.output_max:
            raise MachineControlError("PID output_min must be smaller than output_max")

    def reset(self) -> None:
        self.integral = D0
        self.previous_measurement = None
        self.derivative_state = D0

    def step(
        self,
        setpoint: Decimal,
        measurement: Decimal,
        feedforward: Decimal,
        dt_seconds: Decimal,
    ) -> Decimal:
        setpoint = _d("setpoint", setpoint)
        measurement = _d("measurement", measurement)
        feedforward = _d("feedforward", feedforward)
        dt = _positive("dt_seconds", dt_seconds)

        error = setpoint - measurement
        proportional = self.kp * (self.beta * setpoint - measurement)

        derivative = D0
        if self.previous_measurement is not None:
            raw = -(measurement - self.previous_measurement) / dt
            if self.derivative_tau == 0:
                self.derivative_state = raw
            else:
                alpha = dt / (self.derivative_tau + dt)
                self.derivative_state += alpha * (raw - self.derivative_state)
            derivative = self.derivative_state

        integral_candidate = self.integral + self.ki * error * dt
        unclamped = proportional + integral_candidate + self.kd * derivative + feedforward
        output = _clamp(unclamped, self.output_min, self.output_max)

        correction = self.antiwindup_gain * (output - unclamped) * dt
        self.integral = integral_candidate + correction
        # Keeping the integral contribution within the output range makes the
        # recovery bound explicit and prevents a long hidden unwind tail.
        self.integral = _clamp(self.integral, self.output_min, self.output_max)
        self.previous_measurement = measurement
        return output


@dataclass(slots=True)
class AlphaBetaObserver:
    alpha: Decimal
    beta: Decimal
    position: Decimal = D0
    velocity: Decimal = D0

    def __post_init__(self) -> None:
        self.alpha = _d("alpha", self.alpha)
        self.beta = _d("beta", self.beta)
        self.position = _d("position", self.position)
        self.velocity = _d("velocity", self.velocity)
        if not D0 < self.alpha <= D1:
            raise MachineControlError("alpha must be in (0,1]")
        if not D0 <= self.beta <= D2:
            raise MachineControlError("beta must be in 0..2")

    def reset(self, position: Decimal, velocity: Decimal) -> None:
        self.position = _d("position", position)
        self.velocity = _d("velocity", velocity)

    def step(self, measurement: Decimal, dt_seconds: Decimal) -> tuple[Decimal, Decimal]:
        measurement = _d("measurement", measurement)
        dt = _positive("dt_seconds", dt_seconds)
        predicted = self.position + self.velocity * dt
        residual = measurement - predicted
        self.position = predicted + self.alpha * residual
        self.velocity = self.velocity + (self.beta / dt) * residual
        return self.position, self.velocity


@dataclass(slots=True)
class BiquadFilter:
    b0: Decimal
    b1: Decimal
    b2: Decimal
    a1: Decimal
    a2: Decimal
    z1: Decimal = D0
    z2: Decimal = D0

    @classmethod
    def notch(cls, sample_hz: Decimal, center_hz: Decimal, q: Decimal) -> "BiquadFilter":
        fs = float(_positive("sample_hz", sample_hz))
        f0 = float(_positive("center_hz", center_hz))
        quality = float(_positive("q", q))
        if f0 >= fs / 2.0:
            raise MachineControlError("notch center_hz must be below Nyquist")
        omega = 2.0 * math.pi * f0 / fs
        alpha = math.sin(omega) / (2.0 * quality)
        c = math.cos(omega)
        a0 = 1.0 + alpha
        return cls(
            _decimal_from_float(1.0 / a0, "notch b0"),
            _decimal_from_float(-2.0 * c / a0, "notch b1"),
            _decimal_from_float(1.0 / a0, "notch b2"),
            _decimal_from_float(-2.0 * c / a0, "notch a1"),
            _decimal_from_float((1.0 - alpha) / a0, "notch a2"),
        )

    def reset(self) -> None:
        self.z1 = D0
        self.z2 = D0

    def step(self, sample: Decimal) -> Decimal:
        x = _d("sample", sample)
        # Transposed direct-form II uses two state variables and no allocation.
        y = self.b0 * x + self.z1
        self.z1 = self.b1 * x - self.a1 * y + self.z2
        self.z2 = self.b2 * x - self.a2 * y
        return y


@dataclass(slots=True)
class DeadlineBudget:
    period_us: int
    budget_us: int
    samples: int = 0
    violations: int = 0
    max_elapsed_us: int = 0
    last_elapsed_us: int = 0
    _started_ns: int | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.period_us <= 0:
            raise MachineControlError("period_us must be > 0")
        if self.budget_us <= 0 or self.budget_us > self.period_us:
            raise MachineControlError("budget_us must be in 1..period_us")

    def begin(self) -> None:
        if self._started_ns is not None:
            raise MachineControlError("deadline budget sample already started")
        self._started_ns = time.monotonic_ns()

    def end(self) -> bool:
        if self._started_ns is None:
            raise MachineControlError("deadline budget sample was not started")
        elapsed_ns = max(0, time.monotonic_ns() - self._started_ns)
        self._started_ns = None
        elapsed_us = (elapsed_ns + 999) // 1000
        self.last_elapsed_us = int(elapsed_us)
        self.max_elapsed_us = max(self.max_elapsed_us, self.last_elapsed_us)
        self.samples += 1
        over = self.last_elapsed_us > self.budget_us
        if over:
            self.violations += 1
        return over

    def reset(self) -> None:
        self.samples = 0
        self.violations = 0
        self.max_elapsed_us = 0
        self.last_elapsed_us = 0
        self._started_ns = None

    def stats_json(self) -> str:
        return json.dumps({
            "period_us": self.period_us,
            "budget_us": self.budget_us,
            "samples": self.samples,
            "violations": self.violations,
            "last_elapsed_us": self.last_elapsed_us,
            "max_elapsed_us": self.max_elapsed_us,
            "timing_class": "hosted-soft-realtime",
        }, separators=(",", ":"))


@dataclass(slots=True)
class ControlGuard:
    """Deterministic runtime contract for timestamped industrial control loops.

    All timestamps use one caller-selected monotonic clock domain. The guard does
    not sleep, allocate policy, or stop actuators; it only records violations so
    the application can make an explicit safety decision.
    """

    rate_hz: int
    budget_us: int
    stale_input_us: int
    max_jitter_us: int
    samples: int = 0
    budget_misses: int = 0
    stale_inputs: int = 0
    jitter_violations: int = 0
    invalid_timestamps: int = 0
    max_execution_us: int = 0
    max_abs_jitter_us: int = 0
    last_execution_us: int = 0
    last_abs_jitter_us: int = 0
    last_cycle_ok: bool = True
    _previous_start_ns: int | None = field(default=None, repr=False)
    _started_ns: int | None = field(default=None, repr=False)
    _precheck_ok: bool = field(default=True, repr=False)

    def __post_init__(self) -> None:
        if self.rate_hz <= 0 or self.rate_hz > 1_000_000:
            raise MachineControlError("control guard rate_hz must be in 1..1000000")
        if self.budget_us <= 0 or self.budget_us * self.rate_hz > 1_000_000:
            raise MachineControlError("control guard budget_us must fit inside one period")
        if self.stale_input_us < 0 or self.max_jitter_us < 0:
            raise MachineControlError("control guard stale_input_us/max_jitter_us must be >= 0")

    @property
    def period_ns(self) -> int:
        return 1_000_000_000 // self.rate_hz

    def begin(self, input_timestamp_ns: int, now_ns: int) -> bool:
        if self._started_ns is not None:
            raise MachineControlError("control guard cycle already started")
        if input_timestamp_ns < 0 or now_ns < 0:
            raise MachineControlError("control guard timestamps must be >= 0")
        ok = True
        if input_timestamp_ns > now_ns:
            self.invalid_timestamps += 1
            ok = False
        elif now_ns - input_timestamp_ns > self.stale_input_us * 1000:
            self.stale_inputs += 1
            ok = False
        if self._previous_start_ns is not None:
            interval = now_ns - self._previous_start_ns
            if interval < 0:
                self.invalid_timestamps += 1
                ok = False
                jitter_ns = 0
            else:
                jitter_ns = abs(interval - self.period_ns)
            jitter_us = (jitter_ns + 999) // 1000
            self.last_abs_jitter_us = int(jitter_us)
            self.max_abs_jitter_us = max(self.max_abs_jitter_us, self.last_abs_jitter_us)
            if jitter_ns > self.max_jitter_us * 1000:
                self.jitter_violations += 1
                ok = False
        else:
            self.last_abs_jitter_us = 0
        self._previous_start_ns = now_ns
        self._started_ns = now_ns
        self._precheck_ok = ok
        return ok

    def end(self, end_ns: int) -> bool:
        if self._started_ns is None:
            raise MachineControlError("control guard cycle was not started")
        if end_ns < self._started_ns:
            self.invalid_timestamps += 1
            elapsed_ns = 0
            ok = False
        else:
            elapsed_ns = end_ns - self._started_ns
            ok = self._precheck_ok
        self._started_ns = None
        elapsed_us = (elapsed_ns + 999) // 1000
        self.last_execution_us = int(elapsed_us)
        self.max_execution_us = max(self.max_execution_us, self.last_execution_us)
        self.samples += 1
        if elapsed_ns > self.budget_us * 1000:
            self.budget_misses += 1
            ok = False
        self.last_cycle_ok = ok
        return ok

    def ok(self) -> bool:
        return self.last_cycle_ok and not (self.budget_misses or self.stale_inputs or self.jitter_violations or self.invalid_timestamps)

    def reset(self) -> None:
        self.samples = self.budget_misses = self.stale_inputs = 0
        self.jitter_violations = self.invalid_timestamps = 0
        self.max_execution_us = self.max_abs_jitter_us = 0
        self.last_execution_us = self.last_abs_jitter_us = 0
        self.last_cycle_ok = True
        self._previous_start_ns = self._started_ns = None
        self._precheck_ok = True

    def stats_json(self) -> str:
        return json.dumps({
            "rate_hz": self.rate_hz,
            "period_ns": self.period_ns,
            "budget_us": self.budget_us,
            "stale_input_us": self.stale_input_us,
            "max_jitter_us": self.max_jitter_us,
            "samples": self.samples,
            "budget_misses": self.budget_misses,
            "stale_inputs": self.stale_inputs,
            "jitter_violations": self.jitter_violations,
            "invalid_timestamps": self.invalid_timestamps,
            "last_execution_us": self.last_execution_us,
            "max_execution_us": self.max_execution_us,
            "last_abs_jitter_us": self.last_abs_jitter_us,
            "max_abs_jitter_us": self.max_abs_jitter_us,
            "last_cycle_ok": self.last_cycle_ok,
            "timing_class": "caller-clock-contract",
        }, separators=(",", ":"))


def motor_feedforward(
    static_gain: Decimal,
    velocity_gain: Decimal,
    acceleration_gain: Decimal,
    velocity: Decimal,
    acceleration: Decimal,
) -> Decimal:
    ks = _d("static_gain", static_gain)
    kv = _d("velocity_gain", velocity_gain)
    ka = _d("acceleration_gain", acceleration_gain)
    velocity = _d("velocity", velocity)
    acceleration = _d("acceleration", acceleration)
    direction = D0
    if velocity > 0 or (velocity == 0 and acceleration > 0):
        direction = D1
    elif velocity < 0 or (velocity == 0 and acceleration < 0):
        direction = -D1
    return ks * direction + kv * velocity + ka * acceleration


def clarke(ia: Decimal, ib: Decimal, ic: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    ia, ib, ic = _d("ia", ia), _d("ib", ib), _d("ic", ic)
    sqrt3 = _decimal_from_float(math.sqrt(3.0), "sqrt(3)")
    alpha = (D2 / Decimal(3)) * (ia - ib / D2 - ic / D2)
    beta = (sqrt3 / Decimal(3)) * (ib - ic)
    zero = (ia + ib + ic) / Decimal(3)
    return alpha, beta, zero


def park(alpha: Decimal, beta: Decimal, theta_rad: Decimal) -> tuple[Decimal, Decimal]:
    alpha = _d("alpha", alpha)
    beta = _d("beta", beta)
    theta = float(_d("theta_rad", theta_rad))
    c = _decimal_from_float(math.cos(theta), "cos(theta)")
    s = _decimal_from_float(math.sin(theta), "sin(theta)")
    return alpha * c + beta * s, -alpha * s + beta * c


def inverse_park(d: Decimal, q: Decimal, theta_rad: Decimal) -> tuple[Decimal, Decimal]:
    d = _d("d", d)
    q = _d("q", q)
    theta = float(_d("theta_rad", theta_rad))
    c = _decimal_from_float(math.cos(theta), "cos(theta)")
    s = _decimal_from_float(math.sin(theta), "sin(theta)")
    return d * c - q * s, d * s + q * c


def svpwm(alpha: Decimal, beta: Decimal, bus_voltage: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    alpha = _d("alpha", alpha)
    beta = _d("beta", beta)
    vbus = _positive("bus_voltage", bus_voltage)
    sqrt3 = _decimal_from_float(math.sqrt(3.0), "sqrt(3)")
    va = alpha
    vb = -alpha / D2 + sqrt3 * beta / D2
    vc = -alpha / D2 - sqrt3 * beta / D2
    offset = (max(va, vb, vc) + min(va, vb, vc)) / D2
    half = Decimal("0.5")
    duties = [half + (phase - offset) / vbus for phase in (va, vb, vc)]
    return tuple(_clamp(v, D0, D1) for v in duties)

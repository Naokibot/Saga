from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass, field
from decimal import Decimal

from .machine_control import MachineControlError

D0 = Decimal(0)
D1 = Decimal(1)
D2 = Decimal(2)
PI2 = Decimal(str(2.0 * math.pi))
SQRT3 = Decimal(str(math.sqrt(3.0)))


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


def _sqrt(value: Decimal, name: str) -> Decimal:
    if value < 0:
        raise MachineControlError(f"{name} must be >= 0")
    result = math.sqrt(float(value))
    if not math.isfinite(result):
        raise MachineControlError(f"{name} became non-finite")
    return Decimal(str(result))


def _sin_cos(theta: Decimal) -> tuple[Decimal, Decimal]:
    t = float(_d("theta_rad", theta))
    return Decimal(str(math.sin(t))), Decimal(str(math.cos(t)))


@dataclass(slots=True)
class FOCCurrentLoop:
    """Fixed-state d/q current loop suitable for a preallocated control kernel.

    The loop performs Clarke/Park transforms, PI current regulation, standard
    PMSM cross-coupling/feed-forward compensation, voltage-vector limiting and
    SVPWM duty generation. State is held inside the object so the Saga surface
    does not need to allocate a result list on every cycle.
    """

    kp_d: Decimal
    ki_d: Decimal
    kp_q: Decimal
    ki_q: Decimal
    resistance: Decimal
    ld: Decimal
    lq: Decimal
    flux: Decimal
    current_limit: Decimal
    voltage_limit: Decimal
    antiwindup_gain: Decimal
    integral_d: Decimal = D0
    integral_q: Decimal = D0
    measured_d: Decimal = D0
    measured_q: Decimal = D0
    voltage_d: Decimal = D0
    voltage_q: Decimal = D0
    duty_a: Decimal = Decimal("0.5")
    duty_b: Decimal = Decimal("0.5")
    duty_c: Decimal = Decimal("0.5")

    def __post_init__(self) -> None:
        for name in ("kp_d", "ki_d", "kp_q", "ki_q", "resistance", "ld", "lq", "flux", "antiwindup_gain"):
            setattr(self, name, _d(name, getattr(self, name)))
        self.current_limit = _positive("current_limit", self.current_limit)
        self.voltage_limit = _positive("voltage_limit", self.voltage_limit)
        if self.resistance < 0 or self.ld <= 0 or self.lq <= 0 or self.flux < 0:
            raise MachineControlError("FOC motor parameters require R>=0, Ld/Lq>0 and flux>=0")
        if self.antiwindup_gain < 0:
            raise MachineControlError("FOC antiwindup_gain must be >= 0")

    def reset(self) -> None:
        self.integral_d = self.integral_q = D0
        self.measured_d = self.measured_q = D0
        self.voltage_d = self.voltage_q = D0
        self.duty_a = self.duty_b = self.duty_c = Decimal("0.5")

    def step(
        self,
        id_ref: Decimal,
        iq_ref: Decimal,
        ia: Decimal,
        ib: Decimal,
        ic: Decimal,
        electrical_theta_rad: Decimal,
        electrical_omega_rad_s: Decimal,
        bus_voltage: Decimal,
        dt_seconds: Decimal,
    ) -> None:
        id_ref = _clamp(_d("id_ref", id_ref), -self.current_limit, self.current_limit)
        iq_ref = _clamp(_d("iq_ref", iq_ref), -self.current_limit, self.current_limit)
        ia, ib, ic = _d("ia", ia), _d("ib", ib), _d("ic", ic)
        theta = _d("electrical_theta_rad", electrical_theta_rad)
        omega = _d("electrical_omega_rad_s", electrical_omega_rad_s)
        vbus = _positive("bus_voltage", bus_voltage)
        dt = _positive("dt_seconds", dt_seconds)

        alpha = (D2 / Decimal(3)) * (ia - ib / D2 - ic / D2)
        beta = (SQRT3 / Decimal(3)) * (ib - ic)
        s, c = _sin_cos(theta)
        self.measured_d = alpha * c + beta * s
        self.measured_q = -alpha * s + beta * c

        error_d = id_ref - self.measured_d
        error_q = iq_ref - self.measured_q
        candidate_d = self.integral_d + self.ki_d * error_d * dt
        candidate_q = self.integral_q + self.ki_q * error_q * dt

        vd_ff = self.resistance * id_ref - omega * self.lq * self.measured_q
        vq_ff = self.resistance * iq_ref + omega * (self.ld * self.measured_d + self.flux)
        vd = self.kp_d * error_d + candidate_d + vd_ff
        vq = self.kp_q * error_q + candidate_q + vq_ff

        # Linear SVPWM voltage radius. voltage_limit is an application limit;
        # Vbus/sqrt(3) is the modulation-side ceiling used by this profile.
        limit = min(self.voltage_limit, vbus / SQRT3)
        magnitude = _sqrt(vd * vd + vq * vq, "FOC voltage magnitude")
        scale = D1 if magnitude <= limit or magnitude == 0 else limit / magnitude
        sat_d, sat_q = vd * scale, vq * scale
        self.integral_d = candidate_d + self.antiwindup_gain * (sat_d - vd) * dt
        self.integral_q = candidate_q + self.antiwindup_gain * (sat_q - vq) * dt
        self.integral_d = _clamp(self.integral_d, -self.voltage_limit, self.voltage_limit)
        self.integral_q = _clamp(self.integral_q, -self.voltage_limit, self.voltage_limit)
        self.voltage_d, self.voltage_q = sat_d, sat_q

        alpha_v = sat_d * c - sat_q * s
        beta_v = sat_d * s + sat_q * c
        va = alpha_v
        vb = -alpha_v / D2 + SQRT3 * beta_v / D2
        vc = -alpha_v / D2 - SQRT3 * beta_v / D2
        offset = (max(va, vb, vc) + min(va, vb, vc)) / D2
        half = Decimal("0.5")
        self.duty_a = _clamp(half + (va - offset) / vbus, D0, D1)
        self.duty_b = _clamp(half + (vb - offset) / vbus, D0, D1)
        self.duty_c = _clamp(half + (vc - offset) / vbus, D0, D1)


@dataclass(slots=True)
class UnifiedEncoder:
    counts_per_revolution: int
    gear_ratio: Decimal
    modulus: int
    direction: int
    velocity_alpha: Decimal
    zero_offset_degrees: Decimal = D0
    raw_count: int = 0
    unwrapped_count: int = 0
    position_degrees: Decimal = D0
    velocity_deg_s: Decimal = D0
    _last_raw: int | None = None
    _last_position: Decimal | None = None
    _last_timestamp_ns: int | None = None

    def __post_init__(self) -> None:
        if self.counts_per_revolution <= 0:
            raise MachineControlError("encoder counts_per_revolution must be > 0")
        self.gear_ratio = _positive("gear_ratio", self.gear_ratio)
        if self.modulus < 0 or self.modulus == 1:
            raise MachineControlError("encoder modulus must be 0 or > 1")
        if self.direction not in (-1, 1):
            raise MachineControlError("encoder direction must be -1 or 1")
        self.velocity_alpha = _d("velocity_alpha", self.velocity_alpha)
        if not D0 < self.velocity_alpha <= D1:
            raise MachineControlError("encoder velocity_alpha must be in (0,1]")

    def sample(self, raw_count: int, timestamp_ns: int) -> None:
        if timestamp_ns < 0:
            raise MachineControlError("encoder timestamp_ns must be >= 0")
        raw_count = int(raw_count)
        if self.modulus:
            raw_count %= self.modulus
        if self._last_raw is None:
            self.unwrapped_count = raw_count
        else:
            delta = raw_count - self._last_raw
            if self.modulus:
                half = self.modulus // 2
                if delta > half:
                    delta -= self.modulus
                elif delta < -half:
                    delta += self.modulus
            self.unwrapped_count += delta if self.modulus else raw_count - self._last_raw
        self.raw_count = raw_count
        effective = Decimal(self.counts_per_revolution) * self.gear_ratio
        new_position = Decimal(self.direction * self.unwrapped_count) * Decimal(360) / effective + self.zero_offset_degrees
        if self._last_timestamp_ns is not None and self._last_position is not None:
            dt_ns = timestamp_ns - self._last_timestamp_ns
            if dt_ns <= 0:
                raise MachineControlError("encoder timestamps must increase")
            raw_velocity = (new_position - self._last_position) * Decimal(1_000_000_000) / Decimal(dt_ns)
            self.velocity_deg_s += self.velocity_alpha * (raw_velocity - self.velocity_deg_s)
        self.position_degrees = new_position
        self._last_raw = raw_count
        self._last_position = new_position
        self._last_timestamp_ns = timestamp_ns

    def align_absolute(self, raw_count: int, mechanical_degrees: Decimal) -> None:
        target = _d("mechanical_degrees", mechanical_degrees)
        raw = int(raw_count) % self.modulus if self.modulus else int(raw_count)
        effective = Decimal(self.counts_per_revolution) * self.gear_ratio
        base = Decimal(self.direction * raw) * Decimal(360) / effective
        self.zero_offset_degrees = target - base
        self._last_raw = None
        self._last_position = None
        self._last_timestamp_ns = None

    @property
    def velocity_rpm(self) -> Decimal:
        return self.velocity_deg_s / Decimal(6)


@dataclass(slots=True)
class RLS2:
    forgetting_factor: Decimal
    p00: Decimal
    p01: Decimal
    p10: Decimal
    p11: Decimal
    theta0: Decimal = D0
    theta1: Decimal = D0
    last_error: Decimal = D0

    @classmethod
    def create(cls, forgetting_factor: Decimal, covariance: Decimal) -> "RLS2":
        lam = _d("forgetting_factor", forgetting_factor)
        p = _positive("covariance", covariance)
        if not D0 < lam <= D1:
            raise MachineControlError("RLS forgetting_factor must be in (0,1]")
        return cls(lam, p, D0, D0, p)

    def update(self, x0: Decimal, x1: Decimal, y: Decimal) -> None:
        x0, x1, y = _d("x0", x0), _d("x1", x1), _d("y", y)
        px0 = self.p00 * x0 + self.p01 * x1
        px1 = self.p10 * x0 + self.p11 * x1
        denom = self.forgetting_factor + x0 * px0 + x1 * px1
        if denom <= 0:
            raise MachineControlError("RLS covariance lost positive denominator")
        k0, k1 = px0 / denom, px1 / denom
        self.last_error = y - (self.theta0 * x0 + self.theta1 * x1)
        self.theta0 += k0 * self.last_error
        self.theta1 += k1 * self.last_error
        # P=(P-K phi^T P)/lambda. Save old row products first.
        row0x0 = x0 * self.p00 + x1 * self.p10
        row0x1 = x0 * self.p01 + x1 * self.p11
        self.p00 = (self.p00 - k0 * row0x0) / self.forgetting_factor
        self.p01 = (self.p01 - k0 * row0x1) / self.forgetting_factor
        self.p10 = (self.p10 - k1 * row0x0) / self.forgetting_factor
        self.p11 = (self.p11 - k1 * row0x1) / self.forgetting_factor


@dataclass(slots=True)
class MPC2:
    """2-state/1-input box-constrained linear MPC with precomputed Hessian.

    A projected-gradient solve is performed against a fixed horizon using a
    warm-started, preallocated command vector. It is intentionally bounded and
    deterministic in iteration count rather than being a general QP solver.
    """

    a00: Decimal
    a01: Decimal
    a10: Decimal
    a11: Decimal
    b0: Decimal
    b1: Decimal
    q0: Decimal
    q1: Decimal
    r: Decimal
    horizon: int
    u_min: Decimal
    u_max: Decimal
    iterations: int = 12
    _h: list[list[Decimal]] = field(default_factory=list, repr=False)
    _influence: list[list[tuple[Decimal, Decimal]]] = field(default_factory=list, repr=False)
    _a_powers: list[tuple[Decimal, Decimal, Decimal, Decimal]] = field(default_factory=list, repr=False)
    _u: list[Decimal] = field(default_factory=list, repr=False)
    _step: Decimal = D0

    def __post_init__(self) -> None:
        for name in ("a00", "a01", "a10", "a11", "b0", "b1", "q0", "q1", "r", "u_min", "u_max"):
            setattr(self, name, _d(name, getattr(self, name)))
        if self.q0 < 0 or self.q1 < 0 or self.r <= 0:
            raise MachineControlError("MPC requires q0/q1>=0 and r>0")
        if not 1 <= self.horizon <= 32:
            raise MachineControlError("MPC horizon must be in 1..32")
        if self.u_min >= self.u_max:
            raise MachineControlError("MPC u_min must be smaller than u_max")
        if not 1 <= self.iterations <= 64:
            raise MachineControlError("MPC iterations must be in 1..64")
        self._precompute()

    @staticmethod
    def _mul(a: tuple[Decimal, Decimal, Decimal, Decimal], b: tuple[Decimal, Decimal, Decimal, Decimal]) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        return (
            a[0]*b[0]+a[1]*b[2], a[0]*b[1]+a[1]*b[3],
            a[2]*b[0]+a[3]*b[2], a[2]*b[1]+a[3]*b[3],
        )

    def _precompute(self) -> None:
        A = (self.a00, self.a01, self.a10, self.a11)
        ident = (D1, D0, D0, D1)
        self._a_powers = [ident]
        for _ in range(self.horizon):
            self._a_powers.append(self._mul(self._a_powers[-1], A))
        # influence[k][j] is the effect of u_j on x_(k+1).
        self._influence = []
        for k in range(self.horizon):
            row: list[tuple[Decimal, Decimal]] = []
            for j in range(self.horizon):
                if j > k:
                    row.append((D0, D0))
                else:
                    p = self._a_powers[k-j]
                    row.append((p[0]*self.b0+p[1]*self.b1, p[2]*self.b0+p[3]*self.b1))
            self._influence.append(row)
        self._h = [[D0 for _ in range(self.horizon)] for _ in range(self.horizon)]
        for i in range(self.horizon):
            for j in range(self.horizon):
                total = self.r if i == j else D0
                for k in range(max(i, j), self.horizon):
                    ci, cj = self._influence[k][i], self._influence[k][j]
                    total += self.q0*ci[0]*cj[0] + self.q1*ci[1]*cj[1]
                self._h[i][j] = total
        max_row = max(sum(abs(v) for v in row) for row in self._h)
        self._step = D1 / (D2 * max_row) if max_row > 0 else D1
        self._u = [D0 for _ in range(self.horizon)]

    def reset(self) -> None:
        for i in range(self.horizon):
            self._u[i] = D0

    def step(self, x0: Decimal, x1: Decimal, ref0: Decimal, ref1: Decimal) -> Decimal:
        x0, x1 = _d("x0", x0), _d("x1", x1)
        ref0, ref1 = _d("ref0", ref0), _d("ref1", ref1)
        # Linear term g from free response relative to a constant reference.
        g = [D0 for _ in range(self.horizon)]
        for i in range(self.horizon):
            total = D0
            for k in range(i, self.horizon):
                p = self._a_powers[k+1]
                free0 = p[0]*x0 + p[1]*x1 - ref0
                free1 = p[2]*x0 + p[3]*x1 - ref1
                c = self._influence[k][i]
                total += self.q0*c[0]*free0 + self.q1*c[1]*free1
            g[i] = total
        # Warm-started projected gradient with fixed iteration count.
        for _ in range(self.iterations):
            for i in range(self.horizon):
                hu = sum(self._h[i][j] * self._u[j] for j in range(self.horizon))
                gradient = D2 * (hu + g[i])
                self._u[i] = _clamp(self._u[i] - self._step * gradient, self.u_min, self.u_max)
        command = self._u[0]
        for i in range(self.horizon - 1):
            self._u[i] = self._u[i+1]
        self._u[-1] = self._u[-2] if self.horizon > 1 else command
        return command


@dataclass(slots=True)
class DisturbanceObserver:
    input_gain: Decimal
    damping: Decimal
    bandwidth_hz: Decimal
    estimate: Decimal = D0
    _previous_velocity: Decimal | None = None

    def __post_init__(self) -> None:
        self.input_gain = _d("input_gain", self.input_gain)
        self.damping = _d("damping", self.damping)
        self.bandwidth_hz = _positive("bandwidth_hz", self.bandwidth_hz)

    def reset(self, estimate: Decimal = D0) -> None:
        self.estimate = _d("estimate", estimate)
        self._previous_velocity = None

    def step(self, command: Decimal, measured_velocity: Decimal, dt_seconds: Decimal) -> Decimal:
        command = _d("command", command)
        velocity = _d("measured_velocity", measured_velocity)
        dt = _positive("dt_seconds", dt_seconds)
        if self._previous_velocity is None:
            self._previous_velocity = velocity
            return self.estimate
        acceleration = (velocity - self._previous_velocity) / dt
        nominal = self.input_gain * command - self.damping * velocity
        raw = acceleration - nominal
        alpha = Decimal(str(1.0 - math.exp(-2.0 * math.pi * float(self.bandwidth_hz * dt))))
        self.estimate += alpha * (raw - self.estimate)
        self._previous_velocity = velocity
        return self.estimate


def friction_compensation(
    coulomb: Decimal,
    viscous: Decimal,
    static: Decimal,
    stribeck_velocity: Decimal,
    velocity: Decimal,
    smoothing_velocity: Decimal,
) -> Decimal:
    fc = _d("coulomb", coulomb)
    fv = _d("viscous", viscous)
    fs = _d("static", static)
    vs = _positive("stribeck_velocity", stribeck_velocity)
    v = _d("velocity", velocity)
    eps = _positive("smoothing_velocity", smoothing_velocity)
    if fc < 0 or fv < 0 or fs < fc:
        raise MachineControlError("friction requires coulomb/viscous>=0 and static>=coulomb")
    ratio = float(abs(v) / vs)
    magnitude = fc + (fs - fc) * Decimal(str(math.exp(-(ratio * ratio))))
    sign = Decimal(str(math.tanh(float(v / eps))))
    return magnitude * sign + fv * v


@dataclass(slots=True)
class MultiAxisSynchronizer:
    axis_count: int
    kp: Decimal
    max_correction: Decimal
    skew_limit: Decimal
    ratios: list[Decimal] = field(default_factory=list)
    offsets: list[Decimal] = field(default_factory=list)
    errors: list[Decimal] = field(default_factory=list)
    master_position: Decimal = D0
    healthy: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.axis_count <= 32:
            raise MachineControlError("axis_sync axis_count must be in 1..32")
        self.kp = _d("kp", self.kp)
        self.max_correction = _positive("max_correction", self.max_correction)
        self.skew_limit = _positive("skew_limit", self.skew_limit)
        self.ratios = [D1 for _ in range(self.axis_count)]
        self.offsets = [D0 for _ in range(self.axis_count)]
        self.errors = [D0 for _ in range(self.axis_count)]

    def configure(self, axis: int, ratio: Decimal, offset: Decimal) -> None:
        if not 0 <= axis < self.axis_count:
            raise MachineControlError("axis_sync axis index out of range")
        self.ratios[axis] = _d("ratio", ratio)
        self.offsets[axis] = _d("offset", offset)

    def begin(self, master_position: Decimal) -> None:
        self.master_position = _d("master_position", master_position)
        self.healthy = True

    def correction(self, axis: int, actual_position: Decimal) -> Decimal:
        if not 0 <= axis < self.axis_count:
            raise MachineControlError("axis_sync axis index out of range")
        actual = _d("actual_position", actual_position)
        expected = self.master_position * self.ratios[axis] + self.offsets[axis]
        error = expected - actual
        self.errors[axis] = error
        if abs(error) > self.skew_limit:
            self.healthy = False
        return _clamp(self.kp * error, -self.max_correction, self.max_correction)

    def error(self, axis: int) -> Decimal:
        if not 0 <= axis < self.axis_count:
            raise MachineControlError("axis_sync axis index out of range")
        return self.errors[axis]


# EtherCAT frame helpers. This profile deliberately exposes generic datagram
# framing rather than silently implementing a topology/configuration policy.
ETHERCAT_ETHERTYPE = 0x88A4
ETHERCAT_TYPE_COMMAND = 0x1
ETHERCAT_MAX_DATAGRAM_DATA = 0x07FF
ETHERCAT_COMMANDS = {
    "NOP": 0x00, "APRD": 0x01, "APWR": 0x02, "APRW": 0x03,
    "FPRD": 0x04, "FPWR": 0x05, "FPRW": 0x06, "BRD": 0x07,
    "BWR": 0x08, "BRW": 0x09, "LRD": 0x0A, "LWR": 0x0B,
    "LRW": 0x0C, "ARMW": 0x0D, "FRMW": 0x0E,
}


def ethercat_datagram(command: str, index: int, address: int, offset: int, data: bytes, irq: int = 0, more: bool = False) -> bytes:
    cmd = ETHERCAT_COMMANDS.get(command.upper())
    if cmd is None:
        raise MachineControlError("unsupported EtherCAT command")
    if not 0 <= index <= 0xFF:
        raise MachineControlError("EtherCAT index must be 0..255")
    if not 0 <= address <= 0xFFFF or not 0 <= offset <= 0xFFFF:
        raise MachineControlError("EtherCAT address/offset must be 0..65535")
    if not 0 <= irq <= 0xFFFF:
        raise MachineControlError("EtherCAT IRQ must be 0..65535")
    payload = bytes(data)
    if len(payload) > ETHERCAT_MAX_DATAGRAM_DATA:
        raise MachineControlError("EtherCAT datagram payload exceeds 2047 bytes")
    length_flags = len(payload) | (0x8000 if more else 0)
    return struct.pack("<BBHHHH", cmd, index, address, offset, length_flags, irq) + payload + b"\x00\x00"


def ethercat_frame(datagrams: bytes) -> bytes:
    payload = bytes(datagrams)
    if len(payload) > 0x07FF:
        raise MachineControlError("EtherCAT frame payload exceeds 2047 bytes")
    header = len(payload) | (ETHERCAT_TYPE_COMMAND << 12)
    return struct.pack("<H", header) + payload


def ethercat_lrw(index: int, logical_address: int, process_data: bytes) -> bytes:
    if not 0 <= logical_address <= 0xFFFFFFFF:
        raise MachineControlError("EtherCAT logical address must be 0..0xffffffff")
    adp = logical_address & 0xFFFF
    ado = (logical_address >> 16) & 0xFFFF
    return ethercat_frame(ethercat_datagram("LRW", index, adp, ado, process_data))


def ethercat_first_datagram_json(frame: bytes) -> str:
    raw = bytes(frame)
    if len(raw) < 16:
        raise MachineControlError("EtherCAT frame is too short")
    header = struct.unpack_from("<H", raw, 0)[0]
    frame_length = header & 0x07FF
    frame_type = (header >> 12) & 0x0F
    if frame_type != ETHERCAT_TYPE_COMMAND or frame_length + 2 > len(raw):
        raise MachineControlError("invalid EtherCAT frame header")
    cmd, index, address, offset, length_flags, irq = struct.unpack_from("<BBHHHH", raw, 2)
    length = length_flags & 0x07FF
    end = 12 + length
    if end + 2 > len(raw):
        raise MachineControlError("truncated EtherCAT datagram")
    data = raw[12:end]
    wkc = struct.unpack_from("<H", raw, end)[0]
    command_name = next((name for name, value in ETHERCAT_COMMANDS.items() if value == cmd), f"0x{cmd:02x}")
    return json.dumps({
        "command": command_name,
        "index": index,
        "address": address,
        "offset": offset,
        "length": length,
        "more": bool(length_flags & 0x8000),
        "irq": irq,
        "data_hex": data.hex(),
        "working_counter": wkc,
    }, separators=(",", ":"), sort_keys=True)


def canfd_frame_json(received: bool, can_id: int = 0, data: bytes = b"", flags: int = 0, timestamp_ns: int = 0, timestamp_source: str = "none") -> str:
    return json.dumps({
        "received": bool(received),
        "id": int(can_id),
        "data_hex": bytes(data).hex(),
        "brs": bool(flags & 0x01),
        "esi": bool(flags & 0x02),
        "timestamp_ns": int(timestamp_ns),
        "timestamp_source": timestamp_source,
    }, separators=(",", ":"), sort_keys=True)


def allocation_free_profile_json() -> str:
    return json.dumps({
        "profile": "mcu-control-0.47",
        "saga_visible_heap_allocation_in_tick": "forbidden",
        "preallocate_state_before_tick": True,
        "bounded_loops_required": True,
        "blocking_io_in_tick": "forbidden",
        "async_in_tick": "forbidden",
        "host_reference_runtime_hard_realtime": False,
        "target_backend_must_prove_no_allocator_calls": True,
    }, separators=(",", ":"))

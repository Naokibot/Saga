from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import permutations
from typing import Iterable

from .machine_control import JerkLimitedProfile, MachineControlError

D0 = Decimal(0)
D1 = Decimal(1)


def _d(value: object) -> Decimal:
    if isinstance(value, Decimal):
        out = value
    else:
        out = Decimal(str(value))
    if not out.is_finite():
        raise MachineControlError("matrix/control values must be finite")
    return out


def _vec(values: Iterable[object], size: int | None = None, name: str = "vector") -> list[Decimal]:
    out = [_d(v) for v in values]
    if size is not None and len(out) != size:
        raise MachineControlError(f"{name} must contain {size} values")
    return out


def _mat(values: Iterable[Iterable[object]], rows: int | None = None, cols: int | None = None, name: str = "matrix") -> list[list[Decimal]]:
    out = [_vec(row) for row in values]
    if rows is not None and len(out) != rows:
        raise MachineControlError(f"{name} must contain {rows} rows")
    if not out:
        raise MachineControlError(f"{name} must not be empty")
    width = len(out[0])
    if width == 0 or any(len(row) != width for row in out):
        raise MachineControlError(f"{name} rows must have equal non-zero width")
    if cols is not None and width != cols:
        raise MachineControlError(f"{name} must contain {cols} columns")
    return out


def _eye(n: int) -> list[list[Decimal]]:
    return [[D1 if i == j else D0 for j in range(n)] for i in range(n)]


def _transpose(a: list[list[Decimal]]) -> list[list[Decimal]]:
    return [list(row) for row in zip(*a)]


def _mm(a: list[list[Decimal]], b: list[list[Decimal]]) -> list[list[Decimal]]:
    if len(a[0]) != len(b):
        raise MachineControlError("matrix dimensions do not align")
    bt = _transpose(b)
    return [[sum((x*y for x, y in zip(row, col)), D0) for col in bt] for row in a]


def _mv(a: list[list[Decimal]], x: list[Decimal]) -> list[Decimal]:
    if len(a[0]) != len(x):
        raise MachineControlError("matrix/vector dimensions do not align")
    return [sum((u*v for u, v in zip(row, x)), D0) for row in a]


def _add(a: list[list[Decimal]], b: list[list[Decimal]]) -> list[list[Decimal]]:
    if len(a) != len(b) or len(a[0]) != len(b[0]):
        raise MachineControlError("matrix dimensions do not align")
    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def _sub(a: list[list[Decimal]], b: list[list[Decimal]]) -> list[list[Decimal]]:
    if len(a) != len(b) or len(a[0]) != len(b[0]):
        raise MachineControlError("matrix dimensions do not align")
    return [[a[i][j] - b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def _inverse(a: list[list[Decimal]]) -> list[list[Decimal]]:
    n = len(a)
    if n == 0 or any(len(row) != n for row in a):
        raise MachineControlError("inverse requires a square matrix")
    aug = [list(a[i]) + _eye(n)[i] for i in range(n)]
    eps = Decimal("1e-24")
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) <= eps:
            raise MachineControlError("matrix is singular")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        aug[col] = [v/div for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor == 0:
                continue
            aug[r] = [aug[r][c] - factor*aug[col][c] for c in range(2*n)]
    return [row[n:] for row in aug]


def _diag(values: list[Decimal]) -> list[list[Decimal]]:
    return [[values[i] if i == j else D0 for j in range(len(values))] for i in range(len(values))]


@dataclass(slots=True)
class StateSpaceController:
    """Discrete state-feedback controller u = N*r - K*x with clamping.

    The plant matrices are retained for simulation/prediction so the same object can
    be used in HIL and offline tuning without a second host-language model.
    """

    A: list[list[Decimal]]
    B: list[list[Decimal]]
    K: list[list[Decimal]]
    N: list[list[Decimal]]
    state: list[Decimal]
    minimum: list[Decimal]
    maximum: list[Decimal]

    @classmethod
    def create(cls, A, B, K, N, initial_state, minimum, maximum) -> "StateSpaceController":
        A = _mat(A, name="A")
        n = len(A)
        if len(A[0]) != n:
            raise MachineControlError("A must be square")
        B = _mat(B, rows=n, name="B")
        m = len(B[0])
        K = _mat(K, rows=m, cols=n, name="K")
        N = _mat(N, rows=m, name="N")
        x = _vec(initial_state, n, "initial_state")
        lo = _vec(minimum, m, "minimum")
        hi = _vec(maximum, m, "maximum")
        if any(lo[i] > hi[i] for i in range(m)):
            raise MachineControlError("minimum must be <= maximum")
        return cls(A, B, K, N, x, lo, hi)

    def command(self, reference: Iterable[object], measured_state: Iterable[object] | None = None) -> list[Decimal]:
        x = self.state if measured_state is None else _vec(measured_state, len(self.state), "measured_state")
        r = _vec(reference, len(self.N[0]), "reference")
        ff = _mv(self.N, r)
        fb = _mv(self.K, x)
        return [min(self.maximum[i], max(self.minimum[i], ff[i]-fb[i])) for i in range(len(ff))]

    def predict(self, command: Iterable[object]) -> list[Decimal]:
        u = _vec(command, len(self.B[0]), "command")
        ax = _mv(self.A, self.state)
        bu = _mv(self.B, u)
        self.state = [ax[i]+bu[i] for i in range(len(ax))]
        return list(self.state)

    def set_state(self, state: Iterable[object]) -> None:
        self.state = _vec(state, len(self.state), "state")


@dataclass(slots=True)
class LinearKalmanFilter:
    A: list[list[Decimal]]
    H: list[list[Decimal]]
    Q: list[list[Decimal]]
    R: list[list[Decimal]]
    x: list[Decimal]
    P: list[list[Decimal]]

    @classmethod
    def create(cls, A, H, Q, R, initial_state, initial_covariance) -> "LinearKalmanFilter":
        A = _mat(A, name="A")
        n = len(A)
        if len(A[0]) != n:
            raise MachineControlError("Kalman A must be square")
        H = _mat(H, cols=n, name="H")
        k = len(H)
        Q = _mat(Q, rows=n, cols=n, name="Q")
        R = _mat(R, rows=k, cols=k, name="R")
        P = _mat(initial_covariance, rows=n, cols=n, name="initial_covariance")
        return cls(A, H, Q, R, _vec(initial_state, n, "initial_state"), P)

    def predict(self) -> list[Decimal]:
        self.x = _mv(self.A, self.x)
        self.P = _add(_mm(_mm(self.A, self.P), _transpose(self.A)), self.Q)
        return list(self.x)

    def update(self, measurement: Iterable[object]) -> list[Decimal]:
        z = _vec(measurement, len(self.H), "measurement")
        hx = _mv(self.H, self.x)
        y = [z[i]-hx[i] for i in range(len(z))]
        ht = _transpose(self.H)
        s = _add(_mm(_mm(self.H, self.P), ht), self.R)
        kg = _mm(_mm(self.P, ht), _inverse(s))
        correction = _mv(kg, y)
        self.x = [self.x[i]+correction[i] for i in range(len(self.x))]
        self.P = _mm(_sub(_eye(len(self.x)), _mm(kg, self.H)), self.P)
        return list(self.x)


@dataclass(slots=True)
class SynchronizedMotionGroup:
    positions: list[Decimal]
    max_velocity: Decimal
    max_acceleration: Decimal
    max_jerk: Decimal
    profiles: list[JerkLimitedProfile] = field(default_factory=list)
    target: list[Decimal] = field(default_factory=list)

    @classmethod
    def create(cls, initial_positions, max_velocity, max_acceleration, max_jerk) -> "SynchronizedMotionGroup":
        pos = _vec(initial_positions, name="initial_positions")
        if not pos:
            raise MachineControlError("motion group requires at least one axis")
        mv, ma, mj = _d(max_velocity), _d(max_acceleration), _d(max_jerk)
        if mv <= 0 or ma <= 0 or mj <= 0:
            raise MachineControlError("motion limits must be > 0")
        obj = cls(pos, mv, ma, mj)
        obj.retarget(pos)
        return obj

    def retarget(self, target: Iterable[object]) -> None:
        tgt = _vec(target, len(self.positions), "target")
        distances = [abs(tgt[i]-self.positions[i]) for i in range(len(tgt))]
        longest = max(distances, default=D0)
        self.profiles = []
        for i, distance in enumerate(distances):
            # Scale the shorter axes so they converge on approximately the same cycle.
            ratio = D1 if longest == 0 else max(Decimal("0.05"), distance/longest)
            self.profiles.append(JerkLimitedProfile(self.positions[i], D0, D0, tgt[i], self.max_velocity*ratio, self.max_acceleration*ratio, self.max_jerk*ratio))
        self.target = tgt

    def step(self, dt: object) -> dict[str, object]:
        dt = _d(dt)
        if dt <= 0:
            raise MachineControlError("dt must be > 0")
        pos, vel, acc = [], [], []
        for p in self.profiles:
            position = p.step(dt)
            pos.append(position); vel.append(p.velocity); acc.append(p.acceleration)
        self.positions = pos
        return {"position": pos, "velocity": vel, "acceleration": acc, "done": self.done()}

    def done(self) -> bool:
        return all(p.done() for p in self.profiles)


@dataclass(slots=True)
class DHKinematicChain:
    """Serial manipulator kinematics using standard DH parameters.

    Each row is [a, alpha, d, theta_offset]. Revolute joints are assumed.
    """

    rows: list[list[Decimal]]

    @classmethod
    def create(cls, rows) -> "DHKinematicChain":
        return cls(_mat(rows, cols=4, name="DH rows"))

    @staticmethod
    def _mul4(a, b):
        return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]

    def forward(self, joints: Iterable[object]) -> list[list[Decimal]]:
        q = _vec(joints, len(self.rows), "joints")
        t = [[1.0,0.0,0.0,0.0],[0.0,1.0,0.0,0.0],[0.0,0.0,1.0,0.0],[0.0,0.0,0.0,1.0]]
        for row, qi in zip(self.rows, q):
            a, alpha, d, offset = map(float, row)
            th = float(qi) + offset
            ct, st, ca, sa = math.cos(th), math.sin(th), math.cos(alpha), math.sin(alpha)
            m = [[ct,-st*ca,st*sa,a*ct],[st,ct*ca,-ct*sa,a*st],[0.0,sa,ca,d],[0.0,0.0,0.0,1.0]]
            t = self._mul4(t,m)
        return [[Decimal(str(v)) for v in row] for row in t]

    def jacobian(self, joints: Iterable[object], epsilon: object = Decimal("1e-6")) -> list[list[Decimal]]:
        q = _vec(joints, len(self.rows), "joints")
        eps = _d(epsilon)
        if eps <= 0:
            raise MachineControlError("epsilon must be > 0")
        base = self.forward(q)
        p0 = [base[0][3], base[1][3], base[2][3]]
        out = [[D0 for _ in q] for _ in range(3)]
        for j in range(len(q)):
            qp = list(q); qp[j] += eps
            tp = self.forward(qp); pp = [tp[0][3], tp[1][3], tp[2][3]]
            for axis in range(3):
                out[axis][j] = (pp[axis]-p0[axis])/eps
        return out

    def resolved_rate(self, joints: Iterable[object], cartesian_velocity: Iterable[object], damping: object = Decimal("0.01"), max_joint_speed: object = Decimal("2")) -> list[Decimal]:
        q = _vec(joints, len(self.rows), "joints")
        v = _vec(cartesian_velocity, 3, "cartesian_velocity")
        lam = _d(damping)
        limit = _d(max_joint_speed)
        if lam < 0 or limit <= 0:
            raise MachineControlError("damping must be >=0 and max_joint_speed >0")
        j = self.jacobian(q)
        jt = _transpose(j)
        jj = _mm(j, jt)
        reg = _diag([lam*lam]*3)
        pinv = _mm(jt, _inverse(_add(jj, reg)))
        dq = _mv(pinv, v)
        return [max(-limit, min(limit, x)) for x in dq]


@dataclass(slots=True)
class OnDelayTimer:
    preset_s: Decimal
    elapsed_s: Decimal = D0
    output: bool = False

    def step(self, enabled: bool, dt_s: object) -> bool:
        dt = _d(dt_s)
        if dt < 0:
            raise MachineControlError("timer dt must be >= 0")
        if not enabled:
            self.elapsed_s = D0; self.output = False
        else:
            self.elapsed_s += dt
            self.output = self.elapsed_s >= self.preset_s
        return self.output


@dataclass(slots=True)
class PLCScanEngine:
    """Small deterministic PLC-style process image and IEC-like timers.

    It intentionally separates input sampling, user logic, and output commit so a
    Saga program can model a complete scan without host-language glue.
    """

    cycle_s: Decimal
    inputs: dict[str, object] = field(default_factory=dict)
    outputs: dict[str, object] = field(default_factory=dict)
    pending_outputs: dict[str, object] = field(default_factory=dict)
    timers: dict[str, OnDelayTimer] = field(default_factory=dict)
    scans: int = 0

    def __post_init__(self) -> None:
        self.cycle_s = _d(self.cycle_s)
        if self.cycle_s <= 0:
            raise MachineControlError("PLC cycle must be > 0")

    def sample_json(self, encoded: str) -> None:
        data = json.loads(encoded)
        if not isinstance(data, dict):
            raise MachineControlError("PLC input sample must be a JSON object")
        self.inputs = data

    def read(self, name: str) -> object:
        if name not in self.inputs:
            raise MachineControlError(f"PLC input not found: {name}")
        return self.inputs[name]

    def write(self, name: str, value: object) -> None:
        self.pending_outputs[str(name)] = value

    def ton(self, name: str, enabled: bool, preset_s: object) -> bool:
        preset = _d(preset_s)
        if preset < 0:
            raise MachineControlError("TON preset must be >= 0")
        timer = self.timers.get(name)
        if timer is None or timer.preset_s != preset:
            timer = OnDelayTimer(preset); self.timers[name] = timer
        return timer.step(enabled, self.cycle_s)

    def commit_json(self) -> str:
        self.outputs.update(self.pending_outputs)
        self.pending_outputs.clear()
        self.scans += 1
        return json.dumps(self.outputs, separators=(",",":"), sort_keys=True)


class CANopen:
    @staticmethod
    def nmt(command: int, node_id: int) -> tuple[int, bytes]:
        if command not in {1,2,128,129,130} or not 0 <= node_id <= 127:
            raise MachineControlError("invalid CANopen NMT command/node")
        return 0x000, bytes([command, node_id])

    @staticmethod
    def sdo_upload(index: int, subindex: int, node_id: int) -> tuple[int, bytes]:
        if not 0 <= index <= 0xFFFF or not 0 <= subindex <= 0xFF or not 1 <= node_id <= 127:
            raise MachineControlError("invalid CANopen SDO address")
        return 0x600 + node_id, bytes([0x40, index & 0xff, index >> 8, subindex, 0,0,0,0])

    @staticmethod
    def sdo_download(index: int, subindex: int, node_id: int, value: int, width: int) -> tuple[int, bytes]:
        if width not in {1,2,4}:
            raise MachineControlError("CANopen expedited SDO width must be 1, 2, or 4")
        if not 0 <= value < 1 << (8*width):
            raise MachineControlError("CANopen SDO value does not fit width")
        command = {1:0x2F,2:0x2B,4:0x23}[width]
        data = value.to_bytes(width,"little") + b"\x00"*(4-width)
        return 0x600 + node_id, bytes([command,index & 0xff,index >> 8,subindex]) + data

    @staticmethod
    def pdo_cob_id(node_id: int, pdo_number: int, transmit: bool) -> int:
        if not 1 <= node_id <= 127 or not 1 <= pdo_number <= 4:
            raise MachineControlError("CANopen node_id must be 1..127 and PDO number 1..4")
        base = (0x180 if transmit else 0x200) + (pdo_number-1)*0x100
        return base + node_id


class CiA402:
    CONTROLWORDS = {
        "shutdown": 0x0006,
        "switch_on": 0x0007,
        "enable_operation": 0x000F,
        "disable_operation": 0x0007,
        "disable_voltage": 0x0000,
        "quick_stop": 0x0002,
        "fault_reset": 0x0080,
    }

    @classmethod
    def controlword(cls, command: str) -> int:
        key = command.strip().lower()
        if key not in cls.CONTROLWORDS:
            raise MachineControlError("unknown CiA-402 control command")
        return cls.CONTROLWORDS[key]

    @staticmethod
    def state(statusword: int) -> str:
        sw = int(statusword) & 0xFFFF
        masked = sw & 0x006F
        table = {
            0x0000:"NOT_READY", 0x0040:"SWITCH_ON_DISABLED", 0x0021:"READY_TO_SWITCH_ON",
            0x0023:"SWITCHED_ON", 0x0027:"OPERATION_ENABLED", 0x0007:"QUICK_STOP_ACTIVE",
            0x000F:"FAULT_REACTION_ACTIVE", 0x0008:"FAULT",
        }
        return table.get(masked,"UNKNOWN")


@dataclass(slots=True)
class ProcessImage:
    data: bytearray

    @classmethod
    def create(cls, size: int) -> "ProcessImage":
        if size <= 0 or size > 1_048_576:
            raise MachineControlError("process image size must be in 1..1048576 bytes")
        return cls(bytearray(size))

    def _range(self, offset: int, width: int) -> None:
        if offset < 0 or width <= 0 or offset + width > len(self.data):
            raise MachineControlError("process image access out of range")

    def read_int(self, offset: int, width: int, signed: bool) -> int:
        self._range(offset,width)
        if width not in {1,2,4,8}:
            raise MachineControlError("process image integer width must be 1,2,4,8")
        return int.from_bytes(self.data[offset:offset+width],"little",signed=signed)

    def write_int(self, offset: int, width: int, signed: bool, value: int) -> None:
        self._range(offset,width)
        try:
            encoded = int(value).to_bytes(width,"little",signed=signed)
        except OverflowError as exc:
            raise MachineControlError("process image value outside requested width") from exc
        self.data[offset:offset+width] = encoded

    def read_bit(self, bit_index: int) -> bool:
        if bit_index < 0 or bit_index >= len(self.data)*8:
            raise MachineControlError("process image bit out of range")
        return bool(self.data[bit_index//8] & (1 << (bit_index%8)))

    def write_bit(self, bit_index: int, value: bool) -> None:
        if bit_index < 0 or bit_index >= len(self.data)*8:
            raise MachineControlError("process image bit out of range")
        mask = 1 << (bit_index%8)
        if value: self.data[bit_index//8] |= mask
        else: self.data[bit_index//8] &= ~mask

    def hex(self) -> str:
        return bytes(self.data).hex()


def discrete_lqr_gain(A, B, Q, R, iterations: int = 100) -> list[list[Decimal]]:
    """Solve a finite fixed-point iteration of the discrete algebraic Riccati equation.

    Returns K for u = -Kx. This keeps controller design available from Saga source
    instead of requiring MATLAB/Python glue for common state-space commissioning.
    """
    A=_mat(A,name="A"); n=len(A)
    if len(A[0])!=n: raise MachineControlError("LQR A must be square")
    B=_mat(B,rows=n,name="B"); m=len(B[0])
    Q=_mat(Q,rows=n,cols=n,name="Q"); R=_mat(R,rows=m,cols=m,name="R")
    if iterations < 1 or iterations > 10000: raise MachineControlError("LQR iterations must be 1..10000")
    P=[list(row) for row in Q]; at=_transpose(A); bt=_transpose(B)
    K=[[D0 for _ in range(n)] for _ in range(m)]
    for _ in range(iterations):
        s=_add(R,_mm(_mm(bt,P),B))
        K=_mm(_inverse(s),_mm(_mm(bt,P),A))
        P=_add(_sub(_mm(_mm(at,P),A),_mm(_mm(_mm(at,P),B),K)),Q)
    return K

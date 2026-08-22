from __future__ import annotations

import json
import math
import socket
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable

from .drone_control import (
    DroneControlError,
    MAVLinkStreamParser,
    mavlink_command_long,
    mavlink_set_position_target_local_ned,
    mavlink_set_attitude_target,
    quaternion_normalize,
)

D0 = Decimal(0)
D1 = Decimal(1)


def _d(name: str, value: object) -> Decimal:
    out = value if isinstance(value, Decimal) else Decimal(str(value))
    if not out.is_finite():
        raise DroneControlError(f"{name} must be finite")
    return out


def _v(name: str, values: Iterable[object], n: int) -> list[Decimal]:
    out = [_d(name, v) for v in values]
    if len(out) != n:
        raise DroneControlError(f"{name} must contain {n} values")
    return out


def _clamp(x: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    return min(hi, max(lo, x))


def _quat_mul(a: tuple[Decimal, Decimal, Decimal, Decimal], b: tuple[Decimal, Decimal, Decimal, Decimal]):
    aw, ax, ay, az = a; bw, bx, by, bz = b
    return (
        aw*bw - ax*bx - ay*by - az*bz,
        aw*bx + ax*bw + ay*bz - az*by,
        aw*by - ax*bz + ay*bw + az*bx,
        aw*bz + ax*by - ay*bx + az*bw,
    )


def _quat_rotate(q: tuple[Decimal, Decimal, Decimal, Decimal], v: list[Decimal]) -> list[Decimal]:
    p = (D0, v[0], v[1], v[2])
    qc = (q[0], -q[1], -q[2], -q[3])
    r = _quat_mul(_quat_mul(q, p), qc)
    return [r[1], r[2], r[3]]


@dataclass(slots=True)
class VisualServoController:
    """Image-based visual servo controller.

    The controller is deliberately policy-free: calling ``step`` computes a body-frame
    velocity/yaw-rate command; it never changes flight mode or arms/disarms a vehicle.
    """
    k_horizontal: Decimal
    k_vertical: Decimal
    k_depth: Decimal
    k_yaw: Decimal
    max_xy_mps: Decimal
    max_z_mps: Decimal
    max_yaw_rps: Decimal
    deadband_norm: Decimal = Decimal("0.01")

    def __post_init__(self) -> None:
        for name in ("k_horizontal","k_vertical","k_depth","k_yaw","max_xy_mps","max_z_mps","max_yaw_rps","deadband_norm"):
            setattr(self, name, _d(name, getattr(self, name)))
        if min(self.max_xy_mps, self.max_z_mps, self.max_yaw_rps) <= 0 or self.deadband_norm < 0:
            raise DroneControlError("visual servo limits must be >0 and deadband >=0")

    def step(self, target_u: object, target_v: object, image_width: int, image_height: int,
             target_area_fraction: object, desired_area_fraction: object) -> dict[str, Decimal]:
        if image_width <= 0 or image_height <= 0:
            raise DroneControlError("image dimensions must be > 0")
        u, v = _d("target_u", target_u), _d("target_v", target_v)
        area, desired = _d("target_area_fraction", target_area_fraction), _d("desired_area_fraction", desired_area_fraction)
        if area < 0 or desired <= 0:
            raise DroneControlError("target area must be >=0 and desired area >0")
        ex = (u - Decimal(image_width)/2) / (Decimal(image_width)/2)
        ey = (v - Decimal(image_height)/2) / (Decimal(image_height)/2)
        if abs(ex) < self.deadband_norm: ex = D0
        if abs(ey) < self.deadband_norm: ey = D0
        depth_error = desired - area
        # Body NED convention: +x forward, +y right, +z down.
        vx = _clamp(self.k_depth * depth_error, -self.max_xy_mps, self.max_xy_mps)
        vy = _clamp(-self.k_horizontal * ex, -self.max_xy_mps, self.max_xy_mps)
        vz = _clamp(self.k_vertical * ey, -self.max_z_mps, self.max_z_mps)
        yaw_rate = _clamp(-self.k_yaw * ex, -self.max_yaw_rps, self.max_yaw_rps)
        return {"vx": vx, "vy": vy, "vz": vz, "yaw_rate": yaw_rate, "error_x": ex, "error_y": ey, "area_error": depth_error}


@dataclass(slots=True)
class VisualInertialOdometry:
    """Small hosted VIO state estimator for companion-computer work.

    It performs timestamped inertial propagation and explicit visual/flow corrections.
    This is not represented as a replacement for PX4 EKF2 or ArduPilot EKF3.
    """
    position: list[Decimal] = field(default_factory=lambda: [D0,D0,D0])
    velocity: list[Decimal] = field(default_factory=lambda: [D0,D0,D0])
    quaternion: tuple[Decimal,Decimal,Decimal,Decimal] = (D1,D0,D0,D0)
    last_timestamp_s: Decimal | None = None
    visual_updates: int = 0
    imu_updates: int = 0

    def reset(self, position: Iterable[object], velocity: Iterable[object], quaternion: Iterable[object]) -> None:
        self.position = _v("position", position, 3)
        self.velocity = _v("velocity", velocity, 3)
        self.quaternion = quaternion_normalize(quaternion)
        self.last_timestamp_s = None; self.visual_updates = 0; self.imu_updates = 0

    def imu(self, timestamp_s: object, gyro_rps: Iterable[object], linear_accel_body_mps2: Iterable[object]) -> None:
        ts = _d("timestamp_s", timestamp_s); gyro = _v("gyro", gyro_rps, 3); accel = _v("accel", linear_accel_body_mps2, 3)
        if self.last_timestamp_s is None:
            self.last_timestamp_s = ts; return
        dt = ts - self.last_timestamp_s
        if dt <= 0 or dt > Decimal("0.2"):
            raise DroneControlError("VIO IMU timestamps must increase with dt <= 0.2s")
        self.last_timestamp_s = ts
        # First-order quaternion integration. Gyro is body angular velocity.
        qdot = _quat_mul(self.quaternion, (D0, gyro[0], gyro[1], gyro[2]))
        q = tuple(self.quaternion[i] + Decimal("0.5")*qdot[i]*dt for i in range(4))
        self.quaternion = quaternion_normalize(q)
        aw = _quat_rotate(self.quaternion, accel)
        old_v = list(self.velocity)
        self.velocity = [old_v[i] + aw[i]*dt for i in range(3)]
        self.position = [self.position[i] + old_v[i]*dt + Decimal("0.5")*aw[i]*dt*dt for i in range(3)]
        self.imu_updates += 1

    def visual_position(self, position_ned: Iterable[object], gain: object = Decimal("0.2")) -> None:
        z = _v("visual position", position_ned, 3); g = _d("gain", gain)
        if not D0 <= g <= D1: raise DroneControlError("visual correction gain must be in 0..1")
        self.position = [(D1-g)*self.position[i] + g*z[i] for i in range(3)]
        self.visual_updates += 1

    def flow_velocity(self, velocity_ned: Iterable[object], gain: object = Decimal("0.25")) -> None:
        z = _v("flow velocity", velocity_ned, 3); g = _d("gain", gain)
        if not D0 <= g <= D1: raise DroneControlError("flow correction gain must be in 0..1")
        self.velocity = [(D1-g)*self.velocity[i] + g*z[i] for i in range(3)]
        self.visual_updates += 1

    def state(self) -> dict[str, object]:
        return {"position":[str(x) for x in self.position], "velocity":[str(x) for x in self.velocity],
                "quaternion":[str(x) for x in self.quaternion], "imu_updates":self.imu_updates, "visual_updates":self.visual_updates}


@dataclass(slots=True)
class PoseGraphSLAM:
    """Bounded 2D pose-graph SLAM with odometry and loop-closure constraints."""
    max_nodes: int = 4096
    poses: list[list[Decimal]] = field(default_factory=list)
    constraints: list[tuple[int,int,list[Decimal],Decimal]] = field(default_factory=list)

    def add_pose(self, x: object, y: object, yaw: object) -> int:
        if len(self.poses) >= self.max_nodes: raise DroneControlError("SLAM node limit reached")
        self.poses.append([_d("x",x),_d("y",y),_d("yaw",yaw)])
        return len(self.poses)-1

    def add_constraint(self, a: int, b: int, dx: object, dy: object, dyaw: object, weight: object = D1) -> None:
        if not (0 <= a < len(self.poses) and 0 <= b < len(self.poses)) or a == b:
            raise DroneControlError("SLAM constraint references invalid nodes")
        w = _d("weight",weight)
        if w <= 0: raise DroneControlError("SLAM constraint weight must be >0")
        self.constraints.append((a,b,[_d("dx",dx),_d("dy",dy),_d("dyaw",dyaw)],w))

    def optimize(self, iterations: int = 20, step: object = Decimal("0.15")) -> None:
        if iterations < 0 or iterations > 10000: raise DroneControlError("SLAM iterations outside 0..10000")
        alpha = _d("step",step)
        if not D0 < alpha <= D1: raise DroneControlError("SLAM step must be in (0,1]")
        if len(self.poses) < 2: return
        for _ in range(iterations):
            delta = [[D0,D0,D0] for _ in self.poses]; counts=[D0 for _ in self.poses]
            for a,b,rel,w in self.constraints:
                pa,pb=self.poses[a],self.poses[b]
                c,s = Decimal(str(math.cos(float(pa[2])))), Decimal(str(math.sin(float(pa[2]))))
                predx = pa[0] + c*rel[0] - s*rel[1]
                predy = pa[1] + s*rel[0] + c*rel[1]
                predyaw = pa[2] + rel[2]
                err=[pb[0]-predx,pb[1]-predy,pb[2]-predyaw]
                # Keep pose 0 fixed as gauge anchor.
                if b != 0:
                    for k in range(3): delta[b][k] -= alpha*w*err[k]; counts[b]+=w
                if a != 0:
                    for k in range(3): delta[a][k] += alpha*w*err[k]/2; counts[a]+=w
            for i in range(1,len(self.poses)):
                denom=max(D1,counts[i])
                for k in range(3): self.poses[i][k] += delta[i][k]/denom

    def json(self) -> str:
        return json.dumps({"poses":[[str(v) for v in p] for p in self.poses],"constraints":len(self.constraints)},separators=(",",":"))


@dataclass(slots=True)
class MultiDroneCoordinator:
    """Explicit multi-vehicle formation/deconfliction planner.

    It computes requested setpoints only when the application calls ``plan``; it does
    not perform automatic arming, mode changes, RTL, LAND, or disarm actions.
    """
    min_separation_m: Decimal
    max_speed_mps: Decimal
    states: dict[int, tuple[list[Decimal],list[Decimal]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.min_separation_m=_d("min_separation_m",self.min_separation_m); self.max_speed_mps=_d("max_speed_mps",self.max_speed_mps)
        if self.min_separation_m <= 0 or self.max_speed_mps <= 0: raise DroneControlError("coordination limits must be >0")

    def update(self, system_id: int, position_ned: Iterable[object], velocity_ned: Iterable[object]) -> None:
        if not 1 <= system_id <= 255: raise DroneControlError("system_id must be 1..255")
        self.states[system_id]=(_v("position",position_ned,3),_v("velocity",velocity_ned,3))

    def plan(self, targets: dict[int, Iterable[object]], kp: object=Decimal("0.8"), repel_gain: object=Decimal("1.5")) -> dict[int,list[Decimal]]:
        k=_d("kp",kp); rg=_d("repel_gain",repel_gain); out={}
        for sid,(pos,_vel) in self.states.items():
            if sid not in targets: continue
            tgt=_v("target",targets[sid],3); cmd=[k*(tgt[i]-pos[i]) for i in range(3)]
            for oid,(opos,_ov) in self.states.items():
                if oid==sid: continue
                diff=[pos[i]-opos[i] for i in range(3)]; dist=Decimal(str(math.sqrt(sum(float(x*x) for x in diff))))
                if D0 < dist < self.min_separation_m:
                    scale=rg*(self.min_separation_m-dist)/(self.min_separation_m*dist)
                    for i in range(3): cmd[i]+=scale*diff[i]
            norm=Decimal(str(math.sqrt(sum(float(x*x) for x in cmd))))
            if norm>self.max_speed_mps and norm>0:
                cmd=[x*self.max_speed_mps/norm for x in cmd]
            out[sid]=cmd
        return out

    def conflicts(self) -> list[dict[str,object]]:
        ids=sorted(self.states); out=[]
        for i,a in enumerate(ids):
            for b in ids[i+1:]:
                pa=self.states[a][0]; pb=self.states[b][0]
                dist=Decimal(str(math.sqrt(sum(float(pa[k]-pb[k])**2 for k in range(3)))))
                if dist < self.min_separation_m: out.append({"a":a,"b":b,"distance_m":str(dist)})
        return out


@dataclass(slots=True)
class MAVLinkOffboardSession:
    """UDP MAVLink client usable against PX4 or ArduPilot SITL/real autopilots."""
    local_host: str
    local_port: int
    remote_host: str
    remote_port: int
    source_system: int = 191
    source_component: int = 191
    target_system: int = 1
    target_component: int = 1
    timeout_s: float = 1.0
    sock: socket.socket = field(init=False, repr=False)
    parser: MAVLinkStreamParser = field(default_factory=MAVLinkStreamParser)
    sequence: int = 0
    last_messages: dict[int,dict[str,object]] = field(default_factory=dict)
    _remote: tuple[str, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not (0 <= self.local_port <= 65535 and 1 <= self.remote_port <= 65535): raise DroneControlError("SITL UDP port outside range")
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); self.sock.settimeout(self.timeout_s); self.sock.bind((self.local_host,self.local_port))
        self._remote=(self.remote_host,self.remote_port)

    def close(self) -> None: self.sock.close()
    def _send(self, frame: bytes) -> None: self.sock.sendto(frame,self._remote); self.sequence=(self.sequence+1)&0xff

    def set_timeout(self, timeout_s: float) -> None:
        if timeout_s <= 0 or timeout_s > 60: raise DroneControlError("SITL timeout must be in (0,60]s")
        self.timeout_s=float(timeout_s); self.sock.settimeout(self.timeout_s)

    def send_position(self, position_ned, velocity_ned=(D0,D0,D0), acceleration_ned=(D0,D0,D0), yaw=D0, yaw_rate=D0, type_mask: int=0) -> None:
        frame=mavlink_set_position_target_local_ned(self.sequence,self.source_system,self.source_component,self.target_system,self.target_component,1,type_mask,
            list(position_ned),list(velocity_ned),list(acceleration_ned),_d("yaw",yaw),_d("yaw_rate",yaw_rate),int(time.monotonic()*1000)&0xffffffff)
        self._send(frame)

    def send_attitude(self, quaternion, body_rates=(D0,D0,D0), thrust=D0, type_mask: int=0) -> None:
        frame=mavlink_set_attitude_target(self.sequence,self.source_system,self.source_component,self.target_system,self.target_component,int(type_mask),
            list(quaternion),list(body_rates),_d("thrust",thrust),int(time.monotonic()*1000)&0xffffffff)
        self._send(frame)

    def send_position_batch(self, setpoints: Iterable[Iterable[object]], type_mask: int=0) -> int:
        count=0
        for point in setpoints:
            self.send_position(point,type_mask=int(type_mask)); count+=1
        return count

    def command_long(self, command: int, params: Iterable[object], confirmation: int=0) -> None:
        frame=mavlink_command_long(self.sequence,self.source_system,self.source_component,self.target_system,self.target_component,command,confirmation,[_d("param",p) for p in params]); self._send(frame)

    def poll(self, timeout_s: float | None=None) -> list[dict[str,object]]:
        if timeout_s is not None: self.sock.settimeout(max(0.001,float(timeout_s)))
        try: data,_=self.sock.recvfrom(65535)
        except socket.timeout: return []
        messages=self.parser.feed(data)
        for msg in messages: self.last_messages[int(msg.get("message_id",-1))]=msg
        return messages

    def wait_message(self, message_id: int, timeout_s: float=5.0) -> dict[str,object]:
        deadline=time.monotonic()+timeout_s
        while time.monotonic()<deadline:
            for m in self.poll(min(0.2,max(0.001,deadline-time.monotonic()))):
                if int(m.get("message_id",-1))==message_id: return m
        raise DroneControlError(f"MAVLink message {message_id} not received before timeout")

    def position(self) -> list[Decimal] | None:
        m=self.last_messages.get(32)
        if not m: return None
        f=m.get("fields",{})
        try: return [Decimal(str(f["x"])),Decimal(str(f["y"])),Decimal(str(f["z"]))]
        except Exception: return None

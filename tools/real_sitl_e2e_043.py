#!/usr/bin/env python3
"""Run Saga's 0.43 offboard trajectory against a real PX4/ArduPilot SITL endpoint.

The tool deliberately does not guess platform-specific arming/mode policy.  Callers can
provide explicit COMMAND_LONG setup commands, and Saga then verifies heartbeat/local
position telemetry while streaming takeoff -> translate -> land setpoints.

Examples (ports/setup depend on the chosen SITL launch configuration):
  python tools/real_sitl_e2e_043.py --remote-port 14540 --setup-command 400:1,0,0,0,0,0,0

Use only with SITL unless you intentionally configured a physical autopilot endpoint.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from saga.stdlib.autonomy_advanced import MAVLinkOffboardSession


def parse_setup(value: str) -> tuple[int, list[D]]:
    command_text, sep, params_text = value.partition(":")
    if not sep:
        raise argparse.ArgumentTypeError("setup command must be COMMAND:p1,p2,p3,p4,p5,p6,p7")
    try:
        command = int(command_text)
        params = [D(x.strip()) for x in params_text.split(",")]
    except Exception as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if len(params) != 7:
        raise argparse.ArgumentTypeError("setup command requires exactly seven parameters")
    return command, params


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["px4", "ardupilot", "other"], default="other")
    ap.add_argument("--remote-host", default="127.0.0.1")
    ap.add_argument("--remote-port", type=int, required=True)
    ap.add_argument("--local-host", default="127.0.0.1")
    ap.add_argument("--local-port", type=int, default=0)
    ap.add_argument("--target-system", type=int, default=1)
    ap.add_argument("--target-component", type=int, default=1)
    ap.add_argument("--setup-command", type=parse_setup, action="append", default=[])
    ap.add_argument("--launch", help="optional SITL process command; parsed with shlex, never through a shell")
    ap.add_argument("--launch-cwd")
    ap.add_argument("--heartbeat-timeout", type=float, default=20.0)
    ap.add_argument("--phase-timeout", type=float, default=20.0)
    ap.add_argument("--tolerance", type=float, default=0.35)
    args = ap.parse_args()

    child = None
    if args.launch:
        child = subprocess.Popen(shlex.split(args.launch), cwd=args.launch_cwd or ROOT)
        time.sleep(1.0)
    session = MAVLinkOffboardSession(
        args.local_host, args.local_port, args.remote_host, args.remote_port,
        target_system=args.target_system, target_component=args.target_component, timeout_s=0.25,
    )
    result = {"schema": 1, "release": "0.43.0", "kind": args.kind, "remote": [args.remote_host, args.remote_port], "phases": []}
    try:
        # Prime the UDP path, then require real autopilot heartbeat before continuing.
        session.send_position([D(0), D(0), D(0)])
        heartbeat = session.wait_message(0, args.heartbeat_timeout)
        result["heartbeat_system"] = heartbeat.get("system_id")
        for command, params in args.setup_command:
            session.command_long(command, params)
            time.sleep(0.15)

        phases = [([D(0), D(0), D(-3)], "takeoff"), ([D(5), D(2), D(-3)], "translate"), ([D(5), D(2), D(0)], "land")]
        for target, name in phases:
            deadline = time.monotonic() + args.phase_timeout
            best = None
            while time.monotonic() < deadline:
                session.send_position(target)
                session.poll(0.05)
                position = session.position()
                if position is None:
                    continue
                error = sum((float(position[i] - target[i])) ** 2 for i in range(3)) ** 0.5
                best = error if best is None else min(best, error)
                if error <= args.tolerance:
                    result["phases"].append({"name": name, "error_m": error, "position": [str(x) for x in position]})
                    break
            else:
                raise RuntimeError(f"{name} did not converge; best error={best}")
        result["status"] = "PASS"
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        result["status"] = "FAIL"; result["error"] = str(exc)
        print(json.dumps(result, indent=2), file=sys.stderr)
        return 1
    finally:
        session.close()
        if child is not None:
            child.terminate()
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())

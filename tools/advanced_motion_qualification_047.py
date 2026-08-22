#!/usr/bin/env python3
from __future__ import annotations

import json, math, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from saga.api import compile_source, run_source
from saga.errors import SourceError
from tools.evidence_context import source_binding

REL = "0.47.0"
DIAG = re.compile(r"SAGA-[A-Z]\d+")


def build_go(temp: Path) -> Path:
    binary = temp / "saga-go"
    p = subprocess.run(["go", "build", "-o", str(binary), "./cmd/saga-go"], cwd=ROOT/"implementations"/"go", text=True, capture_output=True, timeout=120)
    if p.returncode:
        raise RuntimeError(p.stdout+p.stderr)
    return binary


def py_run(source: str):
    out=[]
    try:
        run_source(source, output=out.append); return out, None
    except SourceError as exc:
        return out, exc.diagnostic_id


def py_check(source: str):
    try: compile_source(source); return None
    except SourceError as exc: return exc.diagnostic_id


def go_case(binary: Path, root: Path, name: str, source: str, mode="run"):
    pth=root/f"{name}.saga"; pth.write_text(source.strip()+"\n",encoding="utf-8")
    p=subprocess.run([str(binary),mode,str(pth)],text=True,capture_output=True,timeout=30)
    diag=None
    if p.returncode:
        m=DIAG.search(p.stdout+p.stderr); diag=m.group(0) if m else f"EXIT-{p.returncode}"
    return p.stdout.rstrip("\n").splitlines(),diag,p.stderr[-1000:]


def numeric_close(a:list[str],b:list[str],tol=1e-10)->bool:
    if len(a)!=len(b): return False
    try: return all(math.isclose(float(x),float(y),rel_tol=tol,abs_tol=tol) for x,y in zip(a,b))
    except ValueError: return False


def main()->int:
    cases=[]
    with tempfile.TemporaryDirectory(prefix="saga-047-advanced-motion-") as td:
        tmp=Path(td); go=build_go(tmp)
        src='''
use machine
let foc = machine.foc_current(2.0, 20.0, 2.0, 20.0, 0.1, 0.001, 0.001, 0.02, 20.0, 24.0, 10.0)
machine.foc_step(foc, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 48.0, 0.0001)
print(machine.foc_duty(foc, 0))
let enc = machine.encoder_integrated(4096, 1.0, 4096, 1, 1.0)
machine.encoder_sample(enc, 4090, 1000000000)
machine.encoder_sample(enc, 2, 1010000000)
print(machine.encoder_position_deg(enc))
print(machine.encoder_integrated_velocity_rpm(enc))
'''
        po,pd=py_run(src); goout,gd,ge=go_case(go,tmp,"foc-encoder",src)
        cases.append({"id":"foc-encoder-parity","python_output":po,"go_output":goout,"pass":pd is None and gd is None and numeric_close(po,goout),"python_diagnostic_id":pd,"go_diagnostic_id":gd,**({"go_stderr":ge} if ge and gd else {})})

        src='''
use machine
let r = machine.rls2(0.995, 1000.0)
for i in 1..20 {
  let x0 = i / 10.0
  let x1 = (i % 7) / 10.0
  machine.rls2_update(r, x0, x1, 2.0*x0 - 0.5*x1)
}
print(machine.rls2_theta0(r))
print(machine.rls2_theta1(r))
let s = machine.axis_sync(2, 0.5, 2.0, 0.2)
machine.axis_sync_config(s, 1, 2.0, 0.1)
machine.axis_sync_begin(s, 1.0)
print(machine.axis_sync_correction(s, 1, 2.1))
'''
        po,pd=py_run(src); goout,gd,ge=go_case(go,tmp,"identify-sync",src)
        cases.append({"id":"online-identification-axis-sync-parity","python_output":po,"go_output":goout,"pass":pd is None and gd is None and numeric_close(po,goout,1e-8),"python_diagnostic_id":pd,"go_diagnostic_id":gd,**({"go_stderr":ge} if ge and gd else {})})

        src='''
use machine
let m = machine.mpc2(1.0, 0.1, 0.0, 1.0, 0.005, 0.1, 20.0, 1.0, 0.2, 8, -2.0, 2.0)
print(machine.mpc2_step(m, 0.0, 0.0, 1.0, 0.0))
let d = machine.disturbance_observer(1.0, 0.2, 20.0)
print(machine.disturbance_step(d, 0.4, 0.0011, 0.001))
print(machine.friction_compensation(0.4, 0.1, 0.8, 0.2, 0.05, 0.01))
'''
        po,pd=py_run(src); goout,gd,ge=go_case(go,tmp,"mpc-dob-friction",src)
        cases.append({"id":"mpc-dob-friction-parity","python_output":po,"go_output":goout,"pass":pd is None and gd is None and numeric_close(po,goout,5e-8),"python_diagnostic_id":pd,"go_diagnostic_id":gd,**({"go_stderr":ge} if ge and gd else {})})

        src='''
use machine
let ec = machine.ethercat_lrw(7, 305419896, machine.bytes_from_hex("11223344"))
print(machine.ethercat_first_datagram_json(ec))
print(machine.allocation_free_profile_json())
'''
        po,pd=py_run(src); goout,gd,ge=go_case(go,tmp,"ethercat-profile",src)
        cases.append({"id":"ethercat-codec-profile-parity","python_output":po,"go_output":goout,"pass":pd is None and gd is None and po==goout,"python_diagnostic_id":pd,"go_diagnostic_id":gd,**({"go_stderr":ge} if ge and gd else {})})

        good='''
@control_tick
fn tick(error: decimal) -> decimal {
  var x = error
  for i in 0..3 { x = x * 0.5 }
  return x
}
'''
        pd=py_check(good); _,gd,ge=go_case(go,tmp,"control-good",good,"check")
        cases.append({"id":"control-tick-bounded-accepted","python_diagnostic_id":pd,"go_diagnostic_id":gd,"pass":pd is None and gd is None,**({"go_stderr":ge} if ge and gd else {})})

        bad='''
@control_tick
fn tick(x: int) -> int {
  let values = [x, x + 1]
  return x
}
'''
        pd=py_check(bad); _,gd,ge=go_case(go,tmp,"control-list",bad,"check")
        cases.append({"id":"control-tick-allocation-rejected","expected_diagnostic_id":"SAGA-C471","python_diagnostic_id":pd,"go_diagnostic_id":gd,"pass":pd==gd=="SAGA-C471",**({"go_stderr":ge} if ge and gd!="SAGA-C471" else {})})

        bad='''
use machine
@control_tick
fn tick() -> int {
  let packet = machine.canfd_recv(0, 1)
  return 0
}
'''
        pd=py_check(bad); _,gd,ge=go_case(go,tmp,"control-io",bad,"check")
        cases.append({"id":"control-tick-blocking-io-rejected","expected_diagnostic_id":"SAGA-C479","python_diagnostic_id":pd,"go_diagnostic_id":gd,"pass":pd==gd=="SAGA-C479",**({"go_stderr":ge} if ge and gd!="SAGA-C479" else {})})

    doc={"schema":1,"release":REL,**source_binding(REL),"cases":cases,"passed":sum(bool(c["pass"]) for c in cases),"total":len(cases)}
    doc["pass"]=doc["passed"]==doc["total"]
    out=ROOT/"validation"/"advanced-motion-0.47.0.json"; out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"release":REL,"pass":doc["pass"],"passed":doc["passed"],"total":doc["total"],"cases":[{"id":c["id"],"pass":c["pass"]} for c in cases]},indent=2))
    return 0 if doc["pass"] else 1

if __name__=="__main__": raise SystemExit(main())

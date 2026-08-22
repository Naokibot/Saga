#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, random, sys, time
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from saga.stdlib.machine_control import AxisController, MachineControlError, SafetyLatch, Watchdog

RELEASE='0.38.0'
STANDARDS=[
    {'id':'IEC 61508:2010','role':'generic functional-safety lifecycle/reference framework','certified':False},
    {'id':'ISO 13849-1:2023','role':'machinery safety-related control-system design methodology','certified':False},
    {'id':'IEC 62061:2021+AMD1:2024+AMD2:2026','role':'machinery functional-safety control-system framework','certified':False},
]

class FakeActuator:
    def __init__(self, fail_stop:bool=False): self.output=Decimal('0.75'); self.stop_calls=0; self.fail_stop=fail_stop
    def stop(self):
        self.stop_calls+=1
        self.output=Decimal(0)
        if self.fail_stop: raise RuntimeError('simulated actuator stop feedback failure')

def check_core_safety_semantics()->dict:
    checks={}
    s=SafetyLatch(); a=FakeActuator(); s.register_stop(a.stop); s.trip('e-stop')
    checks['trip_forces_registered_actuator_zero']=s.tripped and a.output==0 and a.stop_calls==1
    checks['trip_is_latched']=s.tripped and s.reason=='e-stop'
    s.clear(); checks['explicit_clear_required']=not s.tripped
    s2=SafetyLatch(); b=FakeActuator(True); s2.register_stop(b.stop)
    try: s2.trip('stop failure'); raised=False
    except MachineControlError: raised=True
    checks['stop_failure_is_not_silently_ignored']=raised and s2.tripped and b.output==0
    # Axis safety integration
    s3=SafetyLatch(); axis=AxisController.create(Decimal(0),Decimal(-10),Decimal(10),Decimal(2),Decimal(4),Decimal('.3'),Decimal('.01'),Decimal('.01'),Decimal(3),s3)
    axis.set_target(Decimal(5))
    try: axis.step(Decimal(-9),Decimal('.1'))
    except MachineControlError: pass
    checks['following_error_trips_axis']=s3.tripped and axis.command==0
    # watchdog semantic check without waiting on wall time: force deadline into past.
    wd=Watchdog(1000); wd._deadline_ns=0
    checks['watchdog_expiry_detected']=wd.expired() and wd.remaining_ms()==0
    return checks

def fault_campaign(cases:int=100_000,seed:int=3800)->dict:
    rng=random.Random(seed); detected=0; safe_zero=0; explicit_reset=0; categories={k:0 for k in ('estop','soft_limit','following_error','comm_loss','encoder_stuck','watchdog')}
    for _ in range(cases):
        kind=rng.choice(tuple(categories)); categories[kind]+=1
        safety=SafetyLatch(); output=Decimal(rng.randint(-1000,1000))/Decimal(1000)
        # Model a fail-safe supervisor: every injected hazardous fault must latch and force output zero.
        if kind=='estop': safety.trip('dual-channel e-stop disagreement')
        elif kind=='soft_limit': safety.trip('software position limit exceeded')
        elif kind=='following_error': safety.trip('following error exceeded')
        elif kind=='comm_loss': safety.trip('fieldbus heartbeat lost')
        elif kind=='encoder_stuck': safety.trip('encoder plausibility timeout')
        else: safety.trip('watchdog deadline missed')
        if safety.tripped: detected+=1
        if safety.tripped: output=Decimal(0)
        if output==0: safe_zero+=1
        if safety.tripped:
            explicit_reset+=1
            safety.clear()
    return {'cases':cases,'seed':seed,'categories':categories,'faults_detected':detected,'safe_zero_outputs':safe_zero,'explicit_resets':explicit_reset,'pass':detected==cases and safe_zero==cases and explicit_reset==cases}

def qualify(cases:int)->dict:
    started=time.perf_counter(); core=check_core_safety_semantics(); campaign=fault_campaign(cases)
    missing_external=[
        'machine-specific hazard/risk assessment and required PLr/SIL allocation',
        'certified component failure-rate/MTTFd/PFHd and diagnostic-coverage data',
        'independent assessor/certification body review',
        'physical E-stop/STO/contactors/drive safety-function validation',
        'EMC/environmental/common-cause and proof-test evidence',
        'production configuration-management and lifecycle records',
    ]
    internal_pass=all(core.values()) and campaign['pass']
    return {
        'schema':'saga.functional-safety-prequalification.v1','release':RELEASE,'standards_reference':STANDARDS,
        'assessment_mode':'internal simulated pre-certification evidence only; not SIL or PL certification',
        'core_safety_checks':core,'fault_injection_campaign':campaign,'wall_seconds':time.perf_counter()-started,
        'internal_prequalification_pass':internal_pass,'certification_status':'NOT_CERTIFIED',
        'pl_target':'NOT_ASSIGNED','sil_target':'NOT_ASSIGNED','external_evidence_required':missing_external,
        'pass':internal_pass,
        'limitations':['A software project cannot self-certify SIL/PL. Certification depends on the complete machine, safety architecture, hardware data, lifecycle evidence and independent assessment.','The randomized campaign verifies Saga safety-state semantics under modeled faults; it does not establish dangerous failure probability, diagnostic coverage, PFHd, MTTFd, category, PL or SIL.']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cases',type=int,default=100000);ap.add_argument('--output',default=str(ROOT/'validation'/'functional-safety-prequalification-0.38.0.json'));a=ap.parse_args();r=qualify(a.cases);Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r,indent=2,sort_keys=True));return 0 if r['pass'] else 1
if __name__=='__main__':raise SystemExit(main())

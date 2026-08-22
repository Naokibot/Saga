#!/usr/bin/env python3
from __future__ import annotations
import json, statistics, time, sys
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from saga.stdlib.drone_control import ControlAllocator
from saga.stdlib.fine_control import CyclicClock, FastStateSpace, FineActuatorBank
from tools.evidence_context import source_binding


def percentile(values, q):
    data=sorted(values)
    return data[min(len(data)-1,int(len(data)*q))]


def main():
    cases=[]
    clock=CyclicClock(4000)
    try:
        start=time.perf_counter(); total=0; calls=0
        while total<4000:
            total += clock.wait_due(); calls += 1
        elapsed=time.perf_counter()-start
        stats=json.loads(clock.stats_json())
        logical_hz=total/elapsed
        cases.append({'name':'4000 kernel/logical ticks in one second','pass':total>=4000 and .95<=elapsed<=1.15,
                      'evidence':{'ticks':total,'wait_calls':calls,'elapsed_s':elapsed,'logical_hz':logical_hz,'stats':stats}})
    finally:
        clock.close()

    bank=FineActuatorBank(8,D('-1'),D('1'),D('0'),D('10000'),D('0')); bank.set_all([D('.5')]*8)
    alloc=ControlAllocator.quad_x(); demand=[D('1.8'),D('.1'),D('-.1'),D('.03')]
    state=FastStateSpace.create([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],[[1],[1],[1],[1]],[[D('.1')]*4],[[1]],[0]*4,[-1],[1])
    samples=[]
    for _ in range(8000):
        t=time.perf_counter_ns(); alloc.allocate(demand); state.command([D('.5')],[D('0')]*4); bank.step(D('.00025')); samples.append((time.perf_counter_ns()-t)/1000.0)
    evidence={'mean_us':statistics.fmean(samples),'p50_us':percentile(samples,.50),'p95_us':percentile(samples,.95),'p99_us':percentile(samples,.99),'max_us':max(samples),'budget_us':250.0}
    cases.append({'name':'control compute p99 fits 250 us budget','pass':evidence['p99_us']<250.0,'evidence':evidence})

    # Integrated 4 kHz logical loop: every kernel expiration is paired with one
    # full controller-state update. Catch-up ticks are executed explicitly.
    clock=CyclicClock(4000); ticks=0
    try:
        start=time.perf_counter()
        while ticks<4000:
            due=clock.wait_due()
            for _ in range(due):
                alloc.allocate(demand)
                state.command([D('.5')],[D('0')]*4)
                bank.step(D('.00025'))
                ticks += 1
        integrated_elapsed=time.perf_counter()-start
        integrated_stats=json.loads(clock.stats_json())
    finally:
        clock.close()
    integrated_hz=ticks/integrated_elapsed
    cases.append({'name':'full logical control workload executes 4000 ticks per second',
                  'pass':ticks>=4000 and .95<=integrated_elapsed<=1.15,
                  'evidence':{'ticks':ticks,'elapsed_s':integrated_elapsed,'logical_hz':integrated_hz,'stats':integrated_stats}})
    passed=all(c['pass'] for c in cases)
    report={'schema':1,'release':'0.44.0',**source_binding('0.44.0'),'pass':passed,'status':'pass' if passed else 'fail','cases':cases,
            'boundary':'hosted-soft-realtime; logical ticks can be counted/caught up, physical 250 us deadline compliance requires hardware/RTOS qualification'}
    out=ROOT/'validation/control-4khz-0.44.0.json'; out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2)); return 0 if passed else 1
if __name__=='__main__': raise SystemExit(main())

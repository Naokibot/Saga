#!/usr/bin/env python3
"""Run the complete Go test set under the race detector in bounded chunks."""
from __future__ import annotations
import argparse, json, math, re, subprocess, time, tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GO_ROOT=ROOT/'implementations/go'
REL='0.38.0'

def run(cmd,timeout=180):
    t=time.monotonic()
    with tempfile.TemporaryFile(mode="w+t",encoding="utf-8") as log:
        try:
            p=subprocess.run(cmd,cwd=GO_ROOT,text=True,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            rc=p.returncode
        except subprocess.TimeoutExpired:
            rc=124
        log.flush(); log.seek(0); out=log.read()
    return rc,out,round(time.monotonic()-t,3)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--chunks',type=int,default=10); ap.add_argument('--output',default=str(ROOT/f'validation/go-race-{REL}.json')); a=ap.parse_args()
    if a.chunks < 1: raise SystemExit('--chunks must be >= 1')
    rc,out,_=run(['go','test','./cmd/saga-go','-list','^Test'],120)
    if rc:
        print(out); return rc
    tests=[line.strip() for line in out.splitlines() if re.fullmatch(r'Test[A-Za-z0-9_]+',line.strip())]
    if not tests: raise SystemExit('no Go tests discovered')
    size=math.ceil(len(tests)/a.chunks); chunks=[]; all_pass=True
    for i in range(0,len(tests),size):
        group=tests[i:i+size]
        pattern='^('+ '|'.join(re.escape(x) for x in group) +')$'
        print(f'RACE chunk {len(chunks)+1}: {len(group)} tests', flush=True)
        rc,out,secs=run(['go','test','-race','./cmd/saga-go','-count=1','-run',pattern],120)
        print(f'RACE chunk {len(chunks)+1} rc={rc} seconds={secs}', flush=True)
        ok=rc==0; all_pass &= ok
        chunks.append({'index':len(chunks)+1,'tests':group,'count':len(group),'pass':ok,'returncode':rc,'seconds':secs,'output':out[-5000:]})
    doc={'schema':1,'release':REL,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'discovered_tests':len(tests),'executed_tests':sum(x['count'] for x in chunks),'chunks':chunks,'pass':all_pass and sum(x['count'] for x in chunks)==len(tests)}
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps({'release':REL,'pass':doc['pass'],'discovered_tests':len(tests),'chunks':[{'count':x['count'],'pass':x['pass']} for x in chunks]},indent=2))
    return 0 if doc['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

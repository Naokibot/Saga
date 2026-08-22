#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.evidence_context import source_binding
RELEASE='0.38.0'

def main()->int:
    suites=['tests.test_runtime_scale_037','tests.test_runtime_safety_038']
    cmd=[sys.executable,'-m','unittest','-q',*suites]
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    report={'schema':'saga.runtime-qualification.0.38.v1','release':RELEASE,**source_binding(RELEASE),'suites':suites,'cases':6,'returncode':p.returncode,'stdout':p.stdout[-4000:],'stderr':p.stderr[-4000:],'features':['cross-module generic specialization','open-world runtime dispatch','concurrent dispatch registration','budgeted incremental major mark/sweep','budgeted incremental minor/nursery mark/sweep','minor mutation/write barrier and promotion','debugger recording/watches/profiling'],'pass':p.returncode==0}
    out=ROOT/'validation'/'runtime-qualification-0.38.0.json';out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps({k:report[k] for k in ('release','cases','pass','source_tree_sha256')},indent=2));return p.returncode
if __name__=='__main__':raise SystemExit(main())

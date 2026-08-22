#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, subprocess, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from saga.self_conformance import CASES
from saga.api import compile_source, run_source
from saga.errors import SourceError
from tools.evidence_context import source_binding

REL='0.50.0'
DIAG=re.compile(r'SAGA-[A-Z]\d+')

def python_case(case):
    out=[]; broad=None; detail=None
    try:
        if case.check_only: compile_source(case.source, f'<cross:{case.id}>')
        else: run_source(case.source, f'<cross:{case.id}>', output=out.append)
    except SourceError as exc:
        broad=exc.code; detail=exc.diagnostic_id
    return '\n'.join(out),broad,detail

def go_case(binary:Path, case, root:Path):
    p=root/(case.id+'.saga');p.write_text(case.source,encoding='utf-8')
    mode='check' if case.check_only else 'run'
    r=subprocess.run([str(binary),mode,str(p)],text=True,capture_output=True,timeout=30)
    err=None
    if r.returncode:
        m=DIAG.search(r.stdout+r.stderr);err=m.group(0) if m else f'EXIT-{r.returncode}'
    return r.stdout.rstrip('\n'),err,r.stderr

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default=str(ROOT/f'validation/cross-implementation-{REL}.json')); a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='saga-cross-025-') as td0:
        td=Path(td0);binary=td/'saga-native'
        b=subprocess.run(['go','build','-o',str(binary),'./cmd/saga-go'],cwd=ROOT/'implementations/go',text=True,capture_output=True,timeout=120)
        if b.returncode: raise SystemExit(b.stdout+b.stderr)
        records=[]
        for case in CASES:
            po,pb,pd=python_case(case);go,ge,ges=go_case(binary,case,td)
            expected_ok=(pb==case.error_code if case.error_code else pb is None and po==case.expected)
            cross_ok=(po==go and pd==ge)
            records.append({'id':case.id,'python_output':po,'native_output':go,'python_error_category':pb,'python_diagnostic_id':pd,'native_diagnostic_id':ge,'expected_output':case.expected,'expected_error_category':case.error_code,'python_expected_pass':expected_ok,'cross_match':cross_ok,'pass':expected_ok and cross_ok,**({'native_stderr':ges[-1000:]} if not cross_ok else {})})
    binding=source_binding(REL)
    doc={'schema':2,'release':REL,**binding,'profile':'Standard Core common differential corpus','python_implementation':'Saga Python reference','native_implementation':'Saga Go independent Standard Core','total':len(records),'passed':sum(r['pass'] for r in records),'pass':all(r['pass'] for r in records),'cases':records}
    Path(a.output).write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'total':doc['total'],'passed':doc['passed'],'pass':doc['pass']},indent=2));return 0 if doc['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

#!/usr/bin/env python3
"""Reproducible reviewer preflight for the Saga 0.50.0 review candidate."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, time, tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REL='0.50.0'

def run(name,cmd,*,cwd=ROOT,timeout=240):
    t=time.monotonic()
    with tempfile.TemporaryFile(mode="w+t",encoding="utf-8") as log:
        try:
            p=subprocess.run(cmd,cwd=cwd,text=True,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            rc=p.returncode; err=None
        except subprocess.TimeoutExpired:
            rc=None; err='timeout'
        log.flush(); log.seek(0); out=log.read()
    doc={'name':name,'pass':rc==0,'returncode':rc,'seconds':round(time.monotonic()-t,3),'output':out[-6000:]}
    if err: doc['error']=err
    return doc

def python_modules():
    return [p.stem for p in sorted((ROOT/'tests').glob('test_*.py'))]

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--quick',action='store_true'); ap.add_argument('--output'); a=ap.parse_args()
    checks=[]; manifest=ROOT/f'release/source-manifest-{REL}.json'; manifest_sha=''; tree_sha=''
    if manifest.exists():
        c=run('source manifest exact-tree verification',[sys.executable,'tools/review_evidence.py','--verify',str(manifest)]); checks.append(c)
        if c['pass']:
            manifest_sha=hashlib.sha256(manifest.read_bytes()).hexdigest()
            try: tree_sha=json.loads(manifest.read_text(encoding='utf-8')).get('tree_sha256','')
            except Exception: tree_sha=''
    else: checks.append({'name':'source manifest exact-tree verification','pass':False,'returncode':None,'seconds':0,'output':'release source manifest is missing'})
    checks.append(run('specification final-candidate lint',[sys.executable,'tools/spec_review_lint.py']))
    py_total=0
    for mod in python_modules():
        c=run('python '+mod,[sys.executable,'-m','unittest','tests.'+mod],timeout=180)
        m=re.search(r'Ran (\d+) tests?',c['output']); py_total += int(m.group(1)) if m and c['pass'] else 0; checks.append(c)
    checks += [
        run('Go full regression',['go','test','./...','-count=1'],cwd=ROOT/'implementations/go'),
        run('Go vet',['go','vet','./...'],cwd=ROOT/'implementations/go'),
        run('Registry Protocol v1 Python-Go interoperability',[sys.executable,'tools/registry_interop_validation.py']),
        run('Python-Go language differential conformance',[sys.executable,'tools/cross_implementation_validation.py']),
        run('Security API surface',[sys.executable,'tools/validate_security_api.py']),
        run('Hosted API surface',[sys.executable,'tools/hosted_api_validation.py']),
        run('Native game API surface',[sys.executable,'tools/validate_native_game_api.py']),
        run('Browser host API surface',[sys.executable,'tools/validate_web_host_api.py']),
        run('Universal app API surface',[sys.executable,'tools/validate_app_action_api.py']),
        run('Machine smoke',[sys.executable,'tools/machine_smoke.py']),
        run('Machine control software qualification',[sys.executable,'tools/machine_control_qualification.py']),
        run('Production & Industrial 0.49 qualification',[sys.executable,'tools/production_industrial_qualification_049.py']),
        run('Internal security audit',[sys.executable,'tools/internal_security_audit.py']),
        run('SH-3 source-boundary audit',[sys.executable,'tools/sh3_audit.py']),
    ]
    if not a.quick:
        checks += [
            run('Go Race Detector complete split qualification',[sys.executable,'tools/go_race_qualification.py'],timeout=780),
            run('Real Chromium integration',[sys.executable,'tools/validate_chromium_web.py'],timeout=180),
            run('Parser/expression fuzz smoke',[sys.executable,'tools/fuzz_smoke.py'],timeout=240),
        ]
    doc={'schema':2,'release':REL,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'qualification_level':'quick' if a.quick else 'full','quick':a.quick,'source_manifest_sha256':manifest_sha,'source_tree_sha256':tree_sha,'python_tests_passed':py_total,'checks':checks,'pass':all(c['pass'] for c in checks)}
    default=ROOT/f"validation/{'reviewer-preflight' if a.quick else 'release-validation'}-{REL}.json"
    out=Path(a.output) if a.output else default
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps({'release':REL,'pass':doc['pass'],'qualification_level':doc['qualification_level'],'python_tests_passed':py_total,'failed':[c['name'] for c in checks if not c['pass']]},indent=2)); return 0 if doc['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

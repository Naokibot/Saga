from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def run(command: list[str], cwd: Path) -> dict:
    proc=subprocess.run(command,cwd=cwd,text=True,capture_output=True,encoding='utf-8',errors='replace')
    return {"command":command,"returncode":proc.returncode,"stdout":proc.stdout.strip(),"stderr":proc.stderr.strip()}


def evaluate(result: dict, test: dict) -> tuple[bool,str]:
    mode=test['mode']
    if mode=='run':
        ok=result['returncode']==test.get('exit_code',0) and result['stdout']==test['stdout']
        return ok, f"expected stdout={test['stdout']!r}, rc=0"
    if mode in {'check-fail','run-fail'}:
        hay=result['stderr']+'\n'+result['stdout']
        code=test.get('diagnostic_id') or test.get('diagnostic_code','')
        ok=(result['returncode']==test.get('exit_code',result['returncode']) and (not code or code in hay))
        return ok, f"expected failure category {code!r}"
    return False,f"unknown mode {mode}"


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--python',default=sys.executable)
    ap.add_argument('--python-entry',default='saga.py')
    ap.add_argument('--go-entry',default='implementations/go/saga-go')
    ap.add_argument('--output',default='validation/differential-conformance.json')
    args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    go_entry=root/args.go_entry
    if not go_entry.exists():
        go_tool=shutil.which('go')
        if not go_tool:
            raise SystemExit(f"Go implementation is missing ({go_entry}) and the 'go' tool was not found")
        build_dir=root/'validation'/'build'
        build_dir.mkdir(parents=True,exist_ok=True)
        go_entry=build_dir/('saga-go.exe' if os.name=='nt' else 'saga-go')
        build=subprocess.run(
            [go_tool,'build','-o',str(go_entry),'./cmd/saga-go'],
            cwd=root/'implementations/go',text=True,capture_output=True,encoding='utf-8',errors='replace'
        )
        if build.returncode!=0:
            raise SystemExit('Failed to build the Go implementation:\n'+build.stderr)
    manifest=json.loads((root/'conformance/manifest.json').read_text(encoding='utf-8'))
    records=[]; all_ok=True
    for test in manifest['tests']:
        source=root/'conformance'/test['file']
        py_action='check' if test['mode']=='check-fail' else 'run'
        go_action='check' if test['mode']=='check-fail' else 'run'
        py=run([args.python,args.python_entry,py_action,str(source)],root)
        go=run([str(go_entry),go_action,str(source)],root)
        py_ok,expect=evaluate(py,test); go_ok,_=evaluate(go,test)
        agreement=(py['returncode']==go['returncode']==test.get('exit_code',py['returncode']) and (test['mode']!='run' or py['stdout']==go['stdout']))
        ok=py_ok and go_ok and agreement
        all_ok=all_ok and ok
        records.append({"id":test['id'],"clause":test['clause'],"mode":test['mode'],"source_sha256":sha256(source),"expectation":expect,"python":py,"go":go,"agreement":agreement,"pass":ok})
    report={
      "schema":1,"language":manifest['language'],"version":manifest['version'],
      "profile":"Portable Core Level 1",
      "generated_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
      "host":{"platform":platform.platform(),"python":platform.python_version(),"machine":platform.machine()},
      "implementations":{"python_entry":args.python_entry,"go_entry":str(go_entry.relative_to(root)),"go_sha256":sha256(go_entry)},
      "tests":records,"summary":{"total":len(records),"passed":sum(r['pass'] for r in records),"failed":sum(not r['pass'] for r in records),"pass":all_ok},
      "independence_note":"The Go implementation is a separate lexer, parser, exact-number runtime and evaluator. It does not invoke or import the Python implementation. Agreement is claimed only for Portable Core Level 1 cases listed by this manifest, not for the full Core or hosted profiles."
    }
    out=root/args.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],ensure_ascii=False))
    return 0 if all_ok else 1
if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys
root=Path(__file__).resolve().parents[2]
bin=Path(__file__).with_name('saga-c-core')
manifest=json.loads((root/'conformance/manifest.json').read_text())
supported={'C001','C002','C003','C004','C005','C006','C010','C011','C012','C013','C014'}
results=[]
for t in manifest['tests']:
    if t['id'] not in supported: continue
    mode='run' if t['mode'].startswith('run') else 'check'
    p=subprocess.run([str(bin),mode,str(root/'conformance'/t['file'])],text=True,capture_output=True)
    got=p.stdout.strip(); err=p.stderr.strip()
    ok=p.returncode==t['exit_code']
    if 'stdout' in t: ok=ok and got==t['stdout']
    if 'diagnostic_id' in t: ok=ok and t['diagnostic_id'] in err
    results.append({'id':t['id'],'pass':ok,'exit':p.returncode,'stdout':got,'stderr':err})
print(json.dumps({'implementation':'saga-c-core','profile':'clean-room Standard Core subset','passed':sum(x['pass'] for x in results),'total':len(results),'results':results},ensure_ascii=False,indent=2))
sys.exit(0 if all(x['pass'] for x in results) else 1)

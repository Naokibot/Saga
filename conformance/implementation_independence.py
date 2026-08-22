from __future__ import annotations
import hashlib, json, re
from pathlib import Path

root=Path(__file__).resolve().parents[1]
go=root/'implementations/go/cmd/saga-go'
files=sorted(go.glob('*.go'))
forbidden=[r'os\.Exec.*python',r'exec\.Command\([^\n]*python',r'import.*saga\.py',r'subprocess']
findings=[]
for p in files:
    text=p.read_text(encoding='utf-8',errors='replace')
    for pat in forbidden:
        if re.search(pat,text,re.I): findings.append({'file':str(p.relative_to(root)),'pattern':pat})
h=hashlib.sha256()
for p in files:
    h.update(str(p.relative_to(root)).encode());h.update(b'\0');h.update(p.read_bytes())
report={'schema':1,'claim':'technical implementation independence','implementation':'Saga Native (Go-seeded runtime)','source_set_sha256':h.hexdigest(),'files_checked':len(files),'forbidden_runtime_dependency_findings':findings,'pass':not findings,'qualification':'This establishes source/runtime separation from the Python reference implementation. It is not organizational independence or a third-party implementation.'}
out=root/'validation/implementation-independence-0.17.0.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'pass':report['pass'],'files_checked':len(files),'findings':len(findings)}))
raise SystemExit(0 if report['pass'] else 1)

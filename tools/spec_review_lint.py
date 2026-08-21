#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RELEASE='0.50.0'
DEFAULT=ROOT/'SAGA_LANGUAGE_SPECIFICATION_1.0_FINAL_CANDIDATE.md'

def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--spec',default=str(DEFAULT)); ap.add_argument('--output',default=str(ROOT/f'validation/spec-final-candidate-{RELEASE}.json')); a=ap.parse_args()
    p=Path(a.spec); text=p.read_text(encoding='utf-8'); checks=[]
    def ck(name,ok,detail=''): checks.append({'name':name,'pass':bool(ok),'detail':detail})
    nums=[int(x) for x in re.findall(r'^## (\d+)\s',text,re.M)]
    ck('numbered clauses are unique and contiguous',nums==list(range(1,38)),str(nums))
    ck('no unresolved editorial markers',re.search(r'\b(TODO|TBD|FIXME|XXX)\b',text,re.I) is None)
    ck('candidate has 1.0 normative version','**Normative language version:** 1.0' in text)
    ck('candidate is not mislabeled ISO/IEC publication','does not imply approval' in text or 'not an ISO or IEC publication' in text)
    forbidden=re.findall(r'`([^`]*(?:_DRAFT|_RC\d|2027_PREVIEW)[^`]*)`',text,re.I)
    ck('no normative dependency on draft/RC companion file',not forbidden,', '.join(forbidden))
    refs=[]
    for m in re.finditer(r'`((?:spec|docs)/[^`]+\.(?:md|json|ebnf))`',text): refs.append(m.group(1))
    missing=[r for r in refs if not (ROOT/r).is_file()]
    ck('all referenced project documents exist',not missing,', '.join(missing))
    grammar=ROOT/'spec/saga-1.0.ebnf'; ck('normative grammar exists',grammar.is_file(),sha(grammar) if grammar.is_file() else '')
    annexes=re.findall(r'^## Annex ([A-Z]) ',text,re.M)
    ck('annex identifiers unique',len(annexes)==len(set(annexes)),str(annexes))
    ck('finalization clause present','## 37 Finalization and review status' in text)
    ck('no stale implementation release references',re.search(r'Saga Native 0\.\d+\.\d+',text) is None)
    doc={'schema':1,'release':RELEASE,'spec':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'spec_sha256':sha(p),'grammar_sha256':sha(grammar) if grammar.is_file() else None,'checks':checks,'pass':all(x['pass'] for x in checks)}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps(doc,indent=2,ensure_ascii=False)); return 0 if doc['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RELEASE='0.50.0'
EXCLUDED_PARTS={'.git','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','dist','build','bin','payload','saga_language.egg-info'}
EXCLUDED_PREFIXES=('validation/','review-output/','release/source-manifest-')
EXCLUDED_FILES={'SAGA_LANGUAGE_SPECIFICATION_1.0.md'}

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def source_files(root:Path=ROOT):
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root).as_posix()
        if any(part in EXCLUDED_PARTS for part in p.relative_to(root).parts): continue
        if rel.endswith(('.pyc','.pyo','.DS_Store')): continue
        if any(rel.startswith(x) for x in EXCLUDED_PREFIXES) or rel in EXCLUDED_FILES: continue
        if p.is_symlink(): raise ValueError('release source tree must not contain symlinks: '+rel)
        if not p.is_file(): continue
        yield p,rel

def build_manifest(root:Path=ROOT)->dict:
    records=[]
    for p,rel in source_files(root): records.append({'path':rel,'size':p.stat().st_size,'sha256':sha256_file(p)})
    canonical=json.dumps(records,sort_keys=True,separators=(',',':')).encode()
    return {'schema':1,'release':RELEASE,'files':records,'tree_sha256':hashlib.sha256(canonical).hexdigest()}

def verify_manifest(path:Path,root:Path=ROOT)->tuple[bool,list[str],dict]:
    doc=json.loads(path.read_text(encoding='utf-8')); current=build_manifest(root); errors=[]
    if doc.get('schema')!=1: errors.append('manifest schema mismatch')
    if doc.get('release')!=RELEASE: errors.append('manifest release mismatch')
    records=doc.get('files',[]) if isinstance(doc.get('files'),list) else []
    paths=[r.get('path') for r in records if isinstance(r,dict)]
    if len(paths)!=len(records) or len(paths)!=len(set(paths)): errors.append('manifest contains malformed or duplicate file records')
    try:
        manifest_tree=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if doc.get('tree_sha256')!=manifest_tree: errors.append('manifest self-digest mismatch')
    except Exception: errors.append('manifest file records are malformed')
    if doc.get('tree_sha256')!=current.get('tree_sha256'): errors.append('source tree digest mismatch')
    try: exp={r['path']:(r['size'],r['sha256']) for r in records}
    except Exception: exp={}
    got={r['path']:(r['size'],r['sha256']) for r in current['files']}
    for k in sorted(exp.keys()-got.keys()): errors.append('missing: '+k)
    for k in sorted(got.keys()-exp.keys()): errors.append('unexpected: '+k)
    for k in sorted(exp.keys()&got.keys()):
        if exp[k]!=got[k]: errors.append('changed: '+k)
    return not errors,errors,current

def main()->int:
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default=str(ROOT/f'release/source-manifest-{RELEASE}.json')); ap.add_argument('--verify')
    a=ap.parse_args()
    if a.verify:
        ok,errors,current=verify_manifest(Path(a.verify)); print(json.dumps({'pass':ok,'errors':errors,'current_tree_sha256':current['tree_sha256']},indent=2)); return 0 if ok else 1
    doc=build_manifest(); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(out); print(doc['tree_sha256']); return 0
if __name__=='__main__': raise SystemExit(main())

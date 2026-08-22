#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main()->int:
    ap=argparse.ArgumentParser(description='Export an immutable Saga registry tree as static HTTPS-hostable files')
    ap.add_argument('registry_root');ap.add_argument('output');a=ap.parse_args()
    src=Path(a.registry_root).resolve();out=Path(a.output).resolve()
    if out.exists(): shutil.rmtree(out)
    (out/'packages').mkdir(parents=True)
    records=[]
    for name_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        for ver_dir in sorted(p for p in name_dir.iterdir() if p.is_dir()):
            pkg=ver_dir/'package.sagapkg'; sigp=ver_dir/'package.sig'
            if not pkg.is_file() or not sigp.is_file(): continue
            sig=json.loads(sigp.read_text())
            actual=sha256(pkg)
            if sig.get('sha256')!=actual: raise SystemExit(f'hash mismatch: {name_dir.name}@{ver_dir.name}')
            dest=out/'packages'/name_dir.name/ver_dir.name
            dest.mkdir(parents=True)
            shutil.copy2(pkg,dest/'package.sagapkg');shutil.copy2(sigp,dest/'package.sig')
            records.append({'name':name_dir.name,'version':ver_dir.name,'sha256':actual,'fingerprint':sig.get('fingerprint',''),'package_path':f'packages/{name_dir.name}/{ver_dir.name}/package.sagapkg','signature_path':f'packages/{name_dir.name}/{ver_dir.name}/package.sig'})
    index={'schema':1,'format':'Saga static registry v1','immutable_versions':True,'packages':records}
    raw=(json.dumps(index,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
    (out/'index.json').write_bytes(raw)
    (out/'index.sha256').write_text(hashlib.sha256(raw).hexdigest()+'  index.json\n')
    (out/'README.txt').write_text('Serve this directory over HTTPS with immutable caching for packages and short caching for index.json. Publication is append-only: never replace an existing name/version.\n')
    print(json.dumps({'packages':len(records),'index_sha256':hashlib.sha256(raw).hexdigest(),'output':str(out)}))
    return 0
if __name__=='__main__':raise SystemExit(main())

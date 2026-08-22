#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, platform, shutil, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REL='0.38.0'

def run(cmd,*,cwd=ROOT,timeout=180,env=None): return subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout,env=env)
def sha(path:Path)->str:
    h=hashlib.sha256();
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def executable_format_matches(path:Path,key:str)->tuple[bool,str]:
    head=path.read_bytes()[:4]
    if key=='linux': ok=head==b'\x7fELF'; fmt='ELF'
    elif key=='windows': ok=head[:2]==b'MZ'; fmt='PE/MZ'
    elif key=='macos': ok=head in {b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca'}; fmt='Mach-O/FAT'
    else: ok=False; fmt='unknown'
    return ok, f'expected={fmt} magic={head.hex()}'

def git_commit():
    try:
        p=run(['git','rev-parse','HEAD'],timeout=10)
        return p.stdout.strip() if p.returncode==0 else ''
    except Exception: return ''

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--output'); ap.add_argument('--expected-host',choices=['linux','windows','macos']); ap.add_argument('--source-manifest',default=str(ROOT/f'release/source-manifest-{REL}.json')); a=ap.parse_args()
    sysname=platform.system(); key={'Linux':'linux','Windows':'windows','Darwin':'macos'}.get(sysname); checks=[]
    def mark(name,ok,detail=''): checks.append({'name':name,'pass':bool(ok),'detail':str(detail)}); return bool(ok)
    if key is None:
        mark('supported native host',False,sysname)
    elif a.expected_host is not None and a.expected_host != key:
        mark('actual native host matches requested host',False,f'actual={key} expected={a.expected_host}')
    else:
        mark('actual native host matches requested host',True,f'actual={key} expected={a.expected_host or key}')
        manifest=Path(a.source_manifest)
        if manifest.is_file():
            try:
                from review_evidence import verify_manifest
                ok,errs,current=verify_manifest(manifest,ROOT); mark('release source manifest matches checkout',ok,'; '.join(errs) or current['tree_sha256']); source_tree=current['tree_sha256']; manifest_sha=sha(manifest)
            except Exception as exc: mark('release source manifest matches checkout',False,exc); source_tree=''; manifest_sha=''
        else: mark('release source manifest matches checkout',False,'manifest missing'); source_tree=''; manifest_sha=''
        go=shutil.which('go'); mark('Go toolchain present',bool(go),go or 'go not found')
        if go:
            gv=run([go,'version']); mark('Go toolchain starts',gv.returncode==0,gv.stdout.strip()+gv.stderr.strip())
            t=run([go,'test','./...','-count=1'],cwd=ROOT/'implementations/go',timeout=240); mark('Go Native tests on target host',t.returncode==0,(t.stdout+t.stderr)[-2000:])
            v=run([go,'vet','./...'],cwd=ROOT/'implementations/go',timeout=180); mark('Go vet on target host',v.returncode==0,(v.stdout+v.stderr)[-1600:])
            with tempfile.TemporaryDirectory(prefix=f'saga-native-{key}-') as td0:
                td=Path(td0); exe=td/('saga.exe' if key=='windows' else 'saga')
                r=run([go,'build','-trimpath','-o',str(exe),'./cmd/saga-go'],cwd=ROOT/'implementations/go',timeout=180)
                if mark('native build on target host',r.returncode==0,(r.stdout+r.stderr)[-1600:]) and exe.exists():
                    binary_sha=sha(exe); mark('native executable SHA-256 recorded',len(binary_sha)==64,binary_sha)
                    fmt_ok,fmt_detail=executable_format_matches(exe,key); mark('native executable format matches host',fmt_ok,fmt_detail)
                    r=run([str(exe),'--version']); mark('native executable starts',r.returncode==0 and f'0.38.0' in (r.stdout+r.stderr),(r.stdout+r.stderr).strip())
                    r=run([str(exe),'conformance','--json'],timeout=120)
                    try: conf=json.loads(r.stdout); conf_ok=r.returncode==0 and conf.get('pass') is True and conf.get('implementation_version')==REL
                    except Exception: conf={}; conf_ok=False
                    mark('native Standard Core conformance',conf_ok,json.dumps({k:conf.get(k) for k in ('passed','total','pass','implementation_version')},sort_keys=True))
                    src=td/'smoke.saga'; src.write_text('fn twice(x:int)->int=x*2\nprint(twice(21))\n',encoding='utf-8')
                    r=run([str(exe),'check',str(src)]); mark('native source check',r.returncode==0 and 'OK' in r.stdout,(r.stdout+r.stderr).strip())
                    r=run([str(exe),'run',str(src)]); mark('native source execution',r.returncode==0 and r.stdout=='42\n',(r.stdout+r.stderr).strip())
    doc={'schema':3,'release':REL,'native_host':key,'host':{'system':sysname,'release':platform.release(),'version':platform.version(),'machine':platform.machine(),'python':platform.python_version()},'generated_at_utc':datetime.now(timezone.utc).isoformat(),'git_commit':git_commit(),'source_manifest_sha256':locals().get('manifest_sha',''),'source_tree_sha256':locals().get('source_tree',''),'binary_sha256':locals().get('binary_sha',''),'checks':checks,'pass':bool(checks) and all(c['pass'] for c in checks)}
    out=Path(a.output) if a.output else ROOT/f'validation/native-host-{key or "unknown"}-{REL}.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps(doc,indent=2,ensure_ascii=False)); return 0 if doc['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

#!/usr/bin/env python3
"""Qualify a real public HTTPS Saga Registry Protocol v1 endpoint.

This is deliberately opt-in and fail-closed.  GA evidence requires a globally
routable HTTPS endpoint, verified TLS, immutable signed publication, explicit
publisher trust, and Python<->Go protocol interoperability.
"""
from __future__ import annotations
import argparse, hashlib, ipaddress, json, os, re, secrets, shutil, socket, ssl, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from saga.api import run_file
from saga.package import build_lock
from saga.registry import publish, search, install, keygen
from tools.review_evidence import verify_manifest

REL='0.38.0'

def run(cmd, *, cwd=None, env=None, timeout=180):
    p=subprocess.run(cmd,cwd=cwd or ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    if p.returncode: raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str,cmd))}\n{p.stdout}")
    return p.stdout

def public_tls_evidence(url:str)->dict:
    u=urlparse(url)
    if u.scheme!='https' or not u.hostname: raise ValueError('registry URL must be HTTPS with a hostname')
    infos=socket.getaddrinfo(u.hostname,u.port or 443,type=socket.SOCK_STREAM)
    addrs=sorted({x[4][0] for x in infos})
    global_addrs=[]
    for raw in addrs:
        try:
            if ipaddress.ip_address(raw).is_global: global_addrs.append(raw)
        except ValueError: pass
    if not global_addrs: raise ValueError('registry hostname does not resolve to a globally routable address')
    ctx=ssl.create_default_context(); last_error=None
    for address in global_addrs:
        try:
            with socket.create_connection((address,u.port or 443),timeout=15) as raw:
                peer=raw.getpeername()[0]
                if not ipaddress.ip_address(peer).is_global:
                    raise ValueError('connected registry peer is not globally routable')
                with ctx.wrap_socket(raw,server_hostname=u.hostname) as tls:
                    cert=tls.getpeercert(binary_form=True)
                    return {'hostname':u.hostname,'resolved_addresses':addrs,'global_addresses':global_addrs,'peer_address':peer,'tls_version':tls.version(),'cipher':tls.cipher()[0] if tls.cipher() else None,'peer_certificate_sha256':hashlib.sha256(cert).hexdigest()}
        except Exception as exc:
            last_error=exc
    raise ValueError('could not establish verified TLS to a globally routable registry peer: '+str(last_error))

def write_project(path:Path,name:str,answer:int=42):
    path.mkdir(parents=True,exist_ok=True); (path/'tests').mkdir(exist_ok=True)
    (path/'saga.toml').write_text(f'[project]\nname="{name}"\nversion="{REL}"\nlanguage="1.0"\nentry="lib.saga"\ntest_dir="tests"\n',encoding='utf-8')
    (path/'lib.saga').write_text(f'fn qualification_answer()->int = {answer}\n',encoding='utf-8')
    build_lock(path)

def qualification_names(base: str, run_id: str = '') -> tuple[str,str,str]:
    from saga.project import valid_project_name
    if not valid_project_name(base): raise ValueError('qualification package base must be a valid Saga project name')
    rid=run_id.strip() if run_id else 'r'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')+secrets.token_hex(3)
    if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',rid) is None:
        raise ValueError('qualification run id must be one ASCII identifier (for example r20260811a1b2c3)')
    return f'{base}-python-{rid}', f'{base}-go-{rid}', rid

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default=str(ROOT/f'validation/public-registry-live-{REL}.json')); a=ap.parse_args()
    url=os.environ.get('SAGA_REGISTRY_URL','').rstrip('/'); token=os.environ.get('SAGA_REGISTRY_TOKEN',''); key=os.environ.get('SAGA_REGISTRY_SIGNING_KEY','')
    base=os.environ.get('SAGA_REGISTRY_QUALIFICATION_PACKAGE','saga-qualification-probe')
    manifest=ROOT/f'release/source-manifest-{REL}.json'
    doc={'schema':3,'release':REL,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'registry':url,'source_manifest_sha256':'','source_tree_sha256':'','pass':False,'checks':{}}
    def finish(status,reason='',code=3):
        doc['status']=status
        if reason: doc['reason']=reason
        p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps(doc,indent=2,ensure_ascii=False)); return code
    if os.environ.get('SAGA_REGISTRY_LIVE')!='1': return finish('READY_UNEXECUTED','Set SAGA_REGISTRY_LIVE=1 only for a project-authorized public HTTPS registry.')
    if not manifest.is_file(): return finish('BLOCKED','Current release source manifest is missing.',2)
    ok,errors,current=verify_manifest(manifest,ROOT)
    if not ok: return finish('FAIL','Current source tree does not match release manifest: '+'; '.join(errors),1)
    doc['source_manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest(); doc['source_tree_sha256']=current['tree_sha256']; doc['checks']['source_manifest_exact_tree']=True
    key_path=Path(key).expanduser() if key else None
    if not token or key_path is None or not key_path.is_file(): return finish('BLOCKED','Registry token and existing Python publisher Ed25519 private key are required.',2)
    try:
        doc['tls']=public_tls_evidence(url); doc['checks']['public_verified_tls']=True
        go=shutil.which('go')
        if not go: raise RuntimeError('Go toolchain is required for Python<->Go registry interop qualification')
        with tempfile.TemporaryDirectory(prefix='saga-registry-live-') as td0:
            td=Path(td0); native=td/('saga.exe' if os.name=='nt' else 'saga')
            run([go,'build','-trimpath','-o',str(native),'./cmd/saga-go'],cwd=ROOT/'implementations/go')
            py_name,go_name,run_id=qualification_names(base,os.environ.get('SAGA_REGISTRY_QUALIFICATION_RUN_ID',''))
            doc['qualification_run_id']=run_id
            py_project=td/'python-publisher'; write_project(py_project,py_name)
            py_meta=publish(py_project,url,token,key_path); py_fp=py_meta.get('publisher_fingerprint')
            if not py_fp: raise RuntimeError('Python publication omitted publisher fingerprint')
            doc['checks']['python_publish']=True
            # Untrusted publishers must fail closed before an explicit trust decision.
            py_consumer=td/'py-consumer'; py_consumer.mkdir()
            try: install(url,f'{py_name}@{REL}',py_consumer); raise RuntimeError('untrusted package was installed without explicit trust')
            except ValueError as exc:
                if 'untrusted publisher' not in str(exc): raise
            target=install(url,f'{py_name}@{REL}',py_consumer,trust_once=py_fp)
            doc['checks']['python_explicit_trust']=target.exists()
            # Immutable version: changed bytes at the same identity must be rejected.
            (py_project/'lib.saga').write_text('fn qualification_answer()->int = 43\n',encoding='utf-8'); build_lock(py_project)
            try: publish(py_project,url,token,key_path); raise RuntimeError('registry accepted a mutable same-version overwrite')
            except HTTPError as exc:
                if exc.code!=409: raise
            doc['checks']['immutable_version_rejected']=True

            go_project=td/'go-publisher'; write_project(go_project,go_name)
            go_priv,go_pub=td/'go-private.pem',td/'go-public.pem'
            run([str(native),'registry','keygen',str(go_priv),str(go_pub)])
            env=os.environ.copy(); env['SAGA_REGISTRY_TOKEN']=token
            run([str(native),'registry','publish',str(go_project),'--registry',url,'--key',str(go_priv)],env=env)
            found=search(url,go_name); exact=[x for x in found if x.get('name')==go_name and x.get('version')==REL]
            if not exact: raise RuntimeError('Python client could not discover Go-published package')
            go_fp=exact[0].get('publisher_fingerprint');
            if not go_fp: raise RuntimeError('Go publication missing fingerprint')
            py_from_go=td/'py-from-go'; py_from_go.mkdir(); install(url,f'{go_name}@{REL}',py_from_go,trust_once=go_fp)
            doc['checks']['go_publish_python_install']=True

            # Go client must discover and install the Python publication with an explicit pin.
            go_consumer=td/'go-consumer'; go_consumer.mkdir(); write_project(go_consumer,'registry-live-consumer')
            search_out=run([str(native),'registry','search',py_name,'--registry',url])
            if py_name not in search_out: raise RuntimeError('Go search did not return Python publication')
            run([str(native),'registry','add',f'{py_name}@{REL}','--project',str(go_consumer),'--registry',url,'--trust',py_fp])
            if not (go_consumer/'.saga'/'packages'/py_name/REL/'lib.saga').is_file(): raise RuntimeError('Go install did not materialize Python package')
            doc['checks']['python_publish_go_install']=True
            doc['evidence']={'python_package':py_name,'python_publisher_fingerprint':py_fp,'go_package':go_name,'go_publisher_fingerprint':go_fp}
        if not all(doc['checks'].values()): raise RuntimeError('one or more registry qualification checks did not pass')
        doc['pass']=True; return finish('PASS','',0)
    except Exception as exc:
        return finish('FAIL',f'{type(exc).__name__}: {exc}',1)
if __name__=='__main__': raise SystemExit(main())

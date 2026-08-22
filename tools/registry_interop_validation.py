#!/usr/bin/env python3
from __future__ import annotations
import json, os, shutil, socket, subprocess, sys, tempfile, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from saga.registry import init_registry, serve_registry, publish, search, install, keygen
from saga.package import build_lock
REL='0.38.0'

def free_port():
    s=socket.socket(); s.bind(('127.0.0.1',0)); p=s.getsockname()[1]; s.close(); return p

def project(root:Path,name:str,version:str='1.0.0'):
    root.mkdir(parents=True); (root/'tests').mkdir(); (root/'saga.toml').write_text(f'[project]\nname="{name}"\nversion="{version}"\nlanguage="1.0"\nentry="lib.saga"\ntest_dir="tests"\n',encoding='utf-8'); (root/'lib.saga').write_text('fn qualification_answer()->int=42\n',encoding='utf-8'); build_lock(root)

def go(cmd,*,env=None,cwd=ROOT,timeout=60): return subprocess.run(cmd,cwd=cwd,env=env,text=True,capture_output=True,timeout=timeout)

def wait_health(url,timeout=8):
    import urllib.request
    end=time.time()+timeout
    while time.time()<end:
        try:
            with urllib.request.urlopen(url+'/healthz',timeout=.5) as r:
                if r.status==200: return True
        except Exception: time.sleep(.1)
    return False

def main()->int:
    out=ROOT/f'validation/registry-interop-{REL}.json'; checks=[]
    def mark(name,ok,detail=''): checks.append({'name':name,'pass':bool(ok),'detail':detail}); return ok
    gobin=shutil.which('go')
    if not gobin: mark('Go toolchain available',False,'go not found')
    else:
      with tempfile.TemporaryDirectory(prefix='saga-registry-interop-') as td0:
        td=Path(td0); binp=td/('saga.exe' if os.name=='nt' else 'saga')
        r=go([gobin,'build','-o',str(binp),'./cmd/saga-go'],cwd=ROOT/'implementations/go',timeout=120); mark('Go Native registry client/server builds',r.returncode==0,(r.stdout+r.stderr)[-1200:])
        if r.returncode==0:
          # Direction A: Python server, Go publisher/client.
          pyroot=td/'python-reg'; init_registry(pyroot,'secret',require_signatures=True); srv=serve_registry(pyroot,'127.0.0.1',0,'secret',require_signatures=True); threading.Thread(target=srv.serve_forever,daemon=True).start(); url=f'http://127.0.0.1:{srv.server_address[1]}'
          gp=td/'go-pkg'; project(gp,'interop-go-publish'); key=td/'go-private.pem'; pub=td/'go-public.pem'; r=go([str(binp),'registry','keygen',str(key),str(pub)]); env=os.environ.copy(); env['SAGA_REGISTRY_TOKEN']='secret'; r=go([str(binp),'lock',str(gp)],env=env) if not (gp/'saga.lock').exists() else r
          r=go([str(binp),'registry','publish',str(gp),'--registry',url,'--key',str(key)],env=env); mark('Go publish -> Python server',r.returncode==0,r.stdout+r.stderr)
          found=search(url,'interop-go-publish'); mark('Python search sees Go publication',len(found)==1,str(found))
          if found:
            consumer=td/'py-consumer'; consumer.mkdir();
            try: target=install(url,'interop-go-publish@1.0.0',consumer,trust_once=found[0]['publisher_fingerprint']); mark('Python install verifies Go-signed package',target.is_dir(),str(target))
            except Exception as exc: mark('Python install verifies Go-signed package',False,str(exc))
          srv.shutdown(); srv.server_close()

          # Direction B: Go server, Python publisher/client.
          port=free_port(); go_root=td/'go-reg'; env2=os.environ.copy(); env2['SAGA_REGISTRY_TOKEN']='secret'; proc=subprocess.Popen([str(binp),'registry','serve','--root',str(go_root),'--addr',f'127.0.0.1:{port}'],env=env2,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
          url2=f'http://127.0.0.1:{port}'
          try:
            if mark('Go server health',wait_health(url2),'healthz'):
              pp=td/'py-pkg'; project(pp,'interop-python-publish'); priv,pubp=keygen(td/'py-private.pem',td/'py-public.pem')
              try: meta=publish(pp,url2,'secret',priv); mark('Python publish -> Go server',meta.get('name')=='interop-python-publish',str(meta))
              except Exception as exc: meta={}; mark('Python publish -> Go server',False,str(exc))
              r=go([str(binp),'registry','search','interop-python-publish','--registry',url2]); mark('Go search sees Python publication',r.returncode==0 and 'interop-python-publish' in r.stdout,r.stdout+r.stderr)
              if meta:
                gc=td/'go-consumer'; gc.mkdir(); r=go([str(binp),'registry','add','interop-python-publish@1.0.0','--registry',url2,'--project',str(gc),'--trust',meta['publisher_fingerprint']]); mark('Go install verifies Python-signed package',r.returncode==0,r.stdout+r.stderr)
          finally:
            proc.terminate();
            try: proc.wait(timeout=3)
            except Exception: proc.kill()
    doc={'schema':1,'release':REL,'checks':checks,'pass':bool(checks) and all(c['pass'] for c in checks)}; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps(doc,indent=2,ensure_ascii=False)); return 0 if doc['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

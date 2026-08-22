#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json, os, statistics, tempfile, threading, time
from pathlib import Path
import sys
from urllib.request import Request

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from saga.registry import init_registry, serve_registry, keygen, publish, search, urlopen, _read_limited, REGISTRY_MAX_PACKAGE_BYTES

RELEASE='0.38.0'

def percentile(xs,p):
    xs=sorted(xs)
    if not xs:return 0.0
    return xs[min(len(xs)-1,max(0,round((len(xs)-1)*p)))]

def make_project(root:Path,name:str,version:str)->Path:
    p=root/name/version; p.mkdir(parents=True,exist_ok=True)
    (p/'saga.toml').write_text(f'''[project]\nname = "{name}"\nversion = "{version}"\nentry = "main.saga"\n''',encoding='utf-8')
    (p/'main.saga').write_text(f'print("{name}@{version}")\n',encoding='utf-8')
    return p

def qualify(packages:int=24,versions:int=2,virtual_users:int=256,requests_per_user:int=8)->dict:
    if packages<1 or versions<1 or virtual_users<1: raise ValueError('positive scale values required')
    with tempfile.TemporaryDirectory(prefix='saga-public-registry-sim-') as td:
        base=Path(td); reg=base/'registry'; projects=base/'projects'; keys=base/'keys'
        token='qualification-token-'+sha256(str(base).encode()).hexdigest()[:16]
        init_registry(reg,token=token,require_signatures=True)
        priv,pub=keygen(keys/'publisher.pem',keys/'publisher.pub.pem')
        server=serve_registry(reg,host='127.0.0.1',port=0,token=token,require_signatures=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        host,port=server.server_address; url=f'http://{host}:{port}'
        publish_lat=[]; total=packages*versions
        try:
            for i in range(packages):
                name=f'scalepkg{i:03d}'
                for v in range(versions):
                    project=make_project(projects,name,f'1.{v}.0')
                    t=time.perf_counter_ns(); meta=publish(project,url,token=token,signing_key=priv); publish_lat.append((time.perf_counter_ns()-t)/1e6)
                    if meta.get('name')!=name: raise RuntimeError('published identity mismatch')
            health=Request(url+'/healthz');
            with urlopen(health,timeout=5) as r: health_ok=json.loads(r.read()).get('status')=='ok'

            lat=[]; failures=[]; downloads=0; searches=0; lock=threading.Lock()
            def user(uid:int):
                nonlocal downloads,searches
                local=[]; local_fail=[]; d=0;s=0
                for j in range(requests_per_user):
                    idx=(uid*37+j*11)%packages; name=f'scalepkg{idx:03d}'
                    t=time.perf_counter_ns()
                    try:
                        if j%4:
                            out=search(url,name); s+=1
                            if not out: raise RuntimeError('empty search result')
                        else:
                            ver=f'1.{(uid+j)%versions}.0'; req=Request(url+f'/v1/packages/{name}/{ver}')
                            with urlopen(req,timeout=10) as r:
                                data=_read_limited(r,REGISTRY_MAX_PACKAGE_BYTES); expected=r.headers.get('X-Saga-Sha256')
                            if not expected or sha256(data).hexdigest()!=expected: raise RuntimeError('download digest mismatch')
                            d+=1
                    except Exception as exc: local_fail.append(f'{uid}:{j}:{exc}')
                    local.append((time.perf_counter_ns()-t)/1e6)
                with lock:
                    lat.extend(local); failures.extend(local_fail); downloads+=d; searches+=s
            started=time.perf_counter()
            with ThreadPoolExecutor(max_workers=min(32,virtual_users)) as pool: list(pool.map(user,range(virtual_users)))
            load_seconds=time.perf_counter()-started
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)
        expected_requests=virtual_users*requests_per_user
        return {'schema':'saga.public-registry-load-simulation.v1','release':RELEASE,'mode':'real Saga HTTP registry/server/publish/search/download code over loopback with synthetic packages and virtual users; not a public-Internet service and not real human adoption','signed_packages_published':total,'package_names':packages,'versions_per_package':versions,'virtual_users':virtual_users,'requests_per_user':requests_per_user,'total_requests':expected_requests,'search_requests':searches,'download_requests':downloads,'load_seconds':load_seconds,'requests_per_second':expected_requests/load_seconds if load_seconds else None,'publish_latency_ms':{'mean':statistics.fmean(publish_lat),'p95':percentile(publish_lat,.95),'max':max(publish_lat)},'request_latency_ms':{'mean':statistics.fmean(lat),'p50':percentile(lat,.5),'p95':percentile(lat,.95),'p99':percentile(lat,.99),'max':max(lat)},'health_ok':health_ok,'failures':failures[:50],'pass':health_ok and not failures and searches+downloads==expected_requests,'public_internet_endpoint':'UNAVAILABLE','real_human_users':'UNAVAILABLE','limitations':['The execution environment cannot expose an inbound public Internet endpoint or recruit/measure real human users.','This qualification uses the actual Saga registry HTTP server, immutable signed package publish path, search index and package download integrity checks on loopback.','Virtual users generate concurrent network requests; they are load generators, not evidence of ecosystem adoption.']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--packages',type=int,default=24);ap.add_argument('--versions',type=int,default=2);ap.add_argument('--users',type=int,default=256);ap.add_argument('--requests-per-user',type=int,default=8);ap.add_argument('--output',default=str(ROOT/'validation'/'public-registry-load-sim-0.38.0.json'));a=ap.parse_args();r=qualify(a.packages,a.versions,a.users,a.requests_per_user);Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r,indent=2,sort_keys=True));return 0 if r['pass'] else 1
if __name__=='__main__':raise SystemExit(main())

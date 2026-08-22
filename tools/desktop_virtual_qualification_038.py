#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import argparse, json, os, platform, shutil, subprocess, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GO=ROOT/'implementations'/'go'
RELEASE='0.38.0'
TARGETS=(('windows','amd64'),('darwin','amd64'))

def run(cmd,cwd=GO,env=None,timeout=120):
    return subprocess.run(cmd,cwd=cwd,env=env,text=True,capture_output=True,timeout=timeout)

def magic(path:Path,goos:str):
    d=path.read_bytes()[:4]
    if goos=='windows': return d[:2]==b'MZ',d.hex()
    return d in {bytes.fromhex('cffaedfe'),bytes.fromhex('feedfacf')},d.hex()

def inspect_with_go(path:Path,goos:str)->dict:
    with tempfile.TemporaryDirectory(prefix='saga-bin-inspect-') as td:
        src=Path(td)/'inspect.go'
        if goos=='windows':
            src.write_text('''package main\nimport("debug/pe";"encoding/json";"os")\nfunc main(){f,e:=pe.Open(os.Args[1]);if e!=nil{panic(e)};defer f.Close(); im,_:=f.ImportedLibraries(); s:=[]string{};for _,x:=range f.Sections{s=append(s,x.Name)}; json.NewEncoder(os.Stdout).Encode(map[string]any{"machine":f.FileHeader.Machine,"sections":s,"imports":im})}\n''')
        else:
            src.write_text('''package main\nimport("debug/macho";"encoding/json";"os")\nfunc main(){f,e:=macho.Open(os.Args[1]);if e!=nil{panic(e)};defer f.Close(); s:=[]string{};for _,x:=range f.Sections{s=append(s,x.Name)}; json.NewEncoder(os.Stdout).Encode(map[string]any{"cpu":f.Cpu.String(),"type":f.Type.String(),"sections":s})}\n''')
        p=run(['go','run',str(src),str(path)],cwd=ROOT,env=os.environ.copy())
        if p.returncode: return {'pass':False,'stderr':p.stderr[-1000:]}
        try: doc=json.loads(p.stdout)
        except Exception: return {'pass':False,'stderr':'invalid inspector output'}
        doc['pass']=bool(doc.get('sections'))
        return doc

def qualify()->dict:
    host=f"{platform.system().lower()}/{platform.machine().lower()}"
    availability={x:shutil.which(x) for x in ('wine','qemu-x86_64','qemu-aarch64','qemu-system-x86_64')}
    with tempfile.TemporaryDirectory(prefix='saga-desktop-virtual-') as td:
        out=Path(td)
        def one(target):
            goos,arch=target; env=dict(os.environ,GOOS=goos,GOARCH=arch,CGO_ENABLED='0')
            suffix='.exe' if goos=='windows' else ''
            cli=out/f'saga-{goos}-{arch}{suffix}'; rt=out/f'sagaruntime-{goos}-{arch}{suffix}'; tb=out/f'tests-{goos}-{arch}{suffix}'
            t=time.perf_counter()
            p1=run(['go','build','-trimpath','-o',str(cli),'./cmd/saga-go'],env=env)
            p2=run(['go','build','-trimpath','-tags','sagaruntime','-o',str(rt),'./cmd/saga-go'],env=env)
            p3=run(['go','test','-c','-o',str(tb),'./cmd/saga-go'],env=env)
            m1=magic(cli,goos) if cli.exists() else (False,'missing'); m2=magic(rt,goos) if rt.exists() else (False,'missing'); m3=magic(tb,goos) if tb.exists() else (False,'missing')
            inspect=inspect_with_go(cli,goos) if cli.exists() else {'pass':False,'stderr':'missing'}
            buildinfo=run(['go','version','-m',str(cli)],cwd=ROOT,env=os.environ.copy()) if cli.exists() else None
            ok=all([p1.returncode==0,p2.returncode==0,p3.returncode==0,m1[0],m2[0],m3[0],inspect.get('pass',False),buildinfo is not None and buildinfo.returncode==0])
            return {'target':f'{goos}/{arch}','cli_build':p1.returncode==0,'runtime_build':p2.returncode==0,'target_tests_compile':p3.returncode==0,'cli_magic':m1[1],'runtime_magic':m2[1],'test_magic':m3[1],'binary_inspection':inspect,'go_build_info_readable':bool(buildinfo and buildinfo.returncode==0),'seconds':time.perf_counter()-t,'simulated_execution':'STATIC_BINARY_AND_TARGET_TEST_QUALIFICATION','physical_execution':'UNEXECUTED','pass':ok,'stderr':'\n'.join(x for x in (p1.stderr,p2.stderr,p3.stderr) if x)[-4000:]}
        with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(one,TARGETS))
    return {'schema':'saga.desktop-virtual-qualification.v2','release':RELEASE,'host':host,'emulator_availability':availability,'results':results,'pass':all(x['pass'] for x in results),'windows_physical_execution':'UNEXECUTED','macos_physical_execution':'UNEXECUTED','limitations':['No Windows or macOS host, VM, signing identity, GUI session, driver stack, or physical device is available in this execution environment.','Cross-compilation, target-specific test compilation, PE/Mach-O parsing, section/import inspection and Go build-info validation are simulation/static qualification only.','These results must not be relabeled as physical Windows/macOS execution.']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(ROOT/'validation'/'desktop-virtual-0.38.0.json'));a=ap.parse_args();r=qualify();Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r,indent=2,sort_keys=True));return 0 if r['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

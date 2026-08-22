#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REL='0.38.0'
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.evidence_context import source_binding

def run(cmd, *, cwd=ROOT, env=None, check=False, timeout=120):
    r=subprocess.run(cmd,cwd=cwd,env=env,text=True,capture_output=True,timeout=timeout)
    if check and r.returncode!=0:
        print('$',' '.join(map(str,cmd)),file=sys.stderr);print(r.stdout,file=sys.stderr);print(r.stderr,file=sys.stderr);raise SystemExit(r.returncode)
    return r

def sha(path:Path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    evidence={'schema':1,'release':REL,'profile':'SH-3 All-Source Self-Hosting','checks':[]}
    def mark(name,ok,detail=''):
        evidence['checks'].append({'name':name,'pass':bool(ok),'detail':detail});print(('PASS' if ok else 'FAIL'),name,detail)
        if not ok: raise SystemExit(1)
    with tempfile.TemporaryDirectory(prefix='saga-sh3-') as td0:
        td=Path(td0); vm=td/'sh3vm'; launcher=td/'saga';
        cc=shutil.which('cc') or shutil.which('clang')
        if not cc: raise SystemExit('C compiler required for SH-3 bootstrap validation')
        r=run([cc,'-std=c11','-pedantic','-O2','-Wall','-Wextra','-Werror',str(ROOT/'bootstrap/sh3/sh3vm.c'),'-o',str(vm)])
        mark('bootstrap VM strict C11 build',r.returncode==0,r.stderr.strip())
        r=run([cc,'-std=c11','-pedantic','-O2','-Wall','-Wextra','-Werror',str(ROOT/'bootstrap/sh3/launcher.c'),'-o',str(launcher)])
        mark('language-neutral launcher strict C11 build',r.returncode==0,r.stderr.strip())
        s1=ROOT/'bootstrap/sh3/stage1.sbc'; s2=td/'stage2.sbc'; s3=td/'stage3.sbc'
        r=run([str(vm),str(s1),str(ROOT/'selfhost/sh3/sh3c.saga'),str(s2)],timeout=180);mark('Stage1 -> Stage2 compiler rebuild',r.returncode==0,r.stderr.strip())
        r=run([str(vm),str(s2),str(ROOT/'selfhost/sh3/sh3c.saga'),str(s3)],timeout=180);mark('Stage2 -> Stage3 compiler rebuild',r.returncode==0,r.stderr.strip())
        mark('compiler fixed point Stage2 == Stage3',s2.read_bytes()==s3.read_bytes(),sha(s2))
        k2=td/'kernel2.sbc'; k3=td/'kernel3.sbc'
        r=run([str(vm),str(s2),str(ROOT/'selfhost/sh3/kernel.saga'),str(k2)],timeout=180);mark('Stage2 compiles canonical Saga kernel',r.returncode==0,r.stderr.strip())
        r=run([str(vm),str(s3),str(ROOT/'selfhost/sh3/kernel.saga'),str(k3)],timeout=180);mark('Stage3 compiles canonical Saga kernel',r.returncode==0,r.stderr.strip())
        mark('kernel lowering deterministic',k2.read_bytes()==k3.read_bytes(),sha(k2))

        cases=json.loads((ROOT/'conformance/sh3/standard-core-cases-1.0.json').read_text())
        okn=0
        casesdir=td/'cases';casesdir.mkdir()
        for c in cases['success']:
            p=casesdir/(c['name']+'.saga');p.write_text(c['source'])
            r=run([str(vm),str(k2),'run',str(p)],timeout=60)
            ok=r.returncode==0 and r.stdout==c['stdout']
            if not ok: print('case',c['name'],'got',repr(r.stdout),repr(r.stderr),'want',repr(c['stdout']))
            okn+=ok
        mark('Standard Core success corpus',okn==len(cases['success']),f'{okn}/{len(cases["success"])}')
        oke=0
        for c in cases['errors']:
            p=casesdir/(c['name']+'.saga');p.write_text(c['source'])
            r=run([str(vm),str(k2),'check',str(p)],timeout=60)
            m=re.search(r'SAGA-[A-Z]\d+',r.stdout+r.stderr);got=m.group(0) if m else ''
            ok=r.returncode!=0 and got==c['diagnostic'];oke+=ok
            if not ok: print('error case',c['name'],'got',got,r.returncode,repr(r.stdout),repr(r.stderr))
        mark('Standard Core diagnostic corpus',oke==len(cases['errors']),f'{oke}/{len(cases["errors"])}')

        e27=json.loads((ROOT/'conformance/sh3/edition-2027-cases.json').read_text())
        oke27=0
        for c in e27['cases']:
            p=casesdir/(c['name']+'.saga');p.write_text(c['source'])
            wants_error='diagnostic' in c
            r=run([str(vm),str(k2),'check' if wants_error else 'run',str(p)],timeout=60)
            if wants_error:
                m=re.search(r'SAGA-[A-Z]\d+',r.stdout+r.stderr);got=m.group(0) if m else ''
                ok=r.returncode!=0 and got==c['diagnostic']
            else:
                ok=r.returncode==0 and r.stdout==c['stdout']
            oke27+=ok
            if not ok: print('edition case',c['name'],'rc',r.returncode,'got',repr(r.stdout),repr(r.stderr),'want',c.get('stdout',c.get('diagnostic')))
        mark('Edition 2027 Preview corpus through canonical Saga kernel',oke27==len(e27['cases']),f'{oke27}/{len(e27["cases"])}')

        proj=td/'project';proj.mkdir()
        for n,content in cases['source_loader']['files'].items():(proj/n).write_text(content)
        entry=proj/cases['source_loader']['entry']
        r=run([str(vm),str(k2),'run',str(entry)]);mark('canonical Saga source-unit loader',r.returncode==0 and r.stdout==cases['source_loader']['stdout'],repr(r.stdout))
        img1=td/'a.simg';img2=td/'b.simg'
        r1=run([str(vm),str(k2),'compile',str(entry),str(img1)]);r2=run([str(vm),str(k2),'compile',str(entry),str(img2)])
        mark('Saga-written user lowering emits deterministic SH3IMG1',r1.returncode==0 and r2.returncode==0 and img1.read_bytes()==img2.read_bytes() and img1.read_text().startswith('SH3IMG1\n'),sha(img1))
        rr=run([str(vm),str(k2),'run-image',str(img1)]);mark('lowered token image executes',rr.returncode==0 and rr.stdout==cases['source_loader']['stdout'],repr(rr.stdout))

        # Build a no-language-runtime distribution. The launcher only execs sibling generic VM + generated Saga kernel image.
        dist=td/'dist';dist.mkdir(); shutil.copy2(vm,dist/'sh3vm');shutil.copy2(launcher,dist/'saga');shutil.copy2(launcher,dist/'sagac');shutil.copy2(k2,dist/'kernel.sbc');shutil.copy2(s2,dist/'sagac.sbc')
        env={'PATH':'/nonexistent','HOME':str(td)}
        rr=run([str(dist/'saga'),'run',str(entry)],env=env)
        mark('empty-PATH official SH-3 distribution execution',rr.returncode==0 and rr.stdout=='42\n',repr(rr.stdout))
        ri=run([str(dist/'saga'),'info'],env=env)
        mark('official SH-3 info identifies all-source self-hosting',ri.returncode==0 and 'all_runtime_source_self_hosted=true' in ri.stdout and 'version=0.38.0' in ri.stdout,repr(ri.stdout))
        sample=td/'seed-sample.saga';sample.write_text('print(42)\n');samplebc=td/'seed-sample.sbc'
        rc=run([str(dist/'sagac'),str(sample),str(samplebc)],env=env)
        rx=run([str(dist/'sh3vm'),str(samplebc)],env=env) if rc.returncode==0 else rc
        mark('empty-PATH self-host compiler executable',rc.returncode==0 and rx.returncode==0 and rx.stdout=='42\n',repr(rx.stdout if rc.returncode==0 else rc.stderr))

        audit=run([sys.executable,str(ROOT/'tools/sh3_audit.py')]);mark('SH-3 source-boundary audit',audit.returncode==0,audit.stdout.strip())
        evidence['compiler_stage2_sha256']=sha(s2);evidence['compiler_stage3_sha256']=sha(s3);evidence['kernel_sha256']=sha(k2);evidence['token_image_sha256']=sha(img1)
        evidence.update(source_binding(REL)); evidence['schema']=2
        evidence['success_cases']=len(cases['success']);evidence['diagnostic_cases']=len(cases['errors']);evidence['edition_2027_cases']=len(e27['cases']);evidence['pass']=all(x['pass'] for x in evidence['checks'])
    out=ROOT/f'validation/sh3-validation-{REL}.json';out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print('REPORT',out)
    return 0 if evidence['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

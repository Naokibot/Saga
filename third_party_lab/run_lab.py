from __future__ import annotations
import argparse, hashlib, json, platform, subprocess, time
from pathlib import Path

def sha(p:Path):
    h=hashlib.sha256();
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def run(cmd,cwd):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,encoding='utf-8',errors='replace')
    return {'argv':cmd,'returncode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--saga',required=True);ap.add_argument('--source-root',default='..');ap.add_argument('--lab-name',required=True);ap.add_argument('--lab-contact',required=True);ap.add_argument('--output',default='lab-evidence.json');a=ap.parse_args()
    here=Path(__file__).resolve().parent;root=(here/a.source_root).resolve();saga=Path(a.saga).resolve();manifest=json.loads((root/'conformance/manifest.json').read_text())
    rows=[];passed=0
    for t in manifest['tests']:
        src=root/'conformance'/t['file'];act='check' if t['mode']=='check-fail' else 'run';r=run([str(saga),act,str(src)],root);hay=r['stderr']+'\n'+r['stdout'];ok=(r['returncode']==t.get('exit_code',0) and (t['mode']!='run' or r['stdout']==t['stdout']) and (not (t.get('diagnostic_id') or t.get('diagnostic_code')) or (t.get('diagnostic_id') or t.get('diagnostic_code')) in hay));passed+=ok;rows.append({'id':t['id'],'source_sha256':sha(src),'execution':r,'pass':bool(ok)})
    ev={'schema':1,'profile':'Portable Core Level 1 external-lab evidence','language':manifest['language'],'conformance_manifest_version':manifest['version'],'lab':{'name':a.lab_name,'contact':a.lab_contact},'generated_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'host':platform.platform(),'saga_binary':str(saga),'saga_sha256':sha(saga),'tests':rows,'summary':{'total':len(rows),'passed':passed,'failed':len(rows)-passed,'pass':passed==len(rows)},'attestation':{'independent_lab_signature':'REQUIRED_FROM_LAB_AFTER_REVIEW','certificate_id':'REQUIRED_FROM_LAB_IF_ISSUED'}}
    Path(a.output).write_text(json.dumps(ev,ensure_ascii=False,indent=2)+'\n');print(json.dumps(ev['summary']));return 0 if ev['summary']['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

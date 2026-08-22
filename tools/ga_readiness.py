#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REL='0.50.0'
if str(ROOT/'tools') not in sys.path: sys.path.insert(0,str(ROOT/'tools'))
from review_evidence import verify_manifest

def load(path):
    p=Path(path)
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
    except Exception: return None

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def gate(status,reason,evidence=None):
    d={'status':status,'reason':reason}
    if evidence is not None: d['evidence']=evidence
    return d

def source_context():
    manifest=ROOT/f'release/source-manifest-{REL}.json'
    if not manifest.is_file(): return None,['release source manifest missing']
    ok,errors,current=verify_manifest(manifest,ROOT)
    if not ok: return None,errors
    return {'manifest':manifest,'manifest_sha256':sha(manifest),'tree_sha256':current['tree_sha256']},[]

def bound_pass(path:Path,ctx:dict,*,extra=None)->tuple[bool,str]:
    d=load(path)
    if not isinstance(d,dict): return False,'evidence missing or malformed'
    if d.get('pass') is not True: return False,'evidence pass is not true'
    if d.get('release')!=REL: return False,'evidence release mismatch'
    if d.get('source_manifest_sha256')!=ctx['manifest_sha256']: return False,'source manifest SHA-256 mismatch'
    if d.get('source_tree_sha256')!=ctx['tree_sha256']: return False,'source tree SHA-256 mismatch'
    if extra:
        ok,reason=extra(d)
        if not ok: return False,reason
    return True,'exact current-source-bound evidence passed'

def release_validation_check(d):
    if d.get('qualification_level')!='full' or d.get('quick') is not False: return False,'only full reviewer preflight qualifies; quick evidence is insufficient'
    required={'source manifest exact-tree verification','specification final-candidate lint','Go full regression','Go vet','Registry Protocol v1 Python-Go interoperability','Python-Go language differential conformance','Security API surface','Hosted API surface','Native game API surface','Browser host API surface','Universal app API surface','Machine smoke','Machine control software qualification','Production GA 0.50 qualification','Internal security audit','SH-3 source-boundary audit','Go Race Detector complete split qualification','Real Chromium integration','Parser/expression fuzz smoke'}
    checks=d.get('checks') if isinstance(d.get('checks'),list) else []
    names={c.get('name') for c in checks if isinstance(c,dict) and c.get('pass') is True}
    missing=sorted(required-names)
    if missing: return False,'full release validation missing successful checks: '+', '.join(missing)
    return True,'full current-source reviewer preflight passed'

def native_check(expected):
    required={'actual native host matches requested host','release source manifest matches checkout','Go toolchain present','Go toolchain starts','Go Native tests on target host','Go vet on target host','native build on target host','native executable SHA-256 recorded','native executable format matches host','native executable starts','native Standard Core conformance','native source check','native source execution'}
    def check(d):
        if d.get('native_host')!=expected: return False,f'native_host must be {expected}'
        expected_system={'linux':'Linux','windows':'Windows','macos':'Darwin'}[expected]
        host=d.get('host') if isinstance(d.get('host'),dict) else {}
        if host.get('system')!=expected_system: return False,f'host.system must be {expected_system}'
        if not d.get('binary_sha256') or len(str(d.get('binary_sha256')))!=64: return False,'native binary SHA-256 missing'
        checks=d.get('checks') if isinstance(d.get('checks'),list) else []
        names={c.get('name') for c in checks if isinstance(c,dict) and c.get('pass') is True}
        missing=sorted(required-names)
        if missing: return False,'missing successful native checks: '+', '.join(missing)
        return True,'target-host qualification passed'
    return check

def registry_check(d):
    if d.get('status')!='PASS': return False,'registry status is not PASS'
    tls=d.get('tls') if isinstance(d.get('tls'),dict) else {}
    if not tls.get('global_addresses'): return False,'registry evidence lacks globally routable TLS address'
    checks=d.get('checks') if isinstance(d.get('checks'),dict) else {}
    required={'source_manifest_exact_tree','public_verified_tls','python_publish','python_explicit_trust','immutable_version_rejected','go_publish_python_install','python_publish_go_install'}
    if not all(checks.get(k) is True for k in required): return False,'registry evidence is missing one or more mandatory checks'
    return True,'public HTTPS signed interoperability qualification passed'

def internal_check(d):
    issues=d.get('issues',[])
    if d.get('status')!='pass': return False,'internal audit status is not pass'
    if not isinstance(issues,list): return False,'internal audit issues is malformed'
    open_hi=[x for x in issues if isinstance(x,dict) and x.get('severity') in {'critical','high'}]
    if open_hi: return False,'internal audit has critical/high findings'
    return True,'internal current-source audit passed'

def external_check(d):
    findings=d.get('open_findings') if isinstance(d.get('open_findings'),dict) else {}
    if findings.get('critical_open')!=0 or findings.get('high_open')!=0: return False,'external audit has open critical/high findings'
    if not d.get('report_sha256') or not d.get('attestation_payload_sha256'): return False,'external audit binding fields missing'
    return True,'independent signed current-source audit passed'

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--platform',default=str(ROOT/f'validation/platform-qualification-{REL}.json')); ap.add_argument('--output',default=str(ROOT/f'validation/ga-readiness-{REL}.json')); a=ap.parse_args()
    gates={}; ctx,ctx_errors=source_context()
    if ctx is None:
        reason='Current source tree is not frozen to the release manifest: '+'; '.join(ctx_errors)
        for k in ('language-spec-1.0-final','compiler-runtime-conformance','self-host-fixed-point','second-implementation','native-desktop-hosts','live-signed-registry','security-evidence','developer-workflow','production-industrial-local'):
            gates[k]=gate('BLOCKED',reason)
        ready=False
    else:
        final_spec=ROOT/'SAGA_LANGUAGE_SPECIFICATION_1.0.md'; spec_review=ROOT/f'validation/spec-review-final-{REL}.json'
        sd=load(spec_review)
        spec_ok=isinstance(sd,dict) and sd.get('pass') is True and sd.get('release')==REL and final_spec.is_file() and sd.get('proposed_final_sha256')==sha(final_spec)
        gates['language-spec-1.0-final']=gate('PASS' if spec_ok else 'BLOCKED','Final 1.0 bytes must exactly match the independently approved proposed_final_sha256.',{'spec':str(final_spec) if final_spec.exists() else None,'review':str(spec_review) if spec_review.exists() else None})

        release_validation=ROOT/f'validation/release-validation-{REL}.json'; ok,reason=bound_pass(release_validation,ctx,extra=release_validation_check)
        gates['compiler-runtime-conformance']=gate('PASS' if ok else 'BLOCKED',reason,str(release_validation) if release_validation.exists() else None)

        sh3=ROOT/f'validation/sh3-validation-{REL}.json'; ok,reason=bound_pass(sh3,ctx)
        gates['self-host-fixed-point']=gate('PASS' if ok else 'BLOCKED',reason,str(sh3) if sh3.exists() else None)

        cross=ROOT/f'validation/cross-implementation-{REL}.json'; ok,reason=bound_pass(cross,ctx)
        gates['second-implementation']=gate('PASS' if ok else 'BLOCKED',reason,str(cross) if cross.exists() else None)

        host_evidence=[]; missing=[]
        for name in ('linux','windows','macos'):
            path=ROOT/f'validation/native-host-{name}-{REL}.json'; ok,reason=bound_pass(path,ctx,extra=native_check(name)); host_evidence.append({'host':name,'path':str(path),'pass':ok,'reason':reason})
            if not ok: missing.append(name)
        gates['native-desktop-hosts']=gate('PASS' if not missing else 'BLOCKED','Native-host execution must be current-source-bound and pass on Linux, Windows and macOS; missing/non-pass: '+', '.join(missing),host_evidence)

        registry=ROOT/f'validation/public-registry-live-{REL}.json'; ok,reason=bound_pass(registry,ctx,extra=registry_check)
        gates['live-signed-registry']=gate('PASS' if ok else 'BLOCKED',reason,str(registry) if registry.exists() else None)

        internal=ROOT/f'validation/internal-security-audit-{REL}.json'; external=ROOT/f'validation/external-security-audit-{REL}.json'
        iok,ireason=bound_pass(internal,ctx,extra=internal_check); eok,ereason=bound_pass(external,ctx,extra=external_check)
        security_ok=iok and eok
        gates['security-evidence']=gate('PASS' if security_ok else 'BLOCKED',('internal: '+ireason+'; external: '+ereason),{'internal':str(internal) if internal.exists() else None,'external':str(external) if external.exists() else None})

        production=ROOT/'validation/production-ga-0.50.0.json'; ok,reason=bound_pass(production,ctx)
        gates['production-industrial-local']=gate('PASS' if ok else 'BLOCKED',reason,str(production) if production.exists() else None)

        workflow_files=[ROOT/'saga/formatter.py',ROOT/'saga/linter.py',ROOT/'saga/lsp.py',ROOT/'saga/debugger.py',ROOT/'saga/registry.py',ROOT/'docs/GA_READINESS_1.0.md']
        workflow_ok=all(p.exists() for p in workflow_files) and gates['compiler-runtime-conformance']['status']=='PASS'
        gates['developer-workflow']=gate('PASS' if workflow_ok else 'BLOCKED','Formatter/linter/tests/LSP/debugger/package tooling must exist and the full current-source-bound release qualification must pass.',[str(p) for p in workflow_files if p.exists()])
        ready=all(x['status']=='PASS' for x in gates.values())

    platform=load(a.platform) or {'gates':[]}; pg={x.get('id'):x for x in platform.get('gates',[]) if isinstance(x,dict)}
    optional_ids=('vulkan-swapchain-present','machine-control-software','physical-machine-control','physical-gamepad','aws-live-account','physical-gpio','spark-runtime','pygame-runtime','android-device','ios-device')
    optional={k:pg.get(k,{'status':'NO_EVIDENCE'}) for k in optional_ids}
    doc={'schema':2,'release':REL,'target':'Saga GA 1.0','source_manifest_sha256':ctx['manifest_sha256'] if ctx else None,'source_tree_sha256':ctx['tree_sha256'] if ctx else None,'ga_ready':ready,'core_gates':gates,'optional_platform_profiles':optional,'note':'GA 1.0 is a project production-readiness designation, not ISO/IEC approval.'}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps(doc,indent=2,ensure_ascii=False)); return 0 if ready else 3
if __name__=='__main__': raise SystemExit(main())

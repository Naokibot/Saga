#!/usr/bin/env python3
"""Verify an independent signed Saga security-review attestation and bound report."""
from __future__ import annotations
import argparse, base64, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RELEASE='0.50.0'
if str(ROOT/'tools') not in sys.path: sys.path.insert(0,str(ROOT/'tools'))
from review_evidence import verify_manifest
REQUIRED_SCOPE={'compiler','runtime','package-manager','registry','capability-sandbox','crypto-tls','native-host-boundaries'}

def canonical(payload:dict)->bytes: return json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('attestation'); ap.add_argument('public_key')
    ap.add_argument('--report',required=True); ap.add_argument('--source-manifest',default=str(ROOT/f'release/source-manifest-{RELEASE}.json'))
    ap.add_argument('--output',default=str(ROOT/f'validation/external-security-audit-{RELEASE}.json'))
    a=ap.parse_args()
    att=json.loads(Path(a.attestation).read_text(encoding='utf-8')); payload=att.get('payload'); sig64=att.get('signature_ed25519_base64')
    required={'schema','target_release','source_manifest_sha256','auditor','completed_at_utc','scope','methods','report_sha256','critical_open','high_open','medium_open','low_open','independent','decision'}
    if not isinstance(payload,dict) or not required.issubset(payload): raise SystemExit('invalid or incomplete attestation payload')
    if payload['target_release']!=RELEASE: raise SystemExit(f'attestation target_release does not match {RELEASE}')
    if payload['independent'] is not True or payload['decision']!='PASS': raise SystemExit('auditor did not attest an independent PASS decision')
    for key in ('critical_open','high_open','medium_open','low_open'):
        n=payload[key]
        if isinstance(n,bool) or not isinstance(n,int): raise SystemExit(f'{key} must be an integer')
        if n<0: raise SystemExit(f'{key} must be nonnegative')
    if payload['critical_open']!=0 or payload['high_open']!=0: raise SystemExit('critical/high findings remain open')
    auditor=payload['auditor']
    if not isinstance(auditor,dict) or not str(auditor.get('organization','')).strip() or not str(auditor.get('reviewer','')).strip(): raise SystemExit('auditor identity incomplete')
    scope=set(map(str,payload['scope'])) if isinstance(payload['scope'],list) else set()
    missing=sorted(REQUIRED_SCOPE-scope)
    if missing: raise SystemExit('audit scope missing required areas: '+', '.join(missing))
    methods=set(map(str,payload['methods'])) if isinstance(payload['methods'],list) else set()
    if not {'source-review','dynamic-testing'}.issubset(methods): raise SystemExit('audit methods must include source-review and dynamic-testing')
    report=Path(a.report); manifest=Path(a.source_manifest)
    if not report.is_file(): raise SystemExit('audit report file missing')
    if not manifest.is_file(): raise SystemExit('release source manifest missing')
    if payload['report_sha256']!=sha(report): raise SystemExit('audit report SHA-256 mismatch')
    if payload['source_manifest_sha256']!=sha(manifest): raise SystemExit('source manifest SHA-256 mismatch')
    ok, manifest_errors, current = verify_manifest(manifest, ROOT)
    if not ok: raise SystemExit('source manifest does not match the reviewed source tree: ' + '; '.join(manifest_errors))
    for name,value in [('report_sha256',payload['report_sha256']),('source_manifest_sha256',payload['source_manifest_sha256'])]:
        if re.fullmatch(r'[0-9a-fA-F]{64}',str(value)) is None: raise SystemExit(name+' malformed')
    try:
        completed=datetime.fromisoformat(str(payload['completed_at_utc']).replace('Z','+00:00'))
        if completed.tzinfo is None or completed.utcoffset()!=timezone.utc.utcoffset(completed): raise ValueError
    except Exception: raise SystemExit('completed_at_utc must be an ISO-8601 UTC timestamp')
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        pub=bytes.fromhex(Path(a.public_key).read_text(encoding='utf-8').strip()); sig=base64.b64decode(sig64,validate=True); Ed25519PublicKey.from_public_bytes(pub).verify(sig,canonical(payload))
    except Exception as exc: raise SystemExit('signature verification failed: '+str(exc))
    doc={'schema':2,'release':RELEASE,'pass':True,'auditor':auditor,'scope':sorted(scope),'methods':sorted(methods),'report_sha256':payload['report_sha256'],'source_manifest_sha256':payload['source_manifest_sha256'],'source_tree_sha256':current['tree_sha256'],'open_findings':{k:payload[k] for k in ('critical_open','high_open','medium_open','low_open')},'attestation_payload_sha256':hashlib.sha256(canonical(payload)).hexdigest()}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps(doc,indent=2,ensure_ascii=False)); return 0
if __name__=='__main__': raise SystemExit(main())

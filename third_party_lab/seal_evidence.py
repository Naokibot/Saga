#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, json, subprocess, tempfile
from pathlib import Path

def canonical_payload(doc:dict)->bytes:
    d=json.loads(json.dumps(doc))
    att=d.setdefault('attestation',{})
    for k in ('signature_ed25519_base64','public_key_pem','payload_sha256','signed_at_utc'):
        att.pop(k,None)
    return (json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()

def main()->int:
    ap=argparse.ArgumentParser(description='Seal reviewed Saga lab evidence with a lab-owned Ed25519 key')
    ap.add_argument('evidence'); ap.add_argument('--private-key',required=True); ap.add_argument('--public-key',required=True)
    a=ap.parse_args(); p=Path(a.evidence); d=json.loads(p.read_text())
    if d.get('attestation',{}).get('independent_lab_signature')=='REQUIRED_FROM_LAB_AFTER_REVIEW':
        d['attestation']['independent_lab_signature']='ed25519-detached'
    payload=canonical_payload(d); digest=hashlib.sha256(payload).hexdigest()
    with tempfile.NamedTemporaryFile(delete=False) as f: f.write(payload); payload_path=f.name
    sig_path=payload_path+'.sig'
    try:
        subprocess.run(['openssl','pkeyutl','-sign','-rawin','-inkey',a.private_key,'-in',payload_path,'-out',sig_path],check=True)
        sig=Path(sig_path).read_bytes()
    finally:
        Path(payload_path).unlink(missing_ok=True); Path(sig_path).unlink(missing_ok=True)
    pub=Path(a.public_key).read_text()
    d['attestation'].update({'payload_sha256':digest,'signature_ed25519_base64':base64.b64encode(sig).decode(),'public_key_pem':pub})
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'sealed':True,'payload_sha256':digest,'signature_bytes':len(sig)}))
    return 0
if __name__=='__main__': raise SystemExit(main())

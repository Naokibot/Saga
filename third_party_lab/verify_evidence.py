#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,hashlib,json,subprocess,tempfile
from pathlib import Path

def canonical_payload(doc:dict)->bytes:
    d=json.loads(json.dumps(doc)); att=d.setdefault('attestation',{})
    for k in ('signature_ed25519_base64','public_key_pem','payload_sha256','signed_at_utc'): att.pop(k,None)
    return (json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('evidence');a=ap.parse_args();p=Path(a.evidence);d=json.loads(p.read_text())
    att=d.get('attestation',{}); payload=canonical_payload(d); digest=hashlib.sha256(payload).hexdigest()
    structural=bool(d.get('summary',{}).get('pass')) and len(d.get('saga_sha256',''))==64 and bool(d.get('lab',{}).get('name'))
    cryptographic=False; reason='missing signature/public key'
    if att.get('signature_ed25519_base64') and att.get('public_key_pem'):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); (td/'payload').write_bytes(payload); (td/'sig').write_bytes(base64.b64decode(att['signature_ed25519_base64'])); (td/'pub.pem').write_text(att['public_key_pem'])
            r=subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(td/'pub.pem'),'-rawin','-in',str(td/'payload'),'-sigfile',str(td/'sig')],capture_output=True,text=True)
            cryptographic=r.returncode==0; reason=(r.stdout+r.stderr).strip()
    digest_match=att.get('payload_sha256') in (None,'',digest)
    ok=structural and cryptographic and digest_match
    print(json.dumps({'schema':d.get('schema'),'tests_pass':d.get('summary',{}).get('pass'),'lab':d.get('lab',{}).get('name'),'evidence_file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'payload_sha256':digest,'payload_digest_match':digest_match,'structural_verification':structural,'ed25519_signature_valid':cryptographic,'verification':ok,'detail':reason},indent=2))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RELEASE='0.50.0'
CANDIDATE=ROOT/'SAGA_LANGUAGE_SPECIFICATION_1.0_FINAL_CANDIDATE.md'; GRAMMAR=ROOT/'spec/saga-1.0.ebnf'

def canonical(x:dict)->bytes: return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def proposed_final_bytes()->bytes:
    text=CANDIDATE.read_text(encoding='utf-8')
    text=text.replace('# Saga programming language — Language Specification 1.0 Final Candidate','# Saga programming language — Language Specification 1.0 Final',1)
    text=text.replace('This document is the project Final Candidate submitted for independent technical review.','This document is the project-published Saga Language Specification 1.0 Final.',1)
    text=text.replace('Language Edition 1.0 Final Candidate freezes the intended Standard Core semantics for independent review. Project publication as **Saga Language Specification 1.0 Final** requires a signed independent review attestation over the exact proposed-final bytes and closure of all normative-blocking review findings.','Language Edition 1.0 is the project-published Standard Core compatibility baseline. The signed independent review evidence used for publication is retained with the release evidence.',1)
    return text.encode('utf-8')

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('attestation'); ap.add_argument('public_key'); ap.add_argument('--output',default=str(ROOT/f'validation/spec-review-final-{RELEASE}.json')); a=ap.parse_args()
    att=json.loads(Path(a.attestation).read_text(encoding='utf-8')); payload=att.get('payload'); sig64=att.get('signature_ed25519_base64')
    if not isinstance(payload,dict): raise SystemExit('invalid attestation payload')
    required={'schema','target_release','reviewer','completed_at_utc','candidate_sha256','proposed_final_sha256','grammar_sha256','decision','independent','unresolved_normative_issues'}
    if not required.issubset(payload): raise SystemExit('missing required attestation fields')
    if payload['target_release']!=RELEASE: raise SystemExit('target release mismatch')
    if payload['candidate_sha256']!=sha(CANDIDATE): raise SystemExit('candidate SHA-256 mismatch')
    if payload['proposed_final_sha256']!=hashlib.sha256(proposed_final_bytes()).hexdigest(): raise SystemExit('proposed final SHA-256 mismatch')
    if payload['grammar_sha256']!=sha(GRAMMAR): raise SystemExit('grammar SHA-256 mismatch')
    unresolved=payload['unresolved_normative_issues']
    if isinstance(unresolved,bool) or not isinstance(unresolved,int): raise SystemExit('unresolved_normative_issues must be an integer')
    if payload['decision']!='APPROVE' or payload['independent'] is not True or unresolved!=0: raise SystemExit('review does not approve final publication')
    reviewer=payload['reviewer']
    if not isinstance(reviewer,dict) or not str(reviewer.get('name','')).strip() or not str(reviewer.get('organization','')).strip(): raise SystemExit('reviewer identity incomplete')
    try:
        d=datetime.fromisoformat(str(payload['completed_at_utc']).replace('Z','+00:00'))
        if d.tzinfo is None or d.utcoffset()!=timezone.utc.utcoffset(d): raise ValueError
    except Exception: raise SystemExit('completed_at_utc must be UTC')
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        pub=bytes.fromhex(Path(a.public_key).read_text().strip()); sig=base64.b64decode(sig64,validate=True); Ed25519PublicKey.from_public_bytes(pub).verify(sig,canonical(payload))
    except Exception as exc: raise SystemExit('signature verification failed: '+str(exc))
    doc={'schema':2,'release':RELEASE,'pass':True,'reviewer':reviewer,'candidate_sha256':payload['candidate_sha256'],'grammar_sha256':payload['grammar_sha256'],'proposed_final_sha256':payload['proposed_final_sha256'],'attestation_payload_sha256':hashlib.sha256(canonical(payload)).hexdigest()}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps(doc,indent=2,ensure_ascii=False)); return 0
if __name__=='__main__': raise SystemExit(main())

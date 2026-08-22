#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
from verify_spec_review_attestation import ROOT, proposed_final_bytes, RELEASE

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('attestation'); ap.add_argument('public_key'); a=ap.parse_args()
    rc=subprocess.run([sys.executable,str(ROOT/'tools/verify_spec_review_attestation.py'),a.attestation,a.public_key]).returncode
    if rc!=0: return rc
    out=ROOT/'SAGA_LANGUAGE_SPECIFICATION_1.0.md'; out.write_bytes(proposed_final_bytes()); print(out); return 0
if __name__=='__main__': raise SystemExit(main())

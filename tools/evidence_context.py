#!/usr/bin/env python3
from __future__ import annotations
import hashlib, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'tools') not in sys.path: sys.path.insert(0,str(ROOT/'tools'))
from review_evidence import verify_manifest

def source_binding(release: str) -> dict[str,str]:
    manifest=ROOT/f'release/source-manifest-{release}.json'
    if not manifest.is_file(): raise RuntimeError(f'missing source manifest for {release}')
    ok,errors,current=verify_manifest(manifest,ROOT)
    if not ok: raise RuntimeError('source manifest mismatch: '+'; '.join(errors))
    return {
        'source_manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'source_tree_sha256': current['tree_sha256'],
    }

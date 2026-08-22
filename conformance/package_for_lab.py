from __future__ import annotations
import argparse, hashlib, os, zipfile
from pathlib import Path

INCLUDE = [
    'README.md','LICENSE','pyproject.toml','saga.py','saga','tests','spec','conformance','third_party_lab',
    'implementations/go/cmd','implementations/go/go.mod','implementations/go/README.md',
    'tools/generate_unicode_go.py','tools/internal_security_audit.py','docs/standards','docs/iso','security',
    'docs/STANDARD_PROFILE.md','docs/IMPLEMENTATION_DEFINED_BEHAVIOR.md',
    'docs/CONFORMANCE_STATEMENT_TEMPLATE.md','compatibility/api-0.17.0.json',
]
EXCLUDE_NAMES={'__pycache__','.DS_Store'}

def files(root:Path):
    for item in INCLUDE:
        path=root/item
        if path.is_file():yield path
        elif path.is_dir():
            for child in sorted(path.rglob('*')):
                if child.is_file() and not any(part in EXCLUDE_NAMES for part in child.parts) and child.suffix!='.pyc':yield child

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='dist/saga-conformance-lab-0.17.0.zip');args=ap.parse_args()
    root=Path(__file__).resolve().parents[1];selected=list(dict.fromkeys(files(root)))
    manifest=[]
    for path in selected:
        data=path.read_bytes();manifest.append((hashlib.sha256(data).hexdigest(),str(path.relative_to(root)).replace(os.sep,'/')))
    readme='''Saga 0.17.0 independent conformance handoff\n\nBuild the Go implementation from implementations/go, install the Python package in a clean Python 3.13 environment, then run `python conformance/standard_core.py` and `python conformance/go_standard_core.py`. Run both implementation self-conformance commands as well. Do not treat project-generated validation as an independent certificate. Record additional tests, toolchains, platforms and deviations.\n'''
    out=root/args.output;out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('LAB_README.txt',readme)
        z.writestr('MANIFEST.sha256',''.join(f'{h}  {n}\n' for h,n in manifest))
        for path in selected:z.write(path,str(path.relative_to(root)).replace(os.sep,'/'))
    print(out)
    return 0
if __name__=='__main__':raise SystemExit(main())

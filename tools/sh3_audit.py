#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json, re, sys
ROOT=Path(__file__).resolve().parents[1]
manifest_path=ROOT/'implementations/sh3/OFFICIAL_IMPLEMENTATION.json'
manifest=json.loads(manifest_path.read_text())
canon=list(manifest['canonical_language_sources'].values())
seed_src=list(manifest['language_neutral_bootstrap_sources'])
seed_bin=manifest['bootstrap_compiler_seed']
problems=[]
for rel in canon:
    p=ROOT/rel
    if not p.exists(): problems.append(f'missing canonical Saga source: {rel}')
    elif p.suffix!='.saga': problems.append(f'canonical source is not Saga: {rel}')
for rel in seed_src+[seed_bin]:
    if not (ROOT/rel).exists(): problems.append(f'missing bootstrap artifact: {rel}')

# Static boundary audit for the non-Saga seed. Strip comments before scanning.
def strip_comments(s:str)->str:
    s=re.sub(r'/\*.*?\*/','',s,flags=re.S)
    s=re.sub(r'//[^\n]*','',s)
    return s
for rel in seed_src:
    s=strip_comments((ROOT/rel).read_text(errors='replace'))
    # The seed may parse SH3BC1, but must not grow Saga-language semantic entry points.
    funcs=re.findall(r'(?m)^\s*(?:static\s+)?(?:[A-Za-z_][\w\s\*]*?)\s+([A-Za-z_]\w*)\s*\(',s)
    badf=[f for f in funcs if re.search(r'(saga_?(lex|parse|check|type|class|generic|match|option|result)|standard_?core)',f,re.I)]
    if badf: problems.append(f'{rel}: semantic-looking seed functions: {badf}')
    strings=re.findall(r'"((?:\\.|[^"\\])*)"',s)
    forbidden={'class','interface','abstract','override','private','enum','record','match','option','result','throw','catch','finally','generic','where'}
    bads=sorted({x for x in strings if x in forbidden})
    if bads: problems.append(f'{rel}: Saga grammar keyword literals in seed: {bads}')

# Reference implementations are allowed only because they are explicitly outside the official path.
ref_files=[]
for rootrel in manifest.get('reference_implementations',[]):
    rr=ROOT/rootrel
    if rr.is_dir(): ref_files += [str(p.relative_to(ROOT)) for p in rr.rglob('*') if p.is_file()]

h=hashlib.sha256()
for rel in canon+seed_src+[seed_bin,'implementations/sh3/OFFICIAL_IMPLEMENTATION.json']:
    p=ROOT/rel; h.update(rel.encode()+b'\0'+p.read_bytes()+b'\0')
report={
  'schema':2,
  'profile':'SH-3 All-Source Self-Hosting',
  'release':manifest['release'],
  'pass':not problems,
  'official_canonical_saga_sources':canon,
  'language_neutral_bootstrap_sources':seed_src,
  'bootstrap_compiler_seed':seed_bin,
  'reference_sources_not_in_official_kernel':len(ref_files),
  'problems':problems,
  'official_source_set_sha256':h.hexdigest(),
  'rule':manifest['qualification_rule'],
}
out=ROOT/f"validation/sh3-audit-{manifest['release']}.json"
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pass':report['pass'],'problems':len(problems),'report':str(out)}))
raise SystemExit(0 if report['pass'] else 7)

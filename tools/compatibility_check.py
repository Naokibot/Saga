from __future__ import annotations
import argparse,json
from pathlib import Path

def flatten(api: dict) -> set[str]:
    items={f'keyword:{x}' for x in api['keywords']}|{f'builtin:{x}' for x in api['builtins']}
    for module,names in api['modules'].items():items|={f'module:{module}.{x}' for x in names}
    return items

def major(version:str)->int:return int(version.split('.')[0])

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('baseline');ap.add_argument('candidate');args=ap.parse_args()
    a=json.loads(Path(args.baseline).read_text(encoding='utf-8'));b=json.loads(Path(args.candidate).read_text(encoding='utf-8'))
    removed=sorted(flatten(a)-flatten(b));grammar_changed=a['grammar_sha256']!=b['grammar_sha256']
    semantic_changes=b.get('semantic_changes',[])
    source_compatible=not removed or major(b['version'])>major(a['version'])
    behavioral_compatible=not semantic_changes
    result={'baseline':a['version'],'candidate':b['version'],'removed':removed,'grammar_changed':grammar_changed,'semantic_changes':semantic_changes,'source_compatible':source_compatible,'behaviorally_compatible':behavioral_compatible,'compatible':source_compatible and behavioral_compatible}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['source_compatible'] else 1
if __name__=='__main__':raise SystemExit(main())

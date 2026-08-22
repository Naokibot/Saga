from __future__ import annotations
import json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GO=ROOT/'implementations/go/bin/saga-native-linux-amd64'
CASES={
'exact':'print(0.1 + 0.2 == 0.3)\nprint(1 / 3 + 1 / 6)',
'collections':'print(sort(unique([3,1,2,1])))\nprint(map_get(map_of("a",1),"a",0))',
'recursion':'fn fact(n:int)->int { if n <= 1 { return 1 } return n * fact(n-1) }\nprint(fact(7))',
'generic_fn':'fn first[T](xs:list[T])->T { return xs[0] }\nprint(first([8,9]), first(["a","b"]))',
'oop':'interface Named { fn name()->text }\nclass P(let n:text) implements Named { override fn name()->text=self.n }\nlet x:Named=P("Saga")\nprint(x.name())',
'generic_class':'class Box[T](let v:T) { fn get()->T=self.v }\nlet b:Box[int]=Box(42)\nprint(b.get())',
'closure':'fn make(start:int)->fn[int] { var n=start fn next()->int { n=n+1 return n } return next }\nlet c=make(5)\nprint(c(),c())',
'exception':'try { throw "boom" } catch e { print(e.kind,e.message) } finally { print("done") }',
'option_result':'let a:option[int]=some(4)\nlet r:result[int,text]=ok(7)\nprint(unwrap(a),unwrap_ok(r))',
'unicode':'let 合計=40+2\nprint(合計)',
}

def run(cmd): return subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,encoding='utf-8',errors='replace')
rows=[]; okall=True
with tempfile.TemporaryDirectory() as td:
  for name,src in CASES.items():
    p=Path(td)/(name+'.saga');p.write_text(src)
    py=run([sys.executable,'saga.py','run',str(p),'--language','en']);go=run([str(GO),'run',str(p)])
    ok=py.returncode==go.returncode==0 and py.stdout==go.stdout;okall &= ok
    rows.append({'id':name,'python_rc':py.returncode,'native_rc':go.returncode,'python_stdout':py.stdout.strip(),'native_stdout':go.stdout.strip(),'pass':ok})
out={'schema':1,'profile':'Standard Core extended cross-implementation subset','cases':rows,'summary':{'total':len(rows),'passed':sum(r['pass'] for r in rows),'pass':okall},'qualification':'Representative extended subset; does not replace the full Standard Core conformance suite.'}
(ROOT/'validation/cross-implementation-extended-0.17.0.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out['summary']))
raise SystemExit(0 if okall else 1)

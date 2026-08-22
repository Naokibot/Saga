from __future__ import annotations
import argparse, json, random, string, time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.api import compile_source, run_source
from saga.errors import SourceError


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--parse-cases',type=int,default=100000); ap.add_argument('--expr-cases',type=int,default=25000); ap.add_argument('--output',default='validation/fuzz-smoke-0.38.0.json'); args=ap.parse_args()
    randomizer=random.Random(20260807)
    alphabet=string.ascii_letters+string.digits+' _\n\t{}[]()=+-*/.,:;<>!"\'@#'+'日本語'
    unexpected=[]; start=time.perf_counter()
    for index in range(args.parse_cases):
        source=''.join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(0,180)))
        try: compile_source(source,f'<fuzz-{index}>')
        except SourceError: pass
        except Exception as exc: unexpected.append({'phase':'parse','index':index,'type':type(exc).__name__,'message':str(exc)}); break
    ops=['+','-','*','/','%','**','==','<']
    for index in range(args.expr_cases):
        expr=str(randomizer.randint(-20,20))
        for _ in range(randomizer.randint(1,8)):
            expr=f'({expr} {randomizer.choice(ops)} {randomizer.randint(-5,5)})'
        try: run_source('print('+expr+')',f'<expr-{index}>',output=lambda _:None,step_limit=10000)
        except SourceError: pass
        except Exception as exc: unexpected.append({'phase':'expression','index':index,'type':type(exc).__name__,'message':str(exc)}); break
    report={'schema':1,'seed':20260807,'parse_cases':args.parse_cases,'expression_cases':args.expr_cases,'unexpected_host_exceptions':unexpected,'duration_ms':round((time.perf_counter()-start)*1000,3),'pass':not unexpected}
    path=Path(args.output); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False)); return 0 if report['pass'] else 1
if __name__=='__main__': raise SystemExit(main())

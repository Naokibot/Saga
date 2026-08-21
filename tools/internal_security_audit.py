from __future__ import annotations
import ast, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.evidence_context import source_binding
issues=[]; notes=[]

def issue(sev,rule,path,line,msg): issues.append({'severity':sev,'rule':rule,'path':str(path.relative_to(ROOT)),'line':line,'message':msg})

for path in sorted((ROOT/'saga').rglob('*.py')):
    text=path.read_text(encoding='utf-8')
    try: tree=ast.parse(text,filename=str(path))
    except SyntaxError as e: issue('critical','PY-SYNTAX',path,e.lineno or 1,str(e));continue
    for n in ast.walk(tree):
        if isinstance(n,ast.Call):
            # shell=True is never accepted in runtime/installer code.
            for kw in n.keywords:
                if kw.arg=='shell' and isinstance(kw.value,ast.Constant) and kw.value.value is True:
                    issue('high','PROC-SHELL',path,n.lineno,'subprocess shell=True')
            if isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='os' and n.func.attr=='system':
                issue('high','PROC-OSSYSTEM',path,n.lineno,'os.system is forbidden')
            if isinstance(n.func,ast.Name) and n.func.id in {'eval'}:
                issue('high','DYNAMIC-EVAL',path,n.lineno,'eval is forbidden')
            if isinstance(n.func,ast.Name) and n.func.id=='exec':
                rel=str(path.relative_to(ROOT))
                if rel not in {'saga/plugin_host.py','saga/processor_host.py'}:
                    issue('high','DYNAMIC-EXEC',path,n.lineno,'exec outside isolated extension host')
                else:
                    notes.append({'rule':'DYNAMIC-EXEC-REVIEWED','path':rel,'line':n.lineno,'message':'exec is inside strict isolated host after AST policy validation'})
    # Do not allow compatibility identity to depend on localized message text.
    if re.search(r'(classify\s*\(|re\.search\([^\n]*message|message\s+in\s+)',text):
        issue('high','DIAG-PROSE-CLASSIFY',path,1,'diagnostic identity appears to parse prose')

# Dynamic plugin/sandbox checks are executed by the unit suite; ensure relevant files exist.
for required in ['saga/plugin_host.py','saga/plugin_runtime.py','saga/sandbox.py','tests/test_security_010.py','conformance/go_standard_core.py','saga/control_profile.py','saga/production.py','tests/test_control_ga_050.py','spec/SAGA_PRODUCTION_GA_CONTROL_0.50.md']:
    if not (ROOT/required).is_file(): issue('high','MISSING-SECURITY-COMPONENT',ROOT/required,1,'required component missing')

status='pass' if not [x for x in issues if x['severity'] in {'critical','high'}] else 'fail'
report={'schema':2,'release':'0.50.0',**source_binding('0.50.0'),'status':status,'pass':status=='pass','issues':issues,'reviewed_notes':notes,'limitations':['This is a project-internal automated review, not an independent third-party security audit.','No external vulnerability database scanner is installed in the execution environment.']}
out=ROOT/'validation/internal-security-audit-0.50.0.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'issues':len(issues),'reviewed_notes':len(notes),'report':str(out)},ensure_ascii=False))
raise SystemExit(0 if status=='pass' else 1)

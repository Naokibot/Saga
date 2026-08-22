#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one occurrence, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "saga/interpreter.py",
    '''        elif isinstance(stmt, ast.MatchStmt):
            value = self._evaluate(stmt.value)
            for case in stmt.cases:
                payload_match = self._match_enum_payload_pattern(value, case.pattern)
                if payload_match is not None:
                    env = Environment(self.environment)
                    for name, item in payload_match.items():
                        env.define(name, item, False)
                    self._execute_block(case.body.statements, env)
                    return
                pattern = self._evaluate(case.pattern)
''',
    '''        elif isinstance(stmt, ast.MatchStmt):
            value = self._evaluate(stmt.value)
            for case in stmt.cases:
                enum_pattern, payload_match = self._match_enum_payload_pattern(value, case.pattern)
                if enum_pattern:
                    if payload_match is None:
                        continue
                    env = Environment(self.environment)
                    for name, item in payload_match.items():
                        env.define(name, item, False)
                    self._execute_block(case.body.statements, env)
                    return
                pattern = self._evaluate(case.pattern)
''',
)

replace_once(
    "saga/interpreter.py",
    '''    def _match_enum_payload_pattern(self, value: object, pattern: ast.Expr) -> dict[str, object] | None:
        if not isinstance(value, EnumValue) or not isinstance(pattern, ast.Call):
            return None
        callee = pattern.callee
        if not isinstance(callee, ast.Member):
            return None
        qname = self._qualified_expr_name_runtime(callee.target)
        if qname is None:
            return None
        expected_enum = qname
        # Module aliases are part of the observable enum identity in the
        # interpreter.  Accept exact identity and the local/unqualified form.
        if value.enum_name != expected_enum and not value.enum_name.endswith("." + expected_enum):
            return None
        if value.variant != callee.name.lexeme or len(value.payload) != len(pattern.arguments):
            return None
        bindings: dict[str, object] = {}
        for expr, item in zip(pattern.arguments, value.payload):
            if not isinstance(expr, ast.Variable):
                return None
            name = expr.name.lexeme
            if name != "_":
                bindings[name] = item
        return bindings
''',
    '''    def _match_enum_payload_pattern(
        self, value: object, pattern: ast.Expr
    ) -> tuple[bool, dict[str, object] | None]:
        """Recognize a payload enum pattern without evaluating its bind variables.

        The boolean distinguishes "not an enum payload pattern" from "recognized
        enum pattern whose variant did not match".  Conflating those states made
        a failed `Some(item)` case fall back to normal expression evaluation,
        where `item` was incorrectly looked up as a runtime variable.
        """
        if not isinstance(value, EnumValue) or not isinstance(pattern, ast.Call):
            return False, None
        callee = pattern.callee
        if not isinstance(callee, ast.Member):
            return False, None
        qname = self._qualified_expr_name_runtime(callee.target)
        if qname is None:
            return False, None
        expected_enum = qname
        # Module aliases are part of the observable enum identity in the
        # interpreter. Accept exact identity and the local/unqualified form.
        if value.enum_name != expected_enum and not value.enum_name.endswith("." + expected_enum):
            return False, None
        if value.variant != callee.name.lexeme or len(value.payload) != len(pattern.arguments):
            return True, None
        bindings: dict[str, object] = {}
        for expr, item in zip(pattern.arguments, value.payload):
            if not isinstance(expr, ast.Variable):
                return True, None
            name = expr.name.lexeme
            if name != "_":
                bindings[name] = item
        return True, bindings
''',
)

replace_once(
    "implementations/go/cmd/saga-go/runtime.go",
    '''\t\tfor _, mc := range x.Cases {
\t\t\tif ev, ok := v.(EnumValue); ok {
\t\t\t\tif call, ok := mc.Pattern.(*Call); ok {
\t\t\t\t\tif m, ok := call.Callee.(*Member); ok {
\t\t\t\t\t\towner, qok := sourceQualifiedExprName(m.Target)
\t\t\t\t\t\tif qok && (ev.Enum == owner || strings.HasSuffix(ev.Enum, "."+owner)) && ev.Variant == m.Name && len(ev.Payload) == len(call.Args) {
\t\t\t\t\t\t\tenv := newEnv(i.Env)
\t\t\t\t\t\t\tvalid := true
\t\t\t\t\t\t\tfor idx, a := range call.Args {
\t\t\t\t\t\t\t\tvr, vok := a.(*Variable)
\t\t\t\t\t\t\t\tif !vok {
\t\t\t\t\t\t\t\t\tvalid = false
\t\t\t\t\t\t\t\t\tbreak
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\tif vr.Name != "_" {
\t\t\t\t\t\t\t\t\tenv.define(vr.Name, ev.Payload[idx], false)
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t}
\t\t\t\t\t\t\tif valid {
\t\t\t\t\t\t\t\treturn i.execBlock(mc.Body.Stmts, env)
\t\t\t\t\t\t\t}
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t\tp, pe := i.eval(mc.Pattern)
''',
    '''\t\tfor _, mc := range x.Cases {
\t\t\tif ev, ok := v.(EnumValue); ok {
\t\t\t\tif call, ok := mc.Pattern.(*Call); ok {
\t\t\t\t\tif m, ok := call.Callee.(*Member); ok {
\t\t\t\t\t\towner, qok := sourceQualifiedExprName(m.Target)
\t\t\t\t\t\tif qok && (ev.Enum == owner || strings.HasSuffix(ev.Enum, "."+owner)) {
\t\t\t\t\t\t\t// A payload pattern belonging to the matched enum is
\t\t\t\t\t\t\t// syntactic data, not an expression to evaluate. If its
\t\t\t\t\t\t\t// variant does not match, continue to the next case instead
\t\t\t\t\t\t\t// of resolving binding names as ordinary variables.
\t\t\t\t\t\t\tif ev.Variant != m.Name || len(ev.Payload) != len(call.Args) {
\t\t\t\t\t\t\t\tcontinue
\t\t\t\t\t\t\t}
\t\t\t\t\t\t\tenv := newEnv(i.Env)
\t\t\t\t\t\t\tvalid := true
\t\t\t\t\t\t\tfor idx, a := range call.Args {
\t\t\t\t\t\t\t\tvr, vok := a.(*Variable)
\t\t\t\t\t\t\t\tif !vok {
\t\t\t\t\t\t\t\t\tvalid = false
\t\t\t\t\t\t\t\t\tbreak
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\tif vr.Name != "_" {
\t\t\t\t\t\t\t\t\tenv.define(vr.Name, ev.Payload[idx], false)
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t}
\t\t\t\t\t\t\tif valid {
\t\t\t\t\t\t\t\treturn i.execBlock(mc.Body.Stmts, env)
\t\t\t\t\t\t\t}
\t\t\t\t\t\t\tcontinue
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t\tp, pe := i.eval(mc.Pattern)
''',
)

replace_once(
    "implementations/go/cmd/saga-go/generic_adts_051_test.go",
    '''func TestGenericADT051NullaryVariantNeedsContext(t *testing.T) {
''',
    '''func TestGenericADT051PayloadCaseFallsThroughToNullaryVariant(t *testing.T) {
\tsrc := `enum Maybe[T] { None, Some(T) }
let value: Maybe[int] = Maybe.None
match value {
case Maybe.Some(item) { print(item) }
case Maybe.None { print("empty") }
}`
\tout, err := runSagaForTest(t, src)
\tif err != nil {
\t\tt.Fatal(err)
\t}
\tif out != "empty" {
\t\tt.Fatalf("output=%q", out)
\t}
}

func TestGenericADT051NullaryVariantNeedsContext(t *testing.T) {
''',
)

print("Saga 0.51 enum match runtime fix staged successfully")

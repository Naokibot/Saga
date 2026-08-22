from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .api import compile_source, run_source
from .errors import SourceError


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    source: str
    expected: str | None = None
    error_code: str | None = None
    check_only: bool = False


CASES = (
    Case("SC001-exact-decimal", "print(0.1 + 0.2, 0.1 + 0.2 == 0.3)", "0.3 true"),
    Case("SC002-rational", "print(1 / 3 + 1 / 6)", "1/2"),
    Case("SC003-let", "let x = 1\nx = 2", error_code="SAGA-T001", check_only=True),
    Case("SC004-bool-condition", "if 1 { print(1) }", error_code="SAGA-T001", check_only=True),
    Case("SC005-range", "var s = 0\nfor n in 1..5 { s = s + n }\nprint(s)", "15"),
    Case("SC006-function", "fn add(a: int, b: int) -> int = a + b\nprint(add(20, 22))", "42"),
    Case("SC007-option", "let x: option[text] = none()\nprint(unwrap_or(x, \"none\"))", "none"),
    Case("SC008-exception", "try { throw \"boom\" } catch e { print(e.kind, e.message) }", "Thrown boom"),
    Case("SC009-bounds", "print([1][2])", error_code="SAGA-R001"),
    Case("SC010-power", "print(-2 ** 2, 2 ** 3 ** 2)", "-4 512"),
    Case("SC011-unicode", "let 合計 = 42\nprint(合計)", "42"),
    Case("SC012-identity", "class Box(let x: int) {}\nlet a = Box(1)\nlet b = Box(1)\nprint(a == a, a == b)", "true false"),
    Case("SC013-closure", "fn make(start:int)->fn[int]{ var n=start fn next()->int { n=n+1 return n } return next }\nlet c=make(5)\nprint(c())\nprint(c())", "6\n7"),
    Case("SC014-remainder-sign", "print(-2 % 7, 7 % -3, -7 % -3)", "-2 1 -1"),
    Case("SC015-natural-binding", 'name = "Saga"\nprint(name)', "Saga"),
    Case("SC016-natural-map", "values = [1, 2, 3]\nprint(values.map { it * 2 })", "[2, 4, 6]"),
    Case("SC017-explicit-closure", "values = [1, 2, 3]\nprint(values.fold(0) { total, n -> total + n })", "6"),
    Case("SC018-pipeline", "values = [1, 2, 3]\nprint(values |> filter { it > 1 } |> transform { it * 2 })", "[4, 6]"),
    Case("SC019-first-class-closure", 'greet = { print("Hello") }\ngreet()', "Hello"),
    Case("SC020-closure-return", "values = [1, 2]\nprint(values.map { if it > 1 { return it * 10 } return it })", "[1, 20]"),
    Case("SC021-control-call-brace", 'fn ready() -> bool { return true }\nif ready() { print("yes") }', "yes"),
    Case("SC022-natural-pipeline-names", "values = [3, 1, 2, 2]\nprint(values |> map { it * 2 } |> distinct |> sorted |> take(2))", "[2, 4]"),
    Case("SC023-legacy-pipeline-order", "fn add(a:int,b:int)->int { return a+b }\nvalues=[1,2,3]\nprint(values |> reduce(add, 0))", "6"),
    Case("SC024-duplicate-closure-parameters", "let f: fn[int,int,int] = { x, x -> x }", error_code="SAGA-P001", check_only=True),
    Case("SC025-result-propagation", 'fn source(okay:bool)->result[int,text]{if okay{return ok(4)} return err("bad")}\nfn consume(okay:bool)->result[int,text]{let value=source(okay)? return ok(value+1)}\nprint(consume(true), consume(false))', "ok(5) err(bad)"),
    Case("SC026-natural-each", "values=[1,2,3]\nvar total=0\nvalues.each { total=total+it }\nprint(total)", "6"),
    Case("SC027-natural-find", "values=[1,2,3]\nprint(unwrap_or(values.find { it>1 },0))", "2"),
    Case("SC028-natural-none", "values=[1,2,3]\nprint(values.none { it>3 })", "true"),
    Case("SC029-natural-sorted-by", "values=[3,1,2]\nprint(values.sortedBy { -it })", "[3, 2, 1]"),
    Case("SC030-natural-skip", "values=[1,2,3]\nprint(values.skip(1))", "[2, 3]"),
    Case("SC031-natural-zip", "print([1,2].zip([3,4]))", "[[1, 3], [2, 4]]"),
    Case("SC032-natural-flatten", "print([[1,2],[3]].flatten())", "[1, 2, 3]"),
    Case("SC033-natural-flat-map", "print([1,2].flatMap { [it,it] })", "[1, 1, 2, 2]"),
    Case("SC034-natural-chunk", "print([1,2,3].chunk(2))", "[[1, 2], [3]]"),
    Case("SC035-natural-window", "print([1,2,3].window(2))", "[[1, 2], [2, 3]]"),
    Case("SC036-natural-text", 'print(" Saga ".trim().upper())\nprint("a,b".split(","))', "SAGA\n[a, b]"),
    Case("SC037-natural-map-value", 'let m=map_of("a",1)\nprint(m.containsKey("a"))\nprint(unwrap_or(m.get("b"),9))', "true\n9"),
    Case("SC038-natural-set", "let s=set_of(1,2)\nprint(s.contains(2))\nprint(s.toList())", "true\n[1, 2]"),
    Case("SC039-natural-group", "print([1,1,2].group())", "{1: [1, 1], 2: [2]}"),
    Case("SC040-natural-group-by", "print([1,2,3].groupBy { it % 2 })", "{1: [1, 3], 0: [2]}"),
    Case("SC041-natural-bare-call", 'print "Hello"\nfn add(a:int,b:int)->int{return a+b}\nprint add(2,3)', "Hello\n5"),
    Case("SC042-natural-bare-call-block", 'fn panel(title:text,body:fn[unit]){print(title) body()}\npanel "Todo" { print("inside") }', "Todo\ninside"),
    Case("SC043-bare-call-subtraction-guard", "let n=3\nprint(n - 1)", "2"),
    Case("SC044-remainder-zero-diagnostic", "print(1 % 0)", error_code="SAGA-R001"),
    Case("SC045-enum-match", "enum State { Ready, Running, Done }\nlet state: State = State.Running\nmatch state { case State.Ready { print(1) } case State.Running { print(2) } case State.Done { print(3) } }", "2"),
    Case("SC046-unless", 'let ready=false\nunless ready { print "not ready" }', "not ready"),
    Case("SC047-tagged-union-payload", 'enum Result { Ok(int), Err(text) }\nlet value: Result = Result.Ok(42)\nmatch value { case Result.Ok(number) { print(number) } case Result.Err(message) { print(message) } }', "42"),
    Case("SC048-tagged-union-equality", 'enum Pair { Value(int,text), Empty }\nprint(Pair.Value(7,"x") == Pair.Value(7,"x"))\nprint(Pair.Value(7,"x") == Pair.Value(8,"x"))', "true\nfalse"),
)


def run_self_conformance() -> dict:
    records: list[dict] = []
    for case in CASES:
        output: list[str] = []
        actual_error: str | None = None
        try:
            if case.check_only:
                compile_source(case.source, f"<{case.id}>")
            else:
                run_source(case.source, f"<{case.id}>", output=output.append)
        except SourceError as exc:
            actual_error = exc.code
        actual_output = "\n".join(output)
        passed = actual_error == case.error_code if case.error_code else actual_error is None and actual_output == case.expected
        records.append({
            "id": case.id,
            "pass": passed,
            "expected_output": case.expected,
            "actual_output": actual_output,
            "expected_error": case.error_code,
            "actual_error": actual_error,
        })
    passed = sum(item["pass"] for item in records)
    return {"schema": 1, "language": "Saga", "version": "0.50.0", "language_edition": "Production GA Control 0.50 / Advanced Motion Control 0.47 / Precision Machine Control 0.46 / Language Synthesis 0.45 / Native Runtime ABI 0.35", "natural_core_version": "0.29", "module_core_version": "0.30", "native_object_core_version": "0.31", "native_codegen_abi_version": "0.32", "native_value_abi_version": "0.33", "native_aggregate_abi_version": "0.35", "gc_preview_version": "0.38", "total": len(records), "passed": passed, "pass": passed == len(records), "cases": records}

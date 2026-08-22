from __future__ import annotations

"""Restricted Saga @control_tick -> freestanding C proof backend.

This tool is intentionally a qualification backend, not Saga's general MCU
compiler.  It accepts only scalar arithmetic/control flow already admitted by
Saga's @control_tick checker.  The emitted C uses preallocated caller state and
contains no heap API by construction.  The qualification pipeline compiles the
output for Cortex-M4F and inspects the object for unresolved allocator calls.
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from saga import ast_nodes as ast
from saga.api import compile_source
from saga.control_profile import is_control_tick
from saga.tokens import TokenKind


class ControlTickCodegenError(RuntimeError):
    pass


C_TYPES = {
    "decimal": "float",
    "int": "int",
    "bool": "unsigned char",
}


BINOPS = {
    TokenKind.PLUS: "+",
    TokenKind.MINUS: "-",
    TokenKind.STAR: "*",
    TokenKind.SLASH: "/",
    TokenKind.PERCENT: "%",
    TokenKind.EQUAL_EQUAL: "==",
    TokenKind.BANG_EQUAL: "!=",
    TokenKind.LESS: "<",
    TokenKind.LESS_EQUAL: "<=",
    TokenKind.GREATER: ">",
    TokenKind.GREATER_EQUAL: ">=",
    TokenKind.AND: "&&",
    TokenKind.OR: "||",
}

UNOPS = {
    TokenKind.PLUS: "+",
    TokenKind.MINUS: "-",
    TokenKind.BANG: "!",
    TokenKind.NOT: "!",
}


def _annotation_name(annotation: ast.Annotation) -> str:
    return annotation.name.lexeme


def _literal(value: object) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, Decimal):
        text = format(value, "f")
        if "." not in text:
            text += ".0"
        return text + "f"
    if isinstance(value, int):
        return str(value)
    raise ControlTickCodegenError(f"unsupported literal: {value!r}")


def _expr(node: ast.Expr) -> str:
    if isinstance(node, ast.Literal):
        return _literal(node.value)
    if isinstance(node, ast.Variable):
        return node.name.lexeme
    if isinstance(node, ast.Unary):
        op = UNOPS.get(node.operator.kind)
        if op is None:
            raise ControlTickCodegenError(f"unsupported unary operator: {node.operator.lexeme}")
        return f"({op}{_expr(node.right)})"
    if isinstance(node, ast.Binary):
        op = BINOPS.get(node.operator.kind)
        if op is None:
            raise ControlTickCodegenError(f"unsupported binary operator: {node.operator.lexeme}")
        return f"({_expr(node.left)} {op} {_expr(node.right)})"
    raise ControlTickCodegenError(f"unsupported expression node: {type(node).__name__}")


def _ctype(type_name: str | None) -> str:
    if not type_name or type_name not in C_TYPES:
        raise ControlTickCodegenError(f"unsupported control-tick type: {type_name!r}")
    return C_TYPES[type_name]


def _stmt_lines(stmt: ast.Stmt, indent: int = 1) -> list[str]:
    pad = "    " * indent
    if isinstance(stmt, ast.VarDecl):
        return [f"{pad}{_ctype(stmt.type_name)} {stmt.name.lexeme} = {_expr(stmt.initializer)};"]
    if isinstance(stmt, ast.Assign):
        if not isinstance(stmt.target, ast.Variable):
            raise ControlTickCodegenError("qualification backend only supports scalar variable assignment")
        return [f"{pad}{stmt.target.name.lexeme} = {_expr(stmt.value)};"]
    if isinstance(stmt, ast.ReturnStmt):
        if stmt.value is None:
            return [f"{pad}return;"]
        return [f"{pad}return {_expr(stmt.value)};"]
    if isinstance(stmt, ast.ExpressionStmt):
        return [f"{pad}{_expr(stmt.expression)};"]
    if isinstance(stmt, ast.IfStmt):
        out = [f"{pad}if ({_expr(stmt.condition)}) {{"]
        for child in stmt.then_branch.statements:
            out.extend(_stmt_lines(child, indent + 1))
        out.append(f"{pad}}}")
        if stmt.else_branch is not None:
            out[-1] += " else {"
            for child in stmt.else_branch.statements:
                out.extend(_stmt_lines(child, indent + 1))
            out.append(f"{pad}}}")
        return out
    if isinstance(stmt, ast.ForStmt):
        if not isinstance(stmt.iterable, ast.RangeExpr):
            raise ControlTickCodegenError("control-tick for requires literal range")
        if not isinstance(stmt.iterable.start, ast.Literal) or not isinstance(stmt.iterable.end, ast.Literal):
            raise ControlTickCodegenError("control-tick for range must be literal")
        start, end = int(stmt.iterable.start.value), int(stmt.iterable.end.value)
        # Saga 0..N is inclusive in the language surface used by the checker.
        out = [f"{pad}for (int {stmt.name.lexeme} = {start}; {stmt.name.lexeme} <= {end}; ++{stmt.name.lexeme}) {{"]
        for child in stmt.body.statements:
            out.extend(_stmt_lines(child, indent + 1))
        out.append(f"{pad}}}")
        return out
    raise ControlTickCodegenError(f"unsupported statement node: {type(stmt).__name__}")


def emit_control_tick_c(source: str, function_name: str | None = None) -> str:
    program = compile_source(source, "<control-tick-cgen>")
    functions = [s for s in program.statements if isinstance(s, ast.FunctionDecl) and is_control_tick(s)]
    if function_name is not None:
        functions = [f for f in functions if f.name.lexeme == function_name]
    if len(functions) != 1:
        raise ControlTickCodegenError(f"expected exactly one @control_tick function, found {len(functions)}")
    fn = functions[0]
    if fn.body is None:
        raise ControlTickCodegenError("expression-only control ticks are not supported by qualification backend")
    params = ", ".join(f"{_ctype(p.type_name)} {p.name.lexeme}" for p in fn.parameters)
    lines = [
        "/* Generated by Saga 0.47 Virtual-HIL qualification backend 0.48. */",
        "/* Restricted scalar @control_tick subset; no heap/runtime dependency. */",
        f"{_ctype(fn.return_type)} saga_{fn.name.lexeme}({params}) {{",
    ]
    for stmt in fn.body.statements:
        lines.extend(_stmt_lines(stmt, 1))
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--function")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    text = Path(args.source).read_text(encoding="utf-8")
    Path(args.output).write_text(emit_control_tick_c(text, args.function), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

from . import ast_nodes as ast


def _value(expr: ast.Expr) -> object:
    if isinstance(expr, ast.Literal):
        if isinstance(expr.value, (Decimal, Fraction)): return str(expr.value)
        return expr.value
    if isinstance(expr, ast.ListLiteral): return [_value(item) for item in expr.elements]
    return "<expression>"


def _annotations(items: list[ast.Annotation]) -> dict[str, list[object]]:
    return {item.name.lexeme: [_value(arg) for arg in item.arguments] for item in items}


def extract_metadata(program: ast.Program) -> dict[str, object]:
    classes: list[dict[str, object]] = []
    functions: list[dict[str, object]] = []
    variables: list[dict[str, object]] = []
    modules: list[str] = []
    for stmt in program.statements:
        if isinstance(stmt, ast.UseStmt): modules.append(stmt.module.lexeme)
        elif isinstance(stmt, ast.FunctionDecl):
            functions.append({
                "name": stmt.name.lexeme,
                "type_params": stmt.type_params,
                "parameters": [{"name": p.name.lexeme, "type": p.type_name} for p in stmt.parameters],
                "return_type": stmt.return_type or ("unit" if stmt.body is not None else "inferred"),
                "annotations": _annotations(stmt.annotations),
                "abstract": stmt.abstract,
            })
        elif isinstance(stmt, ast.VarDecl):
            variables.append({"name": stmt.name.lexeme, "mutable": stmt.mutable, "type": stmt.type_name or "inferred", "annotations": _annotations(stmt.annotations)})
        elif isinstance(stmt, ast.ClassDecl):
            classes.append({
                "name": stmt.name.lexeme,
                "type_params": stmt.type_params,
                "base": stmt.base_name,
                "interfaces": list(stmt.interfaces),
                "abstract": stmt.abstract,
                "interface": stmt.interface,
                "annotations": _annotations(stmt.annotations),
                "fields": [
                    {"name": f.name.lexeme, "type": f.type_name, "mutable": f.mutable, "private": f.private}
                    for f in stmt.fields
                ],
                "methods": [
                    {
                        "name": m.name.lexeme,
                        "type_params": m.type_params,
                        "parameters": [{"name": p.name.lexeme, "type": p.type_name} for p in m.parameters],
                        "return_type": m.return_type or ("unit" if m.body is not None else "inferred"),
                        "annotations": _annotations(m.annotations),
                        "abstract": m.abstract,
                    }
                    for m in stmt.methods
                ],
            })
    return {"modules": modules, "variables": variables, "functions": functions, "classes": classes}

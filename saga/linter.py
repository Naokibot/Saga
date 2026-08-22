from __future__ import annotations

from dataclasses import dataclass
from dataclasses import fields, is_dataclass
import re

from . import ast_nodes as ast


@dataclass(frozen=True, slots=True)
class LintDiagnostic:
    code: str
    message: str
    line: int
    column: int
    severity: str = "warning"

    def render(self, filename: str) -> str:
        return f"{filename}:{self.line}:{self.column}: {self.severity} {self.code}: {self.message}"


_CANONICAL_TYPES = {
    "Int": "int", "integer": "int", "Decimal": "decimal", "number": "decimal",
    "Rational": "rational", "fraction": "rational", "Bool": "bool", "boolean": "bool",
    "Text": "text", "String": "text", "string": "text", "Unit": "unit",
    "Range": "range", "Any": "any", "Bytes": "bytes", "Error": "error",
    "DateTime": "datetime", "Duration": "duration",
}

_NATURAL_COLLECTION_REPLACEMENTS = {
    "transform": "list.map(function)",
    "filter": "list.filter(function)",
    "reduce": "list.fold(initial, function)",
    "any": "list.any(function)",
    "all": "list.all(function)",
    "sort": "list.sorted()",
    "unique": "list.distinct()",
}


def _type_warnings(type_name: str | None, line: int, column: int, standard: bool) -> list[LintDiagnostic]:
    if not type_name:
        return []
    result: list[LintDiagnostic] = []
    for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", type_name):
        canonical = _CANONICAL_TYPES.get(word)
        if canonical:
            result.append(LintDiagnostic("S101", f"型名 '{word}' ではなく標準表記 '{canonical}' を使用してください", line, column))
        if word.lower() == "any":
            severity = "error" if standard else "warning"
            result.append(LintDiagnostic("S102", "any は外部境界に限定し、公開APIでは具体的な型を使用してください", line, column, severity))
    return result


def lint_program(program: ast.Program, *, standard: bool = False) -> list[LintDiagnostic]:
    result: list[LintDiagnostic] = []

    def natural_surface(node: ast.Node) -> None:
        if isinstance(node, ast.Call) and isinstance(node.callee, ast.Variable):
            replacement = _NATURAL_COLLECTION_REPLACEMENTS.get(node.callee.name.lexeme)
            if replacement:
                result.append(LintDiagnostic(
                    "S106",
                    f"'{node.callee.name.lexeme}(...)' は互換表記です。新しいコードでは {replacement} を優先してください。saga migrate で安全な箇所を変換できます",
                    node.callee.name.line,
                    node.callee.name.column,
                ))
        if not is_dataclass(node):
            return
        for descriptor in fields(node):
            value = getattr(node, descriptor.name)
            if isinstance(value, ast.Node):
                natural_surface(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.Node): natural_surface(item)

    def function(fn: ast.FunctionDecl, *, public_api: bool) -> None:
        if public_api and fn.return_type is None:
            severity = "error" if standard else "warning"
            result.append(LintDiagnostic("S103", f"公開関数 '{fn.name.lexeme}' の戻り値型を明示してください", fn.name.line, fn.name.column, severity))
        result.extend(_type_warnings(fn.return_type, fn.name.line, fn.name.column, standard))
        for param in fn.parameters:
            result.extend(_type_warnings(param.type_name, param.name.line, param.name.column, standard))

    for stmt in program.statements:
        natural_surface(stmt)
        if isinstance(stmt, ast.UseStmt) and stmt.module.lexeme in {"plugin", "process", "cloud"}:
            result.append(LintDiagnostic("S104", f"'{stmt.module.lexeme}' はホスト権限を拡張するため、信頼境界を文書化してください", stmt.module.line, stmt.module.column))
        elif isinstance(stmt, ast.VarDecl):
            result.extend(_type_warnings(stmt.type_name, stmt.name.line, stmt.name.column, standard))
        elif isinstance(stmt, ast.FunctionDecl):
            function(stmt, public_api=True)
        elif isinstance(stmt, ast.ClassDecl):
            for field in stmt.fields:
                result.extend(_type_warnings(field.type_name, field.name.line, field.name.column, standard))
                if field.mutable and not field.private:
                    result.append(LintDiagnostic("S105", f"公開varフィールド '{field.name.lexeme}' は状態変更を外部へ露出します", field.name.line, field.name.column))
            for method in stmt.methods:
                function(method, public_api=not method.abstract)
    return sorted(result, key=lambda item: (item.line, item.column, item.code))

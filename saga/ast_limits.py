from __future__ import annotations

from dataclasses import fields, is_dataclass

from . import ast_nodes as ast


def ast_node_count(program: ast.Program) -> int:
    stack: list[object] = [program]
    count = 0
    while stack:
        value = stack.pop()
        if isinstance(value, ast.Node):
            count += 1
            if is_dataclass(value):
                for descriptor in fields(value):
                    stack.append(getattr(value, descriptor.name))
        elif isinstance(value, (list, tuple)):
            stack.extend(value)
    return count


def validate_ast_size(program: ast.Program, filename: str) -> None:
    """Compatibility hook retained for pre-0.8 callers.

    Saga 0.9 has no normative AST-node ceiling.  The traversal is intentionally
    no longer used as a rejection criterion.
    """
    return None

from __future__ import annotations

from dataclasses import dataclass, field

from .tokens import Token


class Node: pass
class Expr(Node): pass
class Stmt(Node): pass


@dataclass(slots=True)
class Annotation(Node):
    name: Token
    arguments: list[Expr]


@dataclass(slots=True)
class Program(Node):
    statements: list[Stmt]


@dataclass(slots=True)
class Literal(Expr):
    value: object
    token: Token


@dataclass(slots=True)
class Variable(Expr):
    name: Token


@dataclass(slots=True)
class ListLiteral(Expr):
    elements: list[Expr]
    token: Token


@dataclass(slots=True)
class Unary(Expr):
    operator: Token
    right: Expr


@dataclass(slots=True)
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr


@dataclass(slots=True)
class RangeExpr(Expr):
    start: Expr
    operator: Token
    end: Expr


@dataclass(slots=True)
class Call(Expr):
    callee: Expr
    paren: Token
    arguments: list[Expr]


@dataclass(slots=True)
class Index(Expr):
    target: Expr
    bracket: Token
    index: Expr


@dataclass(slots=True)
class Member(Expr):
    target: Expr
    dot: Token
    name: Token


@dataclass(slots=True)
class PropagateExpr(Expr):
    value: Expr
    question: Token


@dataclass(slots=True)
class AwaitExpr(Expr):
    value: Expr
    keyword: Token


@dataclass(slots=True)
class MoveExpr(Expr):
    value: Expr
    keyword: Token


@dataclass(slots=True)
class ClosureExpr(Expr):
    """A lexical block used as a first-class callable.

    A closure without an explicit parameter list is context-sensitive: collection
    APIs may supply the conventional ``it`` binding, while zero-argument DSLs
    simply execute the block without one.  This keeps the surface syntax small
    without introducing a separate lambda language.
    """

    brace: Token
    parameters: list[Token]
    body: "Block"
    implicit_parameter: bool = True


@dataclass(slots=True)
class ExpressionStmt(Stmt):
    expression: Expr


@dataclass(slots=True)
class UseStmt(Stmt):
    keyword: Token
    module: Token
    source_path: str | None = None
    alias: Token | None = None


@dataclass(slots=True)
class ModuleDecl(Stmt):
    keyword: Token
    name: Token


@dataclass(slots=True)
class SourceModuleStmt(Stmt):
    name: str
    bind_name: str
    statements: list[Stmt]
    token: Token
    interface: dict | None = None


@dataclass(slots=True)
class EnumVariantDecl(Node):
    name: Token
    payload_types: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EnumDecl(Stmt):
    keyword: Token
    name: Token
    variants: list[EnumVariantDecl]
    visibility: str = "internal"
    type_params: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MatchCase(Node):
    keyword: Token
    pattern: Expr
    body: "Block"


@dataclass(slots=True)
class MatchStmt(Stmt):
    keyword: Token
    value: Expr
    cases: list[MatchCase]
    default: "Block | None" = None


@dataclass(slots=True)
class VarDecl(Stmt):
    keyword: Token
    name: Token
    mutable: bool
    type_name: str | None
    initializer: Expr
    annotations: list[Annotation] = field(default_factory=list)
    visibility: str = "internal"


@dataclass(slots=True)
class Assign(Stmt):
    target: Expr
    equals: Token
    value: Expr


@dataclass(slots=True)
class Block(Stmt):
    statements: list[Stmt]


@dataclass(slots=True)
class IfStmt(Stmt):
    keyword: Token
    condition: Expr
    then_branch: Block
    else_branch: Block | None


@dataclass(slots=True)
class WhileStmt(Stmt):
    keyword: Token
    condition: Expr
    body: Block


@dataclass(slots=True)
class ForStmt(Stmt):
    keyword: Token
    name: Token
    iterable: Expr
    body: Block


@dataclass(slots=True)
class BreakStmt(Stmt):
    keyword: Token


@dataclass(slots=True)
class ContinueStmt(Stmt):
    keyword: Token


@dataclass(slots=True)
class ReturnStmt(Stmt):
    keyword: Token
    value: Expr | None


@dataclass(slots=True)
class ThrowStmt(Stmt):
    keyword: Token
    value: Expr


@dataclass(slots=True)
class DeferStmt(Stmt):
    keyword: Token
    value: Expr


@dataclass(slots=True)
class UsingStmt(Stmt):
    keyword: Token
    name: Token
    initializer: Expr
    body: "Block"


@dataclass(slots=True)
class TaskGroupStmt(Stmt):
    keyword: Token
    body: "Block"


@dataclass(slots=True)
class TryStmt(Stmt):
    keyword: Token
    try_block: Block
    catch_name: Token | None
    catch_block: Block | None
    finally_block: Block | None


@dataclass(slots=True)
class Parameter(Node):
    name: Token
    type_name: str


@dataclass(slots=True)
class FunctionDecl(Stmt):
    keyword: Token
    name: Token
    parameters: list[Parameter]
    return_type: str | None
    body: Block | None
    expression_body: Expr | None
    type_params: list[str] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    abstract: bool = False
    override: bool = False
    visibility: str = "internal"
    async_: bool = False


@dataclass(slots=True)
class FieldDecl(Node):
    name: Token
    type_name: str
    mutable: bool = False
    private: bool = False


@dataclass(slots=True)
class ClassDecl(Stmt):
    keyword: Token
    name: Token
    fields: list[FieldDecl]
    methods: list[FunctionDecl]
    type_params: list[str] = field(default_factory=list)
    base_name: str | None = None
    interfaces: list[str] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    abstract: bool = False
    interface: bool = False
    visibility: str = "internal"

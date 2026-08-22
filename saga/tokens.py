from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    EOF = auto()
    IDENT = auto()
    INT = auto()
    DECIMAL = auto()
    STRING = auto()

    LET = auto(); VAR = auto(); FN = auto(); RETURN = auto()
    IF = auto(); ELSE = auto(); WHILE = auto(); FOR = auto(); IN = auto()
    BREAK = auto(); CONTINUE = auto(); TRUE = auto(); FALSE = auto()
    AND = auto(); OR = auto(); NOT = auto()
    USE = auto(); TRY = auto(); CATCH = auto(); FINALLY = auto(); THROW = auto()
    CLASS = auto(); INTERFACE = auto(); ABSTRACT = auto(); EXTENDS = auto(); IMPLEMENTS = auto()
    PRIVATE = auto(); PUBLIC = auto(); INTERNAL = auto(); OVERRIDE = auto()
    MODULE = auto(); AS = auto(); ENUM = auto(); MATCH = auto(); CASE = auto(); DEFAULT = auto(); UNLESS = auto()
    ASYNC = auto(); AWAIT = auto(); DEFER = auto(); USING = auto(); TASKGROUP = auto(); MOVE = auto()

    LPAREN = auto(); RPAREN = auto(); LBRACE = auto(); RBRACE = auto()
    LBRACKET = auto(); RBRACKET = auto(); COMMA = auto(); COLON = auto()
    SEMICOLON = auto(); ARROW = auto(); RANGE = auto(); DOT = auto(); AT = auto()
    PIPE = auto(); QUESTION = auto()

    PLUS = auto(); MINUS = auto(); STAR = auto(); POWER = auto(); SLASH = auto(); PERCENT = auto()
    BANG = auto(); EQUAL = auto(); EQUAL_EQUAL = auto(); BANG_EQUAL = auto()
    LESS = auto(); LESS_EQUAL = auto(); GREATER = auto(); GREATER_EQUAL = auto()


KEYWORDS = {
    "let": TokenKind.LET, "var": TokenKind.VAR, "fn": TokenKind.FN,
    "return": TokenKind.RETURN, "if": TokenKind.IF, "else": TokenKind.ELSE,
    "while": TokenKind.WHILE, "for": TokenKind.FOR, "in": TokenKind.IN,
    "break": TokenKind.BREAK, "continue": TokenKind.CONTINUE,
    "true": TokenKind.TRUE, "false": TokenKind.FALSE,
    "and": TokenKind.AND, "or": TokenKind.OR, "not": TokenKind.NOT,
    "use": TokenKind.USE, "try": TokenKind.TRY, "catch": TokenKind.CATCH,
    "finally": TokenKind.FINALLY, "throw": TokenKind.THROW,
    "class": TokenKind.CLASS, "interface": TokenKind.INTERFACE,
    "abstract": TokenKind.ABSTRACT, "extends": TokenKind.EXTENDS,
    "implements": TokenKind.IMPLEMENTS, "private": TokenKind.PRIVATE,
    "public": TokenKind.PUBLIC, "internal": TokenKind.INTERNAL, "override": TokenKind.OVERRIDE,
    "module": TokenKind.MODULE, "as": TokenKind.AS,
    "enum": TokenKind.ENUM, "match": TokenKind.MATCH, "case": TokenKind.CASE, "default": TokenKind.DEFAULT, "unless": TokenKind.UNLESS,
    "async": TokenKind.ASYNC, "await": TokenKind.AWAIT, "defer": TokenKind.DEFER,
    "using": TokenKind.USING, "taskgroup": TokenKind.TASKGROUP, "move": TokenKind.MOVE,
}


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    lexeme: str
    literal: object | None
    line: int
    column: int
    filename: str = "<input>"

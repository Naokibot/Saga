from __future__ import annotations

from decimal import Decimal

from .errors import LexError
from .tokens import KEYWORDS, Token, TokenKind
from .unicode_profile import (
    ensure_unicode_version, is_bidi_control, is_identifier_continue,
    is_identifier_start, validate_identifier,
)


class Lexer:
    def __init__(self, source: str, filename: str = "<input>") -> None:
        ensure_unicode_version()
        try:
            source_size = len(source.encode("utf-8", errors="strict"))
        except UnicodeEncodeError as exc:
            raise LexError("ソースコードに不正なUnicode文字があります", 1, 1, filename, detail_code="SAGA-L101") from exc
        # Saga source text has implementation-independent line semantics.
        # CRLF and legacy CR are normalized to LF before token positions are
        # calculated. A single leading UTF-8 BOM is permitted.
        source = source.replace("\r\n", "\n").replace("\r", "\n")
        if source.startswith("\ufeff"):
            source = source[1:]
        self.source = source
        self.filename = filename
        self.tokens: list[Token] = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.start_line = 1
        self.start_column = 1

    def scan_tokens(self) -> list[Token]:
        while not self._at_end():
            self.start = self.current
            self.start_line = self.line
            self.start_column = self.column
            self._scan_token()
        self.tokens.append(Token(TokenKind.EOF, "", None, self.line, self.column, self.filename))
        return self.tokens

    def _scan_token(self) -> None:
        c = self._advance()
        single = {
            "(": TokenKind.LPAREN, ")": TokenKind.RPAREN,
            "{": TokenKind.LBRACE, "}": TokenKind.RBRACE,
            "[": TokenKind.LBRACKET, "]": TokenKind.RBRACKET,
            ",": TokenKind.COMMA, ":": TokenKind.COLON,
            ";": TokenKind.SEMICOLON, "+": TokenKind.PLUS,
            "%": TokenKind.PERCENT, "@": TokenKind.AT, "?": TokenKind.QUESTION,
        }
        if c in single:
            self._add(single[c]); return
        if c == ".":
            if self._match("."):
                self._add(TokenKind.RANGE); return
            self._add(TokenKind.DOT); return
        if c == "-":
            self._add(TokenKind.ARROW if self._match(">") else TokenKind.MINUS); return
        if c == "*":
            self._add(TokenKind.POWER if self._match("*") else TokenKind.STAR); return
        if c == "!":
            self._add(TokenKind.BANG_EQUAL if self._match("=") else TokenKind.BANG); return
        if c == "=":
            self._add(TokenKind.EQUAL_EQUAL if self._match("=") else TokenKind.EQUAL); return
        if c == "<":
            self._add(TokenKind.LESS_EQUAL if self._match("=") else TokenKind.LESS); return
        if c == ">":
            self._add(TokenKind.GREATER_EQUAL if self._match("=") else TokenKind.GREATER); return
        if c == "&":
            if self._match("&"):
                self._add(TokenKind.AND); return
            self._error("'&' は使えません", "論理積は and と書きます")
        if c == "|":
            if self._match(">"):
                self._add(TokenKind.PIPE); return
            if self._match("|"):
                self._add(TokenKind.OR); return
            self._error("'|' 単体は使えません", "パイプは |>、論理和は or と書きます")
        if c == "/":
            if self._match("/"):
                while self._peek() not in {"\n", "\0"}: self._advance()
            else:
                self._add(TokenKind.SLASH)
            return
        if c == "#":
            while self._peek() not in {"\n", "\0"}: self._advance()
            return
        if c in {" ", "\r", "\t", "\n"}: return
        if c in {'"', "'"}:
            self._string(c); return
        if "0" <= c <= "9":
            self._number(); return
        if c.isdigit():
            self._error(
                "数値リテラルの数字にはASCII 0-9を使用してください",
                "例: 123 または 3.14。Unicode数字は識別子との見分けを曖昧にするため数値構文では使用しません",
                "SAGA-L103",
            )
        if is_identifier_start(c):
            self._identifier(); return
        if is_bidi_control(c):
            self._error("双方向テキスト制御文字はソースコード中で使用できません", "文字列として必要な場合は\\u形式ではなく明示的なデータ入力を使用してください", "SAGA-L106")
        self._error(f"使用できない文字です: {c!r}")

    def _identifier(self) -> None:
        while is_identifier_continue(self._peek()):
            self._advance()
        text = self.source[self.start:self.current]
        error = validate_identifier(text)
        if error is not None:
            self._error(error, "同じ見た目の異なる識別子を避けるため、NFCの文字列を使用してください", "SAGA-L105" if "NFC" in error else "SAGA-L101")
        self._add(KEYWORDS.get(text, TokenKind.IDENT))

    def _number(self) -> None:
        while ("0" <= self._peek() <= "9") or self._peek() == "_": self._advance()
        kind = TokenKind.INT
        if self._peek() == "." and self._peek_next() == "_":
            self._error("小数点の直後に '_' は置けません", "例: 1.25 または 1.2_5", "SAGA-L103")
        if self._peek() == "." and self._peek_next() != "." and ("0" <= self._peek_next() <= "9"):
            kind = TokenKind.DECIMAL
            self._advance()
            while ("0" <= self._peek() <= "9") or self._peek() == "_": self._advance()
        raw = self.source[self.start:self.current]
        parts = raw.split(".")
        if any(not part or part.startswith("_") or part.endswith("_") or "__" in part for part in parts):
            self._error("数値の区切り '_' は数字の間に1つだけ置けます", "例: 1_000 または 3.141_592", "SAGA-L103")
        text = raw.replace("_", "")
        try:
            literal = Decimal(text) if kind is TokenKind.DECIMAL else int(text)
        except (ValueError, ArithmeticError):
            self._error("数値の書き方が正しくありません", diagnostic_id="SAGA-L103")
        self._add(kind, literal)

    def _string(self, quote: str) -> None:
        value: list[str] = []
        while not self._at_end():
            c = self._advance()
            if c == quote:
                self._add(TokenKind.STRING, "".join(value)); return
            if c == "\n": self._error("文字列は改行できません", "改行文字は \\n と書きます")
            if c == "\\":
                if self._at_end(): self._error("文字列のエスケープが途中で終わっています", diagnostic_id="SAGA-L102")
                escaped = self._advance()
                mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "\\": "\\"}
                if escaped not in mapping: self._error(f"未対応のエスケープです: \\{escaped}")
                value.append(mapping[escaped])
            else:
                value.append(c)
        self._error("文字列を閉じる引用符がありません", diagnostic_id="SAGA-L102")

    def _add(self, kind: TokenKind, literal: object | None = None) -> None:
        self.tokens.append(Token(
            kind, self.source[self.start:self.current], literal,
            self.start_line, self.start_column, self.filename,
        ))

    def _advance(self) -> str:
        c = self.source[self.current]; self.current += 1
        if c == "\n": self.line += 1; self.column = 1
        else: self.column += 1
        return c

    def _match(self, expected: str) -> bool:
        if self._at_end() or self.source[self.current] != expected: return False
        self._advance(); return True

    def _peek(self) -> str: return "\0" if self._at_end() else self.source[self.current]
    def _peek_next(self) -> str: return "\0" if self.current + 1 >= len(self.source) else self.source[self.current + 1]
    def _at_end(self) -> bool: return self.current >= len(self.source)

    def _error(self, message: str, hint: str | None = None, diagnostic_id: str | None = None) -> None:
        raise LexError(
            message, self.start_line, self.start_column, self.filename, hint,
            end_column=self.start_column + max(self.current - self.start, 1),
            detail_code=diagnostic_id,
        )

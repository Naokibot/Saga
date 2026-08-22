from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
import unicodedata


def _terminal_width(text: str, *, tabstop: int = 4) -> int:
    width = 0
    for char in text:
        if char == "\t":
            width += tabstop - (width % tabstop)
        elif unicodedata.combining(char) or unicodedata.category(char) in {"Mn", "Me", "Cf"}:
            continue
        elif unicodedata.east_asian_width(char) in {"W", "F"}:
            width += 2
        else:
            width += 1
    return width


def _expand_for_display(text: str, *, tabstop: int = 4) -> str:
    out: list[str] = []
    width = 0
    for char in text:
        if char == "\t":
            count = tabstop - (width % tabstop)
            out.append(" " * count); width += count
        else:
            out.append(char); width += _terminal_width(char, tabstop=tabstop)
    return "".join(out)


@dataclass(slots=True)
class SourceError(Exception):
    message: str
    line: int
    column: int
    filename: str = "<input>"
    hint: str | None = None
    end_column: int | None = None
    note: str | None = None
    detail_code: str | None = None
    detail_data: dict[str, str] | None = None

    code: ClassVar[str] = "SAGA0000"

    @property
    def diagnostic_id(self) -> str:
        # Machine-readable identity is explicit. Human wording is never parsed
        # to infer compatibility or conformance categories. Legacy call sites
        # without a detailed ID retain only their broad category code.
        return self.detail_code or self.code

    def __str__(self) -> str:
        suffix = f"\nヒント: {self.hint}" if self.hint else ""
        return f"{self.filename}:{self.line}:{self.column}: [{self.diagnostic_id}] {self.message}{suffix}"


class LexError(SourceError):
    code = "SAGA-L001"


class LexLimitError(SourceError):
    code = "SAGA-L002"


class ParseError(SourceError):
    code = "SAGA-P001"


class ParseLimitError(SourceError):
    code = "SAGA-P002"


class TypeCheckError(SourceError):
    code = "SAGA-T001"


class TypeLimitError(SourceError):
    code = "SAGA-T002"


class RuntimeLanguageError(SourceError):
    code = "SAGA-R001"


class RuntimeResourceError(SourceError):
    code = "SAGA-R002"


class InternalLanguageError(SourceError):
    """A controlled implementation-failure diagnostic.

    Conforming programs shall never produce this diagnostic.  The CLI emits
    it instead of a host traceback unless ``--debug`` is requested.
    """

    code = "SAGA-I001"


def format_diagnostic(error: SourceError, source: str, *, language: str = "ja") -> str:
    from .diagnostics import get_spec, localize_message, normalize_language
    language = normalize_language(language)
    spec = get_spec(error.diagnostic_id)
    lines = source.splitlines()
    title = spec.title(language) if spec else error.message
    detail = localize_message(error.code, error.diagnostic_id, error.message, language, error.detail_data)
    head = f"error[{error.diagnostic_id}]: {title}"
    location = f"  --> {error.filename}:{error.line}:{error.column}"
    body = ""
    if 1 <= error.line <= len(lines):
        text = lines[error.line - 1]
        end = error.end_column or (error.column + 1)
        prefix = text[:max(error.column - 1, 0)]
        marked = text[max(error.column - 1, 0):max(end - 1, error.column)]
        pointer = " " * _terminal_width(prefix) + "^" * max(1, _terminal_width(marked))
        shown = _expand_for_display(text)
        body = f"\n   |\n  {error.line:>4} | {shown}\n   | {pointer}"
        if detail and detail != title:
            body += f" {detail}"
    parts = [head, location + body]
    if error.diagnostic_id != error.code:
        parts.append(("category: " if language == "en" else "分類: ") + error.code)
    if error.note:
        parts.append(("note: " if language == "en" else "注記: ") + error.note)
    if error.hint and error.hint.startswith("candidate:"):
        candidate = error.hint.split(":", 1)[1]
        help_text = (f"Did you mean `{candidate}`?" if language == "en" else f"`{candidate}` の間違いではありませんか？")
    elif language == "ja":
        help_text = error.hint or (spec.help(language) if spec else None)
    else:
        help_text = (spec.help(language) if spec else None) or error.hint
    if help_text:
        parts.append(("help: " if language == "en" else "修正案: ") + help_text)
    if spec:
        parts.append(("why: " if language == "en" else "理由: ") + spec.explanation(language))
        parts.append(("more: " if language == "en" else "詳細: ") + f"saga explain {error.diagnostic_id} --language {language}")
    return "\n".join(parts)

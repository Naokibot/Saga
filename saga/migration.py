from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class MigrationChange:
    line: int
    before: str
    after: str
    reason: str


@dataclass(frozen=True, slots=True)
class MigrationResult:
    source: str
    changes: tuple[MigrationChange, ...]


_IDENT = r"[\w\u0080-\uffff]+"
_ATOM = rf"(?:{_IDENT}|-?\d+(?:\.\d+)?|\"[^\"\n]*\"|'[^'\n]*')"

# Deliberately conservative.  Only expressions whose argument boundaries are
# syntactically unambiguous without rebuilding the whole source printer are
# rewritten automatically.  More complex calls stay untouched and are handled
# by the compiler indefinitely during the compatibility window.


def _split_protected_segments(line: str) -> list[tuple[bool, str]]:
    """Split a source line into code and protected string/comment segments.

    Migration rewrites are source-to-source compatibility aids, so they must
    never alter user-visible string contents or comments.  The scanner is
    intentionally small and line-local because Saga string literals are
    single-line in the current grammar.
    """
    segments: list[tuple[bool, str]] = []
    start = 0
    i = 0
    while i < len(line):
        ch = line[i]
        if ch in {'"', "'"}:
            if start < i:
                segments.append((True, line[start:i]))
            quote = ch
            j = i + 1
            escaped = False
            while j < len(line):
                current = line[j]
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    j += 1
                    break
                j += 1
            segments.append((False, line[i:j]))
            i = j
            start = i
            continue
        if ch == "#" or (ch == "/" and i + 1 < len(line) and line[i + 1] == "/"):
            if start < i:
                segments.append((True, line[start:i]))
            segments.append((False, line[i:]))
            return segments
        i += 1
    if start < len(line):
        segments.append((True, line[start:]))
    elif not segments:
        segments.append((True, ""))
    return segments


def _rewrite_code_only(line: str, pattern: re.Pattern[str], replacement: callable) -> str:
    return "".join(
        pattern.sub(replacement, text) if is_code else text
        for is_code, text in _split_protected_segments(line)
    )

_PATTERNS: tuple[tuple[re.Pattern[str], callable, str], ...] = (
    (re.compile(rf"\btransform\(({_IDENT}),\s*({_IDENT})\)"), lambda m: f"{m.group(2)}.map({m.group(1)})", "transform(function, list) → list.map(function)"),
    (re.compile(rf"\bfilter\(({_IDENT}),\s*({_IDENT})\)"), lambda m: f"{m.group(2)}.filter({m.group(1)})", "filter(function, list) → list.filter(function)"),
    (re.compile(rf"\bany\(({_IDENT}),\s*({_IDENT})\)"), lambda m: f"{m.group(2)}.any({m.group(1)})", "any(function, list) → list.any(function)"),
    (re.compile(rf"\ball\(({_IDENT}),\s*({_IDENT})\)"), lambda m: f"{m.group(2)}.all({m.group(1)})", "all(function, list) → list.all(function)"),
    (re.compile(rf"\breduce\(({_IDENT}),\s*({_IDENT}),\s*({_ATOM})\)"), lambda m: f"{m.group(2)}.fold({m.group(3)}, {m.group(1)})", "reduce(function, list, initial) → list.fold(initial, function)"),
    (re.compile(rf"\bsort\(({_IDENT})\)"), lambda m: f"{m.group(1)}.sorted()", "sort(list) → list.sorted()"),
    (re.compile(rf"\bunique\(({_IDENT})\)"), lambda m: f"{m.group(1)}.distinct()", "unique(list) → list.distinct()"),
)


def migrate_source(source: str) -> MigrationResult:
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    output: list[str] = []
    changes: list[MigrationChange] = []
    for line_number, raw in enumerate(normalized.split("\n"), 1):
        current = raw
        for pattern, replacement, reason in _PATTERNS:
            replaced = _rewrite_code_only(current, pattern, replacement)
            if replaced != current:
                changes.append(MigrationChange(line_number, current, replaced, reason))
                current = replaced
        output.append(current)
    return MigrationResult("\n".join(output), tuple(changes))

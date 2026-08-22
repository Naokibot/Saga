from __future__ import annotations


def _brace_counts(line: str) -> tuple[int, int]:
    opens = closes = 0
    quote: str | None = None
    escaped = False
    i = 0
    while i < len(line):
        ch = line[i]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch in {'"', "'"}:
            quote = ch
            i += 1
            continue
        if ch == "#" or (ch == "/" and i + 1 < len(line) and line[i + 1] == "/"):
            break
        if ch == "{": opens += 1
        elif ch == "}": closes += 1
        i += 1
    return opens, closes


def format_source(source: str, indent_width: int = 4) -> str:
    """Apply the conservative Saga standard layout without rewriting tokens.

    Comments and string contents are preserved. The formatter normalizes line
    endings, trailing whitespace, brace indentation, and the final newline.
    """
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    output: list[str] = []
    indent = 0
    blank = False
    for raw in normalized.split("\n"):
        text = raw.strip()
        if not text:
            if output and not blank:
                output.append("")
            blank = True
            continue
        blank = False
        leading_closes = 0
        for ch in text:
            if ch == "}": leading_closes += 1
            elif ch.isspace(): continue
            else: break
        line_indent = max(0, indent - leading_closes)
        output.append(" " * (line_indent * indent_width) + text)
        opens, closes = _brace_counts(text)
        indent = max(0, indent + opens - closes)
    while output and output[-1] == "":
        output.pop()
    return "\n".join(output) + "\n"

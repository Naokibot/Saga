from __future__ import annotations

from bisect import bisect_right
import unicodedata

from .unicode15_1_tables import UNICODE_VERSION, XID_CONTINUE_RANGES, XID_START_RANGES

BIDI_CONTROL_CODEPOINTS = frozenset({
    0x061C,
    0x200E, 0x200F,
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
})

_STARTS = tuple(item[0] for item in XID_START_RANGES)
_CONTINUE_STARTS = tuple(item[0] for item in XID_CONTINUE_RANGES)


def ensure_unicode_version() -> None:
    """Confirm that the normative vendored profile is available.

    Saga no longer delegates identifier membership to the host Unicode
    database. Unicode normalization is stable for characters assigned in
    Unicode 15.1, while membership is decided by the vendored 15.1 tables.
    This keeps future Python Unicode database upgrades from changing source
    acceptance.
    """
    if not XID_START_RANGES or not XID_CONTINUE_RANGES:
        raise RuntimeError("Saga Unicode 15.1 tables are missing")


def _in_ranges(codepoint: int, ranges: tuple[tuple[int, int], ...], starts: tuple[int, ...]) -> bool:
    index = bisect_right(starts, codepoint) - 1
    return index >= 0 and codepoint <= ranges[index][1]


def is_identifier_start(char: str) -> bool:
    return len(char) == 1 and _in_ranges(ord(char), XID_START_RANGES, _STARTS)


def is_identifier_continue(char: str) -> bool:
    return len(char) == 1 and _in_ranges(ord(char), XID_CONTINUE_RANGES, _CONTINUE_STARTS)


def validate_identifier(text: str) -> str | None:
    if not text:
        return "識別子が空です"
    if unicodedata.normalize("NFC", text) != text:
        return "識別子はUnicode NFCで正規化してください"
    if not is_identifier_start(text[0]):
        return "識別子の先頭文字はXID_Startまたは_である必要があります"
    if any(not is_identifier_continue(char) for char in text[1:]):
        return "識別子にはXID_Continue以外の文字を使用できません"
    return None


def is_bidi_control(char: str) -> bool:
    return len(char) == 1 and ord(char) in BIDI_CONTROL_CODEPOINTS

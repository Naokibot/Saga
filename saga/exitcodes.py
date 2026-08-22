"""Stable process exit status profile for Saga command-line tools."""

SUCCESS = 0
LEXICAL_ERROR = 2
SYNTAX_ERROR = 3
TYPE_ERROR = 4
RUNTIME_ERROR = 5
RESOURCE_ERROR = 6
CONFORMANCE_FAILURE = 7
INPUT_ERROR = 66
INTERNAL_ERROR = 70


def for_error(error: BaseException) -> int:
    from .errors import (
        InternalLanguageError,
        LexError,
        LexLimitError,
        ParseError,
        ParseLimitError,
        RuntimeLanguageError,
        RuntimeResourceError,
        TypeCheckError,
        TypeLimitError,
    )
    if isinstance(error, (LexError, LexLimitError)):
        return LEXICAL_ERROR
    if isinstance(error, (ParseError, ParseLimitError)):
        return SYNTAX_ERROR
    if isinstance(error, (TypeCheckError, TypeLimitError)):
        return TYPE_ERROR
    if isinstance(error, RuntimeResourceError):
        return RESOURCE_ERROR
    if isinstance(error, RuntimeLanguageError):
        return RUNTIME_ERROR
    if isinstance(error, InternalLanguageError):
        return INTERNAL_ERROR
    return INTERNAL_ERROR

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OptionValue:
    """Runtime representation of Saga option[T].

    The payload may itself be unit (Python ``None``); ``present`` is therefore
    the only discriminator. Host nulls must be converted to ``OptionValue.none``
    before crossing into Saga code.
    """

    present: bool
    value: object = None

    @classmethod
    def some(cls, value: object) -> "OptionValue":
        return cls(True, value)

    @classmethod
    def none(cls) -> "OptionValue":
        return cls(False, None)


@dataclass(frozen=True, slots=True)
class ResultValue:
    ok: bool
    value: object = None

    @classmethod
    def success(cls, value: object) -> "ResultValue":
        return cls(True, value)

    @classmethod
    def failure(cls, value: object) -> "ResultValue":
        return cls(False, value)

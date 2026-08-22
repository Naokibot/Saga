"""Adaptive host-resource helpers.

These helpers do not define Saga language limits.  They expand host recursion
capacity in proportion to the actual compilation unit so the reference
implementation does not accidentally turn Python's default recursion setting
into a de-facto Saga syntax ceiling.
"""
from __future__ import annotations

from contextlib import contextmanager
import sys
import threading

_RECURSION_LOCK = threading.RLock()


@contextmanager
def adaptive_recursion_capacity(work_units: int, *, frames_per_unit: int = 12):
    requested = max(sys.getrecursionlimit(), max(1, int(work_units)) * frames_per_unit + 2048)
    with _RECURSION_LOCK:
        previous = sys.getrecursionlimit()
        changed = requested > previous
        if changed:
            sys.setrecursionlimit(requested)
        try:
            yield
        finally:
            if changed:
                # Restore only after the protected compiler phase.  The lock
                # prevents another Saga compiler thread from observing a
                # prematurely lowered setting.
                sys.setrecursionlimit(previous)

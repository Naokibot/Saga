from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path


@contextmanager
def exclusive_file_lock(path: str | Path):
    """Cross-process exclusive lock backed by one byte in a private lock file."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "r+b", closefd=False) as handle:
            if os.fstat(fd).st_size == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(fd)
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)

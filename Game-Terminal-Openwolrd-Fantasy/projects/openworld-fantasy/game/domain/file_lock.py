"""
Cross-process file locks for world shared state (W3).

Uses fcntl.flock on Unix/macOS; no-op fallback with stale lockfile cleanup.
Locks live under saves/{world_id}/.locks/
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from game.config import SAVES_DIR

try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:  # Windows
    fcntl = None  # type: ignore
    _HAS_FCNTL = False


def locks_dir(world_id: str) -> Path:
    d = Path(SAVES_DIR) / str(world_id or "default") / ".locks"
    d.mkdir(parents=True, exist_ok=True)
    return d


@contextmanager
def world_file_lock(
    world_id: str,
    name: str,
    *,
    timeout: float = 8.0,
    stale_sec: float = 60.0,
) -> Iterator[bool]:
    """
    Exclusive lock named e.g. market, rank, meta, echo.
    Yields True if lock acquired, False if timed out (caller may still proceed carefully).
    """
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name or "file"))
    path = locks_dir(world_id) / f"{safe}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+", encoding="utf-8")
    acquired = False
    deadline = time.time() + max(0.5, float(timeout))
    try:
        if _HAS_FCNTL:
            while time.time() < deadline:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except (BlockingIOError, OSError):
                    time.sleep(0.05)
        else:
            # naive lockfile for non-fcntl
            while time.time() < deadline:
                try:
                    if path.exists():
                        age = time.time() - path.stat().st_mtime
                        if age > stale_sec:
                            path.unlink(missing_ok=True)  # type: ignore[arg-type]
                    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.write(fd, str(os.getpid()).encode())
                    os.close(fd)
                    acquired = True
                    break
                except FileExistsError:
                    time.sleep(0.05)
        if acquired:
            try:
                fh.seek(0)
                fh.truncate()
                fh.write(f"pid={os.getpid()} t={time.time():.3f}\n")
                fh.flush()
            except Exception:
                pass
        yield acquired
    finally:
        try:
            if acquired and _HAS_FCNTL:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            elif acquired and not _HAS_FCNTL:
                try:
                    path.unlink(missing_ok=True)  # type: ignore[arg-type]
                except TypeError:
                    if path.exists():
                        path.unlink()
        except Exception:
            pass
        try:
            fh.close()
        except Exception:
            pass

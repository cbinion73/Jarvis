from __future__ import annotations

import json
import os
from contextlib import contextmanager
import fcntl
from pathlib import Path
import tempfile
from typing import Any, Iterator

from .state_log_utils import trim_file_to_recent_bytes


def _lock_path(path: Path) -> Path:
    suffix = f"{path.suffix}.lock" if path.suffix else ".lock"
    return path.with_suffix(suffix)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    _ensure_parent(path)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_json(
    path: Path,
    payload: Any,
    *,
    indent: int = 2,
    encoding: str = "utf-8",
    ensure_ascii: bool = False,
) -> None:
    _ensure_parent(path)
    lock_path = _lock_path(path)
    serialized = json.dumps(payload, indent=indent, ensure_ascii=ensure_ascii) + "\n"
    with _exclusive_lock(lock_path):
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f"{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding=encoding) as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


# Log files are capped at this size. When exceeded, the oldest half is dropped so
# the file stays bounded without losing all recent history.
_JSONL_ROTATE_BYTES: int = 50 * 1024 * 1024  # 50 MB


def _rotate_if_needed(path: Path, encoding: str) -> None:
    """Trim the oldest half of a JSONL file once it exceeds _JSONL_ROTATE_BYTES."""
    try:
        if path.stat().st_size <= _JSONL_ROTATE_BYTES:
            return
        trim_file_to_recent_bytes(path, _JSONL_ROTATE_BYTES // 2)
    except (OSError, ValueError):
        pass


def append_jsonl(
    path: Path,
    payload: Any,
    *,
    encoding: str = "utf-8",
    ensure_ascii: bool = False,
) -> None:
    _ensure_parent(path)
    lock_path = _lock_path(path)
    serialized = json.dumps(payload, ensure_ascii=ensure_ascii) + "\n"
    with _exclusive_lock(lock_path):
        with path.open("a", encoding=encoding) as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        _rotate_if_needed(path, encoding)


def atomic_write_jsonl(
    path: Path,
    records: list[Any],
    *,
    encoding: str = "utf-8",
    ensure_ascii: bool = False,
) -> None:
    _ensure_parent(path)
    lock_path = _lock_path(path)
    serialized = "\n".join(json.dumps(record, ensure_ascii=ensure_ascii) for record in records)
    if serialized:
        serialized += "\n"
    with _exclusive_lock(lock_path):
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f"{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding=encoding) as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

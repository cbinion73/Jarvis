from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_DEFAULT_TAIL_BYTES = 4 * 1024 * 1024
_DEFAULT_TAIL_LINES = 2000


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


def state_log_tail_bytes() -> int:
    return _env_int("JARVIS_STATE_LOG_TAIL_BYTES", _DEFAULT_TAIL_BYTES)


def state_log_tail_lines() -> int:
    return _env_int("JARVIS_STATE_LOG_TAIL_LINES", _DEFAULT_TAIL_LINES)


def read_text_tail_lines(
    path: Path,
    *,
    max_bytes: int | None = None,
    max_lines: int | None = None,
    encoding: str = "utf-8",
) -> list[str]:
    if not path.exists():
        return []
    tail_bytes = max(1, max_bytes or state_log_tail_bytes())
    tail_lines = max(1, max_lines or state_log_tail_lines())
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            if size <= 0:
                return []
            read_size = min(size, tail_bytes)
            if read_size < size:
                handle.seek(-read_size, os.SEEK_END)
            else:
                handle.seek(0)
            raw = handle.read(read_size)
    except OSError:
        return []
    text = raw.decode(encoding, errors="ignore")
    if read_size < size:
        newline = text.find("\n")
        if newline >= 0:
            text = text[newline + 1 :]
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) > tail_lines:
        lines = lines[-tail_lines:]
    return lines


def read_jsonl_tail(
    path: Path,
    *,
    max_bytes: int | None = None,
    max_lines: int | None = None,
    encoding: str = "utf-8",
) -> list[Any]:
    items: list[Any] = []
    for line in read_text_tail_lines(
        path,
        max_bytes=max_bytes,
        max_lines=max_lines,
        encoding=encoding,
    ):
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def trim_file_to_recent_bytes(path: Path, keep_bytes: int) -> None:
    if keep_bytes <= 0:
        return
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size <= keep_bytes:
        return
    with path.open("rb+") as handle:
        handle.seek(-keep_bytes, os.SEEK_END)
        raw = handle.read(keep_bytes)
        newline = raw.find(b"\n")
        if newline >= 0 and newline + 1 < len(raw):
            raw = raw[newline + 1 :]
        handle.seek(0)
        handle.write(raw)
        handle.truncate()

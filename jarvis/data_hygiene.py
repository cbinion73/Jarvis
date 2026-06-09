from __future__ import annotations

import os
import re
from typing import Any


_TEST_VALUE_PATTERNS = [
    re.compile(r"\btest-browser-\d+\b", re.IGNORECASE),
    re.compile(r"\btest-morning-[\w-]+\b", re.IGNORECASE),
    re.compile(r"\bqa camera mount\b", re.IGNORECASE),
    re.compile(r"\bqa-camera-mount\b", re.IGNORECASE),
    re.compile(r"\bautonomy-seed\b", re.IGNORECASE),
    re.compile(r"\bqa learning\b", re.IGNORECASE),
    re.compile(r"\btroop families qa\b", re.IGNORECASE),
    re.compile(r"\bqa bracket\b", re.IGNORECASE),
    re.compile(r"\btroop parents\b", re.IGNORECASE),
    re.compile(r"\btroop meeting\b", re.IGNORECASE),
    re.compile(r"\btroop arrival\b", re.IGNORECASE),
    re.compile(r"\bindoor backup update\b", re.IGNORECASE),
    re.compile(r"\bparent-facing troop note\b", re.IGNORECASE),
    re.compile(r"\bstewardship under pressure\b", re.IGNORECASE),
    re.compile(r"\btoday felt noisy\b", re.IGNORECASE),
    re.compile(r"\bgrace in restraint\b", re.IGNORECASE),
    re.compile(r"\blow-friction lane\b", re.IGNORECASE),
    re.compile(r"\bpray(?:er|ers)?\s+(?:for|over)\s+sarah\b", re.IGNORECASE),
    re.compile(r"\bprayer(?:\s+request)?\s+for\s+sarah\b", re.IGNORECASE),
]


def include_test_data() -> bool:
    raw = os.getenv("JARVIS_INCLUDE_TEST_DATA", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def string_looks_like_test_data(value: str) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return False
    for pattern in _TEST_VALUE_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


def record_looks_like_test_data(value: Any) -> bool:
    if include_test_data():
        return False
    if isinstance(value, str):
        return string_looks_like_test_data(value)
    if isinstance(value, dict):
        for key, item in value.items():
            if string_looks_like_test_data(str(key)):
                return True
            if record_looks_like_test_data(item):
                return True
        return False
    if isinstance(value, (list, tuple, set)):
        return any(record_looks_like_test_data(item) for item in value)
    return False


def filter_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if include_test_data():
        return list(records)
    return [item for item in records if not record_looks_like_test_data(item)]

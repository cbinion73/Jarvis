"""
mychart_reader.py — MyChart Chrome Reader
==========================================
Reads medical records from an authenticated MyChart session.
Uses the Chrome DevTools Protocol (via httpx) to read page content
from an already-logged-in MyChart tab.

Called from service.py endpoints that use Chrome MCP tools to
navigate and read MyChart pages.

Storage: ~/.jarvis/health/mychart_records.json
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

logger = logging.getLogger("jarvis.mychart_reader")

_HEALTH_DIR = Path.home() / ".jarvis" / "health"
_RECORDS_PATH = _HEALTH_DIR / "mychart_records.json"
_RECORDS_LOG_PATH = _HEALTH_DIR / "mychart_records_log.jsonl"
_RECORDS_STATE_LOG_PATH = _HEALTH_DIR / "mychart_records_state_log.jsonl"
_lock = threading.Lock()

MYCHART_BASE = "https://mychart.stelizabeth.com/MyChart"

# MyChart page paths to scrape
PAGES = {
    "test_results":  "/TestResults/Index",
    "medications":   "/Medications/Index",
    "conditions":    "/Health/Index",
    "visits":        "/Visits/Index",
    "vitals":        "/Health/Vitals",
    "immunizations": "/Immunizations/Index",
    "allergies":     "/Allergies/Index",
    "care_team":     "/CareTeam/Index",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_records() -> dict:
    """Load stored MyChart records."""
    try:
        if _RECORDS_PATH.exists():
            payload = json.loads(_RECORDS_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload:
                return payload
    except Exception:
        replayed = _load_records_from_state_log()
        if replayed:
            return replayed
        return _load_records_from_log()
    if not _RECORDS_PATH.exists():
        replayed = _load_records_from_state_log()
        if replayed:
            return replayed
        return _load_records_from_log()
    replayed = _load_records_from_state_log()
    if replayed:
        return replayed
    return {}


def save_records(records: dict) -> dict:
    """Save MyChart records to disk."""
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    records = dict(records)
    records["last_updated"] = _now()
    atomic_write_json(_RECORDS_PATH, records)
    append_jsonl(
        _RECORDS_LOG_PATH,
        {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "records": records,
        },
    )
    append_jsonl(
        _RECORDS_STATE_LOG_PATH,
        {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "records": records,
        },
    )
    return records


def _load_records_from_log() -> dict:
    try:
        if _RECORDS_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _RECORDS_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, dict):
                    latest = dict(records)
            if latest is not None:
                return latest
    except Exception:
        pass
    return {}


def _load_records_from_state_log() -> dict:
    try:
        if _RECORDS_STATE_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _RECORDS_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, dict):
                    latest = dict(records)
            if latest is not None:
                return latest
    except Exception:
        pass
    return {}


def parse_test_results(html: str) -> list[dict]:
    """Parse test results from MyChart HTML."""
    results = []
    # Look for result rows - MyChart uses various table/list patterns
    # Pattern: date, test name, result, status
    patterns = [
        # Table rows with test data
        r'(?s)<tr[^>]*>.*?(\d{1,2}/\d{1,2}/\d{4}).*?</tr>',
        # Result items
        r'data-resultid[^>]*>.*?</tr>',
    ]

    # Extract text blocks that look like lab results
    # Remove script/style tags first
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    return {"raw_text": clean[:5000], "parsed": results}


def parse_medications(html: str) -> list[dict]:
    """Parse medication list from MyChart HTML."""
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return {"raw_text": clean[:3000]}


def parse_conditions(html: str) -> list[dict]:
    """Parse health conditions/issues from MyChart HTML."""
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return {"raw_text": clean[:3000]}


def store_page_data(page_key: str, content: str, page_type: str = "html") -> dict:
    """
    Store scraped page content. Called from service.py after Chrome reads a page.
    content: the page text/HTML content
    Returns the updated records dict.
    """
    with _lock:
        records = load_records()
        records[page_key] = {
            "content": content[:10000],
            "scraped_at": _now(),
            "page_type": page_type,
        }
        # Try to parse structured data
        if page_key == "test_results":
            records[page_key]["parsed"] = parse_test_results(content)
        elif page_key == "medications":
            records[page_key]["parsed"] = parse_medications(content)
        elif page_key == "conditions":
            records[page_key]["parsed"] = parse_conditions(content)
        records = save_records(records)
    return records


def get_summary() -> dict:
    """Return a summary of all scraped MyChart data."""
    records = load_records()
    summary = {
        "last_updated": records.get("last_updated"),
        "pages_scraped": [k for k in records if k not in ("last_updated",)],
        "records": {},
    }
    for key in ("test_results", "medications", "conditions", "visits", "vitals", "immunizations"):
        if key in records:
            summary["records"][key] = {
                "scraped_at": records[key].get("scraped_at"),
                "has_content": bool(records[key].get("content")),
                "content_preview": records[key].get("content", "")[:200],
            }
    return summary


def get_briefing_summary() -> str:
    """Short text summary for morning brief."""
    records = load_records()
    if not records or not records.get("pages_scraped") and len(records) <= 1:
        return ""
    parts = []
    if "test_results" in records:
        scraped = records["test_results"].get("scraped_at", "")[:10]
        parts.append(f"Lab results synced {scraped}")
    if "medications" in records:
        parts.append("Medications on file")
    if not parts:
        return ""
    return f"**Medical Records (St. Elizabeth):** {', '.join(parts)}."

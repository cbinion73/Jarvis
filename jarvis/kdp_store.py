"""
kdp_store.py — Data layer for KDP integration.
Saves and loads books, sales history, sync metadata, and provides
CSV parsing and rule-based insights.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .persistence import append_jsonl, atomic_write_json

log = logging.getLogger("jarvis.kdp_store")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KDP_DATA_DIR   = Path("data/kdp")
BOOKS_PATH     = KDP_DATA_DIR / "books.json"
BOOKS_LOG_PATH = KDP_DATA_DIR / "books_log.jsonl"
SALES_PATH     = KDP_DATA_DIR / "sales_history.jsonl"
SALES_STATE_LOG_PATH = KDP_DATA_DIR / "sales_history_state_log.jsonl"
SYNC_META_PATH = KDP_DATA_DIR / "sync_meta.json"
SYNC_META_LOG_PATH = KDP_DATA_DIR / "sync_meta_log.jsonl"

# Imported here for get_status()
try:
    from .kdp_scraper import CREDS_PATH
except ImportError:
    CREDS_PATH = Path("data/settings/kdp_credentials.json")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_dir() -> None:
    KDP_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# save_sync_result
# ---------------------------------------------------------------------------

def save_sync_result(result: dict) -> None:
    """
    Persist a sync result returned by run_full_sync():
    - Write books list to BOOKS_PATH
    - Append sales snapshot to SALES_PATH (one JSON line per call)
    - Write sync metadata to SYNC_META_PATH
    """
    try:
        _ensure_dir()

        books: list[dict] = result.get("books") or []
        sales: dict = result.get("sales") or {}
        synced_at: str = result.get("synced_at") or _now_iso()
        ok: bool = bool(result.get("ok", True))

        # ── Books ────────────────────────────────────────────────────────
        try:
            atomic_write_json(
                BOOKS_PATH,
                books,
                ensure_ascii=False,
            )
            append_jsonl(
                BOOKS_LOG_PATH,
                {"saved_at": synced_at, "books": books},
                ensure_ascii=False,
            )
        except Exception as exc:
            log.warning("KDP store: failed to write books.json: %s", exc)

        # ── Sales history (append) ────────────────────────────────────────
        if sales:
            snapshot = {**sales, "synced_at": synced_at}
            try:
                existing = load_sales_history(limit=1000)
                existing.append(snapshot)
                append_jsonl(
                    SALES_STATE_LOG_PATH,
                    {"saved_at": synced_at, "records": existing},
                    ensure_ascii=False,
                )
                atomic_write_json(
                    SALES_PATH,
                    existing,
                    indent=None,
                    ensure_ascii=False,
                )
            except Exception as exc:
                log.warning("KDP store: failed to append sales_history.jsonl: %s", exc)

        # ── Sync metadata ────────────────────────────────────────────────
        meta = {
            "last_synced_at": synced_at,
            "ok": ok,
            "book_count": len(books),
            "status": "synced" if ok else "error",
        }
        try:
            atomic_write_json(
                SYNC_META_PATH,
                meta,
                ensure_ascii=False,
            )
            append_jsonl(
                SYNC_META_LOG_PATH,
                {"saved_at": synced_at, "meta": meta},
                ensure_ascii=False,
            )
        except Exception as exc:
            log.warning("KDP store: failed to write sync_meta.json: %s", exc)

        log.info("KDP store: saved sync result (books=%d, ok=%s)", len(books), ok)

    except Exception as exc:
        log.error("KDP store: save_sync_result failed: %s", exc)


# ---------------------------------------------------------------------------
# load_books
# ---------------------------------------------------------------------------

def load_books() -> list[dict]:
    """Read BOOKS_PATH. Return [] if not found or on error."""
    try:
        if not BOOKS_PATH.exists():
            return _load_books_from_log()
        return json.loads(BOOKS_PATH.read_text(encoding="utf-8")) or []
    except Exception as exc:
        log.warning("KDP store: failed to load books.json: %s", exc)
        return _load_books_from_log()


def _load_books_from_log() -> list[dict]:
    try:
        if not BOOKS_LOG_PATH.exists():
            return []
        latest: list[dict] = []
        for line in BOOKS_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            books = payload.get("books")
            if isinstance(books, list):
                latest = [dict(item) for item in books if isinstance(item, dict)]
        return latest
    except Exception as exc:
        log.warning("KDP store: failed to replay books log: %s", exc)
        return []


# ---------------------------------------------------------------------------
# load_sales_history
# ---------------------------------------------------------------------------

def load_sales_history(limit: int = 90) -> list[dict]:
    """
    Read the last `limit` lines from SALES_PATH.
    Returns [] if file not found or on error.
    """
    try:
        if not SALES_PATH.exists():
            return _load_sales_history_from_log(limit=limit)
        payload = json.loads(SALES_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            records = [dict(item) for item in payload if isinstance(item, dict)]
            return records[-limit:]
        return _load_sales_history_from_log(limit=limit)
    except Exception as exc:
        log.warning("KDP store: failed to load sales_history.jsonl: %s", exc)
        return _load_sales_history_from_log(limit=limit)


def _load_sales_history_from_log(limit: int = 90) -> list[dict]:
    try:
        if not SALES_STATE_LOG_PATH.exists():
            return []
        latest: list[dict] = []
        for line in SALES_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            records = payload.get("records")
            if isinstance(records, list):
                latest = [dict(item) for item in records if isinstance(item, dict)]
        return latest[-limit:]
    except Exception as exc:
        log.warning("KDP store: failed to replay sales history log: %s", exc)
        return []


# ---------------------------------------------------------------------------
# load_sync_meta
# ---------------------------------------------------------------------------

def load_sync_meta() -> dict:
    """
    Read SYNC_META_PATH.
    Returns default dict if not found.
    """
    try:
        if not SYNC_META_PATH.exists():
            return _load_sync_meta_from_log()
        return json.loads(SYNC_META_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("KDP store: failed to load sync_meta.json: %s", exc)
        return _load_sync_meta_from_log(error_fallback=True)


def _load_sync_meta_from_log(*, error_fallback: bool = False) -> dict:
    default = {"last_synced_at": None, "book_count": 0, "status": "error" if error_fallback else "never_synced"}
    try:
        if not SYNC_META_LOG_PATH.exists():
            return default
        latest: dict | None = None
        for line in SYNC_META_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            meta = payload.get("meta")
            if isinstance(meta, dict):
                latest = dict(meta)
        return latest or default
    except Exception as exc:
        log.warning("KDP store: failed to replay sync_meta log: %s", exc)
        return default


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

def get_status() -> dict:
    """
    Return current KDP integration status.
    {"configured": bool, "last_synced_at": str|None, "book_count": int, "status": str}
    """
    meta = load_sync_meta()
    configured = CREDS_PATH.exists()
    return {
        "configured": configured,
        "last_synced_at": meta.get("last_synced_at"),
        "book_count": meta.get("book_count", 0),
        "status": meta.get("status", "never_synced"),
    }


# ---------------------------------------------------------------------------
# parse_csv_report
# ---------------------------------------------------------------------------

def parse_csv_report(csv_text: str) -> list[dict]:
    """
    Parse a KDP CSV royalty report.
    KDP CSV headers (typical):
      Title, Author, ASIN, Marketplace, Units Sold, Units Refunded,
      Net Units Sold, Royalty Type, Royalty, Currency

    Handles BOM and encoding issues. Returns list of dicts.
    """
    if not csv_text:
        return []

    try:
        # Strip BOM if present
        if csv_text.startswith("﻿"):
            csv_text = csv_text[1:]

        # KDP sometimes uses Windows line endings
        csv_text = csv_text.replace("\r\n", "\n").replace("\r", "\n")

        reader = csv.DictReader(io.StringIO(csv_text))
        rows: list[dict] = []
        for row in reader:
            # Normalise keys: strip whitespace from both key and value
            clean = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

            # Parse numeric fields safely
            def _int(val: str) -> int:
                try:
                    return int(val.replace(",", "").strip()) if val else 0
                except (ValueError, AttributeError):
                    return 0

            def _float(val: str) -> float:
                try:
                    return float(val.replace(",", "").strip()) if val else 0.0
                except (ValueError, AttributeError):
                    return 0.0

            rows.append({
                "title":         clean.get("Title", ""),
                "author":        clean.get("Author", ""),
                "asin":          clean.get("ASIN", ""),
                "marketplace":   clean.get("Marketplace", ""),
                "units_sold":    _int(clean.get("Units Sold", "0")),
                "units_refunded": _int(clean.get("Units Refunded", "0")),
                "net_units_sold": _int(clean.get("Net Units Sold", "0")),
                "royalty_type":  clean.get("Royalty Type", ""),
                "royalty":       _float(clean.get("Royalty", "0")),
                "currency":      clean.get("Currency", ""),
            })

        log.info("KDP store: parsed %d rows from CSV", len(rows))
        return rows

    except Exception as exc:
        log.warning("KDP store: parse_csv_report failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# generate_insights
# ---------------------------------------------------------------------------

def generate_insights(books: list[dict], sales_history: list[dict]) -> list[dict]:
    """
    Rule-based insights (no AI). Returns up to 5 insight dicts.
    Each insight: {"type": "attention"|"positive"|"info", "book"?: str, "message": str}
    """
    insights: list[dict] = []

    try:
        # ── Insight 1: Books with no recent units ────────────────────────
        # Look at the most recent sales snapshot for per-book data.
        # KDP's dashboard-level scrape is aggregate; CSV rows have per-book data.
        # If we have CSV-parsed history, use it.
        recent_csv_rows: list[dict] = []
        for snapshot in reversed(sales_history[-30:]):
            csv_rows = snapshot.get("csv_rows")
            if isinstance(csv_rows, list) and csv_rows:
                recent_csv_rows = csv_rows
                break

        if recent_csv_rows:
            for row in recent_csv_rows:
                title = row.get("title", "Unknown")
                net_units = row.get("net_units_sold", 0) or 0
                if net_units == 0 and len(insights) < 3:
                    # Match against live books
                    for book in books:
                        if (book.get("asin") == row.get("asin") or book.get("title", "").lower() == title.lower()):
                            if book.get("status", "").lower() in ("live", "published", ""):
                                insights.append({
                                    "type": "attention",
                                    "book": title,
                                    "message": f"No sales in latest report period — consider a price promotion or keyword refresh",
                                })
                            break

        # ── Insight 2: KENP page read growth ────────────────────────────
        if len(sales_history) >= 2:
            try:
                recent = sales_history[-1]
                older  = sales_history[-2]
                recent_kenp = float(recent.get("kenp_pages_read") or 0)
                older_kenp  = float(older.get("kenp_pages_read") or 0)
                if older_kenp > 0 and recent_kenp > older_kenp:
                    growth_pct = ((recent_kenp - older_kenp) / older_kenp) * 100
                    if growth_pct >= 20:
                        insights.append({
                            "type": "positive",
                            "book": "All titles",
                            "message": f"Page reads up {growth_pct:.0f}% — KDP Select is working",
                        })
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        # ── Insight 3: Total royalties ────────────────────────────────────
        if sales_history:
            try:
                latest = sales_history[-1]
                royalties = float(latest.get("royalties_usd") or 0)
                if royalties > 0:
                    insights.append({
                        "type": "info",
                        "message": f"Total royalties this period: ${royalties:,.2f}",
                    })
            except (TypeError, ValueError):
                pass

        # ── Insight 4: Unit sales info ────────────────────────────────────
        if sales_history:
            try:
                latest = sales_history[-1]
                units = int(latest.get("units_sold") or 0)
                if units > 0:
                    insights.append({
                        "type": "info",
                        "message": f"Units sold this period: {units:,}",
                    })
            except (TypeError, ValueError):
                pass

        # ── Insight 5: Book count ────────────────────────────────────────
        live_books = [b for b in books if b.get("status", "").lower() in ("live", "published", "")]
        if live_books:
            insights.append({
                "type": "info",
                "message": f"{len(live_books)} title(s) live on KDP",
            })

    except Exception as exc:
        log.warning("KDP store: generate_insights failed: %s", exc)

    return insights[:5]

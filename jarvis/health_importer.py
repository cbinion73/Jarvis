"""
JARVIS Health — CSV / File Import Pipeline
==========================================
Imports lab results, vitals, CGM readings, Garmin activity, and Apple Health
export data into the JARVIS health SQLite database at ~/.jarvis/health/health.db.

Supported importers
-------------------
* import_labs_csv        — standard lab CSV
* import_vitals_csv      — general vitals CSV
* import_cgm_csv         — Dexcom Clarity export
* import_garmin_csv      — Garmin Connect activity/daily CSV
* import_apple_health_xml — Apple Health export.xml
* get_import_history     — last 50 import events

Usage
-----
    from jarvis.health_importer import import_labs_csv
    result = import_labs_csv("/path/to/labs.csv")
"""
from __future__ import annotations

import csv
import json
import logging
import sqlite3
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_DB_PATH = Path.home() / ".jarvis" / "health" / "health.db"

# ---------------------------------------------------------------------------
# Test-name normalisation map
# ---------------------------------------------------------------------------
_LAB_NAME_MAP: dict[str, str] = {
    # HbA1c
    "hba1c": "HbA1c",
    "a1c": "HbA1c",
    "hemoglobin a1c": "HbA1c",
    "glycated hemoglobin": "HbA1c",
    "glycohemoglobin": "HbA1c",
    # Glucose
    "fasting glucose": "Fasting Glucose",
    "glucose fasting": "Fasting Glucose",
    "blood glucose": "Glucose",
    "glucose": "Glucose",
    # Lipids
    "total cholesterol": "Total Cholesterol",
    "cholesterol total": "Total Cholesterol",
    "cholesterol": "Total Cholesterol",
    "ldl": "LDL Cholesterol",
    "ldl cholesterol": "LDL Cholesterol",
    "ldl-c": "LDL Cholesterol",
    "hdl": "HDL Cholesterol",
    "hdl cholesterol": "HDL Cholesterol",
    "hdl-c": "HDL Cholesterol",
    "triglycerides": "Triglycerides",
    "trigs": "Triglycerides",
    "tg": "Triglycerides",
    # Kidney
    "creatinine": "Creatinine",
    "serum creatinine": "Creatinine",
    "egfr": "eGFR",
    "estimated gfr": "eGFR",
    "gfr": "eGFR",
    "bun": "BUN",
    "blood urea nitrogen": "BUN",
    # Thyroid
    "tsh": "TSH",
    "thyroid stimulating hormone": "TSH",
    "free t4": "Free T4",
    "free t3": "Free T3",
    "t4": "Total T4",
    "t3": "Total T3",
    # CBC
    "cbc": "CBC",
    "wbc": "WBC",
    "white blood cell": "WBC",
    "rbc": "RBC",
    "red blood cell": "RBC",
    "hemoglobin": "Hemoglobin",
    "hgb": "Hemoglobin",
    "hematocrit": "Hematocrit",
    "hct": "Hematocrit",
    "platelets": "Platelets",
    "plt": "Platelets",
    # Electrolytes / metabolic
    "sodium": "Sodium",
    "na": "Sodium",
    "potassium": "Potassium",
    "k": "Potassium",
    "chloride": "Chloride",
    "cl": "Chloride",
    "co2": "CO2",
    "bicarbonate": "CO2",
    "calcium": "Calcium",
    "ca": "Calcium",
    "magnesium": "Magnesium",
    "mg": "Magnesium",
    # Liver / metabolic
    "alt": "ALT",
    "alanine aminotransferase": "ALT",
    "ast": "AST",
    "aspartate aminotransferase": "AST",
    "alkaline phosphatase": "Alkaline Phosphatase",
    "alp": "Alkaline Phosphatase",
    "total bilirubin": "Total Bilirubin",
    "bilirubin": "Total Bilirubin",
    "albumin": "Albumin",
    "total protein": "Total Protein",
    # Vitamins / micronutrients
    "vitamin d": "Vitamin D",
    "25-oh vitamin d": "Vitamin D",
    "25-hydroxyvitamin d": "Vitamin D",
    "vitamin b12": "Vitamin B12",
    "b12": "Vitamin B12",
    "folate": "Folate",
    "folic acid": "Folate",
    "ferritin": "Ferritin",
    "iron": "Iron",
    "serum iron": "Iron",
    "zinc": "Zinc",
    # Cardiac
    "bnp": "BNP",
    "nt-probnp": "NT-proBNP",
    "troponin": "Troponin",
    # Inflammation
    "crp": "CRP",
    "c-reactive protein": "CRP",
    "hs-crp": "hs-CRP",
    "esr": "ESR",
    # Urine
    "microalbumin": "Microalbumin",
    "urine microalbumin": "Microalbumin",
    "acr": "Albumin-Creatinine Ratio",
}


def _normalize_lab_name(raw: str) -> str:
    """Normalize a raw test name string to a canonical form."""
    key = raw.strip().lower()
    return _LAB_NAME_MAP.get(key, raw.strip().title())


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    """Return a SQLite connection, creating the DB and tables if needed."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create all required tables if they do not already exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS lab_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT,
            test_name       TEXT    NOT NULL,
            value           REAL,
            value_text      TEXT,
            unit            TEXT,
            reference_range TEXT,
            flag            TEXT,
            source          TEXT    DEFAULT 'csv_import',
            imported_at     TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS vitals_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    NOT NULL,
            type        TEXT    NOT NULL,
            value       REAL,
            unit        TEXT,
            source      TEXT    DEFAULT 'csv_import',
            imported_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cgm_readings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT    NOT NULL,
            glucose_mgdl    REAL,
            rate_of_change  REAL,
            source          TEXT    DEFAULT 'dexcom',
            imported_at     TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wearable_daily (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            steps           INTEGER,
            distance_km     REAL,
            active_minutes  INTEGER,
            resting_hr      REAL,
            stress          REAL,
            body_battery    REAL,
            sleep_hours     REAL,
            hrv             REAL,
            source          TEXT    DEFAULT 'garmin',
            imported_at     TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS import_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            filename         TEXT,
            import_type      TEXT,
            records_imported INTEGER DEFAULT 0,
            errors           TEXT,
            imported_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


def _log_import(
    conn: sqlite3.Connection,
    filename: str,
    import_type: str,
    records_imported: int,
    errors: list[str],
) -> None:
    conn.execute(
        "INSERT INTO import_log (filename, import_type, records_imported, errors, imported_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            filename,
            import_type,
            records_imported,
            json.dumps(errors) if errors else "[]",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> float | None:
    """Convert *value* to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int | None:
    f = _safe_float(value)
    return int(f) if f is not None else None


def _norm_date(raw: str) -> str | None:
    """
    Parse a date string in various formats and return ISO-8601 date (YYYY-MM-DD).
    Returns None when parsing fails.
    """
    if not raw:
        return None
    raw = raw.strip()
    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(raw[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try ISO datetime
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _norm_timestamp(raw: str) -> str | None:
    """
    Parse a timestamp string and return ISO-8601 datetime.
    Returns None on failure.
    """
    if not raw:
        return None
    raw = raw.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%dT%H:%M",
    ):
        try:
            return datetime.strptime(raw[:19], fmt).isoformat()
        except ValueError:
            continue
    d = _norm_date(raw)
    return d if d else None


def _sniff_header(filepath: str) -> list[str]:
    """Read and return the CSV header row, normalised to lowercase stripped strings."""
    with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if row:
                return [c.strip().lower() for c in row]
    return []


# ---------------------------------------------------------------------------
# 1. import_labs_csv
# ---------------------------------------------------------------------------

def import_labs_csv(filepath: str) -> dict:
    """
    Import a standard lab result CSV into the ``lab_results`` table.

    Expected columns (case-insensitive):
        date, test_name, value, unit, reference_range, flag

    Parameters
    ----------
    filepath : str
        Path to the CSV file.

    Returns
    -------
    dict
        ``{"imported": N, "skipped": N, "errors": [...], "tests": [...]}``
    """
    filepath = str(filepath)
    imported = 0
    skipped = 0
    errors: list[str] = []
    tests_seen: list[str] = []

    try:
        conn = _get_connection()
    except Exception as exc:
        return {"imported": 0, "skipped": 0, "errors": [str(exc)], "tests": []}

    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                return {"imported": 0, "skipped": 0, "errors": ["Empty or unreadable CSV"], "tests": []}

            # Normalise field names
            reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
            col_map = {col: col for col in reader.fieldnames}

            # Accept common column name variants
            _aliases = {
                "test_name": ("test", "test name", "analyte", "panel", "name"),
                "date": ("collection_date", "result_date", "drawn_date", "specimen_date", "date collected"),
                "reference_range": ("ref_range", "reference range", "range", "normal_range", "normal range"),
                "flag": ("abnormal_flag", "result_flag", "status", "interpretation"),
            }
            for canonical, aliases in _aliases.items():
                if canonical not in col_map:
                    for alias in aliases:
                        if alias in col_map:
                            col_map[canonical] = alias
                            break

            for lineno, row in enumerate(reader, start=2):
                try:
                    raw_name = (row.get(col_map.get("test_name", "test_name")) or "").strip()
                    raw_date = (row.get(col_map.get("date", "date")) or "").strip()
                    raw_value = (row.get("value") or "").strip()
                    raw_unit = (row.get("unit") or row.get("units") or "").strip()
                    raw_ref = (row.get(col_map.get("reference_range", "reference_range")) or "").strip()
                    raw_flag = (row.get(col_map.get("flag", "flag")) or "").strip()

                    if not raw_name:
                        skipped += 1
                        continue

                    test_name = _normalize_lab_name(raw_name)
                    date_str = _norm_date(raw_date)
                    numeric_value = _safe_float(raw_value)

                    conn.execute(
                        "INSERT INTO lab_results "
                        "(date, test_name, value, value_text, unit, reference_range, flag, source, imported_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            date_str,
                            test_name,
                            numeric_value,
                            raw_value if numeric_value is None else None,
                            raw_unit or None,
                            raw_ref or None,
                            raw_flag or None,
                            "csv_import",
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    imported += 1
                    if test_name not in tests_seen:
                        tests_seen.append(test_name)

                except Exception as exc:
                    errors.append(f"Row {lineno}: {exc}")
                    skipped += 1

        conn.commit()
        _log_import(conn, filepath, "labs_csv", imported, errors)

    except FileNotFoundError:
        errors.append(f"File not found: {filepath}")
    except Exception as exc:
        errors.append(f"Unexpected error: {exc}")
        log.exception("import_labs_csv failed for %s", filepath)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    log.info("import_labs_csv: %d imported, %d skipped, %d errors from %s", imported, skipped, len(errors), filepath)
    return {"imported": imported, "skipped": skipped, "errors": errors, "tests": tests_seen}


# ---------------------------------------------------------------------------
# 2. import_vitals_csv
# ---------------------------------------------------------------------------

_VITAL_TYPES = frozenset({
    "weight_lbs", "systolic_bp", "diastolic_bp", "heart_rate", "spo2",
    "weight", "bp_systolic", "bp_diastolic", "hr", "blood_oxygen",
})


def import_vitals_csv(filepath: str) -> dict:
    """
    Import a vitals CSV into the ``vitals_log`` table.

    Expected columns (case-insensitive):
        date, type, value, unit

    The ``type`` column should contain one of:
        weight_lbs, systolic_bp, diastolic_bp, heart_rate, spo2

    Parameters
    ----------
    filepath : str
        Path to the CSV file.

    Returns
    -------
    dict
        ``{"imported": N, "skipped": N, "errors": [...], "types": {...}}``
    """
    filepath = str(filepath)
    imported = 0
    skipped = 0
    errors: list[str] = []
    type_counts: dict[str, int] = defaultdict(int)

    # Canonical aliases for type field values
    _type_aliases = {
        "weight": "weight_lbs",
        "weight_lbs": "weight_lbs",
        "systolic": "systolic_bp",
        "systolic_bp": "systolic_bp",
        "bp_systolic": "systolic_bp",
        "sbp": "systolic_bp",
        "diastolic": "diastolic_bp",
        "diastolic_bp": "diastolic_bp",
        "bp_diastolic": "diastolic_bp",
        "dbp": "diastolic_bp",
        "heart_rate": "heart_rate",
        "hr": "heart_rate",
        "pulse": "heart_rate",
        "resting_hr": "heart_rate",
        "spo2": "spo2",
        "oxygen_saturation": "spo2",
        "blood_oxygen": "spo2",
        "o2_sat": "spo2",
    }

    try:
        conn = _get_connection()
    except Exception as exc:
        return {"imported": 0, "skipped": 0, "errors": [str(exc)], "types": {}}

    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                return {"imported": 0, "skipped": 0, "errors": ["Empty CSV"], "types": {}}
            reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

            for lineno, row in enumerate(reader, start=2):
                try:
                    raw_date = (row.get("date") or "").strip()
                    raw_type = (row.get("type") or row.get("measurement") or "").strip().lower()
                    raw_value = (row.get("value") or row.get("reading") or "").strip()
                    raw_unit = (row.get("unit") or row.get("units") or "").strip()

                    if not raw_type or not raw_date:
                        skipped += 1
                        continue

                    canonical_type = _type_aliases.get(raw_type, raw_type)
                    date_str = _norm_date(raw_date)
                    if not date_str:
                        errors.append(f"Row {lineno}: unparseable date '{raw_date}'")
                        skipped += 1
                        continue

                    numeric_value = _safe_float(raw_value)
                    if numeric_value is None:
                        errors.append(f"Row {lineno}: non-numeric value '{raw_value}' for {canonical_type}")
                        skipped += 1
                        continue

                    conn.execute(
                        "INSERT INTO vitals_log (date, type, value, unit, source, imported_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (date_str, canonical_type, numeric_value, raw_unit or None, "csv_import",
                         datetime.now(timezone.utc).isoformat()),
                    )
                    imported += 1
                    type_counts[canonical_type] += 1

                except Exception as exc:
                    errors.append(f"Row {lineno}: {exc}")
                    skipped += 1

        conn.commit()
        _log_import(conn, filepath, "vitals_csv", imported, errors)

    except FileNotFoundError:
        errors.append(f"File not found: {filepath}")
    except Exception as exc:
        errors.append(f"Unexpected error: {exc}")
        log.exception("import_vitals_csv failed for %s", filepath)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    log.info("import_vitals_csv: %d imported, %d skipped from %s", imported, skipped, filepath)
    return {"imported": imported, "skipped": skipped, "errors": errors, "types": dict(type_counts)}


# ---------------------------------------------------------------------------
# 3. import_cgm_csv  (Dexcom Clarity)
# ---------------------------------------------------------------------------

_DEXCOM_GLUCOSE_COL = "glucose value (mg/dl)"
_DEXCOM_TIMESTAMP_COL = "timestamp (yyyy-mm-ddthh:mm:ss)"
_DEXCOM_EVENT_TYPE_COL = "event type"
_DEXCOM_ROC_COL = "glucose rate of change (mg/dl/min)"


def import_cgm_csv(filepath: str, source: str = "dexcom") -> dict:
    """
    Import a Dexcom Clarity CGM export CSV into the ``cgm_readings`` table.

    Only rows with ``Event Type == "EGV"`` (Estimated Glucose Value) are imported.
    Dexcom Clarity header names are matched case-insensitively.

    Parameters
    ----------
    filepath : str
        Path to the Dexcom Clarity CSV export.
    source : str
        Data source label stored in the database (default: ``"dexcom"``).

    Returns
    -------
    dict
        Summary including imported count, basic glucose statistics, and
        time-in-range metrics.
    """
    filepath = str(filepath)
    imported = 0
    skipped = 0
    errors: list[str] = []
    glucose_values: list[float] = []

    try:
        conn = _get_connection()
    except Exception as exc:
        return {"imported": 0, "skipped": 0, "errors": [str(exc)], "stats": {}}

    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            # Dexcom exports may have metadata rows before the header; find the header row.
            lines = fh.readlines()

        header_idx = None
        for i, line in enumerate(lines):
            if "event type" in line.lower():
                header_idx = i
                break

        if header_idx is None:
            return {
                "imported": 0, "skipped": 0,
                "errors": ["Could not find Dexcom header row in file"],
                "stats": {},
            }

        from io import StringIO
        csv_text = "".join(lines[header_idx:])
        reader = csv.DictReader(StringIO(csv_text))
        if reader.fieldnames is None:
            return {"imported": 0, "skipped": 0, "errors": ["Empty Dexcom CSV"], "stats": {}}

        norm_fields = {f.strip().lower(): f for f in reader.fieldnames}

        # Locate required columns
        ts_col = None
        glucose_col = None
        event_type_col = None
        roc_col = None

        for nf, orig in norm_fields.items():
            if "timestamp" in nf:
                ts_col = orig
            if "glucose value" in nf and "mg" in nf:
                glucose_col = orig
            if "event type" in nf:
                event_type_col = orig
            if "rate of change" in nf:
                roc_col = orig

        if not (ts_col and glucose_col and event_type_col):
            return {
                "imported": 0, "skipped": 0,
                "errors": [f"Missing required columns. Found: {list(norm_fields.keys())}"],
                "stats": {},
            }

        for lineno, row in enumerate(reader, start=header_idx + 2):
            try:
                event_type = (row.get(event_type_col) or "").strip()
                if event_type.upper() != "EGV":
                    skipped += 1
                    continue

                raw_ts = (row.get(ts_col) or "").strip()
                raw_glucose = (row.get(glucose_col) or "").strip()
                raw_roc = (row.get(roc_col) or "").strip() if roc_col else ""

                timestamp = _norm_timestamp(raw_ts)
                if not timestamp:
                    errors.append(f"Row {lineno}: unparseable timestamp '{raw_ts}'")
                    skipped += 1
                    continue

                glucose = _safe_float(raw_glucose)
                if glucose is None:
                    # Dexcom uses "Low" / "High" for out-of-range readings
                    if raw_glucose.lower() == "low":
                        glucose = 39.0
                    elif raw_glucose.lower() == "high":
                        glucose = 401.0
                    else:
                        skipped += 1
                        continue

                roc = _safe_float(raw_roc)

                conn.execute(
                    "INSERT INTO cgm_readings (timestamp, glucose_mgdl, rate_of_change, source, imported_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (timestamp, glucose, roc, source, datetime.now(timezone.utc).isoformat()),
                )
                imported += 1
                glucose_values.append(glucose)

            except Exception as exc:
                errors.append(f"Row {lineno}: {exc}")
                skipped += 1

        conn.commit()
        _log_import(conn, filepath, f"cgm_csv_{source}", imported, errors)

    except FileNotFoundError:
        errors.append(f"File not found: {filepath}")
    except Exception as exc:
        errors.append(f"Unexpected error: {exc}")
        log.exception("import_cgm_csv failed for %s", filepath)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # Compute basic statistics
    stats: dict[str, Any] = {}
    if glucose_values:
        n = len(glucose_values)
        in_range = sum(1 for g in glucose_values if 70 <= g <= 180)
        below_70 = sum(1 for g in glucose_values if g < 70)
        above_180 = sum(1 for g in glucose_values if g > 180)
        stats = {
            "count": n,
            "mean_mgdl": round(sum(glucose_values) / n, 1),
            "min_mgdl": round(min(glucose_values), 1),
            "max_mgdl": round(max(glucose_values), 1),
            "time_in_range_70_180_pct": round(in_range / n * 100, 1),
            "time_below_70_pct": round(below_70 / n * 100, 1),
            "time_above_180_pct": round(above_180 / n * 100, 1),
        }

    log.info("import_cgm_csv: %d imported, %d skipped from %s", imported, skipped, filepath)
    return {"imported": imported, "skipped": skipped, "errors": errors, "stats": stats}


# ---------------------------------------------------------------------------
# 4. import_garmin_csv
# ---------------------------------------------------------------------------

_GARMIN_COL_MAP = {
    "date": ("date",),
    "steps": ("steps",),
    "distance_km": ("distance (km)", "distance_km", "distance"),
    "active_minutes": ("active minutes", "active_minutes", "intensity minutes"),
    "resting_hr": ("resting heart rate", "resting_hr", "resting heart rate (bpm)"),
    "stress": ("average stress", "stress", "avg stress"),
    "body_battery": ("body battery high", "body battery", "body_battery"),
    "sleep_hours": ("sleep (hours)", "sleep hours", "sleep_hours", "sleep"),
    "hrv": ("hrv", "heart rate variability", "hrv status"),
}


def _find_garmin_col(fieldnames: list[str], canonical: str) -> str | None:
    """Return the actual fieldname matching a Garmin canonical column, or None."""
    lower_fields = {f.lower(): f for f in fieldnames}
    for alias in _GARMIN_COL_MAP.get(canonical, (canonical,)):
        if alias in lower_fields:
            return lower_fields[alias]
    return None


def import_garmin_csv(filepath: str) -> dict:
    """
    Import a Garmin Connect activity/daily summary CSV into ``wearable_daily``.

    Expected columns (flexible matching):
        Date, Steps, Distance (km), Active Minutes, Resting Heart Rate,
        Average Stress, Body Battery High, Sleep (hours), HRV

    Parameters
    ----------
    filepath : str
        Path to the Garmin Connect CSV export.

    Returns
    -------
    dict
        ``{"imported": N, "skipped": N, "errors": [...], "date_range": {...}}``
    """
    filepath = str(filepath)
    imported = 0
    skipped = 0
    errors: list[str] = []
    dates: list[str] = []

    try:
        conn = _get_connection()
    except Exception as exc:
        return {"imported": 0, "skipped": 0, "errors": [str(exc)], "date_range": {}}

    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                return {"imported": 0, "skipped": 0, "errors": ["Empty CSV"], "date_range": {}}

            fields = list(reader.fieldnames)
            col = {key: _find_garmin_col(fields, key) for key in _GARMIN_COL_MAP}

            if not col["date"]:
                return {
                    "imported": 0, "skipped": 0,
                    "errors": [f"Date column not found. Available: {fields}"],
                    "date_range": {},
                }

            for lineno, row in enumerate(reader, start=2):
                try:
                    raw_date = (row.get(col["date"]) or "").strip()
                    date_str = _norm_date(raw_date)
                    if not date_str:
                        errors.append(f"Row {lineno}: unparseable date '{raw_date}'")
                        skipped += 1
                        continue

                    def _get(key: str) -> str:
                        c = col.get(key)
                        return (row.get(c) or "").strip() if c else ""

                    conn.execute(
                        "INSERT INTO wearable_daily "
                        "(date, steps, distance_km, active_minutes, resting_hr, stress, "
                        "body_battery, sleep_hours, hrv, source, imported_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            date_str,
                            _safe_int(_get("steps")),
                            _safe_float(_get("distance_km")),
                            _safe_int(_get("active_minutes")),
                            _safe_float(_get("resting_hr")),
                            _safe_float(_get("stress")),
                            _safe_float(_get("body_battery")),
                            _safe_float(_get("sleep_hours")),
                            _safe_float(_get("hrv")),
                            "garmin",
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    imported += 1
                    dates.append(date_str)

                except Exception as exc:
                    errors.append(f"Row {lineno}: {exc}")
                    skipped += 1

        conn.commit()
        _log_import(conn, filepath, "garmin_csv", imported, errors)

    except FileNotFoundError:
        errors.append(f"File not found: {filepath}")
    except Exception as exc:
        errors.append(f"Unexpected error: {exc}")
        log.exception("import_garmin_csv failed for %s", filepath)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    date_range = {"earliest": min(dates), "latest": max(dates)} if dates else {}
    log.info("import_garmin_csv: %d imported, %d skipped from %s", imported, skipped, filepath)
    return {"imported": imported, "skipped": skipped, "errors": errors, "date_range": date_range}


# ---------------------------------------------------------------------------
# 5. import_apple_health_xml
# ---------------------------------------------------------------------------

_APPLE_HEALTH_TYPES = {
    "HKQuantityTypeIdentifierHeartRate": ("heart_rate", "vitals_log", "count/min"),
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": ("hrv", "wearable_daily", "ms"),
    "HKQuantityTypeIdentifierStepCount": ("steps", "wearable_daily", "count"),
    "HKQuantityTypeIdentifierBloodPressureSystolic": ("systolic_bp", "vitals_log", "mmHg"),
    "HKQuantityTypeIdentifierBloodPressureDiastolic": ("diastolic_bp", "vitals_log", "mmHg"),
    "HKQuantityTypeIdentifierOxygenSaturation": ("spo2", "vitals_log", "%"),
}

# Types that are summed per day vs averaged
_SUM_TYPES = {"steps"}


def import_apple_health_xml(filepath: str) -> dict:
    """
    Parse an Apple Health export.xml and import selected record types.

    Supported types:
        - HKQuantityTypeIdentifierHeartRate          → vitals_log (heart_rate)
        - HKQuantityTypeIdentifierHeartRateVariabilitySDNN → wearable_daily (hrv)
        - HKQuantityTypeIdentifierStepCount          → wearable_daily (steps)
        - HKQuantityTypeIdentifierBloodPressureSystolic   → vitals_log (systolic_bp)
        - HKQuantityTypeIdentifierBloodPressureDiastolic  → vitals_log (diastolic_bp)
        - HKQuantityTypeIdentifierOxygenSaturation   → vitals_log (spo2)

    Records are aggregated by day (summed for steps; averaged for all others)
    before insertion.

    Parameters
    ----------
    filepath : str
        Path to the Apple Health export.xml file.

    Returns
    -------
    dict
        ``{"imported": N, "skipped": N, "errors": [...], "by_type": {...}}``
    """
    filepath = str(filepath)
    imported = 0
    skipped = 0
    errors: list[str] = []
    by_type: dict[str, int] = defaultdict(int)

    # daily_buckets[hk_type][date] = list of float values
    daily_buckets: dict[str, dict[str, list[float]]] = {
        hk_type: defaultdict(list) for hk_type in _APPLE_HEALTH_TYPES
    }

    try:
        conn = _get_connection()
    except Exception as exc:
        return {"imported": 0, "skipped": 0, "errors": [str(exc)], "by_type": {}}

    try:
        context = ET.iterparse(filepath, events=("end",))
        for event, elem in context:
            if elem.tag != "Record":
                elem.clear()
                continue

            hk_type = elem.get("type", "")
            if hk_type not in _APPLE_HEALTH_TYPES:
                elem.clear()
                continue

            raw_value = elem.get("value") or elem.get("Value") or ""
            raw_date = (elem.get("startDate") or elem.get("creationDate") or "")[:10]

            val = _safe_float(raw_value)
            if val is None:
                skipped += 1
                elem.clear()
                continue

            date_str = _norm_date(raw_date)
            if not date_str:
                skipped += 1
                elem.clear()
                continue

            daily_buckets[hk_type][date_str].append(val)
            elem.clear()

    except ET.ParseError as exc:
        errors.append(f"XML parse error: {exc}")
        log.error("import_apple_health_xml XML error: %s", exc)
    except FileNotFoundError:
        errors.append(f"File not found: {filepath}")
        return {"imported": 0, "skipped": 0, "errors": errors, "by_type": {}}
    except Exception as exc:
        errors.append(f"Unexpected error during XML parse: {exc}")
        log.exception("import_apple_health_xml failed for %s", filepath)

    # Now insert aggregated daily records
    try:
        now_ts = datetime.now(timezone.utc).isoformat()

        for hk_type, day_map in daily_buckets.items():
            canonical_name, table, default_unit = _APPLE_HEALTH_TYPES[hk_type]
            use_sum = canonical_name in _SUM_TYPES

            for date_str, values in day_map.items():
                if not values:
                    continue

                agg_value = sum(values) if use_sum else (sum(values) / len(values))
                agg_value = round(agg_value, 2)

                try:
                    if table == "vitals_log":
                        conn.execute(
                            "INSERT INTO vitals_log (date, type, value, unit, source, imported_at) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (date_str, canonical_name, agg_value, default_unit, "apple_health", now_ts),
                        )
                    elif table == "wearable_daily":
                        # Upsert into wearable_daily by date + source
                        existing = conn.execute(
                            "SELECT id FROM wearable_daily WHERE date = ? AND source = ?",
                            (date_str, "apple_health"),
                        ).fetchone()
                        if existing:
                            conn.execute(
                                f"UPDATE wearable_daily SET {canonical_name} = ? WHERE id = ?",
                                (agg_value, existing["id"]),
                            )
                        else:
                            conn.execute(
                                f"INSERT INTO wearable_daily (date, {canonical_name}, source, imported_at) "
                                "VALUES (?, ?, ?, ?)",
                                (date_str, agg_value, "apple_health", now_ts),
                            )

                    imported += 1
                    by_type[canonical_name] += 1

                except Exception as exc:
                    errors.append(f"{hk_type} {date_str}: {exc}")
                    skipped += 1

        conn.commit()
        _log_import(conn, filepath, "apple_health_xml", imported, errors)

    except Exception as exc:
        errors.append(f"DB write error: {exc}")
        log.exception("import_apple_health_xml DB write failed")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    log.info(
        "import_apple_health_xml: %d imported, %d skipped from %s — types: %s",
        imported, skipped, filepath, dict(by_type),
    )
    return {"imported": imported, "skipped": skipped, "errors": errors, "by_type": dict(by_type)}


# ---------------------------------------------------------------------------
# 6. get_import_history
# ---------------------------------------------------------------------------

def get_import_history() -> list[dict]:
    """
    Return the last 50 import events from the ``import_log`` table.

    Returns
    -------
    list[dict]
        Each entry contains: id, filename, import_type, records_imported,
        errors, imported_at.
    """
    try:
        conn = _get_connection()
        rows = conn.execute(
            "SELECT id, filename, import_type, records_imported, errors, imported_at "
            "FROM import_log ORDER BY id DESC LIMIT 50"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as exc:
        log.error("get_import_history failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if len(sys.argv) < 3:
        print(
            "Usage: python -m jarvis.health_importer <type> <filepath> [source]\n"
            "  type: labs | vitals | cgm | garmin | apple\n"
            "  Example: python -m jarvis.health_importer cgm ~/Downloads/clarity_export.csv dexcom",
            file=sys.stderr,
        )
        sys.exit(1)

    import_type = sys.argv[1].lower()
    file_path = sys.argv[2]
    extra_arg = sys.argv[3] if len(sys.argv) > 3 else None

    dispatch = {
        "labs":   lambda: import_labs_csv(file_path),
        "vitals": lambda: import_vitals_csv(file_path),
        "cgm":    lambda: import_cgm_csv(file_path, extra_arg or "dexcom"),
        "garmin": lambda: import_garmin_csv(file_path),
        "apple":  lambda: import_apple_health_xml(file_path),
        "history": lambda: get_import_history(),
    }

    fn = dispatch.get(import_type)
    if fn is None:
        print(f"Unknown import type '{import_type}'. Choose: {list(dispatch.keys())}", file=sys.stderr)
        sys.exit(1)

    result = fn()
    print(json.dumps(result, indent=2, default=str))

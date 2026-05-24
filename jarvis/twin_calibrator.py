"""
twin_calibrator.py — JARVIS Digital Twin Calibration Engine

Reads from both the health state JSON and health.db SQLite to build the
richest possible data history for calibration. Merges DB-sourced observations
with hardcoded baseline history, deduplicates by date, and fits trajectories
for all tracked metrics.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal imports with fallback pattern
# ---------------------------------------------------------------------------
try:
    from jarvis.digital_twin import (
        DataPoint,
        MetricTrajectory,
        _METRIC_CATALOG,
        _METRIC_HISTORY,
        _HEALTH_DIR,
        _TWIN_STATE_PATH,
        _HEALTH_STATE_PATH,
        _build_trajectory,
        _ensure_health_dir,
        _history_to_datapoints,
        _save_twin_state,
        fit_trajectory,
    )
except ImportError:
    try:
        from digital_twin import (
            DataPoint,
            MetricTrajectory,
            _METRIC_CATALOG,
            _METRIC_HISTORY,
            _HEALTH_DIR,
            _TWIN_STATE_PATH,
            _HEALTH_STATE_PATH,
            _build_trajectory,
            _ensure_health_dir,
            _history_to_datapoints,
            _save_twin_state,
            fit_trajectory,
        )
    except ImportError:
        # Absolute fallback — define minimal stubs so module is importable
        log.error(
            "Could not import from digital_twin. "
            "Ensure digital_twin.py is on sys.path."
        )
        from dataclasses import dataclass
        from pathlib import Path

        _HEALTH_DIR = Path.home() / ".jarvis" / "health"
        _TWIN_STATE_PATH = _HEALTH_DIR / "twin_state.json"
        _HEALTH_STATE_PATH = _HEALTH_DIR / "chris_health_state.json"
        _METRIC_CATALOG: dict = {}
        _METRIC_HISTORY: dict = {}

        @dataclass
        class DataPoint:  # type: ignore[no-redef]
            date: str
            value: float
            source: str = "lab"

        @dataclass
        class MetricTrajectory:  # type: ignore[no-redef]
            metric_name: str
            unit: str
            goal_value: float | None
            goal_direction: str
            history: list
            current_value: float
            current_date: str
            trend_slope_per_month: float
            trend_confidence: float
            residual_std: float

        def _ensure_health_dir() -> None:
            _HEALTH_DIR.mkdir(parents=True, exist_ok=True)

        def _history_to_datapoints(raw: list[dict]) -> list:
            return []

        def _save_twin_state(state: dict) -> None:
            pass

        def _build_trajectory(metric: str, history: list, current_values: dict):  # type: ignore[return]
            pass

        def fit_trajectory(history: list) -> tuple:
            return 0.0, 0.0, 0.0


# ---------------------------------------------------------------------------
# DB paths
# ---------------------------------------------------------------------------
_HEALTH_DB_PATH = _HEALTH_DIR / "health.db"

# ---------------------------------------------------------------------------
# Canonical metric name normalisation map
# DB test names are messy — map them to our internal keys
# ---------------------------------------------------------------------------
_LAB_NAME_MAP: dict[str, str] = {
    # A1c variants
    "hemoglobin a1c": "a1c",
    "a1c": "a1c",
    "hba1c": "a1c",
    "glycated hemoglobin": "a1c",
    "glycohemoglobin": "a1c",
    # LDL variants
    "ldl": "ldl",
    "ldl cholesterol": "ldl",
    "ldl-c": "ldl",
    "low density lipoprotein": "ldl",
    "low-density lipoprotein": "ldl",
    # eGFR variants
    "egfr": "egfr",
    "estimated gfr": "egfr",
    "glomerular filtration rate": "egfr",
    "egfr (ckd-epi)": "egfr",
    "gfr": "egfr",
    # Potassium
    "potassium": "potassium",
    "k+": "potassium",
    "serum potassium": "potassium",
    # Blood pressure
    "systolic bp": "systolic_bp",
    "systolic blood pressure": "systolic_bp",
    "systolic": "systolic_bp",
}

_VITALS_NAME_MAP: dict[str, str] = {
    "systolic_bp":  "systolic_bp",
    "systolic bp":  "systolic_bp",
    "systolic":     "systolic_bp",
    "weight":       "weight_lbs",
    "weight_lbs":   "weight_lbs",
    "bmi":          "bmi",
    "heart_rate":   "resting_hr",
    "resting_hr":   "resting_hr",
    "pulse":        "resting_hr",
}

_WEARABLE_COLUMN_MAP: dict[str, str] = {
    "hrv":             "hrv",
    "hrv_ms":          "hrv",
    "resting_hr":      "resting_hr",
    "resting_heart_rate": "resting_hr",
    "steps":           "steps",
    "step_count":      "steps",
    "sleep_hours":     "sleep_hours",
    "total_sleep":     "sleep_hours",
}


def _normalize_lab_name(raw_name: str) -> Optional[str]:
    """
    Normalise a raw lab test name to an internal metric key.

    Args:
        raw_name: Raw test name from the database.

    Returns:
        Internal metric key or None if unmappable.
    """
    return _LAB_NAME_MAP.get(raw_name.lower().strip())


def _normalize_vital_name(raw_name: str) -> Optional[str]:
    """Normalise a raw vital name to an internal metric key."""
    return _VITALS_NAME_MAP.get(raw_name.lower().strip())


def _open_db() -> Optional[sqlite3.Connection]:
    """
    Open a read-only connection to health.db.

    Returns:
        sqlite3.Connection or None if the DB does not exist or cannot be opened.
    """
    if not _HEALTH_DB_PATH.exists():
        log.debug("health.db not found at %s", _HEALTH_DB_PATH)
        return None
    try:
        conn = sqlite3.connect(f"file:{_HEALTH_DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError as exc:
        log.warning("Could not open health.db: %s", exc)
        return None


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Return True if the named table exists in the connected database."""
    try:
        cur = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return cur.fetchone() is not None
    except Exception:
        return False


def _columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    """Return column names for the given table."""
    try:
        cur = conn.execute(f"PRAGMA table_info({table_name})")
        return [row["name"] for row in cur.fetchall()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Function 1: load_lab_history_from_db
# ---------------------------------------------------------------------------

def load_lab_history_from_db() -> dict[str, list[DataPoint]]:
    """
    Read lab results from health.db's lab_results table.

    Expected schema (flexible — adapts to available columns):
        lab_results(id, date|collected_date|result_date, test_name|name, value|result_value, unit, source)

    Returns:
        Dict mapping metric_name → sorted list of DataPoints.
        Returns empty dict if DB is unavailable.
    """
    result: dict[str, list[DataPoint]] = {}
    conn = _open_db()
    if conn is None:
        return result

    try:
        if not _table_exists(conn, "lab_results"):
            log.debug("lab_results table not found in health.db")
            return result

        cols = _columns(conn, "lab_results")
        log.debug("lab_results columns: %s", cols)

        # Determine column names flexibly
        date_col  = next((c for c in cols if c in ("date", "collected_date", "result_date", "lab_date")), None)
        name_col  = next((c for c in cols if c in ("test_name", "name", "lab_name", "analyte")), None)
        value_col = next((c for c in cols if c in ("value", "result_value", "numeric_value", "result")), None)

        if not all([date_col, name_col, value_col]):
            log.warning(
                "lab_results schema missing required columns. Found: %s", cols
            )
            return result

        source_col = next((c for c in cols if c in ("source", "source_system", "provider")), None)

        query = f"SELECT {date_col}, {name_col}, {value_col}"
        if source_col:
            query += f", {source_col}"
        query += " FROM lab_results ORDER BY {date_col}".format(date_col=date_col)

        rows = conn.execute(query).fetchall()
        for row in rows:
            raw_date  = str(row[0])[:10] if row[0] else None
            raw_name  = str(row[1]) if row[1] else None
            raw_value = row[2]
            source    = str(row[source_col]) if source_col and row[source_col] else "lab_db"

            if not raw_date or not raw_name or raw_value is None:
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue

            metric = _normalize_lab_name(raw_name)
            if metric is None:
                continue

            dp = DataPoint(date=raw_date, value=value, source=source)
            result.setdefault(metric, []).append(dp)

    except Exception as exc:
        log.error("Error loading lab history from DB: %s", exc)
    finally:
        conn.close()

    # Sort each metric by date
    for metric in result:
        result[metric].sort(key=lambda dp: dp.date)

    log.info(
        "Loaded lab history from DB: %s",
        {m: len(pts) for m, pts in result.items()},
    )
    return result


# ---------------------------------------------------------------------------
# Function 2: load_vitals_from_db
# ---------------------------------------------------------------------------

def load_vitals_from_db() -> dict[str, list[DataPoint]]:
    """
    Read vital signs from health.db's vitals_log table.

    Expected schema (flexible):
        vitals_log(id, date|recorded_at, type|vital_type|name, value|reading, unit, source)

    Returns:
        Dict mapping metric_name → sorted list of DataPoints.
        Returns empty dict if DB is unavailable.
    """
    result: dict[str, list[DataPoint]] = {}
    conn = _open_db()
    if conn is None:
        return result

    try:
        if not _table_exists(conn, "vitals_log"):
            log.debug("vitals_log table not found in health.db")
            return result

        cols = _columns(conn, "vitals_log")
        date_col  = next((c for c in cols if c in ("date", "recorded_at", "timestamp", "vital_date")), None)
        type_col  = next((c for c in cols if c in ("type", "vital_type", "name", "vital_name")), None)
        value_col = next((c for c in cols if c in ("value", "reading", "measurement", "numeric_value")), None)
        source_col = next((c for c in cols if c in ("source", "source_system")), None)

        if not all([date_col, type_col, value_col]):
            log.warning("vitals_log schema missing required columns. Found: %s", cols)
            return result

        query = f"SELECT {date_col}, {type_col}, {value_col}"
        if source_col:
            query += f", {source_col}"
        query += f" FROM vitals_log ORDER BY {date_col}"

        rows = conn.execute(query).fetchall()
        for row in rows:
            raw_date  = str(row[0])[:10] if row[0] else None
            raw_type  = str(row[1]) if row[1] else None
            raw_value = row[2]
            source    = str(row[source_col]) if source_col and row[source_col] else "vitals_db"

            if not raw_date or not raw_type or raw_value is None:
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue

            metric = _normalize_vital_name(raw_type)
            if metric is None:
                continue

            dp = DataPoint(date=raw_date, value=value, source=source)
            result.setdefault(metric, []).append(dp)

    except Exception as exc:
        log.error("Error loading vitals from DB: %s", exc)
    finally:
        conn.close()

    for metric in result:
        result[metric].sort(key=lambda dp: dp.date)

    log.info(
        "Loaded vitals from DB: %s",
        {m: len(pts) for m, pts in result.items()},
    )
    return result


# ---------------------------------------------------------------------------
# Function 3: load_wearables_from_db
# ---------------------------------------------------------------------------

def load_wearables_from_db() -> dict[str, list[DataPoint]]:
    """
    Read wearable data from health.db's wearable_daily table.

    Extracts: hrv, resting_hr, steps, sleep_hours.

    Expected schema (flexible — uses column introspection):
        wearable_daily(id, date|recorded_date, hrv|hrv_ms, resting_hr|resting_heart_rate,
                       steps|step_count, sleep_hours|total_sleep, source|device)

    Returns:
        Dict mapping metric_name → sorted list of DataPoints.
        Returns empty dict if DB is unavailable.
    """
    result: dict[str, list[DataPoint]] = {}
    conn = _open_db()
    if conn is None:
        return result

    try:
        if not _table_exists(conn, "wearable_daily"):
            log.debug("wearable_daily table not found in health.db")
            return result

        cols = _columns(conn, "wearable_daily")
        date_col   = next((c for c in cols if c in ("date", "recorded_date", "day", "timestamp")), None)
        source_col = next((c for c in cols if c in ("source", "device", "source_system")), None)

        if not date_col:
            log.warning("wearable_daily has no recognisable date column. Cols: %s", cols)
            return result

        # Build SELECT clause for known metrics
        metric_columns: dict[str, str] = {}  # internal_metric → db_column
        for col in cols:
            canonical = _WEARABLE_COLUMN_MAP.get(col.lower())
            if canonical and canonical not in metric_columns:
                metric_columns[canonical] = col

        if not metric_columns:
            log.warning("No recognisable wearable metric columns found in wearable_daily")
            return result

        select_cols = [date_col] + list(metric_columns.values())
        if source_col and source_col not in select_cols:
            select_cols.append(source_col)

        query = f"SELECT {', '.join(select_cols)} FROM wearable_daily ORDER BY {date_col}"
        rows = conn.execute(query).fetchall()

        for row in rows:
            raw_date = str(row[date_col])[:10] if row[date_col] else None
            if not raw_date:
                continue
            source = str(row[source_col]) if source_col and row[source_col] else "wearable_db"

            for metric, db_col in metric_columns.items():
                raw_val = row[db_col]
                if raw_val is None:
                    continue
                try:
                    value = float(raw_val)
                except (TypeError, ValueError):
                    continue
                dp = DataPoint(date=raw_date, value=value, source=source)
                result.setdefault(metric, []).append(dp)

    except Exception as exc:
        log.error("Error loading wearables from DB: %s", exc)
    finally:
        conn.close()

    for metric in result:
        result[metric].sort(key=lambda dp: dp.date)

    log.info(
        "Loaded wearables from DB: %s",
        {m: len(pts) for m, pts in result.items()},
    )
    return result


# ---------------------------------------------------------------------------
# Function 4: merge_histories
# ---------------------------------------------------------------------------

def merge_histories(
    db_history: dict[str, list[DataPoint]],
    hardcoded: dict[str, list[dict]],
) -> dict[str, list[DataPoint]]:
    """
    Merge DB-loaded history with hardcoded defaults.

    Rules:
    - DB data takes priority over hardcoded data for the same date.
    - Hardcoded entries fill gaps not present in DB data.
    - Deduplication is by date (YYYY-MM-DD); the DB version wins on collision.
    - Results are sorted ascending by date.

    Args:
        db_history: Dict of metric → list[DataPoint] loaded from health.db.
        hardcoded: Dict of metric → list[raw dicts] from _METRIC_HISTORY.

    Returns:
        Merged dict of metric → sorted deduplicated list[DataPoint].
    """
    merged: dict[str, list[DataPoint]] = {}

    # Collect all metric keys from both sources
    all_metrics = set(db_history.keys()) | set(hardcoded.keys())

    for metric in all_metrics:
        db_points  = db_history.get(metric, [])
        hc_raw     = hardcoded.get(metric, [])
        hc_points  = _history_to_datapoints(hc_raw)

        # Build a date → DataPoint map; DB wins on collision
        date_map: dict[str, DataPoint] = {}

        # Load hardcoded first (lower priority)
        for dp in hc_points:
            date_map[dp.date] = dp

        # Overwrite with DB data (higher priority)
        for dp in db_points:
            date_map[dp.date] = dp

        sorted_points = sorted(date_map.values(), key=lambda dp: dp.date)
        merged[metric] = sorted_points

    return merged


# ---------------------------------------------------------------------------
# Function 5: run_calibration
# ---------------------------------------------------------------------------

def run_calibration() -> dict:
    """
    Full calibration run: load, merge, fit, and persist.

    Steps:
    1. Load lab, vitals, and wearable data from health.db.
    2. Merge with hardcoded history (_METRIC_HISTORY).
    3. Load current values from health state JSON (for snapshot).
    4. Fit trajectories for all metrics in _METRIC_CATALOG.
    5. Save twin_state.json.
    6. Return summary: metrics calibrated, data points per metric, confidence.

    Returns:
        Dict with keys: metrics_calibrated, data_points, confidence,
        calibrated_at, sources_used.
    """
    _ensure_health_dir()

    # 1. Load from DB
    lab_history      = load_lab_history_from_db()
    vitals_history   = load_vitals_from_db()
    wearable_history = load_wearables_from_db()

    # Combine DB sources
    db_combined: dict[str, list[DataPoint]] = {}
    for source in (lab_history, vitals_history, wearable_history):
        for metric, points in source.items():
            existing = db_combined.get(metric, [])
            # Merge by date
            date_map = {dp.date: dp for dp in existing}
            for dp in points:
                date_map[dp.date] = dp  # latest source wins within DB
            db_combined[metric] = sorted(date_map.values(), key=lambda dp: dp.date)

    sources_used = {
        "lab_db": bool(lab_history),
        "vitals_db": bool(vitals_history),
        "wearable_db": bool(wearable_history),
        "hardcoded_baseline": True,
    }

    # 2. Merge with hardcoded baseline
    merged = merge_histories(db_combined, _METRIC_HISTORY)

    # 3. Load current values from health state JSON
    current_values: dict[str, float] = {}
    try:
        if _HEALTH_STATE_PATH.exists():
            with open(_HEALTH_STATE_PATH) as fh:
                health_state = json.load(fh)
            current_values = health_state.get("current_values", {})
    except Exception as exc:
        log.warning("Could not load health state for current values: %s", exc)

    # Fill in current values from latest data point if not in health state
    for metric, points in merged.items():
        if metric not in current_values and points:
            current_values[metric] = points[-1].value

    # 4. Fit trajectories
    trajectories: dict[str, dict] = {}
    summary_points: dict[str, int] = {}
    summary_confidence: dict[str, float] = {}

    for metric in _METRIC_CATALOG:
        history = merged.get(metric, [])
        try:
            traj = _build_trajectory(metric, history, current_values)
            if traj is None:
                continue
            trajectories[metric] = {
                "metric_name":          traj.metric_name,
                "unit":                 traj.unit,
                "goal_value":           traj.goal_value,
                "goal_direction":       traj.goal_direction,
                "current_value":        traj.current_value,
                "current_date":         traj.current_date,
                "trend_slope_per_month": traj.trend_slope_per_month,
                "trend_confidence":     traj.trend_confidence,
                "residual_std":         traj.residual_std,
                "n_points":             len(history),
                "history":              [
                    {"date": dp.date, "value": dp.value, "source": dp.source}
                    for dp in history
                ],
            }
            summary_points[metric]     = len(history)
            summary_confidence[metric] = traj.trend_confidence
        except Exception as exc:
            log.error("Failed to build trajectory for %s: %s", metric, exc)

    # 5. Save twin_state.json
    twin_state = {
        "calibrated_at":  datetime.now().isoformat(),
        "sources_used":   sources_used,
        "current_values": current_values,
        "trajectories":   trajectories,
        "predictions":    _load_existing_predictions(),
    }
    _save_twin_state(twin_state)

    summary = {
        "metrics_calibrated": list(trajectories.keys()),
        "data_points":        summary_points,
        "confidence":         summary_confidence,
        "calibrated_at":      twin_state["calibrated_at"],
        "sources_used":       sources_used,
    }
    log.info(
        "Calibration complete: %d metrics, sources=%s",
        len(trajectories),
        sources_used,
    )
    return summary


def _load_existing_predictions() -> list[dict]:
    """Load existing predictions from twin_state.json to preserve them during recalibration."""
    try:
        if _TWIN_STATE_PATH.exists():
            with open(_TWIN_STATE_PATH) as fh:
                state = json.load(fh)
            return state.get("predictions", [])
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Function 6: schedule_recalibration_check
# ---------------------------------------------------------------------------

def schedule_recalibration_check() -> bool:
    """
    Return True if twin_state.json is older than 24 hours.

    Used to determine whether a recalibration pass is needed. Recalibration
    is recommended whenever new lab data may have been imported (daily check).

    Returns:
        True if twin_state.json does not exist or is more than 24 hours old.
        False if it was calibrated within the last 24 hours.
    """
    if not _TWIN_STATE_PATH.exists():
        log.debug("twin_state.json not found — recalibration needed.")
        return True

    try:
        mtime = _TWIN_STATE_PATH.stat().st_mtime
        age_seconds = datetime.now().timestamp() - mtime
        needs_recal = age_seconds > 86400  # 24 hours
        if needs_recal:
            log.info(
                "twin_state.json is %.1f hours old — recalibration recommended.",
                age_seconds / 3600,
            )
        else:
            log.debug(
                "twin_state.json is %.1f hours old — no recalibration needed.",
                age_seconds / 3600,
            )
        return needs_recal
    except Exception as exc:
        log.warning("Could not check twin_state.json age: %s", exc)
        return True


# ---------------------------------------------------------------------------
# Module-level convenience: auto-calibrate if stale
# ---------------------------------------------------------------------------

def ensure_calibrated() -> dict:
    """
    Ensure the twin is calibrated and up to date.

    Runs run_calibration() if twin_state.json is missing or older than 24 hours.

    Returns:
        The calibration summary dict (from run_calibration) or a status dict
        indicating no recalibration was needed.
    """
    if schedule_recalibration_check():
        log.info("Running recalibration...")
        return run_calibration()
    return {
        "status": "up_to_date",
        "twin_state_path": str(_TWIN_STATE_PATH),
        "message": "Twin state is current (< 24h old). No recalibration needed.",
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run a full calibration and print summary."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print("=== JARVIS Twin Calibrator ===")
    print(f"health.db path : {_HEALTH_DB_PATH}")
    print(f"DB exists      : {_HEALTH_DB_PATH.exists()}")
    print()

    summary = run_calibration()
    print("Calibration summary:")
    for metric in summary.get("metrics_calibrated", []):
        n       = summary["data_points"].get(metric, 0)
        conf    = summary["confidence"].get(metric, 0.0)
        print(f"  {metric:15s}  {n:2d} pts  confidence={conf:.2f}")

    print(f"\nCalibrated at: {summary['calibrated_at']}")
    print(f"Sources used : {summary['sources_used']}")


if __name__ == "__main__":
    main()

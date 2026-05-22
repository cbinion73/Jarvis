"""
ehi_ingest.py — Epic EHI Export Ingestion Pipeline
====================================================
Parses the Epic Electronic Health Information (EHI) export TSV files and
ingests them into the JARVIS health database using the existing helper
functions in health_db.py.

Data sources:
  - EHITables/ORDER_RESULTS.tsv  — 878 lab component results with values
  - EHITables/ORDER_PROC.tsv     — lab panel/order names
  - EHITables/PROBLEM_LIST.tsv   — conditions / diagnoses
  - EHITables/ORDER_MED.tsv      — medication history
  - EHITables/PAT_ENC.tsv        — encounter / visit history

Usage:
  cd /Users/chris/Desktop/CODE/JARVIS
  .venv/bin/python -m jarvis.ehi_ingest /tmp/health_record
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> Optional[str]:
    """Parse Epic date strings to ISO date string YYYY-MM-DD."""
    if not s or not s.strip():
        return None
    s = s.strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.split(".")[0], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        return datetime.strptime(s[:10], "%m/%d/%Y").strftime("%Y-%m-%d")
    except Exception:
        return None


def _load_tsv(path: Path) -> list[dict]:
    if not path.exists():
        log.warning("TSV not found: %s", path)
        return []
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append({k: (v.strip() if v else "") for k, v in row.items()})
    return rows


# ---------------------------------------------------------------------------
# Build condition list
# ---------------------------------------------------------------------------

def build_conditions(record_dir: Path) -> list[dict]:
    rows = _load_tsv(record_dir / "EHITables" / "PROBLEM_LIST.tsv")
    result = []
    for row in rows:
        dx_name = row.get("DX_ID_DX_NAME", "").strip()
        description = row.get("DESCRIPTION", "").strip()
        noted_date = _parse_date(row.get("NOTED_DATE", ""))
        resolved_date = _parse_date(row.get("RESOLVED_DATE", ""))
        status = row.get("PROBLEM_STATUS_C_NAME", "Active").strip()
        chronic = row.get("CHRONIC_YN", "N").strip() == "Y"
        comment = row.get("PROBLEM_CMT", "").strip()

        name = dx_name or description
        if not name:
            continue

        is_active = status.lower() == "active"

        notes_parts = []
        if noted_date:
            notes_parts.append(f"Noted: {noted_date}")
        if resolved_date:
            notes_parts.append(f"Resolved: {resolved_date}")
        if chronic:
            notes_parts.append("Chronic")
        if comment:
            notes_parts.append(comment)

        # Determine category
        name_lower = name.lower()
        if any(x in name_lower for x in ("diabetes", "glucose", "insulin", "a1c", "metformin")):
            category = "Diabetes"
        elif any(x in name_lower for x in ("hypertension", "blood pressure", "cardiac", "heart")):
            category = "Cardiovascular"
        elif any(x in name_lower for x in ("obesity", "weight", "bmi", "bariatric", "gastrectomy")):
            category = "Weight Management"
        elif any(x in name_lower for x in ("sleep", "apnea", "cpap")):
            category = "Sleep"
        elif any(x in name_lower for x in ("thyroid", "cortisol", "adrenal", "hypercorticism")):
            category = "Endocrine"
        elif any(x in name_lower for x in ("migraine", "back", "pain")):
            category = "Musculoskeletal/Neurology"
        elif any(x in name_lower for x in ("statin", "myopathy", "cholesterol", "lipid")):
            category = "Medication Side Effects"
        else:
            category = "Other"

        result.append({
            "condition_name": name,
            "category": category,
            "status": "active" if is_active else "resolved",
            "raw_text": " | ".join(notes_parts) if notes_parts else None,
        })

    return result


# ---------------------------------------------------------------------------
# Build medication list
# ---------------------------------------------------------------------------

def build_medications(record_dir: Path) -> list[dict]:
    rows = _load_tsv(record_dir / "EHITables" / "ORDER_MED.tsv")
    today = datetime.now().strftime("%Y-%m-%d")

    # Deduplicate: keep most-recent ordering for each med name
    med_map: dict[str, dict] = {}
    for row in rows:
        name = row.get("MEDICATION_ID_MEDICATION_NAME", "").strip() or row.get("DESCRIPTION", "").strip()
        if not name:
            continue

        ordering_date = _parse_date(row.get("ORDERING_DATE", ""))
        end_date = _parse_date(row.get("END_DATE", ""))
        disc_reason = row.get("RSN_FOR_DISCON_C_NAME", "").strip()
        dosage = row.get("DOSAGE", "").strip()
        description = row.get("DESCRIPTION", "").strip()
        prescriber_raw = row.get("MED_PRESC_PROV_ID_PROV_NAME", "").strip()
        pharmacy_raw = row.get("PHARMACY_ID_PHARMACY_NAME", "").strip()

        # Skip inpatient-only transition meds
        if disc_reason in ("Patient transfer", "Patient discharge"):
            continue

        # Skip old historical meds (pre-2022 with definitive end)
        if end_date and ordering_date:
            try:
                order_year = int(ordering_date[:4])
            except Exception:
                order_year = 2000
            if order_year < 2022 and end_date < "2023-01-01":
                continue

        key = name[:80].upper()
        existing = med_map.get(key)
        if not existing or (ordering_date and ordering_date > (existing.get("ordering_date") or "")):
            med_map[key] = {
                "name": name,
                "dosage": dosage or description,
                "ordering_date": ordering_date,
                "end_date": end_date,
                "disc_reason": disc_reason,
                "prescriber": prescriber_raw,
                "pharmacy": pharmacy_raw,
            }

    result = []
    for key, m in med_map.items():
        is_active = (
            (not m["end_date"] or m["end_date"] >= today) and
            not m["disc_reason"]
        )

        # Build raw_text with relevant info
        notes = []
        if m.get("ordering_date"):
            notes.append(f"Ordered: {m['ordering_date']}")
        if m.get("end_date"):
            notes.append(f"End: {m['end_date']}")
        if m.get("disc_reason"):
            notes.append(f"Discontinued: {m['disc_reason']}")
        if not is_active:
            notes.append("(inactive)")

        result.append({
            "name": m["name"],
            "dosage": m["dosage"] or None,
            "frequency": m["dosage"] or None,  # dosage field often contains sig
            "prescribed_date": m["ordering_date"],
            "prescriber": m["prescriber"] or None,
            "pharmacy": m["pharmacy"] or None,
            "raw_text": " | ".join(notes) if notes else None,
        })

    return result


# ---------------------------------------------------------------------------
# Build lab results list
# ---------------------------------------------------------------------------

def build_lab_results(record_dir: Path) -> list[dict]:
    # Load panels (for names)
    proc_rows = _load_tsv(record_dir / "EHITables" / "ORDER_PROC.tsv")
    proc_map: dict[str, dict] = {r["ORDER_PROC_ID"]: r for r in proc_rows if r.get("ORDER_PROC_ID")}

    # Load result components
    result_rows = _load_tsv(record_dir / "EHITables" / "ORDER_RESULTS.tsv")
    if not result_rows:
        return []

    # Group by ORDER_PROC_ID
    panels: dict[str, list[dict]] = {}
    for row in result_rows:
        proc_id = row.get("ORDER_PROC_ID", "").strip()
        if proc_id:
            panels.setdefault(proc_id, []).append(row)

    results = []

    for proc_id, components in panels.items():
        proc = proc_map.get(proc_id, {})
        panel_name = (
            proc.get("PROC_ID_PROC_NAME", "").strip() or
            proc.get("DESCRIPTION", "").strip() or
            f"Lab Order {proc_id}"
        )
        ordering_date_raw = proc.get("ORDERING_DATE", "").strip()
        provider = proc.get("AUTHRZING_PROV_ID_PROV_NAME", "").strip()

        # Get result date from first component that has one
        result_date = None
        for comp in components:
            result_date = _parse_date(comp.get("RESULT_DATE", ""))
            if result_date:
                break
        if not result_date:
            result_date = _parse_date(ordering_date_raw)
        if not result_date:
            continue

        # Build component list with full data
        comp_list = []
        has_abnormal = False
        primary_value = None
        primary_unit = None
        primary_ref = None
        primary_flag = None

        for comp in components:
            comp_name = comp.get("COMPONENT_ID_NAME", "").strip()
            ord_value = comp.get("ORD_VALUE", "").strip()
            ref_low = comp.get("REFERENCE_LOW", "").strip()
            ref_high = comp.get("REFERENCE_HIGH", "").strip()
            ref_unit = comp.get("REFERENCE_UNIT", "").strip()
            flag = comp.get("RESULT_FLAG_C_NAME", "").strip()
            loinc = comp.get("COMPON_LNC_ID_LNC_LONG_NAME", "").strip()

            if flag and flag.lower() not in ("normal", ""):
                has_abnormal = True

            ref_range = None
            if ref_low or ref_high:
                if ref_low and ref_high:
                    ref_range = f"{ref_low}-{ref_high}"
                elif ref_high:
                    ref_range = f"<={ref_high}"
                elif ref_low:
                    ref_range = f">={ref_low}"
                if ref_unit:
                    ref_range = f"{ref_range} {ref_unit}"

            if ord_value:
                c = {"name": comp_name, "value": ord_value}
                if ref_unit:
                    c["unit"] = ref_unit
                if ref_range:
                    c["reference_range"] = ref_range
                if flag:
                    c["flag"] = flag
                if loinc:
                    c["loinc"] = loinc
                comp_list.append(c)

                if primary_value is None:
                    primary_value = ord_value
                    primary_unit = ref_unit or None
                    primary_ref = ref_range
                    primary_flag = flag or None

        if not comp_list:
            continue

        status_raw = components[0].get("RESULT_STATUS_C_NAME", "Final").strip() if components else "Final"
        status = "final" if "final" in status_raw.lower() else status_raw.lower() or "final"

        overall_flag = "Abnormal" if has_abnormal else None

        if len(comp_list) == 1:
            # Single-component panel: store value at panel level
            results.append({
                "test_name": panel_name,
                "result_date": result_date,
                "status": status,
                "provider": provider or None,
                "facility": "Epic EHI",
                "value": comp_list[0]["value"],
                "unit": comp_list[0].get("unit"),
                "reference_range": comp_list[0].get("reference_range"),
                "flag": comp_list[0].get("flag") or overall_flag,
                "components": None,
                "order_id": proc_id,
            })
        else:
            # Multi-component panel: store all components as JSON
            results.append({
                "test_name": panel_name,
                "result_date": result_date,
                "status": status,
                "provider": provider or None,
                "facility": "Epic EHI",
                "value": primary_value,
                "unit": primary_unit,
                "reference_range": primary_ref,
                "flag": overall_flag,
                "components": json.dumps(comp_list),
                "order_id": proc_id,
            })

            # Also insert each component as an individual row for searchability
            for c in comp_list:
                results.append({
                    "test_name": c["name"],
                    "result_date": result_date,
                    "status": status,
                    "provider": provider or None,
                    "facility": "Epic EHI",
                    "value": c["value"],
                    "unit": c.get("unit"),
                    "reference_range": c.get("reference_range"),
                    "flag": c.get("flag"),
                    "components": None,
                    "order_id": proc_id,
                    "raw_text": panel_name,  # store parent panel name as raw_text
                })

    return results


# ---------------------------------------------------------------------------
# Build visits list
# ---------------------------------------------------------------------------

def build_visits(record_dir: Path) -> list[dict]:
    rows = _load_tsv(record_dir / "EHITables" / "PAT_ENC.tsv")
    today = datetime.now().strftime("%Y-%m-%d")
    results = []

    for row in rows:
        visit_date = _parse_date(row.get("CONTACT_DATE", ""))
        if not visit_date:
            continue

        appt_status = row.get("APPT_STATUS_C_NAME", "").strip().lower()
        if appt_status in ("canceled", "no show", "cancelled"):
            continue

        provider = (
            row.get("VISIT_PROV_ID_PROV_NAME", "").strip() or
            row.get("PCP_PROV_ID_PROV_NAME", "").strip()
        )

        results.append({
            "visit_date": visit_date,
            "visit_type": "Office Visit",
            "provider": provider or None,
            "facility": None,
            "is_upcoming": visit_date >= today,
        })

    return results


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------

async def ingest_all(record_dir: str | Path) -> dict:
    """Run the full EHI ingestion pipeline."""
    try:
        from .health_db import replace_conditions, replace_medications, replace_test_results, replace_visits
    except ImportError:
        from health_db import replace_conditions, replace_medications, replace_test_results, replace_visits

    record_dir = Path(record_dir)
    if not record_dir.exists():
        raise FileNotFoundError(f"Record directory not found: {record_dir}")

    log.info("Building data from %s", record_dir)
    summary = {}

    # Conditions
    conditions = build_conditions(record_dir)
    await replace_conditions(conditions)
    summary["conditions"] = len(conditions)
    log.info("Ingested %d conditions", len(conditions))

    # Medications
    meds = build_medications(record_dir)
    await replace_medications(meds)
    summary["medications"] = len(meds)
    log.info("Ingested %d medications", len(meds))

    # Lab results (largest dataset)
    lab_results = build_lab_results(record_dir)
    await replace_test_results(lab_results)
    summary["lab_results"] = len(lab_results)
    log.info("Ingested %d lab result rows", len(lab_results))

    # Visits
    visits = build_visits(record_dir)
    await replace_visits(visits)
    summary["visits"] = len(visits)
    log.info("Ingested %d visits", len(visits))

    log.info("EHI ingestion complete: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/health_record"
    result = asyncio.run(ingest_all(path))
    print("\n=== EHI Ingestion Summary ===")
    for k, v in result.items():
        print(f"  {k}: {v}")

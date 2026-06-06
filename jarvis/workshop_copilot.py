"""
workshop_copilot.py — Epic 12: Workshop Copilot
================================================
Maker operations intelligence layer for Chris's workshop.

Machines covered:
  - Creality K2 Pro Combo (FDM)
  - Creality HALOT-ONE (Resin MSLA)
  - Creality Falcon 5W (Laser)
  - Titoe 4540 CNC (Router)
  - Cricut Joy Xtra (Vinyl/Paper)

Agents:
  - TonyAgent        (workshop-foreman) — Maker Operations Lead
  - HankAgent        (workshop-watch)   — Workshop Monitor
  - RocketAgent      (rocket)           — Vendor Scout
  - ForgeAgent       (forge)            — Geometry Builder
  - AntManAgent      (ant-man)          — Scale & Measurement

SAFETY NOTE: Workshop automation (laser, CNC) can be prepared and advised
but never autonomously executed — all execution requires explicit approval.
Resin handling reminders are important safety items and are always included.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json, atomic_write_jsonl


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class WorkshopProject:
    project_id: str
    title: str
    description: str
    machine: str          # "k2_pro" | "halot_one" | "falcon_5w" | "titoe_4540" | "cricut_joy" | "multi"
    status: str           # "idea" | "designing" | "printing" | "post_process" | "complete" | "failed"
    material: str         # "pla" | "abs" | "resin" | "wood" | "acrylic" | "vinyl" | etc.
    files: list[str] = field(default_factory=list)   # STL, DXF, SVG, GCODE refs
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    scout_vendor: str = ""           # where material/supplies came from
    print_time_hours: float = 0.0
    material_cost: float = 0.0


@dataclass
class PrintJob:
    job_id: str
    project_id: str
    machine: str
    file: str
    status: str           # "queued" | "running" | "paused" | "complete" | "failed" | "cancelled"
    started_at: str = ""
    estimated_end: str = ""
    completed_at: str = ""
    material: str = ""
    layer_height_mm: float = 0.0
    infill_percent: int = 0
    print_time_minutes: int = 0
    notes: str = ""
    failure_reason: str = ""


@dataclass
class MaterialStock:
    material_id: str
    name: str             # "PLA Black 1kg", "Resin Clear 500ml"
    material_type: str    # "pla" | "abs" | "resin" | "filament" | "laser_material" | "cnc_stock"
    brand: str = ""
    quantity_g: float = 0.0      # in grams (or ml for resin)
    quantity_units: str = "g"    # "g" | "ml" | "sheets" | "rolls"
    quantity_value: float = 0.0
    low_stock_threshold: float = 200.0   # warn when below this
    reorder_url: str = ""
    notes: str = ""
    last_updated: str = ""


@dataclass
class VendorSource:
    vendor_id: str
    name: str             # "Bambu Lab Store", "Amazon", etc.
    url: str
    specialty: list[str] = field(default_factory=list)  # ["pla", "abs", "resin"]
    notes: str = ""
    last_ordered: str = ""
    reliability: str = "medium"   # "high" | "medium" | "low"


# ---------------------------------------------------------------------------
# Workshop Store
# ---------------------------------------------------------------------------

class WorkshopCopilotStore:
    """
    Persistent store for workshop copilot data.

    ~/.jarvis/workshop/projects.json
    ~/.jarvis/workshop/print_jobs.jsonl
    ~/.jarvis/workshop/materials.json
    """

    ROOT = Path.home() / ".jarvis" / "workshop"

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or self.ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.projects_path = self.root / "projects.json"
        self.jobs_path = self.root / "print_jobs.jsonl"
        self.materials_path = self.root / "materials.json"
        self.projects_log_path = self.root / "projects_log.jsonl"
        self.jobs_state_log_path = self.root / "print_jobs_state_log.jsonl"
        self.materials_log_path = self.root / "materials_log.jsonl"

    def _load_json_snapshot(self, path: Path, log_path: Path) -> list[dict]:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except (json.JSONDecodeError, OSError):
                pass
        if not log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except (json.JSONDecodeError, OSError):
            return []
        return latest

    def _persist_json_snapshot(self, path: Path, log_path: Path, records: list[dict]) -> None:
        append_jsonl(
            log_path,
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "records": records,
            },
            ensure_ascii=False,
        )
        atomic_write_json(path, records, ensure_ascii=False)

    def _persist_jsonl_state(self, path: Path, log_path: Path, records: list[dict]) -> None:
        append_jsonl(
            log_path,
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "records": records,
            },
            ensure_ascii=False,
        )
        atomic_write_jsonl(path, records, ensure_ascii=False)

    # -- Projects ----------------------------------------------------------

    def save_project(self, project: WorkshopProject) -> None:
        projects = {p["project_id"]: p for p in self._load_projects()}
        projects[project.project_id] = asdict(project)
        self._persist_json_snapshot(self.projects_path, self.projects_log_path, list(projects.values()))

    def get_project(self, project_id: str) -> WorkshopProject | None:
        for record in self._load_projects():
            if record.get("project_id") == project_id:
                return WorkshopProject(**record)
        return None

    def list_projects(self, status: str | None = None) -> list[WorkshopProject]:
        records = self._load_projects()
        if status:
            records = [r for r in records if r.get("status") == status]
        return [WorkshopProject(**r) for r in records]

    def _load_projects(self) -> list[dict]:
        return self._load_json_snapshot(self.projects_path, self.projects_log_path)

    # -- Print Jobs --------------------------------------------------------

    def log_job(self, job: PrintJob) -> None:
        records = [asdict(existing) for existing in self._load_all_jobs()]
        records.append(asdict(job))
        self._persist_jsonl_state(self.jobs_path, self.jobs_state_log_path, records)

    def get_active_jobs(self) -> list[PrintJob]:
        active_statuses = {"queued", "running", "paused"}
        return [j for j in self._load_all_jobs() if j.status in active_statuses]

    def update_job(self, job_id: str, **kwargs: Any) -> bool:
        jobs = self._load_all_jobs()
        updated = False
        for job in jobs:
            if job.job_id == job_id:
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                updated = True
                break
        if updated:
            self._persist_jsonl_state(
                self.jobs_path,
                self.jobs_state_log_path,
                [asdict(job) for job in jobs],
            )
        return updated

    def get_jobs_by_status(self, status: str) -> list[PrintJob]:
        return [j for j in self._load_all_jobs() if j.status == status]

    def _load_all_jobs(self) -> list[PrintJob]:
        records: list[dict]
        if self.jobs_path.exists():
            records = []
            for line in self.jobs_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except (json.JSONDecodeError, TypeError):
                        pass
        else:
            records = []
        if not records and self.jobs_state_log_path.exists():
            try:
                for line in self.jobs_state_log_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    maybe_records = payload.get("records")
                    if isinstance(maybe_records, list):
                        records = [dict(item) for item in maybe_records if isinstance(item, dict)]
            except (json.JSONDecodeError, OSError):
                records = []
        jobs = []
        for record in records:
            try:
                jobs.append(PrintJob(**record))
            except (json.JSONDecodeError, TypeError):
                pass
        return jobs

    # -- Materials ---------------------------------------------------------

    def get_materials(self) -> list[MaterialStock]:
        return [MaterialStock(**r) for r in self._load_materials()]

    def save_material(self, stock: MaterialStock) -> None:
        materials = {m["material_id"]: m for m in self._load_materials()}
        materials[stock.material_id] = asdict(stock)
        self._persist_json_snapshot(self.materials_path, self.materials_log_path, list(materials.values()))

    def _load_materials(self) -> list[dict]:
        return self._load_json_snapshot(self.materials_path, self.materials_log_path)


# ---------------------------------------------------------------------------
# TonyAgent — Maker Operations Lead
# ---------------------------------------------------------------------------

class TonyAgent:
    """
    Tony Stark energy: loves a build challenge, technically precise, never dry.
    "Let's build something."
    """

    MACHINE_CAPABILITIES: dict[str, dict] = {
        "k2_pro": {
            "type": "FDM 3D printer",
            "name": "Creality K2 Pro Combo",
            "build_volume_mm": "350x350x350",
            "materials": ["PLA", "PETG", "ABS", "ASA", "TPU", "Carbon Fiber PLA"],
            "best_for": ["functional parts", "large models", "multi-color prints"],
            "layer_height_mm": "0.05-0.35",
            "notes": "Multi-filament capable with AMS. Workhorse of the workshop.",
        },
        "halot_one": {
            "type": "MSLA resin printer",
            "name": "Creality HALOT-ONE",
            "build_volume_mm": "130x82x160",
            "materials": ["Standard Resin", "ABS-Like Resin", "Tough Resin"],
            "best_for": ["fine detail", "miniatures", "jewelry", "dental models"],
            "layer_height_mm": "0.01-0.05",
            "notes": (
                "Higher detail than FDM. Requires post-processing: IPA wash + UV cure. "
                "Always use nitrile gloves and ventilation when handling uncured resin."
            ),
        },
        "falcon_5w": {
            "type": "Diode laser engraver/cutter",
            "name": "Creality Falcon 5W",
            "work_area_mm": "400x415",
            "power_w": 5,
            "best_for": [
                "wood engraving", "acrylic cutting", "leather", "anodized aluminum",
                "cardboard", "templates",
            ],
            "notes": (
                "5W diode — excellent for engraving and light cutting. "
                "Not suitable for thick metal or reflective surfaces. "
                "ALWAYS use ventilation and laser safety goggles. "
                "Execution requires approval — never run autonomously."
            ),
        },
        "titoe_4540": {
            "type": "CNC router",
            "name": "Titoe 4540 CNC",
            "work_area_mm": "450x400x70",
            "best_for": ["wood routing", "aluminum milling", "PCB engraving", "sign making"],
            "notes": (
                "Requires Fusion 360 or similar CAM software for toolpaths. "
                "Wear eye protection and hearing protection. "
                "Execution requires approval — never run autonomously."
            ),
        },
        "cricut_joy": {
            "type": "Vinyl/paper cutting machine",
            "name": "Cricut Joy Xtra",
            "cut_width_mm": "137",
            "materials": ["vinyl", "cardstock", "iron-on", "labels", "foam sheets"],
            "best_for": ["labels", "masks", "stencils", "decals", "iron-on designs"],
            "notes": "Cricut Design Space required. No open file format natively.",
        },
    }

    def __init__(self, store: WorkshopCopilotStore) -> None:
        self.store = store

    def get_workshop_status(self) -> dict:
        """
        Quick workshop status snapshot.
        Returns active prints, queued projects, low stock alerts,
        completed today, and a motivational Tony Stark comment.
        """
        now = datetime.now(timezone.utc)
        today_str = now.date().isoformat()

        active_jobs = self.store.get_active_jobs()
        queued_projects = self.store.list_projects(status="printing") + self.store.list_projects(status="designing")

        all_materials = self.store.get_materials()
        low_stock = [m for m in all_materials if m.quantity_value < m.low_stock_threshold]

        all_projects = self.store.list_projects(status="complete")
        completed_today = [
            p for p in all_projects
            if p.completed_at and p.completed_at[:10] == today_str
        ]

        active_count = len(active_jobs)
        if active_count == 0:
            tony_says = "Workshop is idle. Time to load up the next build — let's not waste the machines."
        elif active_count == 1:
            tony_says = f"One job running. Don't hover — trust the machine and get the next file ready."
        else:
            tony_says = f"{active_count} jobs in flight simultaneously. This is how I like it."

        if low_stock:
            tony_says += f" Also, Rocket says you're running low on {len(low_stock)} material(s). Handle that."

        return {
            "active_prints": [asdict(j) for j in active_jobs],
            "queued_projects": [asdict(p) for p in queued_projects],
            "low_stock_alerts": [asdict(m) for m in low_stock],
            "completed_today": [asdict(p) for p in completed_today],
            "tony_says": tony_says,
        }

    def plan_project(self, description: str, constraints: dict | None = None) -> dict:
        """
        Given a project description, plan the build:
        - Which machine(s) to use
        - Material recommendations
        - Estimated build time
        - Key design considerations
        - Safety notes if applicable
        Returns a structured project plan.
        """
        constraints = constraints or {}
        description_lower = description.lower()

        # Infer machine from description
        machine_scores: dict[str, int] = {m: 0 for m in self.MACHINE_CAPABILITIES}

        # Keyword hints
        fdm_keywords = ["functional", "structural", "large", "multi-color", "prototype", "enclosure", "bracket", "mount", "pla", "petg", "abs"]
        resin_keywords = ["detail", "miniature", "fine", "jewelry", "small", "precise", "dental", "figurine", "resin"]
        laser_keywords = ["engrave", "laser", "wood sign", "acrylic", "leather", "anodize", "mark", "etch", "cut plywood"]
        cnc_keywords = ["cnc", "route", "mill", "wood panel", "aluminum", "pcb", "carve", "sign"]
        cricut_keywords = ["vinyl", "label", "sticker", "decal", "iron-on", "mask", "stencil", "cardstock"]

        for kw in fdm_keywords:
            if kw in description_lower:
                machine_scores["k2_pro"] += 1
        for kw in resin_keywords:
            if kw in description_lower:
                machine_scores["halot_one"] += 1
        for kw in laser_keywords:
            if kw in description_lower:
                machine_scores["falcon_5w"] += 1
        for kw in cnc_keywords:
            if kw in description_lower:
                machine_scores["titoe_4540"] += 1
        for kw in cricut_keywords:
            if kw in description_lower:
                machine_scores["cricut_joy"] += 1

        # Default to K2 Pro if nothing matches
        recommended_machine = max(machine_scores, key=lambda m: machine_scores[m])
        if machine_scores[recommended_machine] == 0:
            recommended_machine = "k2_pro"

        machine_info = self.MACHINE_CAPABILITIES[recommended_machine]

        # Material recommendation
        material_map = {
            "k2_pro": "PLA (prototype) or PETG (functional)",
            "halot_one": "Standard ABS-Like Resin",
            "falcon_5w": "Material to be supplied — wood, acrylic, or leather",
            "titoe_4540": "Material to be supplied — wood or aluminum stock",
            "cricut_joy": "Vinyl or iron-on transfer",
        }
        recommended_material = material_map.get(recommended_machine, "PLA")

        # Time estimates
        time_map = {
            "k2_pro": "2-12 hours depending on size and infill",
            "halot_one": "1-4 hours depending on layer count",
            "falcon_5w": "10-60 minutes depending on complexity and speed",
            "titoe_4540": "30 minutes to several hours — CAM toolpath dependent",
            "cricut_joy": "5-20 minutes",
        }
        estimated_time = time_map.get(recommended_machine, "Unknown")

        # Design considerations
        design_notes = ForgeAgent.DESIGN_GUIDELINES.get(recommended_machine, {})

        # Safety notes
        safety_notes = []
        if recommended_machine in ("falcon_5w", "titoe_4540"):
            safety_notes.append("APPROVAL REQUIRED before execution — never run laser or CNC autonomously.")
            safety_notes.append("Wear appropriate PPE: safety goggles and hearing protection.")
            safety_notes.append("Ensure ventilation is active before starting job.")
        if recommended_machine == "halot_one":
            safety_notes.append("Wear nitrile gloves when handling uncured resin.")
            safety_notes.append("Run resin wash + UV cure cycle after print completes.")
            safety_notes.append("Dispose of waste resin properly — do not pour down drain.")

        return {
            "description": description,
            "recommended_machine": recommended_machine,
            "machine_info": machine_info,
            "recommended_material": recommended_material,
            "estimated_time": estimated_time,
            "design_considerations": design_notes,
            "safety_notes": safety_notes,
            "constraints": constraints,
            "tony_says": f"This one's a {machine_info['type']} job. {machine_info.get('notes', '')}",
        }

    def get_machine_recommendations(self, project_type: str, material: str | None = None) -> dict:
        """Recommend best machine for the job with reasoning."""
        plan = self.plan_project(project_type, {"material": material} if material else None)
        machine = plan["recommended_machine"]
        return {
            "recommended_machine": machine,
            "machine_info": self.MACHINE_CAPABILITIES[machine],
            "reasoning": plan["tony_says"],
            "alternatives": [
                {"machine_id": k, "info": v}
                for k, v in self.MACHINE_CAPABILITIES.items()
                if k != machine
            ],
        }


# ---------------------------------------------------------------------------
# HankAgent — Workshop Monitor
# ---------------------------------------------------------------------------

class HankAgent:
    """
    Hank Pym: methodical, precise, obsessive about proper procedure.
    Monitors the workshop so Tony doesn't burn it down.
    """

    def __init__(self, store: WorkshopCopilotStore) -> None:
        self.store = store

    def check_print_status(self) -> list[dict]:
        """
        Check status of all active print jobs.
        Stub — will wire to OctoPrint/Bambu API later.
        """
        active = self.store.get_active_jobs()
        if not active:
            return [{"status": "idle", "message": "No active print jobs. Workshop is clear."}]
        return [asdict(j) for j in active]

    def log_print_job(self, job: PrintJob) -> None:
        """Log a new print job to the JSONL store."""
        self.store.log_job(job)

    def update_print_status(self, job_id: str, status: str, notes: str = "") -> bool:
        """Update status of an existing job."""
        now = datetime.now(timezone.utc).isoformat()
        kwargs: dict[str, Any] = {"status": status}
        if notes:
            kwargs["notes"] = notes
        if status == "complete":
            kwargs["completed_at"] = now
        if status == "running" and not notes:
            kwargs["started_at"] = now
        return self.store.update_job(job_id, **kwargs)

    def get_failure_log(self, limit: int = 10) -> list[dict]:
        """Recent print failures with reasons — for learning."""
        failed = self.store.get_jobs_by_status("failed")
        return [asdict(j) for j in failed[-limit:]]

    def safety_check(self) -> dict:
        """
        Workshop safety status:
        - Is there an active print job? (should someone be aware?)
        - Any overnight prints running?
        - Resin handling: has a cleanup reminder been issued?

        Returns: {"alerts": list, "reminders": list, "all_clear": bool}
        """
        now = datetime.now(timezone.utc)
        hour = now.hour

        alerts: list[str] = []
        reminders: list[str] = []

        active_jobs = self.store.get_active_jobs()
        resin_jobs = [j for j in active_jobs if j.machine == "halot_one"]
        running_jobs = [j for j in active_jobs if j.status == "running"]

        # Overnight check (between 22:00 and 06:00)
        if (hour >= 22 or hour < 6) and running_jobs:
            for job in running_jobs:
                alerts.append(
                    f"Overnight print running on {job.machine}: {job.file or 'unnamed job'}. "
                    "Ensure the machine is in a safe state before sleeping."
                )

        # Resin safety
        if resin_jobs:
            reminders.append(
                "Active resin job detected on HALOT-ONE. "
                "When complete: wash in IPA for 2-3 min, then UV cure for 5+ min. "
                "Wear gloves — uncured resin is a skin irritant."
            )

        # Laser/CNC reminders
        laser_jobs = [j for j in active_jobs if j.machine == "falcon_5w"]
        cnc_jobs = [j for j in active_jobs if j.machine == "titoe_4540"]
        if laser_jobs:
            alerts.append(
                "Laser job active on Falcon 5W. Confirm ventilation is running "
                "and laser safety goggles are on."
            )
        if cnc_jobs:
            alerts.append(
                "CNC job active on Titoe 4540. Confirm eye protection and hearing protection are in use."
            )

        # General good habits
        if not reminders and not alerts:
            reminders.append("Workshop is idle. Good time to check filament levels and inspect print beds.")

        all_clear = len(alerts) == 0

        return {
            "alerts": alerts,
            "reminders": reminders,
            "all_clear": all_clear,
            "active_job_count": len(active_jobs),
            "hank_says": (
                "All clear. Workshop is safe." if all_clear
                else f"{len(alerts)} safety item(s) need your attention."
            ),
        }


# ---------------------------------------------------------------------------
# RocketAgent — Vendor Scout
# ---------------------------------------------------------------------------

class RocketAgent:
    """
    Rocket Raccoon: scrappy, resourceful, always knows where to find the parts.
    "I can get that for you. Don't ask where."
    """

    KNOWN_VENDORS = [
        {
            "name": "Bambu Lab Store",
            "url": "https://store.bambulab.com",
            "specialty": ["filament", "accessories"],
        },
        {
            "name": "Printed Solid",
            "url": "https://www.printedsolid.com",
            "specialty": ["premium filament", "resin"],
        },
        {
            "name": "ELEGOO Store",
            "url": "https://www.elegoo.com",
            "specialty": ["resin", "FDM printers"],
        },
        {
            "name": "Amazon",
            "url": "https://www.amazon.com",
            "specialty": ["general supplies", "tools"],
        },
        {
            "name": "McMaster-Carr",
            "url": "https://www.mcmaster.com",
            "specialty": ["hardware", "raw materials"],
        },
        {
            "name": "Inventables",
            "url": "https://www.inventables.com",
            "specialty": ["CNC materials", "wood", "acrylic"],
        },
        {
            "name": "Cricut",
            "url": "https://cricut.com",
            "specialty": ["vinyl", "cardstock", "iron-on"],
        },
    ]

    def __init__(self, store: WorkshopCopilotStore) -> None:
        self.store = store

    def get_low_stock_alerts(self) -> list[MaterialStock]:
        """Materials below threshold that need reordering."""
        return [m for m in self.store.get_materials() if m.quantity_value < m.low_stock_threshold]

    def suggest_reorder(self, material: MaterialStock) -> dict:
        """
        Suggest where to reorder based on vendor history and material type.
        Returns: {"vendor": str, "url": str, "estimated_cost": str, "notes": str}
        """
        type_map: dict[str, str] = {
            "pla": "Bambu Lab Store",
            "abs": "Printed Solid",
            "petg": "Printed Solid",
            "resin": "ELEGOO Store",
            "filament": "Bambu Lab Store",
            "laser_material": "Inventables",
            "cnc_stock": "Inventables",
            "vinyl": "Cricut",
            "cardstock": "Cricut",
        }

        # Check if there's a saved reorder URL
        if material.reorder_url:
            return {
                "vendor": material.scout_vendor if hasattr(material, "scout_vendor") else "Saved source",
                "url": material.reorder_url,
                "estimated_cost": "See link",
                "notes": f"Using saved reorder URL for {material.name}.",
            }

        preferred_vendor_name = type_map.get(material.material_type.lower(), "Amazon")
        vendor = next(
            (v for v in self.KNOWN_VENDORS if v["name"] == preferred_vendor_name),
            self.KNOWN_VENDORS[3],  # Amazon fallback
        )

        return {
            "vendor": vendor["name"],
            "url": vendor["url"],
            "estimated_cost": "Check current pricing",
            "notes": (
                f"Rocket's recommendation for {material.material_type}: {vendor['name']}. "
                f"You're at {material.quantity_value:.0f} {material.quantity_units} — "
                f"below the {material.low_stock_threshold:.0f} {material.quantity_units} threshold."
            ),
        }

    def log_material_use(
        self, material_id: str, quantity_used: float, project_id: str = ""
    ) -> None:
        """Deduct used quantity from stock."""
        materials = self.store.get_materials()
        for mat in materials:
            if mat.material_id == material_id:
                mat.quantity_value = max(0.0, mat.quantity_value - quantity_used)
                mat.quantity_g = max(0.0, mat.quantity_g - quantity_used)
                mat.last_updated = datetime.now(timezone.utc).isoformat()
                if project_id:
                    mat.notes = f"Last used on project {project_id}. " + mat.notes
                self.store.save_material(mat)
                break

    def add_material(self, stock: MaterialStock) -> None:
        """Add or update a material in inventory."""
        stock.last_updated = datetime.now(timezone.utc).isoformat()
        self.store.save_material(stock)

    def get_inventory(self) -> list[MaterialStock]:
        """Full materials inventory."""
        return self.store.get_materials()


# ---------------------------------------------------------------------------
# ForgeAgent — Geometry Builder
# ---------------------------------------------------------------------------

class ForgeAgent:
    """
    Forge: master of shape, dimension, and manufacturing constraints.
    """

    DESIGN_GUIDELINES: dict[str, dict] = {
        "k2_pro": {
            "min_wall_mm": 1.2,
            "recommended_wall_mm": 2.0,
            "min_detail_mm": 0.4,
            "overhang_degrees": 45,
            "supports_needed": "overhangs > 45°",
            "tolerances_mm": 0.2,
            "tips": [
                "Orient parts to minimize supports",
                "Add 0.2mm clearance for press fits",
                "Elephant foot compensation for bottom layers",
                "Brim recommended for parts with small base footprint",
            ],
        },
        "halot_one": {
            "min_wall_mm": 0.3,
            "recommended_wall_mm": 1.0,
            "min_detail_mm": 0.05,
            "hollowing": "Hollow large parts > 10mm wall to save resin",
            "drain_holes": "2mm drain holes needed for hollow parts",
            "tips": [
                "Anti-aliasing on for smooth curves",
                "Tilt small parts 15-30° for better success rate",
                "Supports must be manually reviewed before printing",
                "Avoid fully flat bottom surfaces — add tilt for FEP release",
            ],
        },
        "falcon_5w": {
            "kerf_mm": 0.1,
            "min_feature_mm": 0.5,
            "tips": [
                "Add kerf offset for tight-fitting parts",
                "Test power/speed on scrap material first",
                "Clean lens before long jobs",
                "Use air assist for cleaner cuts",
                "Avoid PVC — toxic fumes when lasered",
            ],
        },
        "titoe_4540": {
            "min_feature_mm": 1.0,
            "tips": [
                "Set up CAM toolpaths in Fusion 360 or similar before cutting",
                "Use tabs to hold pieces in place during cutting",
                "Secure workpiece firmly — no movement allowed during operation",
                "Choose correct bit for material (spiral up-cut for wood, down-cut for laminates)",
            ],
        },
        "cricut_joy": {
            "min_feature_mm": 2.0,
            "tips": [
                "Mirror design before cutting iron-on material",
                "Use weeding tools for small negative space removal",
                "Calibrate blade for new material batches",
            ],
        },
    }

    def get_design_notes(self, machine: str, material: str | None = None) -> dict:
        """
        Design-for-manufacture notes for a given machine and material:
        - Minimum wall thickness
        - Support requirements
        - Tolerances
        - Common pitfalls
        """
        guidelines = self.DESIGN_GUIDELINES.get(machine, {})
        machine_info = TonyAgent.MACHINE_CAPABILITIES.get(machine, {})

        result: dict[str, Any] = {
            "machine": machine,
            "machine_name": machine_info.get("name", machine),
            "machine_type": machine_info.get("type", "Unknown"),
            "guidelines": guidelines,
            "safety_notes": [],
        }

        if machine in ("falcon_5w", "titoe_4540"):
            result["safety_notes"].append(
                "APPROVAL REQUIRED before execution — these machines can cause injury if run without supervision."
            )
        if machine == "halot_one":
            result["safety_notes"].append(
                "Resin handling: gloves required, ventilation required, wash + cure cycle mandatory."
            )

        if material:
            material_lower = material.lower()
            if material_lower == "pvc":
                result["safety_notes"].append(
                    "NEVER laser-cut PVC — produces toxic chlorine gas."
                )
            if material_lower in ("acrylic", "plywood") and machine == "falcon_5w":
                result["safety_notes"].append(
                    "Acrylic and plywood both cut well on Falcon 5W. "
                    "Run ventilation and check for flame-up with plywood."
                )

        return result


# ---------------------------------------------------------------------------
# AntManAgent — Scale & Measurement
# ---------------------------------------------------------------------------

class AntManAgent:
    """
    Ant-Man: scale is everything.
    """

    UNIT_FACTORS: dict[str, float] = {
        "mm_to_in": 0.03937,
        "in_to_mm": 25.4,
        "cm_to_mm": 10.0,
        "mm_to_cm": 0.1,
        "ft_to_mm": 304.8,
        "mm_to_ft": 0.003281,
    }

    # Build volumes (x, y, z) in mm for fit checking
    MACHINE_BUILD_VOLUMES: dict[str, tuple[float, float, float]] = {
        "k2_pro": (350.0, 350.0, 350.0),
        "halot_one": (130.0, 82.0, 160.0),
        "falcon_5w": (400.0, 415.0, 0.0),      # 2D bed
        "titoe_4540": (450.0, 400.0, 70.0),
        "cricut_joy": (137.0, 999.0, 0.0),     # width limited, length unbounded (roll)
    }

    def calculate_scale(self, original_mm: float, target_mm: float) -> dict:
        """Calculate scale factor and resulting dimensions."""
        if original_mm <= 0:
            return {"error": "Original dimension must be > 0", "scale_factor": None}
        scale_factor = target_mm / original_mm
        return {
            "original_mm": original_mm,
            "target_mm": target_mm,
            "scale_factor": round(scale_factor, 6),
            "scale_percent": round(scale_factor * 100, 2),
            "ant_man_says": (
                f"Scale up {scale_factor:.2f}x — going big." if scale_factor > 1
                else f"Scale down {scale_factor:.2f}x — going small."
            ),
        }

    def unit_convert(self, value: float, from_unit: str, to_unit: str) -> float:
        """mm <-> inches <-> cm <-> feet conversions."""
        # Normalize
        from_u = from_unit.lower().strip()
        to_u = to_unit.lower().strip()

        if from_u == to_u:
            return value

        # Convert to mm first
        to_mm: dict[str, float] = {
            "mm": 1.0,
            "millimeter": 1.0,
            "millimeters": 1.0,
            "cm": self.UNIT_FACTORS["cm_to_mm"],
            "centimeter": self.UNIT_FACTORS["cm_to_mm"],
            "centimeters": self.UNIT_FACTORS["cm_to_mm"],
            "in": self.UNIT_FACTORS["in_to_mm"],
            "inch": self.UNIT_FACTORS["in_to_mm"],
            "inches": self.UNIT_FACTORS["in_to_mm"],
            "ft": self.UNIT_FACTORS["ft_to_mm"],
            "foot": self.UNIT_FACTORS["ft_to_mm"],
            "feet": self.UNIT_FACTORS["ft_to_mm"],
        }
        from_mm: dict[str, float] = {
            "mm": 1.0,
            "millimeter": 1.0,
            "millimeters": 1.0,
            "cm": self.UNIT_FACTORS["mm_to_cm"],
            "centimeter": self.UNIT_FACTORS["mm_to_cm"],
            "centimeters": self.UNIT_FACTORS["mm_to_cm"],
            "in": self.UNIT_FACTORS["mm_to_in"],
            "inch": self.UNIT_FACTORS["mm_to_in"],
            "inches": self.UNIT_FACTORS["mm_to_in"],
            "ft": self.UNIT_FACTORS["mm_to_ft"],
            "foot": self.UNIT_FACTORS["mm_to_ft"],
            "feet": self.UNIT_FACTORS["mm_to_ft"],
        }

        in_mm = value * to_mm.get(from_u, 1.0)
        result = in_mm * from_mm.get(to_u, 1.0)
        return round(result, 6)

    def check_fits_in_machine(
        self, dimensions_mm: tuple[float, float, float], machine: str
    ) -> dict:
        """
        Check if dimensions fit the build volume, with clearance.
        Returns fit status and any axis violations.
        """
        build = self.MACHINE_BUILD_VOLUMES.get(machine)
        if not build:
            return {
                "fits": False,
                "error": f"Unknown machine: {machine}",
            }

        dx, dy, dz = dimensions_mm
        bx, by, bz = build

        clearance_mm = 5.0  # 5mm safety margin
        violations: list[str] = []

        if bx > 0 and dx > bx - clearance_mm:
            violations.append(
                f"X axis: part {dx:.1f}mm > machine {bx:.1f}mm (with {clearance_mm}mm clearance)"
            )
        if by > 0 and dy > by - clearance_mm:
            violations.append(
                f"Y axis: part {dy:.1f}mm > machine {by:.1f}mm (with {clearance_mm}mm clearance)"
            )
        if bz > 0 and dz > bz - clearance_mm:
            violations.append(
                f"Z axis: part {dz:.1f}mm > machine {bz:.1f}mm (with {clearance_mm}mm clearance)"
            )

        fits = len(violations) == 0

        return {
            "fits": fits,
            "machine": machine,
            "part_dimensions_mm": {"x": dx, "y": dy, "z": dz},
            "build_volume_mm": {"x": bx, "y": by, "z": bz},
            "violations": violations,
            "ant_man_says": (
                "Fits cleanly within build volume." if fits
                else f"Does not fit — {len(violations)} axis violation(s)."
            ),
        }


# ---------------------------------------------------------------------------
# WorkshopCopilot — Main Orchestrator
# ---------------------------------------------------------------------------

class WorkshopCopilot:
    """
    Main workshop copilot orchestrator.
    Called by scheduler agents workshop-foreman and workshop-watch.
    """

    def __init__(self, store: WorkshopCopilotStore) -> None:
        self.store = store
        self.tony = TonyAgent(store)
        self.hank = HankAgent(store)
        self.rocket = RocketAgent(store)
        self.forge = ForgeAgent()
        self.ant_man = AntManAgent()

    def daily_workshop_check(self) -> dict:
        """
        Daily workshop check:
        - Active prints (Hank)
        - Low stock alerts (Rocket)
        - Safety status (Hank)
        - Projects in progress (Tony)
        Returns structured report for morning briefing.
        """
        safety = self.hank.safety_check()
        low_stock = self.rocket.get_low_stock_alerts()
        status = self.tony.get_workshop_status()
        active_jobs = self.hank.check_print_status()

        has_safety_alerts = not safety["all_clear"]
        has_low_stock = len(low_stock) > 0

        items: list[str] = []

        if has_safety_alerts:
            for alert in safety["alerts"]:
                items.append(f"SAFETY: {alert}")
        for reminder in safety["reminders"]:
            items.append(f"Reminder: {reminder}")
        if has_low_stock:
            for mat in low_stock[:3]:
                items.append(
                    f"Low stock: {mat.name} — {mat.quantity_value:.0f} {mat.quantity_units} remaining"
                )
        for job in status["active_prints"][:3]:
            items.append(f"Active print: {job.get('file', 'unnamed')} on {job.get('machine', '?')}")
        if status["completed_today"]:
            items.append(f"{len(status['completed_today'])} project(s) completed today.")

        action_required = has_safety_alerts or has_low_stock

        summary_parts = []
        active_count = len(status["active_prints"])
        if active_count:
            summary_parts.append(f"{active_count} active print job(s)")
        if has_low_stock:
            summary_parts.append(f"{len(low_stock)} material(s) low")
        if has_safety_alerts:
            summary_parts.append(f"{len(safety['alerts'])} safety alert(s)")
        if not summary_parts:
            summary_parts.append("Workshop idle, all clear")

        summary = "Workshop status: " + ", ".join(summary_parts) + "."

        return {
            "summary": summary,
            "items": items,
            "action_required": action_required,
            "priority": "high" if has_safety_alerts else ("normal" if has_low_stock else "low"),
            "safety": safety,
            "low_stock": [asdict(m) for m in low_stock],
            "active_jobs": active_jobs,
            "tony_says": status["tony_says"],
        }

    def get_dashboard_status(self) -> dict:
        """For the Already Working zone dashboard widget."""
        status = self.tony.get_workshop_status()
        safety = self.hank.safety_check()
        return {
            "active_prints": status["active_prints"],
            "queued_projects": status["queued_projects"][:5],
            "low_stock_count": len(status["low_stock_alerts"]),
            "all_clear": safety["all_clear"],
            "safety_alerts": safety["alerts"],
            "tony_says": status["tony_says"],
        }

    def start_project(
        self, description: str, constraints: dict | None = None
    ) -> WorkshopProject:
        """
        Tony + Forge plan the project, create it in the store.
        Returns the created WorkshopProject.
        """
        plan = self.tony.plan_project(description, constraints)
        machine = plan["recommended_machine"]
        material_str = plan["recommended_material"].split()[0].lower()

        now = datetime.now(timezone.utc).isoformat()
        project = WorkshopProject(
            project_id=str(uuid.uuid4()),
            title=description[:80],
            description=description,
            machine=machine,
            status="idea",
            material=material_str,
            created_at=now,
            updated_at=now,
            notes=plan.get("tony_says", ""),
            tags=[machine, material_str],
        )
        self.store.save_project(project)
        return project


# ---------------------------------------------------------------------------
# Seed data helper
# ---------------------------------------------------------------------------

def _seed_sample_data(store: WorkshopCopilotStore) -> None:
    """Seed a sample K2 Pro project and some material stock if the store is empty."""
    if store.list_projects():
        return  # Already seeded

    now = datetime.now(timezone.utc).isoformat()

    # Sample project
    sample_project = WorkshopProject(
        project_id=str(uuid.uuid4()),
        title="K2 Pro calibration cube",
        description=(
            "Print a 20mm calibration cube on the K2 Pro to verify first-layer "
            "adhesion and dimensional accuracy after bed leveling."
        ),
        machine="k2_pro",
        status="complete",
        material="pla",
        created_at=now,
        updated_at=now,
        completed_at=now,
        notes="Standard onboarding calibration print.",
        tags=["calibration", "k2_pro", "pla"],
        scout_vendor="Bambu Lab Store",
        print_time_hours=0.5,
        material_cost=0.05,
    )
    store.save_project(sample_project)

    # Sample materials
    if not store.get_materials():
        materials = [
            MaterialStock(
                material_id=str(uuid.uuid4()),
                name="Bambu PLA Basic — White 1kg",
                material_type="pla",
                brand="Bambu Lab",
                quantity_g=850.0,
                quantity_units="g",
                quantity_value=850.0,
                low_stock_threshold=200.0,
                reorder_url="https://store.bambulab.com/products/pla-basic-filament",
                notes="K2 Pro primary filament",
                last_updated=now,
            ),
            MaterialStock(
                material_id=str(uuid.uuid4()),
                name="ELEGOO ABS-Like Resin — Clear 500ml",
                material_type="resin",
                brand="ELEGOO",
                quantity_g=380.0,
                quantity_units="ml",
                quantity_value=380.0,
                low_stock_threshold=100.0,
                reorder_url="https://www.elegoo.com/products/elegoo-rapid-resin",
                notes="HALOT-ONE primary resin",
                last_updated=now,
            ),
            MaterialStock(
                material_id=str(uuid.uuid4()),
                name="3mm Basswood Sheets",
                material_type="laser_material",
                brand="Generic",
                quantity_g=0.0,
                quantity_units="sheets",
                quantity_value=8.0,
                low_stock_threshold=3.0,
                reorder_url="https://www.inventables.com",
                notes="Falcon 5W laser engraving/cutting",
                last_updated=now,
            ),
            MaterialStock(
                material_id=str(uuid.uuid4()),
                name="Oracal 651 Vinyl — Black 12in Roll",
                material_type="vinyl",
                brand="Oracal",
                quantity_g=0.0,
                quantity_units="rolls",
                quantity_value=2.0,
                low_stock_threshold=1.0,
                reorder_url="https://cricut.com",
                notes="Cricut Joy Xtra labels and decals",
                last_updated=now,
            ),
        ]
        for mat in materials:
            store.save_material(mat)


# ---------------------------------------------------------------------------
# Module-level init and accessor
# ---------------------------------------------------------------------------

_workshop_copilot_instance: WorkshopCopilot | None = None


def init_workshop(runtime: Any = None) -> WorkshopCopilot:
    """
    Initialise the WorkshopCopilot singleton.
    Call once at startup (in main.py command_serve).
    """
    global _workshop_copilot_instance
    store = WorkshopCopilotStore()
    _seed_sample_data(store)
    _workshop_copilot_instance = WorkshopCopilot(store)
    return _workshop_copilot_instance


def get_workshop() -> WorkshopCopilot | None:
    """Return the active WorkshopCopilot instance, or None if not initialised."""
    return _workshop_copilot_instance

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig
from .models import (
    CadPackage,
    InventoryItem,
    MaterialRecommendation,
    PrinterStatus,
    PrintPrep,
    SafetyCheck,
    VendorPrep,
    WorkshopInspection,
)
from .openai_tasks import JarvisOpenAIClient
from .persona import build_specialist_prompt


class WorkshopStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.inspections_path = self.root / "inspections.jsonl"
        self.vendor_preps_path = self.root / "vendor_preps.json"
        self.cad_packages_path = self.root / "cad_packages.json"
        self.print_preps_path = self.root / "print_preps.json"
        self.material_recommendations_path = self.root / "material_recommendations.json"
        self.safety_checks_path = self.root / "safety_checks.json"

    def add_inspection(self, inspection: WorkshopInspection) -> None:
        with self.inspections_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(inspection)) + "\n")

    def list_inspections(self, limit: int = 10) -> list[dict]:
        if not self.inspections_path.exists():
            return []
        lines = self.inspections_path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        return list(reversed(records[-limit:]))

    def latest_inspection_for_part(self, part_name: str) -> dict | None:
        lowered = part_name.strip().lower()
        for item in self.list_inspections(limit=50):
            if item["part_name"].strip().lower() == lowered:
                return item
        return None

    def _load_vendor_preps(self) -> list[dict]:
        if not self.vendor_preps_path.exists():
            return []
        return json.loads(self.vendor_preps_path.read_text(encoding="utf-8"))

    def _save_vendor_preps(self, records: list[dict]) -> None:
        self.vendor_preps_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    def add_vendor_prep(self, prep: VendorPrep) -> None:
        records = self._load_vendor_preps()
        records.append(asdict(prep))
        self._save_vendor_preps(records)

    def list_vendor_preps(self, limit: int = 10) -> list[dict]:
        records = self._load_vendor_preps()
        return list(reversed(records[-limit:]))

    def update_vendor_prep_status(self, prep_id: str, status: str) -> dict | None:
        records = self._load_vendor_preps()
        updated = None
        for item in records:
            if item["prep_id"] == prep_id:
                item["status"] = status
                updated = item
                break
        if updated is not None:
            self._save_vendor_preps(records)
        return updated

    def _load_json_records(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_json_records(self, path: Path, records: list[dict]) -> None:
        path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    def add_cad_package(self, package: CadPackage) -> None:
        records = self._load_json_records(self.cad_packages_path)
        records.append(asdict(package))
        self._save_json_records(self.cad_packages_path, records)

    def list_cad_packages(self, limit: int = 10) -> list[dict]:
        return list(reversed(self._load_json_records(self.cad_packages_path)[-limit:]))

    def add_print_prep(self, prep: PrintPrep) -> None:
        records = self._load_json_records(self.print_preps_path)
        records.append(asdict(prep))
        self._save_json_records(self.print_preps_path, records)

    def list_print_preps(self, limit: int = 10) -> list[dict]:
        return list(reversed(self._load_json_records(self.print_preps_path)[-limit:]))

    def add_material_recommendation(self, recommendation: MaterialRecommendation) -> None:
        records = self._load_json_records(self.material_recommendations_path)
        records.append(asdict(recommendation))
        self._save_json_records(self.material_recommendations_path, records)

    def list_material_recommendations(self, limit: int = 10) -> list[dict]:
        return list(reversed(self._load_json_records(self.material_recommendations_path)[-limit:]))

    def add_safety_check(self, check: SafetyCheck) -> None:
        records = self._load_json_records(self.safety_checks_path)
        records.append(asdict(check))
        self._save_json_records(self.safety_checks_path, records)

    def list_safety_checks(self, limit: int = 10) -> list[dict]:
        return list(reversed(self._load_json_records(self.safety_checks_path)[-limit:]))


class WorkshopSupport:
    def __init__(self, config: AppConfig, openai_client: JarvisOpenAIClient, store: WorkshopStore) -> None:
        self.config = config
        self.openai_client = openai_client
        self.store = store
        self.profile = config.load_json_profile(
            config.workshop_profile_path,
            {
                "printers": [],
                "materials": [],
                "safetyNotes": [],
                "vendorTargets": [],
                "designNotes": [],
                "cadNotes": [],
                "printPrepNotes": [],
                "safetyInterlocks": [],
                "inventory": [],
            },
        )

    def workshop_plan(self, actor: str, request: str) -> str:
        system = build_specialist_prompt(
            "workshop copilot",
            "Plan the next maker steps clearly and practically.",
            extra_guidance=(
                "Cover diagnosis, prototype path, material choice, safety, and vendor escalation when relevant. "
                f"Materials: {', '.join(self.profile.get('materials', []))}. "
                f"Safety notes: {' '.join(self.profile.get('safetyNotes', []))}. "
                f"Design notes: {' '.join(self.profile.get('designNotes', []))}."
            ),
        )
        user = f"Actor: {actor}\nRequest: {request}"
        return self.openai_client.prompt_text(system, user, max_output_tokens=500)

    def printer_status(self) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        results = []
        for item in self.profile.get("printers", []):
            status = PrinterStatus(
                printer_id=item["id"],
                name=item["name"],
                status=item.get("status", "simulated"),
                material=item.get("material", "unknown"),
                active_job=item.get("activeJob", "No active job"),
                progress_percent=int(item.get("progressPercent", 0)),
                note=item.get("note", "No live adapter connected yet."),
                timestamp=now,
            )
            results.append(asdict(status))
        return results

    def material_recommendation(self, actor: str, part_name: str, use_case: str, requirements: str) -> dict:
        system = build_specialist_prompt(
            "workshop material recommendation",
            "Recommend one primary material, give a tight rationale, and name backup options.",
            extra_guidance=(
                "Be practical about prototype versus final use. "
                f"Known materials: {', '.join(self.profile.get('materials', []))}."
            ),
        )
        user = (
            f"Actor: {actor}\nPart: {part_name}\nUse case: {use_case}\nRequirements:\n{requirements}\n"
            "Return labeled sections exactly as: Material:, Rationale:, Backup Materials:."
        )
        raw = self.openai_client.prompt_text(system, user, max_output_tokens=280)
        recommendation = MaterialRecommendation(
            recommendation_id=str(uuid.uuid4()),
            actor=actor,
            part_name=part_name,
            use_case=use_case,
            recommended_material=self._extract_section(raw, "Material") or "PETG-CF",
            rationale=self._extract_section(raw, "Rationale") or "Good balance of speed, stiffness, and prototype practicality.",
            backup_materials=self._split_lines(self._extract_section(raw, "Backup Materials")) or ["PLA", "carbon-fiber nylon"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.add_material_recommendation(recommendation)
        return asdict(recommendation)

    def cad_package(self, actor: str, part_name: str, dimensions: str, constraints: str) -> dict:
        system = build_specialist_prompt(
            "CAD generation",
            "Produce a rough parameter-driven CAD package for later hand refinement.",
            extra_guidance=(
                "Return labeled sections exactly as: Summary:, Parameters:, OpenSCAD Stub:, Fit Checks:. "
                f"CAD notes: {' '.join(self.profile.get('cadNotes', []))}."
            ),
        )
        user = (
            f"Actor: {actor}\nPart: {part_name}\nDimensions:\n{dimensions}\n\nConstraints:\n{constraints}"
        )
        raw = self.openai_client.prompt_text(system, user, max_output_tokens=650)
        package = CadPackage(
            package_id=str(uuid.uuid4()),
            actor=actor,
            part_name=part_name,
            summary=self._extract_section(raw, "Summary") or "Parameterized bracket concept for fit-check iteration.",
            parameters=self._split_lines(self._extract_section(raw, "Parameters")) or [
                "hole_spacing_mm = 0",
                "plate_thickness_mm = 0",
                "bend_radius_mm = 0",
            ],
            openscad_stub=self._extract_section(raw, "OpenSCAD Stub") or self._fallback_openscad_stub(part_name),
            fit_checks=self._split_lines(self._extract_section(raw, "Fit Checks")) or self._fallback_fit_checks(part_name),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.add_cad_package(package)
        return asdict(package)

    def print_prep(
        self,
        actor: str,
        part_name: str,
        printer_id: str,
        material: str,
        profile_name: str,
        notes: str,
    ) -> dict:
        chosen_profile = profile_name or "functional-prototype"
        system = build_specialist_prompt(
            "print-prep handoff",
            "Prepare a concise slicer and handoff plan.",
            extra_guidance=(
                "Return labeled sections exactly as: Layer Height:, Infill:, Supports:, Handoff Notes:. "
                f"Print prep notes: {' '.join(self.profile.get('printPrepNotes', []))}."
            ),
        )
        user = (
            f"Actor: {actor}\nPart: {part_name}\nPrinter: {printer_id}\nMaterial: {material}\n"
            f"Profile: {chosen_profile}\nNotes:\n{notes}"
        )
        raw = self.openai_client.prompt_text(system, user, max_output_tokens=260)
        prep = PrintPrep(
            prep_id=str(uuid.uuid4()),
            actor=actor,
            part_name=part_name,
            printer_id=printer_id,
            material=material,
            profile_name=chosen_profile,
            layer_height=self._extract_section(raw, "Layer Height") or "0.20 mm",
            infill=self._extract_section(raw, "Infill") or "35% gyroid",
            supports=self._extract_section(raw, "Supports") or "Minimal supports where overhangs require them",
            handoff_notes=self._extract_section(raw, "Handoff Notes") or "Stage as a manual handoff only; confirm orientation before printing.",
            status="staged",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.add_print_prep(prep)
        return asdict(prep)

    def safety_check(self, actor: str, operation: str, context: str) -> dict:
        lowered = f"{operation} {context}".lower()
        warnings = list(self._fallback_safety_notes())
        interlocks = list(self.profile.get("safetyInterlocks", []))
        allowed = True
        if any(token in lowered for token in ("cnc", "laser", "cut", "grind", "epoxy")):
            warnings.append("Review the operation before running anything that throws debris, dust, or fumes.")
        if "no eye protection" in lowered or "without goggles" in lowered:
            allowed = False
            warnings.append("Eye protection missing. Do not proceed.")
        recommendation = (
            "Proceed only after the listed interlocks are satisfied."
            if allowed
            else "Stop and satisfy the missing safety requirements before proceeding."
        )
        check = SafetyCheck(
            check_id=str(uuid.uuid4()),
            actor=actor,
            operation=operation,
            allowed=allowed,
            warnings=warnings,
            required_interlocks=interlocks,
            recommendation=recommendation,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.add_safety_check(check)
        return asdict(check)

    def inventory_summary(self) -> list[dict]:
        return [asdict(InventoryItem(
            item_id=item["id"],
            name=item["name"],
            category=item["category"],
            quantity=item["quantity"],
            status=item["status"],
            restock_note=item["restockNote"],
        )) for item in self.profile.get("inventory", [])]

    def inspect_part(
        self,
        actor: str,
        part_name: str,
        request: str,
        observations: str,
        goals: str,
        image_path: str = "",
    ) -> dict:
        system = build_specialist_prompt(
            "workshop inspection",
            "Review the part description, diagnose likely failure modes, recommend a prototype approach, and keep the advice practical.",
            extra_guidance=(
                "Return labeled sections exactly as: Diagnosis:, Material:, Process:, Safety:, Next Steps:. "
                f"Known materials: {', '.join(self.profile.get('materials', []))}. "
                f"Safety notes: {' '.join(self.profile.get('safetyNotes', []))}."
            ),
        )
        user = (
            f"Actor: {actor}\n"
            f"Part: {part_name}\n"
            f"Request: {request}\n"
            f"Observations:\n{observations}\n\n"
            f"Goals:\n{goals}\n\n"
            f"Image path: {image_path or 'none provided'}"
        )
        raw = self.openai_client.prompt_text(system, user, max_output_tokens=550)
        diagnosis = self._extract_section(raw, "Diagnosis") or raw.strip()
        material = self._extract_section(raw, "Material") or "PETG-CF prototype"
        process = self._extract_section(raw, "Process") or "Print a reinforced prototype and validate fit before external fabrication."
        safety_text = self._extract_section(raw, "Safety")
        next_text = self._extract_section(raw, "Next Steps")
        inspection = WorkshopInspection(
            inspection_id=str(uuid.uuid4()),
            actor=actor,
            part_name=part_name,
            request=request,
            observations=observations,
            goals=goals,
            diagnosis=diagnosis,
            recommended_material=material,
            recommended_process=process,
            safety_notes=self._split_lines(safety_text)
            or self._fallback_safety_notes(),
            next_steps=self._split_lines(next_text)
            or self._fallback_next_steps(part_name),
            image_path=image_path,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.store.add_inspection(inspection)
        return asdict(inspection)

    def prepare_vendor_prep(
        self,
        actor: str,
        part_name: str,
        vendor_target: str,
        process: str,
        material: str,
        notes: str,
    ) -> dict:
        inspection = self.store.latest_inspection_for_part(part_name)
        context = (
            f"Latest inspection diagnosis: {inspection['diagnosis']}\n"
            f"Latest recommended process: {inspection['recommended_process']}\n"
            if inspection
            else "Latest inspection diagnosis: none available.\n"
        )
        system = build_specialist_prompt(
            "vendor package preparation",
            "Prepare a concise package summary for an external fabrication or quote request.",
            extra_guidance=(
                "Do not imply the request was sent. "
                "Keep it specific enough to review, but clearly staged for approval."
            ),
        )
        user = (
            f"Actor: {actor}\n"
            f"Part: {part_name}\n"
            f"Vendor target: {vendor_target}\n"
            f"Requested process: {process}\n"
            f"Requested material: {material}\n"
            f"Project notes:\n{notes}\n\n"
            f"{context}"
        )
        package_summary = self.openai_client.prompt_text(system, user, max_output_tokens=320)
        prep = VendorPrep(
            prep_id=str(uuid.uuid4()),
            actor=actor,
            part_name=part_name,
            vendor_target=vendor_target,
            process=process,
            material=material,
            package_summary=package_summary,
            approval_request_id="",
            status="staged",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return asdict(prep)

    def save_vendor_prep(self, prep_payload: dict) -> dict:
        prep = VendorPrep(**prep_payload)
        self.store.add_vendor_prep(prep)
        return asdict(prep)

    def list_vendor_preps(self, limit: int = 10) -> list[dict]:
        return self.store.list_vendor_preps(limit=limit)

    def update_vendor_prep_status(self, prep_id: str, status: str) -> dict | None:
        return self.store.update_vendor_prep_status(prep_id, status)

    def list_cad_packages(self, limit: int = 10) -> list[dict]:
        return self.store.list_cad_packages(limit=limit)

    def list_print_preps(self, limit: int = 10) -> list[dict]:
        return self.store.list_print_preps(limit=limit)

    def list_material_recommendations(self, limit: int = 10) -> list[dict]:
        return self.store.list_material_recommendations(limit=limit)

    def list_safety_checks(self, limit: int = 10) -> list[dict]:
        return self.store.list_safety_checks(limit=limit)

    def _extract_section(self, text: str, heading: str) -> str:
        marker = f"{heading}:"
        if marker not in text:
            return ""
        fragment = text.split(marker, 1)[1]
        lines = []
        headings = ("Diagnosis:", "Material:", "Process:", "Safety:", "Next Steps:")
        for line in fragment.splitlines():
            stripped = line.strip()
            if stripped and any(stripped.startswith(item) for item in headings):
                if stripped.startswith(marker):
                    continue
                break
            lines.append(line)
        return "\n".join(line.strip() for line in lines).strip()

    def _split_lines(self, text: str) -> list[str]:
        if not text:
            return []
        items = []
        for line in text.splitlines():
            cleaned = line.strip().lstrip("-").strip()
            if cleaned:
                items.append(cleaned)
        return items

    def _fallback_safety_notes(self) -> list[str]:
        return [
            "Wear eye protection during cutting, drilling, and cleanup.",
            "Validate fit with a low-stakes prototype before structural testing.",
            "Treat any vendor handoff as staged until explicit approval is given.",
        ]

    def _fallback_next_steps(self, part_name: str) -> list[str]:
        return [
            f"Measure the current {part_name} and confirm hole spacing.",
            "Print a fit-check prototype first, then step up material strength.",
            "Review the result before any external fabrication or vendor submission.",
        ]

    def _fallback_openscad_stub(self, part_name: str) -> str:
        label = part_name.lower().replace(" ", "_").replace("-", "_")
        return (
            f"// Rough OpenSCAD stub for {part_name}\n"
            "hole_spacing_mm = 110;\n"
            "plate_width_mm = 30;\n"
            "plate_thickness_mm = 8;\n"
            "bend_radius_mm = 12;\n\n"
            f"module {label}() {{\n"
            "  // Replace with actual geometry after measurement pass\n"
            "  cube([plate_width_mm, hole_spacing_mm, plate_thickness_mm]);\n"
            "}\n\n"
            f"{label}();\n"
        )

    def _fallback_fit_checks(self, part_name: str) -> list[str]:
        return [
            f"Confirm hole spacing on the {part_name}.",
            "Check fastener clearance and wrench access.",
            "Verify drain path does not weaken the load path.",
        ]

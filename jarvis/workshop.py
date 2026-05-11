from __future__ import annotations

import json
import math
import re
import subprocess
import uuid
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

_CADQUERY_MODULE: Any | None = None
_CADQUERY_EXPORTERS: Any | None = None
_CADQUERY_IMPORT_ERROR: Exception | None = None


class WorkshopStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.model_forge_root = self.root / "model_forge"
        self.model_forge_root.mkdir(parents=True, exist_ok=True)
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

    def get_cad_package(self, package_id: str) -> dict | None:
        for item in self._load_json_records(self.cad_packages_path):
            if item.get("package_id") == package_id:
                return item
        return None

    def update_cad_package(self, package_id: str, patch: dict[str, Any]) -> dict | None:
        records = self._load_json_records(self.cad_packages_path)
        updated = None
        for item in records:
            if item.get("package_id") == package_id:
                item.update(patch)
                updated = item
                break
        if updated is not None:
            self._save_json_records(self.cad_packages_path, records)
        return updated

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
        return self.cad_package_advanced(actor, part_name, dimensions, constraints, "", "", "")

    def cad_package_advanced(
        self,
        actor: str,
        part_name: str,
        dimensions: str,
        constraints: str,
        family_hint: str,
        printer_hint: str,
        profile_hint: str,
    ) -> dict:
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
        package_id = str(uuid.uuid4())
        parameters = self._split_lines(self._extract_section(raw, "Parameters")) or [
            "hole_spacing_mm = 0",
            "plate_thickness_mm = 0",
            "bend_radius_mm = 0",
        ]
        openscad_stub = self._extract_section(raw, "OpenSCAD Stub") or self._fallback_openscad_stub(part_name)
        artifact_dir = self.store.model_forge_root / package_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        script_path = artifact_dir / "model.scad"
        script_path.write_text(openscad_stub.rstrip() + "\n", encoding="utf-8")
        export = self._build_model_forge_artifacts(
            package_id=package_id,
            part_name=part_name,
            dimensions=dimensions,
            constraints=constraints,
            parameters=parameters,
            artifact_dir=artifact_dir,
            family_hint=family_hint,
            printer_hint=printer_hint,
            profile_hint=profile_hint,
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata = {
            "package_id": package_id,
            "part_name": part_name,
            "actor": actor,
            "summary": self._extract_section(raw, "Summary") or "Parameterized bracket concept for fit-check iteration.",
            "parameters": parameters,
            "fit_checks": self._split_lines(self._extract_section(raw, "Fit Checks")) or self._fallback_fit_checks(part_name),
            "family": export["family"],
            "artifact_dir": str(artifact_dir),
            "script_path": str(script_path),
            "cadquery_script_path": export["cadquery_script_path"],
            "model_path": export["model_path"],
            "step_path": export["step_path"],
            "mesh_3mf_path": export["mesh_3mf_path"],
            "slicer_pack_dir": export["slicer_pack_dir"],
            "printer_id": export["printer_id"],
            "profile_name": export["profile_name"],
            "material": export["material"],
            "export_status": export["export_status"],
            "export_detail": export["export_detail"],
            "export_engine": export["export_engine"],
            "timestamp": timestamp,
        }
        (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        package = CadPackage(
            package_id=package_id,
            actor=actor,
            part_name=part_name,
            summary=metadata["summary"],
            parameters=parameters,
            openscad_stub=openscad_stub,
            fit_checks=metadata["fit_checks"],
            artifact_dir=str(artifact_dir),
            script_path=str(script_path),
            cadquery_script_path=export["cadquery_script_path"],
            model_path=export["model_path"],
            step_path=export["step_path"],
            mesh_3mf_path=export["mesh_3mf_path"],
            slicer_pack_dir=export["slicer_pack_dir"],
            export_status=export["export_status"],
            export_detail=export["export_detail"],
            export_engine=export["export_engine"],
            timestamp=timestamp,
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
        headings = (
            "Summary:",
            "Parameters:",
            "OpenSCAD Stub:",
            "Fit Checks:",
            "Diagnosis:",
            "Material:",
            "Process:",
            "Safety:",
            "Next Steps:",
            "Layer Height:",
            "Infill:",
            "Supports:",
            "Handoff Notes:",
            "Rationale:",
            "Backup Materials:",
        )
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

    def _build_model_forge_artifacts(
        self,
        package_id: str,
        part_name: str,
        dimensions: str,
        constraints: str,
        parameters: list[str],
        artifact_dir: Path,
        family_hint: str,
        printer_hint: str,
        profile_hint: str,
    ) -> dict[str, str]:
        dims = self._merge_measurements(dimensions, parameters)
        family = family_hint or self._infer_part_family(part_name, constraints, parameters)
        cadquery = self._cadquery_modules()
        if cadquery is None:
            fallback = self._build_fit_check_export(package_id, part_name, constraints, dims, artifact_dir, family)
            fallback["export_detail"] = f"{fallback['export_detail']} CadQuery is unavailable, so this package is staying on the fallback export path."
            return fallback

        cq, exporters = cadquery
        try:
            shape, script, profile = self._build_cadquery_shape(cq, family, part_name, dims, constraints)
            profile = self._apply_slicer_hints(profile, printer_hint, profile_hint)
            cadquery_script_path = artifact_dir / "model_cadquery.py"
            cadquery_script_path.write_text(script.rstrip() + "\n", encoding="utf-8")

            stem = self._slugify(part_name)
            stl_path = artifact_dir / f"{stem}.stl"
            step_path = artifact_dir / f"{stem}.step"
            three_mf_path = artifact_dir / f"{stem}.3mf"
            exporters.export(shape, str(stl_path), exportType=exporters.ExportTypes.STL)
            exporters.export(shape, str(step_path), exportType=exporters.ExportTypes.STEP)
            exporters.export(shape, str(three_mf_path), exportType=exporters.ExportTypes.THREEMF)

            slicer_pack_dir = artifact_dir / "slicer_pack"
            slicer_pack_dir.mkdir(parents=True, exist_ok=True)
            self._write_slicer_pack(
                slicer_pack_dir=slicer_pack_dir,
                part_name=part_name,
                family=family,
                profile=profile,
                dims=dims,
                source_model=three_mf_path,
                fallback_mesh=stl_path,
                constraints=constraints,
            )

            notes = [
                f"Package {package_id} exported a CadQuery-backed {family} model.",
                f"Primary mesh: {three_mf_path.name}",
                f"Fallback mesh: {stl_path.name}",
                f"Solid exchange: {step_path.name}",
                f"Recommended material: {profile['material']}",
                f"Suggested slicer profile: {profile['profile_name']}",
            ]
            (artifact_dir / "export_notes.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")
            return {
                "cadquery_script_path": str(cadquery_script_path),
                "model_path": str(stl_path),
                "step_path": str(step_path),
                "mesh_3mf_path": str(three_mf_path),
                "slicer_pack_dir": str(slicer_pack_dir),
                "family": family,
                "printer_id": profile["printer_id"],
                "profile_name": profile["profile_name"],
                "material": profile["material"],
                "export_status": f"cadquery-{family}",
                "export_detail": f"Exported CadQuery {family} assets as STL, STEP, and 3MF, then assembled a slicer pack for {profile['printer_id']} using the {profile['profile_name']} profile.",
                "export_engine": "cadquery",
            }
        except Exception as exc:
            fallback = self._build_fit_check_export(package_id, part_name, constraints, dims, artifact_dir, family)
            fallback["export_detail"] = f"{fallback['export_detail']} CadQuery export failed and fell back safely: {exc}"
            return fallback

    def _build_fit_check_export(
        self,
        package_id: str,
        part_name: str,
        constraints: str,
        dims: dict[str, float],
        artifact_dir: Path,
        family: str,
    ) -> dict[str, str]:
        extents = self._derive_extents_mm(dims)
        if extents is None:
            return {
                "cadquery_script_path": "",
                "model_path": "",
                "step_path": "",
                "mesh_3mf_path": "",
                "slicer_pack_dir": "",
                "family": family,
                "printer_id": "",
                "profile_name": "",
                "material": "",
                "export_status": "script-only",
                "export_detail": "Generated the OpenSCAD source, but could not derive enough measured extents for a truthful mesh export yet.",
                "export_engine": "openscad-script",
            }
        stl_path = artifact_dir / f"{self._slugify(part_name)}-fit-check.stl"
        self._write_box_stl(stl_path, *extents)
        notes = [
            f"Package {package_id} exported a simple fit-check STL.",
            "This mesh is a conservative rectangular prototype based on the strongest available measured extents.",
            f"Original constraints: {constraints or 'none provided'}",
        ]
        (artifact_dir / "export_notes.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")
        return {
            "cadquery_script_path": "",
            "model_path": str(stl_path),
            "step_path": "",
            "mesh_3mf_path": "",
            "slicer_pack_dir": "",
            "family": family,
            "printer_id": "",
            "profile_name": "",
            "material": "",
            "export_status": "fit-check-stl",
            "export_detail": f"Exported a simple fit-check STL using {extents[0]:.2f} x {extents[1]:.2f} x {extents[2]:.2f} mm derived from the supplied dimensions.",
            "export_engine": "jarvis-fit-check",
        }

    def _cadquery_modules(self) -> tuple[Any, Any] | None:
        global _CADQUERY_MODULE, _CADQUERY_EXPORTERS, _CADQUERY_IMPORT_ERROR
        if _CADQUERY_MODULE is not None and _CADQUERY_EXPORTERS is not None:
            return (_CADQUERY_MODULE, _CADQUERY_EXPORTERS)
        if _CADQUERY_IMPORT_ERROR is not None:
            return None
        try:
            import cadquery as cq
            from cadquery import exporters
        except Exception as exc:
            _CADQUERY_IMPORT_ERROR = exc
            return None
        _CADQUERY_MODULE = cq
        _CADQUERY_EXPORTERS = exporters
        return (cq, exporters)

    def _merge_measurements(self, dimensions: str, parameters: list[str]) -> dict[str, float]:
        dims = self._extract_measurements_mm(dimensions)
        parameter_dims = self._extract_measurements_mm("\n".join(parameters))
        return {**dims, **parameter_dims}

    def _infer_part_family(self, part_name: str, constraints: str, parameters: list[str]) -> str:
        text = f"{part_name} {constraints} {' '.join(parameters)}".lower()
        if any(token in text for token in ("enclosure", "case", "box", "housing")):
            return "enclosure"
        if any(token in text for token in ("spacer", "standoff", "bushing")):
            return "spacer"
        if "mount" in text:
            return "mount"
        if "bracket" in text:
            return "bracket"
        return "mount"

    def _build_cadquery_shape(
        self,
        cq: Any,
        family: str,
        part_name: str,
        dims: dict[str, float],
        constraints: str,
    ) -> tuple[Any, str, dict[str, str]]:
        if family == "bracket":
            return self._build_cadquery_bracket(cq, part_name, dims, constraints)
        if family == "enclosure":
            return self._build_cadquery_enclosure(cq, part_name, dims, constraints)
        if family == "spacer":
            return self._build_cadquery_spacer(cq, part_name, dims, constraints)
        return self._build_cadquery_mount(cq, part_name, dims, constraints)

    def _build_cadquery_bracket(self, cq: Any, part_name: str, dims: dict[str, float], constraints: str) -> tuple[Any, str, dict[str, str]]:
        width = self._dim_or_default(dims, 30.0, "plate width", "width")
        thickness = self._dim_or_default(dims, 8.0, "plate thickness", "thickness", "height")
        spacing = self._dim_or_default(dims, 110.0, "hole spacing", "spacing", "span", "length")
        leg_a = self._dim_or_default(dims, max(70.0, spacing * 0.55), "leg length a", "leg_length_a", "length a")
        leg_b = self._dim_or_default(dims, max(70.0, spacing * 0.45), "leg length b", "leg_length_b", "length b")
        hole_dia = self._dim_or_default(dims, 8.5, "hole dia", "hole diameter", "diameter")
        edge_margin = self._dim_or_default(dims, max(hole_dia, 12.0), "edge margin", "edge offset", "margin")

        leg1 = cq.Workplane("XY").box(leg_a, width, thickness, centered=(False, True, False))
        leg2 = cq.Workplane("YZ").box(width, leg_b, thickness, centered=(True, False, False)).translate((0, 0, 0))
        bracket = leg1.union(leg2.translate((0, 0, thickness)))
        try:
            bracket = bracket.edges("|Y").fillet(min(thickness * 0.45, 3.0))
        except Exception:
            pass
        hole_y = 0
        bracket = (
            bracket.faces(">Z")
            .workplane()
            .center(edge_margin, hole_y)
            .hole(hole_dia)
            .center(spacing, 0)
            .hole(hole_dia)
        )
        bracket = (
            bracket.faces(">X")
            .workplane()
            .center(0, edge_margin)
            .hole(hole_dia)
        )
        script = f"""import cadquery as cq

width = {width}
thickness = {thickness}
spacing = {spacing}
leg_a = {leg_a}
leg_b = {leg_b}
hole_dia = {hole_dia}
edge_margin = {edge_margin}

leg1 = cq.Workplane("XY").box(leg_a, width, thickness, centered=(False, True, False))
leg2 = cq.Workplane("YZ").box(width, leg_b, thickness, centered=(True, False, False))
result = leg1.union(leg2.translate((0, 0, thickness)))
result = result.faces(">Z").workplane().center(edge_margin, 0).hole(hole_dia).center(spacing, 0).hole(hole_dia)
result = result.faces(">X").workplane().center(0, edge_margin).hole(hole_dia)
show_object(result, name="{self._slugify(part_name)}")
"""
        profile = self._default_slicer_profile("bracket", thickness)
        return bracket, script, profile

    def _build_cadquery_enclosure(self, cq: Any, part_name: str, dims: dict[str, float], constraints: str) -> tuple[Any, str, dict[str, str]]:
        length = self._dim_or_default(dims, 120.0, "length", "span", "overall length")
        width = self._dim_or_default(dims, 80.0, "width", "overall width")
        height = self._dim_or_default(dims, 45.0, "height", "depth", "overall height")
        wall = self._dim_or_default(dims, 3.0, "wall", "wall thickness", "thickness")
        lip = self._dim_or_default(dims, 2.0, "lip", "lid lip")
        shell = cq.Workplane("XY").box(length, width, height)
        inner = cq.Workplane("XY").box(length - wall * 2, width - wall * 2, height - wall)
        enclosure = shell.cut(inner.translate((0, 0, wall * 0.5)))
        if lip > 0.5:
            rim = cq.Workplane("XY").box(length - wall * 2, width - wall * 2, lip)
            enclosure = enclosure.union(rim.translate((0, 0, height * 0.5 - lip * 0.5)))
        script = f"""import cadquery as cq

length = {length}
width = {width}
height = {height}
wall = {wall}
lip = {lip}

outer = cq.Workplane("XY").box(length, width, height)
inner = cq.Workplane("XY").box(length - wall * 2, width - wall * 2, height - wall)
result = outer.cut(inner.translate((0, 0, wall * 0.5)))
if lip > 0.5:
    result = result.union(cq.Workplane("XY").box(length - wall * 2, width - wall * 2, lip).translate((0, 0, height * 0.5 - lip * 0.5)))
show_object(result, name="{self._slugify(part_name)}")
"""
        profile = self._default_slicer_profile("enclosure", wall)
        return enclosure, script, profile

    def _build_cadquery_spacer(self, cq: Any, part_name: str, dims: dict[str, float], constraints: str) -> tuple[Any, str, dict[str, str]]:
        outer_dia = self._dim_or_default(dims, 18.0, "outer diameter", "od", "diameter")
        inner_dia = self._dim_or_default(dims, 8.0, "inner diameter", "id", "hole diameter")
        length = self._dim_or_default(dims, 12.0, "length", "height", "thickness")
        spacer = cq.Workplane("XY").circle(outer_dia / 2).extrude(length).faces(">Z").workplane().hole(inner_dia)
        script = f"""import cadquery as cq

outer_dia = {outer_dia}
inner_dia = {inner_dia}
length = {length}

result = cq.Workplane("XY").circle(outer_dia / 2).extrude(length).faces(">Z").workplane().hole(inner_dia)
show_object(result, name="{self._slugify(part_name)}")
"""
        profile = self._default_slicer_profile("spacer", length)
        return spacer, script, profile

    def _build_cadquery_mount(self, cq: Any, part_name: str, dims: dict[str, float], constraints: str) -> tuple[Any, str, dict[str, str]]:
        length = self._dim_or_default(dims, 90.0, "length", "overall length", "span")
        width = self._dim_or_default(dims, 45.0, "width", "plate width")
        thickness = self._dim_or_default(dims, 6.0, "thickness", "height")
        hole_spacing = self._dim_or_default(dims, min(length * 0.6, 60.0), "hole spacing", "spacing")
        hole_dia = self._dim_or_default(dims, 6.0, "hole diameter", "diameter")
        riser_height = self._dim_or_default(dims, 22.0, "riser height", "standoff height", "mount height")
        base = cq.Workplane("XY").box(length, width, thickness)
        riser = cq.Workplane("XY").box(width * 0.55, width * 0.45, riser_height).translate((0, 0, riser_height * 0.5 + thickness * 0.5))
        mount = base.union(riser)
        mount = (
            mount.faces(">Z[-2]")
            .workplane(centerOption="CenterOfMass")
            .pushPoints([(-hole_spacing / 2, 0), (hole_spacing / 2, 0)])
            .hole(hole_dia)
        )
        script = f"""import cadquery as cq

length = {length}
width = {width}
thickness = {thickness}
hole_spacing = {hole_spacing}
hole_dia = {hole_dia}
riser_height = {riser_height}

base = cq.Workplane("XY").box(length, width, thickness)
riser = cq.Workplane("XY").box(width * 0.55, width * 0.45, riser_height).translate((0, 0, riser_height * 0.5 + thickness * 0.5))
result = base.union(riser)
result = result.faces(">Z[-2]").workplane(centerOption="CenterOfMass").pushPoints([(-hole_spacing / 2, 0), (hole_spacing / 2, 0)]).hole(hole_dia)
show_object(result, name="{self._slugify(part_name)}")
"""
        profile = self._default_slicer_profile("mount", thickness)
        return mount, script, profile

    def _default_slicer_profile(self, family: str, reference: float) -> dict[str, str]:
        printer = next((item for item in self.profile.get("printers", []) if "fdm" in item.get("capabilities", [])), None)
        printer_id = printer["id"] if printer else "generic-fdm"
        if family in {"bracket", "mount"}:
            return {
                "printer_id": printer_id,
                "profile_name": "functional-prototype",
                "material": "PETG-CF",
                "layer_height": "0.20 mm",
                "infill": "35% gyroid",
                "supports": "Minimal supports only where required",
            }
        if family == "enclosure":
            return {
                "printer_id": printer_id,
                "profile_name": "enclosure-balanced",
                "material": "PLA",
                "layer_height": "0.20 mm",
                "infill": "20% gyroid",
                "supports": "Support top openings only if needed",
            }
        return {
            "printer_id": printer_id,
            "profile_name": "fit-check-fast",
            "material": "PLA",
            "layer_height": "0.16 mm" if reference <= 8 else "0.20 mm",
            "infill": "100% concentric" if family == "spacer" else "20% gyroid",
            "supports": "None",
        }

    def _apply_slicer_hints(self, profile: dict[str, str], printer_hint: str, profile_hint: str) -> dict[str, str]:
        result = dict(profile)
        printer_hint = printer_hint.strip()
        profile_hint = profile_hint.strip()
        if printer_hint:
            printer = next((item for item in self.profile.get("printers", []) if item.get("id") == printer_hint), None)
            if printer:
                result["printer_id"] = printer["id"]
        if profile_hint:
            result["profile_name"] = profile_hint
        return result

    def workshop_machine_options(self) -> dict[str, Any]:
        families = [
            {"id": "bracket", "label": "Bracket"},
            {"id": "enclosure", "label": "Enclosure"},
            {"id": "spacer", "label": "Spacer"},
            {"id": "mount", "label": "Mount"},
        ]
        printers = [
            {
                "id": item["id"],
                "name": item["name"],
                "profiles": item.get("profiles", []),
                "capabilities": item.get("capabilities", []),
                "material": item.get("material", ""),
            }
            for item in self.profile.get("printers", [])
        ]
        slicers = self.available_slicer_apps()
        return {
            "families": families,
            "printers": printers,
            "slicers": slicers,
            "default_printer_id": printers[0]["id"] if printers else "",
        }

    def available_slicer_apps(self) -> list[dict[str, str]]:
        candidates = [
            ("orcaslicer", "OrcaSlicer.app"),
            ("bambu-studio", "BambuStudio.app"),
            ("creality-print", "Creality Print.app"),
            ("prusaslicer", "PrusaSlicer.app"),
            ("cura", "UltiMaker Cura.app"),
        ]
        roots = [Path("/Applications"), Path.home() / "Applications"]
        found: list[dict[str, str]] = []
        for app_id, app_name in candidates:
            for root in roots:
                app_path = root / app_name
                if app_path.exists():
                    found.append({"id": app_id, "label": app_name.replace(".app", ""), "path": str(app_path)})
                    break
        return found

    def package_artifact_path(self, package_id: str, kind: str) -> tuple[Path, str]:
        package = self.store.get_cad_package(package_id)
        if not package:
            raise FileNotFoundError("Model forge package not found")
        mapping = {
            "stl": package.get("model_path", ""),
            "step": package.get("step_path", ""),
            "3mf": package.get("mesh_3mf_path", ""),
            "scad": package.get("script_path", ""),
            "cadquery": package.get("cadquery_script_path", ""),
        }
        rel = str(mapping.get(kind, "")).strip()
        if not rel:
            raise FileNotFoundError(f"No {kind} artifact is available for this package")
        path = (Path.cwd() / rel).resolve()
        try:
            path.relative_to(self.store.model_forge_root.resolve())
        except ValueError as exc:
            raise PermissionError("Artifact path is outside the model forge root") from exc
        return path, path.name

    def slicer_pack_archive(self, package_id: str) -> tuple[Path, str]:
        package = self.store.get_cad_package(package_id)
        if not package:
            raise FileNotFoundError("Model forge package not found")
        slicer_dir = str(package.get("slicer_pack_dir", "")).strip()
        if not slicer_dir:
            raise FileNotFoundError("This package does not have a slicer pack")
        root = (Path.cwd() / slicer_dir).resolve()
        try:
            root.relative_to(self.store.model_forge_root.resolve())
        except ValueError as exc:
            raise PermissionError("Slicer pack path is outside the model forge root") from exc
        zip_path = root.parent / "slicer_pack.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(root.rglob("*")):
                if file.is_file():
                    archive.write(file, arcname=file.relative_to(root))
        return zip_path, zip_path.name

    def open_package_in_slicer(self, package_id: str, slicer_app: str = "") -> dict[str, str]:
        package = self.store.get_cad_package(package_id)
        if not package:
            raise FileNotFoundError("Model forge package not found")
        model_rel = str(package.get("mesh_3mf_path") or package.get("model_path") or "").strip()
        if not model_rel:
            raise FileNotFoundError("This package does not have a printable model to open")
        model_path = (Path.cwd() / model_rel).resolve()
        try:
            model_path.relative_to(self.store.model_forge_root.resolve())
        except ValueError as exc:
            raise PermissionError("Model path is outside the model forge root") from exc

        app_path = ""
        if slicer_app:
            match = next((item for item in self.available_slicer_apps() if item["id"] == slicer_app), None)
            if not match:
                raise FileNotFoundError("Requested slicer app is not installed")
            app_path = match["path"]
            command = ["open", "-a", app_path, str(model_path)]
            target = match["label"]
        else:
            command = ["open", str(model_path)]
            target = "system default app"

        status = "opened"
        detail = ""
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            subprocess.run(["open", "-R", str(model_path)], check=True)
            status = "revealed"
            detail = "No slicer accepted the handoff, so the model was revealed in Finder instead."
        patch = {"last_opened_in_slicer_at": datetime.now(timezone.utc).isoformat(), "last_opened_model_path": str(model_path)}
        self.store.update_cad_package(package_id, patch)
        return {
            "status": status,
            "target": target,
            "path": str(model_path),
            "detail": detail,
        }

    def _write_slicer_pack(
        self,
        slicer_pack_dir: Path,
        part_name: str,
        family: str,
        profile: dict[str, str],
        dims: dict[str, float],
        source_model: Path,
        fallback_mesh: Path,
        constraints: str,
    ) -> None:
        manifest = {
            "part_name": part_name,
            "family": family,
            "primary_model": source_model.name,
            "fallback_mesh": fallback_mesh.name,
            "printer_id": profile["printer_id"],
            "profile_name": profile["profile_name"],
            "material": profile["material"],
            "layer_height": profile["layer_height"],
            "infill": profile["infill"],
            "supports": profile["supports"],
            "dimensions_mm": dims,
        }
        (slicer_pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (slicer_pack_dir / "print_profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        readme = [
            f"# {part_name} slicer pack",
            "",
            f"- Family: {family}",
            f"- Printer: {profile['printer_id']}",
            f"- Profile: {profile['profile_name']}",
            f"- Material: {profile['material']}",
            f"- Layer height: {profile['layer_height']}",
            f"- Infill: {profile['infill']}",
            f"- Supports: {profile['supports']}",
            "",
            "Use the 3MF file as the preferred import when your slicer accepts it.",
            "Fall back to the STL when you want to override slicer-side settings manually.",
            "",
            f"Constraints: {constraints or 'none provided'}",
        ]
        (slicer_pack_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    def _extract_measurements_mm(self, text: str) -> dict[str, float]:
        units = {
            "mm": 1.0,
            "millimeter": 1.0,
            "millimeters": 1.0,
            "cm": 10.0,
            "centimeter": 10.0,
            "centimeters": 10.0,
            "in": 25.4,
            "inch": 25.4,
            "inches": 25.4,
            "\"": 25.4,
        }
        results: dict[str, float] = {}
        pattern = re.compile(
            r"(?P<label>[A-Za-z][A-Za-z0-9 _/-]{1,40}?)\s*(?:=|:)?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mm|millimeters?|cm|centimeters?|in|inches?|\")",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            label = self._normalize_measurement_label(match.group("label"))
            value = float(match.group("value"))
            unit = match.group("unit").lower()
            mm = value * units[unit]
            results[label] = mm
        return results

    def _dim_or_default(self, dims: dict[str, float], default: float, *tokens: str) -> float:
        for key, value in dims.items():
            lowered = key.lower()
            if any(token in lowered for token in tokens):
                return value
        return default

    def _derive_extents_mm(self, dims: dict[str, float]) -> tuple[float, float, float] | None:
        def first_match(*tokens: str) -> float | None:
            for key, value in dims.items():
                lowered = key.lower()
                if any(token in lowered for token in tokens):
                    return value
            return None

        length = first_match("length", "depth", "hole spacing", "spacing", "span")
        width = first_match("width", "plate width")
        height = first_match("height", "thickness", "plate thickness")
        if length is None or width is None or height is None:
            return None
        if min(length, width, height) <= 0:
            return None
        return (length, width, height)

    def _normalize_measurement_label(self, label: str) -> str:
        cleaned = re.sub(r"\s+", " ", label.strip().lower())
        aliases = {
            "l": "length",
            "w": "width",
            "h": "height",
            "t": "thickness",
        }
        return aliases.get(cleaned, cleaned)

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "part"

    def _write_box_stl(self, path: Path, length_mm: float, width_mm: float, height_mm: float) -> None:
        vertices = [
            (0.0, 0.0, 0.0),
            (length_mm, 0.0, 0.0),
            (length_mm, width_mm, 0.0),
            (0.0, width_mm, 0.0),
            (0.0, 0.0, height_mm),
            (length_mm, 0.0, height_mm),
            (length_mm, width_mm, height_mm),
            (0.0, width_mm, height_mm),
        ]
        triangles = [
            (0, 2, 1), (0, 3, 2),
            (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4),
            (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6),
            (3, 0, 4), (3, 4, 7),
        ]

        def normal(a: tuple[float, float, float], b: tuple[float, float, float], c: tuple[float, float, float]) -> tuple[float, float, float]:
            ux, uy, uz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            vx, vy, vz = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            magnitude = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            return (nx / magnitude, ny / magnitude, nz / magnitude)

        lines = ["solid jarvis_fit_check"]
        for i0, i1, i2 in triangles:
            a, b, c = vertices[i0], vertices[i1], vertices[i2]
            nx, ny, nz = normal(a, b, c)
            lines.append(f"  facet normal {nx:.6f} {ny:.6f} {nz:.6f}")
            lines.append("    outer loop")
            for vertex in (a, b, c):
                lines.append(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}")
            lines.append("    endloop")
            lines.append("  endfacet")
        lines.append("endsolid jarvis_fit_check")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

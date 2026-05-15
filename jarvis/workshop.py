from __future__ import annotations

import base64
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
from .data_hygiene import filter_records
from .models import (
    CadPackage,
    ConceptStudioSession,
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
        self.concept_sessions_path = self.root / "concept_sessions.json"

    def add_inspection(self, inspection: WorkshopInspection) -> None:
        with self.inspections_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(inspection)) + "\n")

    def list_inspections(self, limit: int = 10) -> list[dict]:
        if not self.inspections_path.exists():
            return []
        lines = self.inspections_path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        cleaned = filter_records(records)
        return list(reversed(cleaned[-limit:]))

    def latest_inspection_for_part(self, part_name: str) -> dict | None:
        lowered = part_name.strip().lower()
        for item in self.list_inspections(limit=50):
            if item["part_name"].strip().lower() == lowered:
                return item
        return None

    def _load_vendor_preps(self) -> list[dict]:
        if not self.vendor_preps_path.exists():
            return []
        records = json.loads(self.vendor_preps_path.read_text(encoding="utf-8"))
        return filter_records(records if isinstance(records, list) else [])

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
        records = json.loads(path.read_text(encoding="utf-8"))
        return filter_records(records if isinstance(records, list) else [])

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

    def add_concept_session(self, session: ConceptStudioSession) -> None:
        records = self._load_json_records(self.concept_sessions_path)
        records.append(asdict(session))
        self._save_json_records(self.concept_sessions_path, records)

    def list_concept_sessions(self, limit: int = 10) -> list[dict]:
        return list(reversed(self._load_json_records(self.concept_sessions_path)[-limit:]))

    def get_concept_session(self, session_id: str) -> dict | None:
        for item in self._load_json_records(self.concept_sessions_path):
            if item.get("session_id") == session_id:
                return item
        return None

    def update_concept_session(self, session_id: str, patch: dict[str, Any]) -> dict | None:
        records = self._load_json_records(self.concept_sessions_path)
        updated = None
        for item in records:
            if item.get("session_id") == session_id:
                item.update(patch)
                updated = item
                break
        if updated is not None:
            self._save_json_records(self.concept_sessions_path, records)
        return updated


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

    def concept_studio_chat(
        self,
        actor: str,
        prompt: str,
        object_type: str,
        goals: str,
        constraints: str,
        *,
        session_id: str = "",
        image_path: str = "",
        capture_id: str = "",
        reference_note: str = "",
        silhouette_preference: str = "",
        vision_object_label: str = "",
        vision_contour_confidence: str = "",
        vision_asymmetry_hint: str = "",
        vision_dimension_seed: str = "",
    ) -> dict:
        existing_raw = self.store.get_concept_session(session_id.strip()) if session_id.strip() else None
        existing = dict(existing_raw) if isinstance(existing_raw, dict) else {}
        active_session_id = session_id.strip() or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        transcript_source = existing.get("transcript", [])
        transcript = [dict(item) for item in transcript_source if isinstance(item, dict)]
        user_turn = {
            "role": "user",
            "content": prompt.strip() or "Help me shape a unique printable design.",
        }
        transcript.append(user_turn)
        active_object_type = object_type.strip() or str(existing.get("object_type", "")).strip() or "custom object"
        active_goals = goals.strip() or str(existing.get("goals", "")).strip()
        active_constraints = constraints.strip() or str(existing.get("constraints", "")).strip()
        active_image_path = image_path.strip() or str(existing.get("image_path", "")).strip()
        active_capture_id = capture_id.strip() or str(existing.get("capture_id", "")).strip()
        active_reference_note = reference_note.strip()
        active_silhouette_preference = silhouette_preference.strip() or str(existing.get("silhouette_preference", "")).strip()
        active_vision_object_label = vision_object_label.strip() or str(existing.get("vision_object_label", "")).strip()
        active_vision_contour_confidence = vision_contour_confidence.strip() or str(existing.get("vision_contour_confidence", "")).strip()
        active_vision_asymmetry_hint = vision_asymmetry_hint.strip() or str(existing.get("vision_asymmetry_hint", "")).strip()
        active_vision_dimension_seed = vision_dimension_seed.strip() or str(existing.get("vision_dimension_seed", "")).strip()
        transcript_window = "\n".join(
            f"{item.get('role', 'user').upper()}: {str(item.get('content', '')).strip()}"
            for item in transcript[-8:]
        )
        system = build_specialist_prompt(
            "forge concept studio",
            "Collaborate on original printable object ideas before any CAD package is generated.",
            extra_guidance=(
                "Think like a creative fabrication partner. Explore concept, use case, geometry strategy, printability, and next design move. "
                "Do not jump straight into bracket-like assumptions unless the request points there. "
                "If the idea does not cleanly fit bracket, enclosure, spacer, or mount, leave Suggested Family blank instead of forcing it. "
                "Use the user's silhouette preference when one is supplied, or propose one when the object wants a stronger shape language. "
                "When a photo reference exists, use it as inspiration or evidence, not as permission to invent hidden details. "
                "Return labeled sections exactly as: Title:, Concept Summary:, Design Direction:, Suggested Silhouette:, Suggested Family:, Suggested Part Name:, Suggested Dimensions:, Suggested Constraints:, Print Strategy:, Questions:, Next Step:, Variant A:, Variant B:, Variant C:. "
                "Each Variant section must include labeled sub-lines exactly as: Name:, Silhouette:, Pitch:, Dimensions:, Constraints:, Print Posture:. "
                f"Known materials: {', '.join(self.profile.get('materials', []))}. "
                f"Design notes: {' '.join(self.profile.get('designNotes', []))}. "
                f"CAD notes: {' '.join(self.profile.get('cadNotes', []))}."
            ),
        )
        user = (
            f"Actor: {actor}\n"
            f"Object type: {active_object_type}\n"
            f"Goals:\n{active_goals or 'Not specified yet.'}\n\n"
            f"Constraints:\n{active_constraints or 'No hard constraints yet.'}\n\n"
            f"Silhouette preference: {active_silhouette_preference or 'No silhouette locked yet.'}\n"
            f"Reference note: {active_reference_note or 'None provided.'}\n"
            f"Vision object label: {active_vision_object_label or 'Unknown.'}\n"
            f"Vision contour confidence: {active_vision_contour_confidence or 'Unknown.'}\n"
            f"Vision asymmetry hint: {active_vision_asymmetry_hint or 'Unknown.'}\n"
            f"Vision dimension seed: {active_vision_dimension_seed or 'None.'}\n"
            f"Transcript so far:\n{transcript_window}\n"
        )
        response_text = ""
        if active_image_path:
            image_file = Path(active_image_path)
            if image_file.exists():
                suffix = image_file.suffix.lower().lstrip(".") or "jpeg"
                mime = "image/png" if suffix == "png" else "image/jpeg"
                image_data_url = f"data:{mime};base64," + base64.b64encode(image_file.read_bytes()).decode("ascii")
                response_text = self.openai_client.analyze_images(
                    (
                        f"{system}\n\n"
                        "A user-provided reference image is attached. Use it to ground the concept discussion while following the required labeled response format.\n\n"
                        f"{user}"
                    ),
                    [image_data_url],
                    max_output_tokens=700,
                )
        if not response_text:
            response_text = self.openai_client.prompt_text(system, user, max_output_tokens=700)

        title = self._extract_section(response_text, "Title") or str(existing.get("title", "")).strip() or f"{active_object_type.title()} concept"
        concept_summary = self._extract_section(response_text, "Concept Summary") or response_text.strip()
        design_direction = self._extract_section(response_text, "Design Direction") or "Explore one strong direction before locking geometry."
        suggested_silhouette = self._normalize_silhouette(
            self._extract_section(response_text, "Suggested Silhouette")
            or active_silhouette_preference
        )
        suggested_family = self._normalize_concept_family(self._extract_section(response_text, "Suggested Family"))
        suggested_part_name = self._extract_section(response_text, "Suggested Part Name") or title
        suggested_dimensions = self._extract_section(response_text, "Suggested Dimensions")
        suggested_constraints = self._extract_section(response_text, "Suggested Constraints") or active_constraints
        print_strategy = self._extract_section(response_text, "Print Strategy") or "Prototype the form in simple material before final tuning."
        questions = self._split_lines(self._extract_section(response_text, "Questions"))
        next_step = self._extract_section(response_text, "Next Step") or "Refine the concept, then send the chosen direction into package generation."
        variants = self._extract_concept_variants(
            response_text,
            active_object_type,
            active_silhouette_preference,
            suggested_part_name,
            suggested_dimensions,
            suggested_constraints,
        )
        if not suggested_silhouette and variants:
            suggested_silhouette = str(variants[0].get("silhouette", "")).strip()
        assistant_turn = {
            "role": "assistant",
            "content": concept_summary,
        }
        transcript.append(assistant_turn)
        session_payload = ConceptStudioSession(
            session_id=active_session_id,
            actor=actor,
            object_type=active_object_type,
            silhouette_preference=active_silhouette_preference,
            title=title,
            goals=active_goals,
            constraints=active_constraints,
            concept_summary=concept_summary,
            design_direction=design_direction,
            suggested_silhouette=suggested_silhouette,
            suggested_family=suggested_family,
            suggested_part_name=suggested_part_name,
            suggested_dimensions=suggested_dimensions,
            suggested_constraints=suggested_constraints,
            print_strategy=print_strategy,
            questions=questions,
            next_step=next_step,
            capture_id=active_capture_id,
            image_path=active_image_path,
            vision_object_label=active_vision_object_label,
            vision_contour_confidence=active_vision_contour_confidence,
            vision_asymmetry_hint=active_vision_asymmetry_hint,
            vision_dimension_seed=active_vision_dimension_seed,
            variants=variants,
            transcript=transcript,
            status="active",
            created_at=str(existing.get("created_at", now)),
            updated_at=now,
        )
        if self.store.get_concept_session(active_session_id):
            self.store.update_concept_session(active_session_id, asdict(session_payload))
        else:
            self.store.add_concept_session(session_payload)
        result = asdict(session_payload)
        result["apply_payload"] = {
            "family": suggested_family or ("custom-form" if suggested_silhouette else ""),
            "part": suggested_part_name,
            "dimensions": suggested_dimensions,
            "constraints": suggested_constraints,
            "creative_profile": suggested_silhouette,
        }
        result["response_text"] = response_text
        return result

    def cad_package(self, actor: str, part_name: str, dimensions: str, constraints: str) -> dict:
        return self.cad_package_advanced(actor, part_name, dimensions, constraints, "", "", "", "")

    def cad_package_advanced(
        self,
        actor: str,
        part_name: str,
        dimensions: str,
        constraints: str,
        family_hint: str,
        printer_hint: str,
        profile_hint: str,
        creative_profile: str,
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
            creative_profile=creative_profile,
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
            "creative_profile": creative_profile,
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
            family=export["family"],
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
            creative_profile=creative_profile,
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

    def list_concept_sessions(self, limit: int = 10) -> list[dict]:
        return self.store.list_concept_sessions(limit=limit)

    def get_concept_session(self, session_id: str) -> dict | None:
        return self.store.get_concept_session(session_id)

    def _extract_section(self, text: str, heading: str) -> str:
        marker = f"{heading}:"
        if marker not in text:
            return ""
        fragment = text.split(marker, 1)[1]
        lines = []
        headings = (
            "Title:",
            "Concept Summary:",
            "Design Direction:",
            "Suggested Silhouette:",
            "Suggested Family:",
            "Suggested Part Name:",
            "Suggested Dimensions:",
            "Suggested Constraints:",
            "Print Strategy:",
            "Questions:",
            "Next Step:",
            "Variant A:",
            "Variant B:",
            "Variant C:",
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

    def _normalize_concept_family(self, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"bracket", "enclosure", "spacer", "mount", "custom-form"}:
            return normalized
        mapping = {
            "functional mount": "mount",
            "camera mount": "mount",
            "display mount": "mount",
            "protective shell": "enclosure",
            "case": "enclosure",
            "housing": "enclosure",
            "fit spacer": "spacer",
            "brace": "bracket",
            "custom form": "custom-form",
            "sculpture": "custom-form",
            "organic form": "custom-form",
            "prop or decor": "custom-form",
            "sporting good": "custom-form",
            "organic reconstruction": "custom-form",
        }
        return mapping.get(normalized, "")

    def _extract_variant_block(self, text: str, heading: str) -> str:
        marker = f"{heading}:"
        if marker not in text:
            return ""
        fragment = text.split(marker, 1)[1]
        lines = []
        for line in fragment.splitlines():
            stripped = line.strip()
            if stripped.startswith(("Variant A:", "Variant B:", "Variant C:")) and not stripped.startswith(marker):
                break
            lines.append(line)
        return "\n".join(line.strip() for line in lines).strip()

    def _extract_variant_field(self, block: str, heading: str) -> str:
        marker = f"{heading}:"
        if marker not in block:
            return ""
        fragment = block.split(marker, 1)[1]
        lines = []
        headings = ("Name:", "Silhouette:", "Pitch:", "Dimensions:", "Constraints:", "Print Posture:")
        for line in fragment.splitlines():
            stripped = line.strip()
            if stripped and any(stripped.startswith(item) for item in headings):
                if stripped.startswith(marker):
                    continue
                break
            lines.append(line)
        return "\n".join(line.strip() for line in lines).strip()

    def _extract_concept_variants(
        self,
        text: str,
        object_type: str,
        silhouette_preference: str,
        suggested_part_name: str,
        suggested_dimensions: str,
        suggested_constraints: str,
    ) -> list[dict[str, str]]:
        variants: list[dict[str, str]] = []
        for heading in ("Variant A", "Variant B", "Variant C"):
            block = self._extract_variant_block(text, heading)
            if not block:
                continue
            name = self._extract_variant_field(block, "Name") or f"{suggested_part_name} {heading[-1]}"
            pitch = self._extract_variant_field(block, "Pitch") or "A different direction to compare before package generation."
            silhouette = self._normalize_silhouette(self._extract_variant_field(block, "Silhouette"))
            if not silhouette:
                silhouette = self._infer_variant_silhouette(name, pitch, object_type, silhouette_preference, len(variants))
            dimensions = self._extract_variant_field(block, "Dimensions") or suggested_dimensions
            constraints = self._extract_variant_field(block, "Constraints") or suggested_constraints
            variant = {
                "id": heading.lower().replace(" ", "-"),
                "label": heading,
                "name": name,
                "silhouette": silhouette,
                "pitch": pitch,
                "dimensions": dimensions,
                "constraints": constraints,
                "print_posture": self._extract_variant_field(block, "Print Posture") or "Prototype first.",
                "object_type": object_type,
            }
            variant["apply_payload"] = {
                "family": "custom-form" if silhouette else "",
                "part": name,
                "dimensions": dimensions,
                "constraints": constraints,
                "creative_profile": silhouette,
            }
            variants.append(variant)
        fallback_silhouette = self._normalize_silhouette(silhouette_preference) or "calm-spiral"
        fallback_profiles = [fallback_silhouette]
        for candidate in ("split-ribbon", "monolith", "racket-frame", "display-prop", "organic-reconstruction"):
            if candidate not in fallback_profiles:
                fallback_profiles.append(candidate)
            if len(fallback_profiles) == 5:
                break
        while len(variants) < 3:
            index = len(variants) + 1
            silhouette = fallback_profiles[min(index - 1, len(fallback_profiles) - 1)]
            variants.append(
                {
                    "id": f"variant-{index}",
                    "label": f"Variant {chr(64 + index)}",
                    "name": f"{suggested_part_name} {chr(64 + index)}",
                    "silhouette": silhouette,
                    "pitch": f"Explore the {silhouette.replace('-', ' ')} direction before locking geometry.",
                    "dimensions": suggested_dimensions,
                    "constraints": suggested_constraints,
                    "print_posture": "Prototype and compare.",
                    "object_type": object_type,
                    "apply_payload": {
                        "family": "custom-form" if silhouette else "",
                        "part": f"{suggested_part_name} {chr(64 + index)}",
                        "dimensions": suggested_dimensions,
                        "constraints": suggested_constraints,
                        "creative_profile": silhouette,
                    },
                }
            )
        return variants[:3]

    def _infer_variant_silhouette(
        self,
        name: str,
        pitch: str,
        object_type: str,
        silhouette_preference: str,
        variant_index: int,
    ) -> str:
        inferred = self._normalize_silhouette(f"{name} {pitch}")
        if inferred:
            return inferred
        object_type_key = (object_type or "").strip().lower()
        if "sport" in object_type_key:
            return "racket-frame"
        if "prop" in object_type_key or "decor" in object_type_key:
            return "display-prop"
        if "organic" in object_type_key:
            return "organic-reconstruction"
        if "sculpt" in object_type_key:
            ordered = ["split-ribbon", "tense-twist", "monolith"]
            return ordered[min(variant_index, len(ordered) - 1)]
        preferred = self._normalize_silhouette(silhouette_preference)
        if preferred:
            return preferred
        ordered = ["split-ribbon", "display-prop", "organic-reconstruction"]
        return ordered[min(variant_index, len(ordered) - 1)]

    def _normalize_silhouette(self, value: str) -> str:
        normalized = (value or "").strip().lower()
        allowed = {
            "calm-spiral",
            "tense-twist",
            "split-ribbon",
            "monolith",
            "racket-frame",
            "organic-shell",
            "display-prop",
            "organic-reconstruction",
        }
        if normalized in allowed:
            return normalized
        mapping = {
            "calm spiral": "calm-spiral",
            "spiral": "calm-spiral",
            "tense twist": "tense-twist",
            "twist": "tense-twist",
            "split ribbon": "split-ribbon",
            "ribbon": "split-ribbon",
            "monolith": "monolith",
            "racket frame": "racket-frame",
            "tennis racket": "racket-frame",
            "organic shell": "organic-shell",
            "shell": "organic-shell",
            "display prop": "display-prop",
            "prop": "display-prop",
            "decor": "display-prop",
            "organic reconstruction": "organic-reconstruction",
            "reconstruction": "organic-reconstruction",
        }
        return mapping.get(normalized, "")

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
        creative_profile: str = "",
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
            shape, script, profile = self._build_cadquery_shape(cq, family, part_name, dims, constraints, creative_profile=creative_profile)
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
        if any(token in text for token in ("sculpture", "totem", "monolith", "ribbon", "helix", "racket", "organic")):
            return "custom-form"
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
        *,
        creative_profile: str = "",
    ) -> tuple[Any, str, dict[str, str]]:
        if family == "bracket":
            return self._build_cadquery_bracket(cq, part_name, dims, constraints)
        if family == "enclosure":
            return self._build_cadquery_enclosure(cq, part_name, dims, constraints)
        if family == "spacer":
            return self._build_cadquery_spacer(cq, part_name, dims, constraints)
        if family == "custom-form":
            return self._build_cadquery_custom_form(cq, part_name, dims, constraints, creative_profile)
        return self._build_cadquery_mount(cq, part_name, dims, constraints)

    def _build_cadquery_custom_form(
        self,
        cq: Any,
        part_name: str,
        dims: dict[str, float],
        constraints: str,
        creative_profile: str,
    ) -> tuple[Any, str, dict[str, str]]:
        height = self._dim_or_default(dims, 120.0, "height", "overall height", "tall")
        width = self._dim_or_default(dims, 70.0, "width", "overall width", "span")
        depth = self._dim_or_default(dims, 45.0, "depth", "overall depth")
        base_height = self._dim_or_default(dims, max(10.0, height * 0.08), "base height", "base thickness")
        thickness = self._dim_or_default(dims, max(4.0, min(width, depth) * 0.12), "thickness", "wall thickness", "ribbon thickness")
        profile = self._normalize_silhouette(creative_profile) or "calm-spiral"

        if profile == "split-ribbon":
            left = self._lofted_ribbon(cq, height, width * 0.34, depth * 0.28, thickness, x_shift=-width * 0.12, twist_scale=0.55, y_wave=depth * 0.08)
            right = self._lofted_ribbon(cq, height * 0.94, width * 0.30, depth * 0.24, thickness * 0.88, x_shift=width * 0.13, twist_scale=-0.5, y_wave=-depth * 0.06)
            base = cq.Workplane("XY").ellipse(width * 0.28, depth * 0.22).extrude(base_height)
            shape = base.union(left.translate((0, 0, base_height * 0.25))).union(right.translate((0, 0, base_height * 0.25)))
        elif profile == "tense-twist":
            tower = self._lofted_ribbon(cq, height, width * 0.32, depth * 0.18, thickness, x_shift=width * 0.08, twist_scale=0.9, y_wave=depth * 0.12)
            base = cq.Workplane("XY").ellipse(width * 0.26, depth * 0.18).extrude(base_height)
            shape = base.union(tower.translate((0, 0, base_height * 0.2)))
        elif profile == "monolith":
            tower = self._lofted_ribbon(cq, height, width * 0.26, depth * 0.22, thickness * 1.15, x_shift=0, twist_scale=0.18, y_wave=depth * 0.03)
            base = cq.Workplane("XY").ellipse(width * 0.24, depth * 0.2).extrude(base_height)
            shape = base.union(tower.translate((0, 0, base_height * 0.2)))
        elif profile == "racket-frame":
            ring_outer = cq.Workplane("XY").ellipse(width * 0.28, height * 0.34).extrude(thickness)
            ring_inner = cq.Workplane("XY").ellipse(max(width * 0.20, 6.0), max(height * 0.26, 12.0)).extrude(thickness + 2.0)
            head = ring_outer.cut(ring_inner.translate((0, 0, -1.0))).translate((0, 0, base_height + height * 0.25))
            handle = cq.Workplane("XY").rect(width * 0.12, depth * 0.12).extrude(height * 0.34).translate((0, 0, base_height))
            throat = cq.Workplane("XZ").polyline([
                (-width * 0.08, base_height + height * 0.24),
                (-width * 0.16, base_height + height * 0.1),
                (width * 0.16, base_height + height * 0.1),
                (width * 0.08, base_height + height * 0.24),
            ]).close().extrude(depth * 0.1, both=True)
            base = cq.Workplane("XY").ellipse(width * 0.16, depth * 0.14).extrude(base_height)
            shape = base.union(handle).union(throat).union(head)
        elif profile == "display-prop":
            body = (
                cq.Workplane("XY")
                .ellipse(width * 0.22, depth * 0.18)
                .workplane(offset=height * 0.22)
                .ellipse(width * 0.30, depth * 0.22)
                .workplane(offset=height * 0.28)
                .ellipse(width * 0.24, depth * 0.18)
                .workplane(offset=height * 0.26)
                .ellipse(width * 0.18, depth * 0.12)
                .loft(combine=True)
            )
            pedestal = cq.Workplane("XY").rect(width * 0.28, depth * 0.22).extrude(base_height)
            crown = cq.Workplane("XY").ellipse(width * 0.12, depth * 0.08).extrude(thickness * 1.6).translate((0, 0, base_height + height * 0.76))
            shape = pedestal.union(body.translate((0, 0, base_height * 0.15))).union(crown)
        elif profile == "organic-reconstruction":
            shell = (
                cq.Workplane("XY")
                .ellipse(width * 0.24, depth * 0.2)
                .workplane(offset=height * 0.18)
                .ellipse(width * 0.30, depth * 0.24)
                .workplane(offset=height * 0.22)
                .ellipse(width * 0.22, depth * 0.18)
                .center(width * 0.04, depth * 0.03)
                .workplane(offset=height * 0.20)
                .ellipse(width * 0.14, depth * 0.12)
                .loft(combine=True)
            )
            inner = (
                cq.Workplane("XY")
                .ellipse(width * 0.14, depth * 0.11)
                .workplane(offset=height * 0.18)
                .ellipse(width * 0.18, depth * 0.14)
                .workplane(offset=height * 0.18)
                .ellipse(width * 0.12, depth * 0.09)
                .center(width * 0.02, depth * 0.02)
                .workplane(offset=height * 0.16)
                .ellipse(width * 0.07, depth * 0.05)
                .loft(combine=True)
                .translate((0, 0, thickness * 0.65))
            )
            base = cq.Workplane("XY").ellipse(width * 0.22, depth * 0.18).extrude(base_height)
            shape = base.union(shell).cut(inner)
        else:
            tower = self._lofted_ribbon(cq, height, width * 0.3, depth * 0.24, thickness, x_shift=-width * 0.05, twist_scale=0.55, y_wave=depth * 0.08)
            base = cq.Workplane("XY").ellipse(width * 0.24, depth * 0.2).extrude(base_height)
            shape = base.union(tower.translate((0, 0, base_height * 0.2)))

        try:
            shape = shape.edges("|Z").fillet(min(thickness * 0.25, 2.4))
        except Exception:
            pass
        script = f"""import cadquery as cq

height = {height}
width = {width}
depth = {depth}
base_height = {base_height}
thickness = {thickness}
creative_profile = "{profile}"

# Custom-form concept generated from Forge Concept Studio.
# Use this as a starting point for refinement, not as final industrial geometry.
result = cq.Workplane("XY").ellipse(width * 0.24, depth * 0.2).extrude(base_height)
show_object(result, name="{self._slugify(part_name)}")
"""
        slicer_profile = {
            "printer_id": self._default_slicer_profile("mount", thickness)["printer_id"],
            "profile_name": "creative-concept-balanced",
            "material": "PLA",
            "layer_height": "0.20 mm",
            "infill": "18% gyroid",
            "supports": "Tree or organic supports only where the silhouette truly needs them",
        }
        return shape, script, slicer_profile

    def _lofted_ribbon(
        self,
        cq: Any,
        height: float,
        width: float,
        depth: float,
        thickness: float,
        *,
        x_shift: float,
        twist_scale: float,
        y_wave: float,
    ) -> Any:
        steps = 7
        segment_height = max(height / steps, thickness * 1.15)
        shape = None
        for index in range(steps):
            ratio = index / max(steps - 1, 1)
            z = ratio * (height - segment_height)
            x = x_shift * math.sin(ratio * math.pi)
            y = y_wave * math.sin(ratio * math.pi * 1.2)
            scale = 1.0 - 0.18 * math.cos(ratio * math.pi)
            angle = twist_scale * ratio * 56.0
            segment = (
                cq.Workplane("XY")
                .rect(max(width * scale, thickness), max(depth * (1.0 - ratio * 0.08), thickness * 0.9))
                .extrude(segment_height)
                .translate((x, y, z + segment_height * 0.5))
                .rotate((0, 0, 0), (0, 0, 1), angle)
            )
            shape = segment if shape is None else shape.union(segment)
        return shape

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
        if family == "custom-form":
            return {
                "printer_id": printer_id,
                "profile_name": "creative-concept-balanced",
                "material": "PLA",
                "layer_height": "0.20 mm",
                "infill": "18% gyroid",
                "supports": "Tree supports only where the form needs them",
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
            {"id": "custom-form", "label": "Custom Form"},
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

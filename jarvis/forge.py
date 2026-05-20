"""JARVIS · Forge — Object-to-Manufacturing Workspace
=====================================================
Captures objects (photos/files), builds 3D models, runs print-readiness
checks, stages slice reports, and gates all manufacturing on approval.

Data root: ~/.jarvis/forge/
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORGE_ROOT = Path.home() / ".jarvis" / "forge"

VALID_STATUSES = [
    "idea",
    "reference_uploaded",
    "capture_in_progress",
    "needs_more_views",
    "needs_measurements",
    "modeling",
    "model_ready",
    "inspection_failed",
    "print_ready",
    "slice_ready",
    "approval_required",
    "sent_to_printer",
    "printing",
    "completed",
    "failed",
    "archived",
]

VALID_FILE_EXTS_3D = {".stl", ".obj", ".glb", ".3mf"}
VALID_FILE_EXTS_PHOTO = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff", ".bmp"}

K2_PRO_BED_MM = {"x": 300.0, "y": 300.0, "z": 600.0}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ForgeStore — thread-safe file-based storage
# ---------------------------------------------------------------------------

class ForgeStore:
    """Thread-safe file-based store for Forge projects."""

    def __init__(self, root: Path = FORGE_ROOT) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / "projects.json"
        self._lock = threading.Lock()

    # ── Internal helpers ────────────────────────────────────────────────────

    def _load_index(self) -> list[dict]:
        if not self._index_path.exists():
            return []
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_index(self, index: list[dict]) -> None:
        self._index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    def _project_path(self, project_id: str) -> Path:
        return self.root / "projects" / project_id / "project.json"

    def _load_project_file(self, project_id: str) -> dict | None:
        p = self._project_path(project_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_project_file(self, project: dict) -> None:
        p = self._project_path(project["id"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")

    def _project_dir(self, project_id: str) -> Path:
        return self.root / "projects" / project_id

    # ── Directory accessors ─────────────────────────────────────────────────

    def uploads_dir(self, project_id: str) -> Path:
        d = self._project_dir(project_id) / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def models_dir(self, project_id: str) -> Path:
        d = self._project_dir(project_id) / "models"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def slices_dir(self, project_id: str) -> Path:
        d = self._project_dir(project_id) / "slices"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _timeline_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "timeline.jsonl"

    # ── Project CRUD ─────────────────────────────────────────────────────────

    def create_project(
        self,
        title: str,
        description: str = "",
        intake_type: str = "file_upload",
    ) -> dict:
        with self._lock:
            project_id = str(uuid.uuid4())
            now = _now()
            project: dict[str, Any] = {
                "id": project_id,
                "title": title,
                "description": description,
                "status": "idea",
                "intake_type": intake_type,
                "source_files": [],
                "capture_sessions": [],
                "measurements": [],
                "assumptions": [],
                "generated_models": [],
                "slices": [],
                "approvals": [],
                "printer_jobs": [],
                "notes": "",
                "created_at": now,
                "updated_at": now,
            }
            self._save_project_file(project)
            index = self._load_index()
            index.append({
                "id": project_id,
                "title": title,
                "status": "idea",
                "intake_type": intake_type,
                "created_at": now,
                "updated_at": now,
            })
            self._save_index(index)
            self.log_event(project_id, "project_created", f"title={title!r}")
            return project

    def get_project(self, project_id: str) -> dict | None:
        return self._load_project_file(project_id)

    def list_projects(self, include_archived: bool = False) -> list[dict]:
        index = self._load_index()
        if include_archived:
            return index
        return [p for p in index if p.get("status") != "archived"]

    def update_project(self, project_id: str, **fields: Any) -> dict | None:
        with self._lock:
            project = self._load_project_file(project_id)
            if project is None:
                return None
            for k, v in fields.items():
                if k not in ("id", "created_at"):
                    project[k] = v
            project["updated_at"] = _now()
            self._save_project_file(project)
            # Sync index entry
            index = self._load_index()
            for entry in index:
                if entry["id"] == project_id:
                    entry["title"] = project.get("title", entry["title"])
                    entry["status"] = project.get("status", entry["status"])
                    entry["updated_at"] = project["updated_at"]
                    break
            self._save_index(index)
            return project

    def set_status(self, project_id: str, status: str, note: str = "") -> bool:
        if status not in VALID_STATUSES:
            return False
        result = self.update_project(project_id, status=status)
        if result is None:
            return False
        self.log_event(project_id, "status_changed", f"status={status!r} note={note!r}")
        return True

    # ── Source files ─────────────────────────────────────────────────────────

    def add_source_file(
        self,
        project_id: str,
        filename: str,
        file_type: str,
        size_bytes: int,
    ) -> bool:
        with self._lock:
            project = self._load_project_file(project_id)
            if project is None:
                return False
            project["source_files"].append({
                "filename": filename,
                "file_type": file_type,
                "size_bytes": size_bytes,
                "added_at": _now(),
            })
            project["updated_at"] = _now()
            self._save_project_file(project)
        self.log_event(project_id, "file_added", f"filename={filename!r} type={file_type!r}")
        return True

    # ── Capture sessions ─────────────────────────────────────────────────────

    def add_capture_session(self, project_id: str, session: dict) -> bool:
        with self._lock:
            project = self._load_project_file(project_id)
            if project is None:
                return False
            project["capture_sessions"].append(session)
            project["updated_at"] = _now()
            self._save_project_file(project)
        return True

    def update_capture_session(
        self, project_id: str, session_id: str, **fields: Any
    ) -> bool:
        with self._lock:
            project = self._load_project_file(project_id)
            if project is None:
                return False
            for session in project.get("capture_sessions", []):
                if session.get("session_id") == session_id:
                    for k, v in fields.items():
                        session[k] = v
                    session["updated_at"] = _now()
                    break
            project["updated_at"] = _now()
            self._save_project_file(project)
        return True

    # ── Measurements ─────────────────────────────────────────────────────────

    def add_measurement(
        self,
        project_id: str,
        label: str,
        value: float,
        unit: str,
        confirmed: bool = False,
        source: str = "manual",
        notes: str = "",
    ) -> dict:
        unit_to_mm = {"mm": 1.0, "cm": 10.0, "in": 25.4}
        value_mm = value * unit_to_mm.get(unit.lower(), 1.0)
        measurement = {
            "id": str(uuid.uuid4()),
            "label": label,
            "value": value,
            "unit": unit,
            "value_mm": value_mm,
            "confirmed": confirmed,
            "source": source,
            "notes": notes,
            "created_at": _now(),
        }
        with self._lock:
            project = self._load_project_file(project_id)
            if project is not None:
                project["measurements"].append(measurement)
                project["updated_at"] = _now()
                self._save_project_file(project)
        self.log_event(
            project_id,
            "measurement_added",
            f"label={label!r} value={value}{unit} confirmed={confirmed}",
        )
        return measurement

    # ── Generated models ─────────────────────────────────────────────────────

    def add_generated_model(self, project_id: str, model_dict: dict) -> bool:
        with self._lock:
            project = self._load_project_file(project_id)
            if project is None:
                return False
            project["generated_models"].append(model_dict)
            project["updated_at"] = _now()
            self._save_project_file(project)
        self.log_event(
            project_id,
            "model_added",
            f"model_id={model_dict.get('model_id')!r} method={model_dict.get('method')!r}",
        )
        return True

    # ── Slice reports ────────────────────────────────────────────────────────

    def add_slice_report(self, project_id: str, slice_dict: dict) -> bool:
        with self._lock:
            project = self._load_project_file(project_id)
            if project is None:
                return False
            project["slices"].append(slice_dict)
            project["updated_at"] = _now()
            self._save_project_file(project)
        self.log_event(
            project_id,
            "slice_staged",
            f"slice_id={slice_dict.get('slice_id')!r}",
        )
        return True

    # ── Approvals ────────────────────────────────────────────────────────────

    def add_approval(
        self,
        project_id: str,
        approved_by: str = "chris",
        notes: str = "",
    ) -> bool:
        approval = {
            "approval_id": str(uuid.uuid4()),
            "approved_by": approved_by,
            "notes": notes,
            "approved_at": _now(),
        }
        with self._lock:
            project = self._load_project_file(project_id)
            if project is None:
                return False
            project["approvals"].append(approval)
            project["updated_at"] = _now()
            self._save_project_file(project)
        self.log_event(
            project_id,
            "approved",
            f"by={approved_by!r} notes={notes!r}",
        )
        return True

    # ── Event log ────────────────────────────────────────────────────────────

    def log_event(self, project_id: str, event_type: str, detail: str = "") -> None:
        entry = json.dumps({
            "ts": _now(),
            "event": event_type,
            "detail": detail,
        })
        try:
            tl = self._timeline_path(project_id)
            tl.parent.mkdir(parents=True, exist_ok=True)
            with tl.open("a", encoding="utf-8") as fh:
                fh.write(entry + "\n")
        except Exception:
            pass

    def read_timeline(self, project_id: str) -> list[dict]:
        tl = self._timeline_path(project_id)
        if not tl.exists():
            return []
        lines = tl.read_text(encoding="utf-8").splitlines()
        events = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
        return events


# ---------------------------------------------------------------------------
# ForgeSupport — intelligence layer
# ---------------------------------------------------------------------------

class ForgeSupport:
    """Intelligence layer on top of ForgeStore.

    Args:
        store: ForgeStore instance.
        openai_client: JarvisOpenAIClient — used for chat responses.
    """

    def __init__(self, store: ForgeStore, openai_client: Any = None) -> None:
        self.store = store
        self.openai_client = openai_client

    # ── Model inspection ─────────────────────────────────────────────────────

    def inspect_model(self, project_id: str, model_filename: str) -> dict:
        """Analyze a 3D model with trimesh. Updates project if model found."""
        model_path = self.store.models_dir(project_id) / model_filename
        if not model_path.exists():
            # Try uploads dir too
            model_path = self.store.uploads_dir(project_id) / model_filename
        if not model_path.exists():
            return {
                "ok": False,
                "error": f"File not found: {model_filename}",
                "printable": False,
                "warnings": [],
                "was_repaired": False,
            }

        try:
            import trimesh  # type: ignore[import]
        except ImportError:
            return {
                "ok": False,
                "error": "trimesh not installed",
                "printable": False,
                "warnings": [],
                "was_repaired": False,
            }

        warnings: list[str] = []
        was_repaired = False
        repair_notes = ""

        try:
            mesh = trimesh.load(str(model_path))
            # Handle scene objects (e.g. GLB/OBJ with multiple meshes)
            if hasattr(mesh, "geometry") and mesh.geometry:
                mesh = trimesh.util.concatenate(list(mesh.geometry.values()))

            is_watertight = bool(mesh.is_watertight)

            # Attempt repair if not watertight
            if not is_watertight:
                trimesh.repair.fill_holes(mesh)
                trimesh.repair.fix_normals(mesh)
                was_repaired = True
                is_watertight = bool(mesh.is_watertight)
                if is_watertight:
                    repair_notes = "Filled holes and fixed normals — mesh is now watertight."
                else:
                    repair_notes = "Repair attempted but mesh remains open. Manual fix required."
                    warnings.append("Mesh is not manifold/watertight after repair attempt.")

            # Bounding box in mm
            extents = mesh.bounding_box.extents.tolist()
            bbox_mm = {"x": round(extents[0], 2), "y": round(extents[1], 2), "z": round(extents[2], 2)}

            # Volume
            volume_mm3 = float(mesh.volume) if mesh.is_volume else None

            # Face / vertex counts
            face_count = int(len(mesh.faces))
            vertex_count = int(len(mesh.vertices))

            # Thin wall check: warn if any edge < 0.8 mm
            try:
                edge_lengths = mesh.edges_unique_length
                min_edge = float(edge_lengths.min()) if len(edge_lengths) > 0 else None
                if min_edge is not None and min_edge < 0.8:
                    warnings.append(
                        f"Thin geometry detected: minimum edge length {min_edge:.2f} mm (below 0.8 mm threshold)."
                    )
            except Exception:
                min_edge = None

            # Bed size check (K2 Pro: 300×300×600 mm)
            oversized = False
            for axis, key in [("x", "x"), ("y", "y"), ("z", "z")]:
                if bbox_mm[key] > K2_PRO_BED_MM[axis]:
                    oversized = True
                    warnings.append(
                        f"Model {key.upper()}-axis ({bbox_mm[key]} mm) exceeds K2 Pro bed ({K2_PRO_BED_MM[axis]} mm)."
                    )

            printable = is_watertight and not oversized

            result = {
                "ok": True,
                "printable": printable,
                "is_watertight": is_watertight,
                "was_repaired": was_repaired,
                "repair_notes": repair_notes,
                "bounding_box_mm": bbox_mm,
                "volume_mm3": volume_mm3,
                "face_count": face_count,
                "vertex_count": vertex_count,
                "min_edge_mm": min_edge,
                "oversized_for_k2_pro": oversized,
                "warnings": warnings,
                "inspected_at": _now(),
            }

        except Exception as exc:
            result = {
                "ok": False,
                "error": str(exc),
                "printable": False,
                "warnings": [f"Inspection failed: {exc}"],
                "was_repaired": False,
            }

        # Update project model record if found
        try:
            project = self.store.get_project(project_id)
            if project:
                for model in project.get("generated_models", []):
                    if model.get("filename") == model_filename:
                        model["is_manifold"] = result.get("is_watertight", False)
                        model["was_repaired"] = result.get("was_repaired", False)
                        model["repair_notes"] = result.get("repair_notes", "")
                        model["print_readiness"] = result
                        if result.get("bounding_box_mm"):
                            model["bounding_box_mm"] = result["bounding_box_mm"]
                        break
                new_status = "print_ready" if result.get("printable") else "inspection_failed"
                self.store.update_project(
                    project_id,
                    generated_models=project["generated_models"],
                    status=new_status,
                )
                self.store.log_event(
                    project_id,
                    "model_inspected",
                    f"printable={result.get('printable')} warnings={len(result.get('warnings', []))}",
                )
        except Exception:
            pass

        return result

    # ── Capture completeness ─────────────────────────────────────────────────

    def capture_completeness(self, capture_session: dict) -> dict:
        """Analyze which views are captured vs missing."""
        required_views = {"front", "back", "left", "right", "top"}
        optional_views = {"bottom", "scale_reference", "detail"}

        frames = capture_session.get("frames", [])
        captured_view_types = {f.get("view_type", "").lower() for f in frames}

        captured_required = required_views & captured_view_types
        missing_required = required_views - captured_view_types
        captured_optional = optional_views & captured_view_types

        req_count = len(captured_required)
        if req_count < 2:
            geometry_confidence = "low"
        elif req_count < 5:
            geometry_confidence = "medium"
        else:
            geometry_confidence = "high"

        has_scale_ref = "scale_reference" in captured_optional

        # Check if there's a confirmed measurement from project measurements
        # (caller passes it in separately — we look for it in session confidence hints)
        existing_confidence = capture_session.get("confidence", {})
        has_confirmed_measurement = existing_confidence.get("scale") == "high"

        if has_confirmed_measurement:
            scale_confidence = "high"
        elif has_scale_ref:
            scale_confidence = "medium"
        else:
            scale_confidence = "low"

        # Print readiness: need high geometry + at least medium scale
        if geometry_confidence == "high" and scale_confidence in ("medium", "high"):
            print_readiness = "medium"
        elif geometry_confidence == "high" and scale_confidence == "high":
            print_readiness = "high"
        elif geometry_confidence == "low":
            print_readiness = "not_ready"
        else:
            print_readiness = "low"

        return {
            "total_frames": len(frames),
            "captured_required": sorted(captured_required),
            "missing_required": sorted(missing_required),
            "captured_optional": sorted(captured_optional),
            "required_count": req_count,
            "required_total": len(required_views),
            "geometry_confidence": geometry_confidence,
            "scale_confidence": scale_confidence,
            "print_readiness": print_readiness,
            "ready_to_model": geometry_confidence in ("medium", "high"),
            "missing_views": sorted(missing_required),
        }

    # ── Chat response ─────────────────────────────────────────────────────────

    def forge_chat_response(self, project_id: str, user_message: str) -> str:
        """Generate a JARVIS Forge chat response grounded in project state."""
        if self.openai_client is None:
            return "Forge AI not available — OpenAI client not configured."

        project = self.store.get_project(project_id)
        if project is None:
            return "I don't have a record of that project."

        # Build state summary
        status = project.get("status", "idea")
        measurements = project.get("measurements", [])
        models = project.get("generated_models", [])
        slices = project.get("slices", [])
        approvals = project.get("approvals", [])
        assumptions = project.get("assumptions", [])

        confirmed_measurements = [m for m in measurements if m.get("confirmed")]
        unconfirmed_measurements = [m for m in measurements if not m.get("confirmed")]

        # Capture session summary
        capture_summary = "No capture sessions."
        sessions = project.get("capture_sessions", [])
        if sessions:
            latest_session = sessions[-1]
            completeness = self.capture_completeness(latest_session)
            geo_conf = completeness["geometry_confidence"]
            scale_conf = completeness["scale_confidence"]
            missing = completeness.get("missing_views", [])
            capture_summary = (
                f"Capture: {completeness['required_count']}/{completeness['required_total']} required views. "
                f"Geometry confidence: {geo_conf}. Scale confidence: {scale_conf}. "
                f"Missing: {', '.join(missing) if missing else 'none'}."
            )

        model_summary = "No models yet."
        if models:
            latest_model = models[-1]
            printable = latest_model.get("print_readiness", {}).get("printable", "unknown")
            model_summary = (
                f"Latest model: {latest_model.get('filename', 'unknown')} "
                f"via {latest_model.get('method', '?')}. Printable: {printable}."
            )

        measurement_summary = "No measurements."
        if measurements:
            parts = []
            for m in measurements:
                flag = "confirmed" if m.get("confirmed") else "assumed"
                parts.append(f"{m['label']}: {m['value']}{m['unit']} ({flag})")
            measurement_summary = "Measurements: " + "; ".join(parts) + "."

        system_prompt = f"""You are JARVIS Forge — the manufacturing intelligence layer for Chris's maker workspace.

You are precise, practical, honest, and maker-minded. You tell Chris exactly what you know,
what you are guessing, and what you need. You never overstate your confidence.

Current project: {project.get('title', 'Unnamed')}
Status: {status}
{capture_summary}
{measurement_summary}
{model_summary}
Unconfirmed assumptions: {len(unconfirmed_measurements)} ({', '.join(a for a in assumptions[:3]) if assumptions else 'none'})
Slices staged: {len(slices)}. Approvals: {len(approvals)}.

Voice guidance:
- Be direct and specific. No filler. No emojis.
- If you're unsure, say so clearly.
- Tell Chris exactly what input you need and why.
- Example: "I can see enough to begin, but not enough to print. Give me one confirmed measurement and the rear view, and I'll build the first model."
- If print-ready: tell him the next step is slicing and approval.
- If blocked: name the specific blocker."""

        try:
            return self.openai_client.prompt_text(system_prompt, user_message, max_output_tokens=400)
        except Exception as exc:
            return f"Forge response error: {exc}"

    # ── Slice report staging ─────────────────────────────────────────────────

    def prepare_slice_report(
        self,
        project_id: str,
        model_id: str,
        printer_id: str = "creality-k2-pro-combo",
        material: str = "PLA",
    ) -> dict:
        """Generate a staging slice report (not actual slicing)."""
        warnings: list[str] = []

        # Look up model
        project = self.store.get_project(project_id)
        model_found = None
        if project:
            for m in project.get("generated_models", []):
                if m.get("model_id") == model_id:
                    model_found = m
                    break

        if model_found is None:
            warnings.append(f"Model ID {model_id!r} not found in project — report staged without model data.")
        else:
            readiness = model_found.get("print_readiness", {})
            if not readiness.get("printable", False):
                warnings.extend(readiness.get("warnings", []))
                warnings.append("Model has not passed inspection — review before printing.")

        slice_report = {
            "slice_id": str(uuid.uuid4()),
            "model_id": model_id,
            "printer_id": printer_id,
            "material": material,
            "layer_height_mm": 0.2,
            "infill_percent": 20,
            "supports": "auto",
            "estimated_time_minutes": None,
            "estimated_material_g": None,
            "status": "staged",
            "warnings": warnings,
            "created_at": _now(),
        }

        self.store.add_slice_report(project_id, slice_report)
        self.store.set_status(project_id, "slice_ready")
        return slice_report

    # ── Moonraker status ─────────────────────────────────────────────────────

    def moonraker_status(self, host: str, port: int = 7125) -> dict:
        """Query a Moonraker API for printer status. Never crashes."""
        import urllib.request as _urllib_request
        import urllib.error as _urllib_error

        url = (
            f"http://{host}:{port}/printer/objects/query"
            "?extruder&heater_bed&print_stats"
        )
        try:
            req = _urllib_request.Request(url, method="GET")
            with _urllib_request.urlopen(req, timeout=3) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            status = raw.get("result", {}).get("status", {})
            extruder = status.get("extruder", {})
            heater_bed = status.get("heater_bed", {})
            print_stats = status.get("print_stats", {})
            return {
                "available": True,
                "host": host,
                "port": port,
                "extruder_temp": extruder.get("temperature"),
                "extruder_target": extruder.get("target"),
                "bed_temp": heater_bed.get("temperature"),
                "bed_target": heater_bed.get("target"),
                "print_state": print_stats.get("state"),
                "filename": print_stats.get("filename"),
                "print_duration": print_stats.get("print_duration"),
                "total_duration": print_stats.get("total_duration"),
                "queried_at": _now(),
            }
        except (_urllib_error.URLError, OSError) as exc:
            return {"available": False, "error": str(exc), "host": host, "port": port}
        except Exception as exc:
            return {"available": False, "error": f"Unexpected error: {exc}", "host": host, "port": port}

    # ── Shap-E reconstruction ─────────────────────────────────────────────────

    def reconstruct_shape_e(
        self,
        project_id: str,
        image_path: str = "",
        prompt_text: str = "",
    ) -> dict:
        """Use Shap-E to generate a rough 3D model from image or text prompt."""
        try:
            import torch  # type: ignore[import]
            from shap_e.diffusion.sample import sample_latents  # type: ignore[import]
            from shap_e.diffusion.gaussian_diffusion import diffusion_from_config  # type: ignore[import]
            from shap_e.models.download import load_model, load_config  # type: ignore[import]
            from shap_e.util.notebooks import decode_latent_mesh  # type: ignore[import]
        except ImportError as exc:
            return {
                "ok": False,
                "error": f"Shap-E not available: {exc}",
                "method": "shap_e",
            }

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_id = str(uuid.uuid4())
        output_filename = f"shap_e_{model_id[:8]}.stl"
        output_path = self.store.models_dir(project_id) / output_filename

        try:
            xm = load_model("transmitter", device=device)
            diffusion = diffusion_from_config(load_config("diffusion"))

            if image_path and Path(image_path).exists():
                from shap_e.models.download import load_model as _lm  # type: ignore[import]
                model_fn = _lm("image300M", device=device)
                from PIL import Image as _PIL_Image  # type: ignore[import]
                img = _PIL_Image.open(image_path)
                batch_size = 1
                guidance_scale = 3.0
                latents = sample_latents(
                    batch_size=batch_size,
                    model=model_fn,
                    diffusion=diffusion,
                    guidance_scale=guidance_scale,
                    model_kwargs={"images": [img] * batch_size},
                    progress=False,
                    clip_denoised=True,
                    use_fp16=True,
                    use_karras=True,
                    karras_steps=64,
                    sigma_min=1e-3,
                    sigma_max=160,
                    s_churn=0,
                )
                used_method_note = f"image: {Path(image_path).name}"
            else:
                if not prompt_text:
                    prompt_text = "a simple 3D printable object"
                model_fn = load_model("text300M", device=device)
                batch_size = 1
                guidance_scale = 15.0
                latents = sample_latents(
                    batch_size=batch_size,
                    model=model_fn,
                    diffusion=diffusion,
                    guidance_scale=guidance_scale,
                    model_kwargs={"texts": [prompt_text] * batch_size},
                    progress=False,
                    clip_denoised=True,
                    use_fp16=True,
                    use_karras=True,
                    karras_steps=64,
                    sigma_min=1e-3,
                    sigma_max=160,
                    s_churn=0,
                )
                used_method_note = f"text prompt: {prompt_text[:60]}"

            # Decode first latent to mesh and save as STL
            t = decode_latent_mesh(xm, latents[0]).tri_mesh()
            with output_path.open("wb") as stl_fh:
                t.write_stl(stl_fh)

            file_size = output_path.stat().st_size if output_path.exists() else 0

            model_dict = {
                "model_id": model_id,
                "version": 1,
                "title": f"Shap-E reconstruction ({used_method_note[:40]})",
                "method": "shap_e",
                "filename": output_filename,
                "format": "stl",
                "file_size_bytes": file_size,
                "bounding_box_mm": {},
                "is_manifold": None,
                "was_repaired": False,
                "repair_notes": "",
                "print_readiness": {},
                "created_at": _now(),
                "notes": "AI estimate — confirm measurements before printing.",
            }

            self.store.add_generated_model(project_id, model_dict)
            self.store.set_status(project_id, "model_ready")
            self.store.log_event(
                project_id,
                "shap_e_reconstruction",
                f"method_note={used_method_note!r} file={output_filename!r}",
            )
            return {"ok": True, **model_dict}

        except Exception as exc:
            self.store.log_event(project_id, "shap_e_error", str(exc))
            return {
                "ok": False,
                "error": str(exc),
                "method": "shap_e",
            }

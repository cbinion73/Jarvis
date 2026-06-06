"""
wow_forge.py — World of Warcraft Model Bridge for JARVIS Forge
==============================================================
Pulls WoW character/creature models into the Forge 3D workspace.

Supported import paths
----------------------
1. Watch-folder (default, zero-dependency)
   Point WOW_EXPORT_FOLDER at the directory where wow.export
   (https://github.com/Kruithne/wow.export) saves its GLB/OBJ exports.
   Forge polls the folder and lists available models for one-click import.

2. wago-api / Blizzard CDN  (optional — pip install wago-api)
   Fetch raw file bytes by FileDataID from the CDN; queued for conversion.

3. Blender headless + WoW Blender Studio  (optional)
   Converts raw .m2 → GLB via `blender --background --python`.
   Only used when Stage-2 provides a raw M2 file.

Config  (~/.jarvis/wow_forge.json)
----------------------------------
export_folder       path where wow.export writes GLB/OBJ files
                    default: ~/Desktop/WoW_Exports
wow_install_path    /Applications/World of Warcraft
blender_path        /Applications/Blender.app/Contents/MacOS/Blender
auto_import         false — if true, auto-import new files into the active project
"""
from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_CONFIG_PATH = Path.home() / ".jarvis" / "wow_forge.json"
_CONFIG_LOG_PATH = _CONFIG_PATH.with_name("wow_forge_log.jsonl")
_CONFIG_STATE_LOG_PATH = _CONFIG_PATH.with_name("wow_forge_state_log.jsonl")
_lock = threading.Lock()

_MODEL_EXTS  = {".glb", ".gltf", ".obj", ".stl"}
_PHOTO_EXTS  = {".jpg", ".jpeg", ".png", ".webp"}

_DEFAULT_CONFIG: dict[str, Any] = {
    "export_folder":    str(Path.home() / "Desktop" / "WoW_Exports"),
    "wow_install_path": "/Applications/World of Warcraft",
    "blender_path":     "/Applications/Blender.app/Contents/MacOS/Blender",
    "auto_import":      False,
}

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with _lock:
        if _CONFIG_PATH.exists():
            try:
                cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
                return {**_DEFAULT_CONFIG, **cfg}
            except Exception:
                return {**_DEFAULT_CONFIG, **(_load_config_from_state_log() or _load_config_from_log())}
        if not _CONFIG_PATH.exists():
            return {**_DEFAULT_CONFIG, **(_load_config_from_state_log() or _load_config_from_log())}
        return dict(_DEFAULT_CONFIG)


def save_config(updates: dict) -> dict:
    with _lock:
        existing: dict = _DEFAULT_CONFIG.copy()
        if _CONFIG_PATH.exists():
            try:
                existing.update(json.loads(_CONFIG_PATH.read_text(encoding="utf-8")))
            except Exception:
                pass
        for k, v in updates.items():
            if k in _DEFAULT_CONFIG:
                existing[k] = v
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(_CONFIG_PATH, existing)
        append_jsonl(
            _CONFIG_LOG_PATH,
            {
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "config": existing,
            },
        )
        append_jsonl(
            _CONFIG_STATE_LOG_PATH,
            {
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "config": existing,
            },
        )
        return existing


def _load_config_from_log() -> dict:
    try:
        if _CONFIG_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _CONFIG_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                config = payload.get("config")
                if isinstance(config, dict):
                    latest = dict(config)
            return latest or {}
    except Exception:
        pass
    return {}


def _load_config_from_state_log() -> dict:
    try:
        if _CONFIG_STATE_LOG_PATH.exists():
            latest: dict[str, Any] | None = None
            for line in _CONFIG_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                config = payload.get("config")
                if isinstance(config, dict):
                    latest = dict(config)
            return latest or {}
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Watch-folder scanner
# ---------------------------------------------------------------------------

def list_available_models(search: str = "") -> list[dict]:
    """List GLB/OBJ/STL files in the configured export folder, newest first."""
    cfg = load_config()
    folder = Path(cfg["export_folder"])
    if not folder.exists():
        return []
    models = []
    search_lower = search.strip().lower()
    for p in folder.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in _MODEL_EXTS:
            continue
        if search_lower and search_lower not in p.name.lower():
            continue
        stat = p.stat()
        models.append({
            "filename":    p.name,
            "path":        str(p),
            "size_bytes":  stat.st_size,
            "modified_at": datetime.fromtimestamp(
                stat.st_mtime, timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "format": p.suffix.lower().lstrip("."),
        })
    return sorted(models, key=lambda m: m["modified_at"], reverse=True)


# ---------------------------------------------------------------------------
# Import into Forge project
# ---------------------------------------------------------------------------

def import_model_to_forge(
    filename: str,
    forge_store: Any,   # ForgeStore instance — avoid circular import
    project_id: str,
) -> dict:
    """
    Copy *filename* from the watch folder into a Forge project's uploads/ dir,
    register it as a source file, and advance the project status.
    Returns {ok, filename, source, size_bytes, project_id} or {ok:False, error}.
    """
    cfg = load_config()
    src = Path(cfg["export_folder"]) / filename
    if not src.exists():
        return {"ok": False, "error": f"File not found in WoW export folder: {filename}"}

    project = forge_store.get_project(project_id)
    if project is None:
        return {"ok": False, "error": f"Forge project not found: {project_id}"}

    uploads_dir = forge_store.uploads_dir(project_id)
    dest = uploads_dir / filename
    # Avoid silently overwriting an existing import
    if dest.exists():
        stem, suffix = src.stem, src.suffix
        dest = uploads_dir / f"{stem}_{uuid.uuid4().hex[:6]}{suffix}"

    shutil.copy2(src, dest)
    size_bytes = dest.stat().st_size

    forge_store.add_source_file(project_id, dest.name, "3d_model", size_bytes)
    forge_store.set_status(project_id, "model_ready")
    forge_store.log_event(
        project_id, "wow_import",
        f"source={filename!r} dest={dest.name!r} size={size_bytes}",
    )

    return {
        "ok": True,
        "filename": dest.name,
        "source":   filename,
        "size_bytes": size_bytes,
        "project_id": project_id,
        "format": src.suffix.lower().lstrip("."),
    }


# ---------------------------------------------------------------------------
# Optional: Blender headless M2 → GLB conversion
# ---------------------------------------------------------------------------

_BLENDER_SCRIPT = """\
import bpy, sys, os

m2_path  = sys.argv[-2]
out_path = sys.argv[-1]

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Try WoW Blender Studio import (must be installed in Blender's addon dir)
try:
    bpy.ops.preferences.addon_enable(module='wow_blender_studio')
    bpy.ops.import_scene.wow_m2(filepath=m2_path)
except Exception as e:
    print(f"WoW addon import failed: {e}", file=sys.stderr)
    sys.exit(1)

# Export as GLB
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
)
print(f"Exported: {out_path}")
"""


def convert_m2_to_glb(
    m2_path: str,
    output_dir: str,
    timeout: int = 120,
) -> dict:
    """
    Convert a raw .m2 file to GLB using Blender headless + WoW Blender Studio.
    Returns {ok, glb_path} or {ok:False, error}.
    """
    cfg = load_config()
    blender = Path(cfg["blender_path"])
    if not blender.exists():
        return {"ok": False, "error": f"Blender not found at {blender}. Set blender_path in WoW Forge config."}

    src = Path(m2_path)
    if not src.exists():
        return {"ok": False, "error": f"M2 file not found: {m2_path}"}

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    glb_path = str(out_dir / (src.stem + ".glb"))

    # Write the conversion script to a temp file
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_BLENDER_SCRIPT)
        script_path = tmp.name

    try:
        result = subprocess.run(
            [
                str(blender), "--background", "--python", script_path,
                "--", m2_path, glb_path,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Blender conversion timed out"}
    finally:
        Path(script_path).unlink(missing_ok=True)

    if result.returncode != 0 or not Path(glb_path).exists():
        err = (result.stderr or result.stdout or "unknown").strip()[-400:]
        return {"ok": False, "error": err, "returncode": result.returncode}

    return {"ok": True, "glb_path": glb_path, "size_bytes": Path(glb_path).stat().st_size}


# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------

def get_status() -> dict:
    """Return a UI-facing status dict for the WoW bridge panel."""
    cfg = load_config()
    folder   = Path(cfg["export_folder"])
    wow_path = Path(cfg["wow_install_path"])
    blender  = Path(cfg["blender_path"])
    models   = list_available_models()

    # Check wago-api availability (optional pip package)
    wago_available = False
    try:
        import wago  # noqa: F401
        wago_available = True
    except ImportError:
        pass

    return {
        "export_folder":         cfg["export_folder"],
        "export_folder_exists":  folder.exists(),
        "wow_install_found":     wow_path.exists(),
        "blender_found":         blender.exists(),
        "wago_api_available":    wago_available,
        "available_models":      len(models),
        "auto_import":           cfg.get("auto_import", False),
        # Direct download link for wow.export
        "wow_export_download":   "https://github.com/Kruithne/wow.export/releases/latest",
        "wow_export_setup_tip":  (
            "1. Download wow.export (link above)\n"
            "2. Open it and point it at your WoW install\n"
            "3. Search for your character / model\n"
            "4. Export as GLB — files land in your export folder\n"
            "5. Hit Refresh here to see them"
        ),
    }

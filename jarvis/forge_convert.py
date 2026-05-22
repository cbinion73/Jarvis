"""
forge_convert.py — Forge Convert: format conversion, mesh repair, and scale tools
==================================================================================
All mesh operations use trimesh (already in requirements.txt >= 4.0.0).
Each public function is synchronous (blocking I/O) and should be called
via asyncio.to_thread() from async FastAPI handlers.
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()

# Formats trimesh can round-trip reliably in the Forge context
SUPPORTED_FORMATS = {"glb", "obj", "stl", "ply"}

UNIT_FACTORS_TO_MM: dict[str, float] = {
    "mm": 1.0,
    "cm": 10.0,
    "in": 25.4,
    "m":  1000.0,
}


def _load_mesh(path: Path):
    """Load *path* with trimesh; always returns a single Trimesh (not a Scene)."""
    import trimesh  # lazy import — avoids startup cost

    mesh = trimesh.load(str(path), force="mesh")
    # GLB/GLTF may load as a Scene containing multiple meshes
    if hasattr(mesh, "dump"):
        merged = mesh.dump(concatenate=True)
        if merged is None or (hasattr(merged, "is_empty") and merged.is_empty):
            raise ValueError("File contains no geometry after flattening scene")
        mesh = merged
    if mesh is None or (hasattr(mesh, "is_empty") and mesh.is_empty):
        raise ValueError("No geometry found in file")
    return mesh


# ---------------------------------------------------------------------------
# 1. Format Converter
# ---------------------------------------------------------------------------

def convert_format(
    src_path: str | Path,
    target_format: str,
    output_dir: str | Path,
) -> dict[str, Any]:
    """
    Convert *src_path* to *target_format* (glb / obj / stl / ply).
    Writes <output_dir>/<stem>_converted.<target_format>.
    Returns {ok, output_path, filename, size_bytes, source_format, target_format}
            or {ok: False, error}.
    """
    try:
        import trimesh  # noqa: F401 — verify available
    except ImportError:
        return {"ok": False, "error": "trimesh is not installed (pip install trimesh)"}

    src = Path(src_path)
    fmt = target_format.lower().strip(".")
    if fmt not in SUPPORTED_FORMATS:
        return {
            "ok": False,
            "error": f"Unsupported target format {fmt!r}. Supported: {sorted(SUPPORTED_FORMATS)}",
        }
    if not src.exists():
        return {"ok": False, "error": f"Source file not found: {src}"}

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src.stem}_converted.{fmt}"

    try:
        mesh = _load_mesh(src)
        mesh.export(str(out_path))
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:400]}

    if not out_path.exists():
        return {"ok": False, "error": "Export produced no output file"}

    return {
        "ok": True,
        "output_path": str(out_path),
        "filename": out_path.name,
        "size_bytes": out_path.stat().st_size,
        "source_format": src.suffix.lower().lstrip("."),
        "target_format": fmt,
    }


# ---------------------------------------------------------------------------
# 2. WoW-specific tools
# ---------------------------------------------------------------------------

def check_blender_setup() -> dict[str, Any]:
    """
    Verify that Blender is installed and has the WoW Blender Studio addon.
    Reads blender_path from ~/.jarvis/wow_forge.json via wow_forge.load_config().
    Returns {ok, blender_found, blender_version, addon_found, addon_name, details}.
    """
    try:
        from .wow_forge import load_config
    except ImportError:
        from wow_forge import load_config  # fallback for direct execution

    cfg = load_config()
    blender_path = Path(cfg.get("blender_path", "/Applications/Blender.app/Contents/MacOS/Blender"))

    result: dict[str, Any] = {
        "ok": False,
        "blender_found": blender_path.exists(),
        "blender_path": str(blender_path),
        "blender_version": None,
        "addon_found": False,
        "addon_name": "wow_blender_studio",
        "details": [],
    }

    if not blender_path.exists():
        result["details"].append(
            f"Blender not found at {blender_path}. Update the path in WoW Forge Setup."
        )
        return result

    # Get Blender version
    try:
        ver_proc = subprocess.run(
            [str(blender_path), "--version"],
            capture_output=True, text=True, timeout=15,
        )
        for line in ver_proc.stdout.splitlines():
            if line.startswith("Blender"):
                result["blender_version"] = line.strip()
                result["details"].append(f"Found: {line.strip()}")
                break
    except subprocess.TimeoutExpired:
        result["details"].append("Timed out running blender --version")
        return result
    except Exception as exc:
        result["details"].append(f"Could not run blender --version: {exc}")
        return result

    # Check for WoW Blender Studio addon via headless Python expression
    check_expr = (
        "import bpy, sys; "
        "keys = list(bpy.context.preferences.addons.keys()); "
        "found = 'wow_blender_studio' in keys or any('wow' in k.lower() for k in keys); "
        "print('WBS_ADDON_FOUND' if found else 'WBS_ADDON_MISSING')"
    )
    try:
        addon_proc = subprocess.run(
            [str(blender_path), "--background", "--python-expr", check_expr],
            capture_output=True, text=True, timeout=30,
        )
        combined = addon_proc.stdout + addon_proc.stderr
        if "WBS_ADDON_FOUND" in combined:
            result["addon_found"] = True
            result["ok"] = True
            result["details"].append("WoW Blender Studio addon: FOUND ✓")
        else:
            result["details"].append("WoW Blender Studio addon: NOT FOUND")
            result["details"].append(
                "Install from: https://github.com/skarnproject/WoWBlenderStudio"
            )
    except subprocess.TimeoutExpired:
        result["details"].append("Blender took too long to check addon (>30s)")
    except Exception as exc:
        result["details"].append(f"Addon check failed: {exc}")

    return result


# ---------------------------------------------------------------------------
# 3. Mesh Repair / Cleanup
# ---------------------------------------------------------------------------

def repair_mesh(
    src_path: str | Path,
    output_dir: str | Path,
    fix_normals: bool = True,
    fill_holes: bool = True,
    fix_winding: bool = True,
) -> dict[str, Any]:
    """
    Run trimesh repair operations on *src_path*, write repaired file to
    <output_dir>/<stem>_repaired<ext>.
    Returns {ok, filename, output_path, size_bytes, ops_applied,
             was_watertight, is_watertight} or {ok: False, error}.
    """
    try:
        import trimesh.repair as tr_repair  # noqa: F401
    except ImportError:
        return {"ok": False, "error": "trimesh is not installed"}

    src = Path(src_path)
    if not src.exists():
        return {"ok": False, "error": f"Source file not found: {src}"}

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src.stem}_repaired{src.suffix}"

    try:
        import trimesh.repair as tr_repair
        mesh = _load_mesh(src)
        was_watertight = bool(mesh.is_watertight)
        ops_applied: list[str] = []

        if fix_normals:
            mesh.fix_normals()
            ops_applied.append("fix_normals")
        if fill_holes:
            tr_repair.fill_holes(mesh)
            ops_applied.append("fill_holes")
        if fix_winding:
            tr_repair.fix_winding(mesh)
            ops_applied.append("fix_winding")

        mesh.export(str(out_path))
        is_watertight = bool(mesh.is_watertight)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:400]}

    return {
        "ok": True,
        "filename": out_path.name,
        "output_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "ops_applied": ops_applied,
        "was_watertight": was_watertight,
        "is_watertight": is_watertight,
    }


# ---------------------------------------------------------------------------
# 4. Scale & Unit Tools
# ---------------------------------------------------------------------------

def scale_mesh(
    src_path: str | Path,
    output_dir: str | Path,
    operation: str,             # "rescale" | "normalize_bbox" | "center_origin"
    target_size: float = 100.0,
    target_unit: str = "mm",    # mm | cm | in | m  (rescale only)
    current_unit: str = "mm",   # assumed unit of the source file (rescale only)
) -> dict[str, Any]:
    """
    Apply a scale or translation operation to *src_path*.

    rescale        — scale longest axis to target_size in target_unit
    normalize_bbox — scale so longest axis == 1.0 (unit bounding box)
    center_origin  — translate centroid to world origin (no scaling)

    Returns {ok, filename, output_path, size_bytes, operation,
             scale_factor, original_bbox_mm, final_bbox_mm} or {ok: False, error}.
    """
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        return {"ok": False, "error": "numpy is not installed"}
    try:
        import trimesh  # noqa: F401
    except ImportError:
        return {"ok": False, "error": "trimesh is not installed"}

    src = Path(src_path)
    if not src.exists():
        return {"ok": False, "error": f"Source file not found: {src}"}

    valid_ops = {"rescale", "normalize_bbox", "center_origin"}
    if operation not in valid_ops:
        return {"ok": False, "error": f"Unknown operation {operation!r}. Valid: {sorted(valid_ops)}"}

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src.stem}_{operation}{src.suffix}"

    try:
        import numpy as np

        mesh = _load_mesh(src)
        original_bbox: list[float] = mesh.bounding_box.extents.tolist()
        scale_factor = 1.0

        if operation == "rescale":
            src_to_mm   = UNIT_FACTORS_TO_MM.get(current_unit, 1.0)
            tgt_to_mm   = UNIT_FACTORS_TO_MM.get(target_unit, 1.0)
            longest_mm  = float(np.max(mesh.bounding_box.extents)) * src_to_mm
            if longest_mm == 0:
                return {"ok": False, "error": "Mesh has zero extent — cannot rescale"}
            target_mm   = target_size * tgt_to_mm
            scale_factor = target_mm / longest_mm
            mesh.apply_scale(scale_factor)

        elif operation == "normalize_bbox":
            longest = float(np.max(mesh.bounding_box.extents))
            if longest == 0:
                return {"ok": False, "error": "Mesh has zero extent"}
            scale_factor = 1.0 / longest
            mesh.apply_scale(scale_factor)

        elif operation == "center_origin":
            mesh.apply_translation(-mesh.centroid.copy())

        final_bbox: list[float] = mesh.bounding_box.extents.tolist()
        mesh.export(str(out_path))
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:400]}

    return {
        "ok": True,
        "filename": out_path.name,
        "output_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "operation": operation,
        "scale_factor": scale_factor,
        "original_bbox_mm": original_bbox,
        "final_bbox_mm": final_bbox,
    }

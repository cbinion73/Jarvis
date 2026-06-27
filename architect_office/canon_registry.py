from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BINDING_HINTS = (
    "binding",
    "canonical",
    "canon",
    "authoritative",
    "must follow",
    "governs",
    "source of truth",
)

CHRIS_CANON_PATHS = (
    "docs/CHRIS-INTENT-CANON.md",
    "docs/CHRIS-CONTEXT-CANON.md",
)


@dataclass(frozen=True)
class CanonEntry:
    level: str
    path: str
    note: str


@dataclass(frozen=True)
class CanonRegistry:
    registry_path: Path
    exists: bool
    entries: list[CanonEntry]
    canon_paths: list[str]
    reference_paths: list[str]
    deprecated_paths: list[str]
    missing_required_paths: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class CanonAssessment:
    sources_checked: list[str]
    chris_sources_checked: list[str]
    warnings: list[str]
    truth_warnings: list[str]
    non_canon_references: list[str]
    stale_override_references: list[str]
    unsupported_capability_claims: bool


def load_canon_registry(repo_root: str | Path) -> CanonRegistry:
    root = Path(repo_root)
    registry_path = root / "docs" / "CANON-REGISTRY.md"
    if not registry_path.exists():
        return CanonRegistry(
            registry_path=registry_path,
            exists=False,
            entries=[],
            canon_paths=[],
            reference_paths=[],
            deprecated_paths=[],
            missing_required_paths=list(CHRIS_CANON_PATHS),
            warnings=["Canon Registry is missing."],
        )

    entries: list[CanonEntry] = []
    for line in registry_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- `") or "`" not in stripped[3:]:
            continue
        path = stripped.split("`", 2)[1]
        rest = stripped.split("`", 2)[2].strip()
        level = _parse_level(rest)
        entries.append(CanonEntry(level=level, path=path, note=rest))

    canon_paths = [entry.path for entry in entries if entry.level == "canon"]
    reference_paths = [entry.path for entry in entries if entry.level == "reference"]
    deprecated_paths = [entry.path for entry in entries if entry.level == "deprecated"]
    missing_required_paths = [path for path in CHRIS_CANON_PATHS if not (root / path).exists()]
    warnings: list[str] = []
    if missing_required_paths:
        warnings.append("Chris canon is missing.")
        warnings.append("Cannot fully evaluate product fit because Chris canon is missing.")
    return CanonRegistry(
        registry_path=registry_path,
        exists=True,
        entries=entries,
        canon_paths=canon_paths,
        reference_paths=reference_paths,
        deprecated_paths=deprecated_paths,
        missing_required_paths=missing_required_paths,
        warnings=warnings,
    )


def assess_canon_usage(registry: CanonRegistry, report_text: str) -> CanonAssessment:
    sources_checked = _ordered_sources_checked(registry)
    chris_sources_checked = list(CHRIS_CANON_PATHS)
    warnings = list(registry.warnings)
    non_canon_references = _detect_non_canon_binding_references(registry, report_text)
    stale_override_references = _detect_stale_override_references(registry, report_text)
    truth_warnings = _detect_product_drift_warnings(report_text)
    unsupported_capability_claims = _has_unsupported_capability_claims(report_text, truth_warnings)
    warnings.extend(truth_warnings)
    if non_canon_references:
        warnings.append("Non-canon docs are referenced as binding.")
    if stale_override_references:
        warnings.append("Stale docs appear to override active phase gates.")
    if unsupported_capability_claims:
        warnings.append("Build Office makes capability claims without proof.")
    return CanonAssessment(
        sources_checked=sources_checked,
        chris_sources_checked=chris_sources_checked,
        warnings=_dedupe(warnings),
        truth_warnings=_dedupe(truth_warnings),
        non_canon_references=non_canon_references,
        stale_override_references=stale_override_references,
        unsupported_capability_claims=unsupported_capability_claims,
    )


def _ordered_sources_checked(registry: CanonRegistry) -> list[str]:
    preferred = [
        "docs/CANON-REGISTRY.md",
        "docs/PHASE-GATES.md",
        "docs/ARCHITECTURE-OFFICE-PROTOCOL.md",
        "docs/BUILD-OFFICE-PROTOCOL.md",
    ]
    return [path for path in preferred if path == "docs/CANON-REGISTRY.md" or path in registry.canon_paths]


def _detect_non_canon_binding_references(registry: CanonRegistry, report_text: str) -> list[str]:
    lowered = report_text.lower()
    hits: list[str] = []
    for path in registry.reference_paths + registry.deprecated_paths:
        name = Path(path).name.lower()
        if name in lowered and any(hint in lowered for hint in BINDING_HINTS):
            hits.append(path)
    return _dedupe(hits)


def _detect_stale_override_references(registry: CanonRegistry, report_text: str) -> list[str]:
    lowered = report_text.lower()
    hits: list[str] = []
    override_hints = BINDING_HINTS + ("override", "phase gate", "phase gates")
    for path in registry.deprecated_paths:
        name = Path(path).name.lower()
        if name in lowered and any(hint in lowered for hint in override_hints):
            hits.append(path)
    return _dedupe(hits)


def _detect_product_drift_warnings(report_text: str) -> list[str]:
    lowered = report_text.lower()
    checks = {
        "therapist language risk detected.": ("your concern is valid", "let's explore what this means for you"),
        "dashboard-first behavior risk detected.": ("dashboard-first", "dashboard", "command center"),
        "fake capability language requires evidence.": ("i searched", "i found", "i opened", "i saved", "i remembered", "the agents did", "obsidian says"),
        "empty modal/workbench risk detected.": ("empty modal", "blank modal", "generic template modal"),
        "generic chatbot behavior risk detected.": ("as an ai assistant", "generic assistant", "chatbot wrapper"),
        "mystical tone risk detected.": ("mystical companion", "ooey-gooey", "spiritual presence"),
        "agent theater risk detected.": ("agent theater", "swarm of agents", "visible agents"),
        "obsidian claims without retrieval evidence risk detected.": ("obsidian says", "pulled from the vault", "vault says"),
    }
    warnings: list[str] = []
    for warning, terms in checks.items():
        if any(term in lowered for term in terms):
            warnings.append(warning)
    return warnings


def _has_unsupported_capability_claims(report_text: str, truth_warnings: list[str]) -> bool:
    lowered = report_text.lower()
    if "fake capability language requires evidence." not in truth_warnings:
        return False
    proof_markers = (
        "command:",
        "result:",
        "evidence paired: yes",
        "tests reported:",
        "runtime evidence reported:",
        "exact commands",
        "output:",
    )
    return not any(marker in lowered for marker in proof_markers)


def _parse_level(rest: str) -> str:
    lowered = rest.lower()
    if "[canon]" in lowered:
        return "canon"
    if "[reference]" in lowered:
        return "reference"
    if "[deprecated]" in lowered or "[archive]" in lowered:
        return "deprecated"
    return "reference"


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped

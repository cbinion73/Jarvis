from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PhaseRule:
    phase: str
    allowed: tuple[str, ...]
    forbidden: tuple[str, ...]
    warning_terms: tuple[str, ...]


@dataclass(frozen=True)
class PhaseEvaluation:
    phase: str
    allowed_hits: list[str]
    forbidden_hits: list[str]
    warning_hits: list[str]


COMMON_FAKE_CAPABILITY_TERMS = (
    "searched",
    "found",
    "opened",
    "saved",
    "remembered",
    "created",
    "agents did",
    "obsidian says",
    "i pulled from the vault",
)


PHASE_RULES: dict[str, PhaseRule] = {
    "phase-0a-runtime-health": PhaseRule(
        phase="phase-0a-runtime-health",
        allowed=(
            "runtime health",
            "bounded log reading",
            "cloud-light mode",
            "ollama gating",
            "repo cleanup",
            "smoke validation",
        ),
        forbidden=(
            "conversation behavior changes",
            "obsidian live integration",
            "monday code merge",
            "health feature work",
            "ui redesign",
            "agents/autonomy expansion",
        ),
        warning_terms=COMMON_FAKE_CAPABILITY_TERMS,
    ),
    "phase-1-companion-spine": PhaseRule(
        phase="phase-1-companion-spine",
        allowed=(
            "primary conversation spine",
            "context packet",
            "friend-with-tools voice standard",
            "truth constraints",
            "model-led conversation path",
            "tests for primary spine",
        ),
        forbidden=(
            "obsidian integration",
            "health feature work",
            "agent expansion",
            "agent/autonomy expansion",
            "ui redesign",
            "monday code merge",
            "local data format migration",
            "dashboard/module expansion",
            "data migration",
        ),
        warning_terms=COMMON_FAKE_CAPABILITY_TERMS
        + (
            "obsidian integration",
            "health feature",
            "monday code",
        ),
    ),
    "phase-2-voice-correction": PhaseRule(
        phase="phase-2-voice-correction",
        allowed=(
            "friend-not-therapist voice gate",
            "depth control",
            "pushback rules",
            "response anti-pattern tests",
        ),
        forbidden=(
            "obsidian integration",
            "new tools",
            "agents",
            "ui redesign",
            "data migrations",
        ),
        warning_terms=COMMON_FAKE_CAPABILITY_TERMS,
    ),
    "phase-3-obsidian-memory-grounding": PhaseRule(
        phase="phase-3-obsidian-memory-grounding",
        allowed=(
            "obsidian vault indexing",
            "retrieval",
            "compact context injection",
            "source distinction",
        ),
        forbidden=(
            "fake obsidian claims",
            "destructive vault writes",
            "loading entire vault into memory",
            "copying vault into repo",
        ),
        warning_terms=COMMON_FAKE_CAPABILITY_TERMS,
    ),
}


def get_phase_rule(phase: str) -> PhaseRule:
    try:
        return PHASE_RULES[phase]
    except KeyError as exc:
        known = ", ".join(sorted(PHASE_RULES))
        raise ValueError(f"Unknown phase '{phase}'. Known phases: {known}") from exc


def evaluate_phase_scope(phase: str, texts: Iterable[str]) -> PhaseEvaluation:
    rule = get_phase_rule(phase)
    haystack = "\n".join(texts).lower()
    return PhaseEvaluation(
        phase=phase,
        allowed_hits=_find_hits(rule.allowed, haystack),
        forbidden_hits=_find_hits(rule.forbidden, haystack),
        warning_hits=_find_hits(rule.warning_terms, haystack),
    )


def _find_hits(terms: Iterable[str], haystack: str) -> list[str]:
    hits: list[str] = []
    for term in terms:
        if term.lower() in haystack and term not in hits:
            hits.append(term)
    return hits

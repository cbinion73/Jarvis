"""M2: Decision citation — explains WHY JARVIS made a recommendation.

Each recorded decision captures:
- The recommendation made
- The constitutional principle(s) it rests on
- Authority basis (which trust zone / agent made it)
- Uncertainty level (low/medium/high)
- Override path (what Chris must do to reverse it)

Produced by any JARVIS agent; surfaced via cite_decision() for household review.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_CITATION_ROOT = Path("data/decisions")

UNCERTAINTY_LEVELS = frozenset({"low", "medium", "high"})
AUTHORITY_BASES = frozenset({"observe", "draft", "stage_alert", "sandbox_live", "mature_live", "human_override"})


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(slots=True)
class DecisionCitation:
    """A recorded JARVIS decision with full citation for household review."""
    citation_id: str
    actor: str                       # JARVIS agent or human who made this
    recommendation: str              # What was recommended (plain language)
    rationale: str                   # Why (plain language, household-readable)
    principles: list[str]            # Constitutional principles cited
    authority_basis: str             # Trust zone authority stage
    uncertainty: str                 # low/medium/high
    override_path: str               # How Chris can reverse this
    domain: str                      # health/family/work/faith/finance/etc.
    created_at: str
    reviewed_at: str = ""
    reviewed_by: str = ""
    outcome: str = ""                # what actually happened
    source: str = "decision_citation"
    labels: list[str] = field(default_factory=list)


class DecisionCitationStore:
    """Durable store for decision citations — the 'why' behind JARVIS recommendations."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _CITATION_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.citations_path = self.root / "citations.json"
        self.log_path = self.root / "citations_log.jsonl"

    def _load(self) -> list[dict]:
        if not self.citations_path.exists():
            return []
        try:
            data = json.loads(self.citations_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.citations_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.citations_path, records)

    def record(
        self,
        *,
        actor: str,
        recommendation: str,
        rationale: str,
        principles: list[str],
        authority_basis: str = "observe",
        uncertainty: str = "medium",
        override_path: str = "Tell JARVIS to reconsider, or make the decision yourself.",
        domain: str = "general",
        labels: list[str] | None = None,
    ) -> DecisionCitation:
        if uncertainty not in UNCERTAINTY_LEVELS:
            raise ValueError(f"uncertainty must be one of {sorted(UNCERTAINTY_LEVELS)}")
        citation = DecisionCitation(
            citation_id=str(uuid.uuid4()),
            actor=actor,
            recommendation=recommendation.strip(),
            rationale=rationale.strip(),
            principles=principles,
            authority_basis=authority_basis,
            uncertainty=uncertainty,
            override_path=override_path.strip(),
            domain=domain,
            created_at=_ts(),
            labels=labels or [],
        )
        records = self._load()
        records.append(asdict(citation))
        self._save(records)
        try:
            append_jsonl(self.log_path, asdict(citation))
        except Exception:
            pass
        return citation

    def cite(self, citation_id: str) -> dict | None:
        """Return a single citation by ID — the 'why' surface for household review."""
        for r in self._load():
            if r.get("citation_id") == citation_id:
                return self._render(r)
        return None

    def _render(self, r: dict) -> dict:
        """Return a household-readable representation of a citation."""
        uncertainty_plain = {
            "low": "JARVIS is fairly confident about this.",
            "medium": "JARVIS thinks this is right but you may see it differently.",
            "high": "JARVIS is less certain — treat this as a suggestion to consider.",
        }.get(r.get("uncertainty", "medium"), "")
        return {
            **r,
            "plain_summary": (
                f"JARVIS recommended: {r.get('recommendation', '')}.\n"
                f"Why: {r.get('rationale', '')}.\n"
                f"Confidence: {uncertainty_plain}\n"
                f"To reverse: {r.get('override_path', '')}"
            ),
        }

    def list_recent(
        self,
        actor: str | None = None,
        domain: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        records = self._load()
        if actor:
            records = [r for r in records if r.get("actor") == actor]
        if domain:
            records = [r for r in records if r.get("domain") == domain]
        return [self._render(r) for r in records[-limit:]]

    def record_outcome(self, citation_id: str, reviewed_by: str, outcome: str) -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("citation_id") == citation_id:
                r["reviewed_at"] = _ts()
                r["reviewed_by"] = reviewed_by
                r["outcome"] = outcome
                updated = r
                break
        if updated:
            self._save(records)
        return updated

"""F1: Runtime constitution engine.

Encodes JARVIS-CONSTITUTION-FOR-SELF-IMPROVING-INTELLIGENCE into runtime
decision citations so every significant recommendation cites:
- Applicable constitutional principle
- Authority basis (trust zone, stage, delegation)
- Uncertainty level
- Override path (what would change JARVIS's recommendation)

This module wraps decisions rather than replacing existing governance.
Existing policy_rails.py handles action-boundary checks; this module
adds the constitutional citation layer to significant recommendations.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .persistence import append_jsonl

_CONSTITUTION_AUDIT_PATH = Path("data/constitution/decision_audit.jsonl")


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Constitutional principles (Article III of the JARVIS Constitution)
# ---------------------------------------------------------------------------

CONSTITUTIONAL_PRINCIPLES: dict[str, dict[str, str]] = {
    "III.1.mandate_first": {
        "article": "Article III, Clause 1",
        "title": "Mandate First",
        "text": "JARVIS should default toward helpful initiative, not caution theater, when acting inside a lawful trust zone.",
        "implication": "Proceed unless a hard boundary applies. Do not invent friction.",
    },
    "III.2.boundary_clarity": {
        "article": "Article III, Clause 2",
        "title": "Boundary Clarity",
        "text": "Safety comes from clear resource boundaries and authority envelopes, not universal pre-action permissioning.",
        "implication": "Trust zone + authority stage defines what is safe. Check zone, not intuition.",
    },
    "III.3.legible_agency": {
        "article": "Article III, Clause 3",
        "title": "Legible Agency",
        "text": "JARVIS shall make its reasoning and actions reviewable by human principals.",
        "implication": "Explain the basis for every significant recommendation.",
    },
    "III.4.segmented_delegation": {
        "article": "Article III, Clause 4",
        "title": "Segmented Delegated Agency",
        "text": "Authority is segmented by domain, time, and resource boundary.",
        "implication": "Do not treat authority in one arena as authority in another.",
    },
    "III.5.review_after_action": {
        "article": "Article III, Clause 5",
        "title": "Review After Action",
        "text": "JARVIS shall enable review after action where pre-approval would be impractical.",
        "implication": "Log what was done. Make it inspectable. Offer correction paths.",
    },
    "III.6.trust_earns_promotion": {
        "article": "Article III, Clause 6",
        "title": "Trust Earns Promotion",
        "text": "JARVIS authority expands through demonstrated reliability, not assertion.",
        "implication": "Do not act beyond current authority stage. Request promotion through evidence.",
    },
    "III.7.safe_degradation": {
        "article": "Article III, Clause 7",
        "title": "Safe Degradation",
        "text": "JARVIS shall fail safely when uncertain, using the most conservative option available.",
        "implication": "When the safe path is unknown, do less and escalate to human principal.",
    },
    "VI.hard_escalation": {
        "article": "Article VI",
        "title": "Hard Escalation Lines",
        "text": "Certain actions may never be taken without explicit human-principal authorization regardless of trust zone.",
        "implication": "Money, identity, legal, public reputation, physical security, and children require explicit authority.",
    },
    "II.2.broad_delegation": {
        "article": "Article II, Clause 2",
        "title": "Broad Delegated Agency",
        "text": "Within lawful zones, JARVIS has broad delegated authority to observe, infer, plan, draft, organize, coordinate, build, and improve.",
        "implication": "Inside the zone, act with initiative. Outside the zone, escalate.",
    },
    "II.4.mission_priority": {
        "article": "Article II, Clause 4",
        "title": "Mission Priority",
        "text": "JARVIS may not place its own growth or internal neatness above the legitimate best interests of the family.",
        "implication": "Optimize for family flourishing, not JARVIS capability accumulation.",
    },
}

# ---------------------------------------------------------------------------
# Authority basis descriptors
# ---------------------------------------------------------------------------

AUTHORITY_STAGES = {
    "monitor": "Observer only — no writes, no external actions.",
    "suggest": "Suggestions surfaced for human decision — no autonomous execution.",
    "sandbox": "Sandbox execution in ring-fenced environment — no live effects.",
    "sandbox_live": "Live effects within bounded arena — reviewed post-action.",
    "live": "Full delegated authority within trust zone and resource scope.",
}

UNCERTAINTY_LEVELS = ("none", "low", "moderate", "high", "blocking")


# ---------------------------------------------------------------------------
# Constitutional decision record
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ConstitutionalCitation:
    """A constitutional citation for a significant recommendation."""
    decision_id: str
    actor: str
    recommendation_summary: str        # one sentence
    principle_ids: list[str]           # which principles apply
    authority_basis: str               # trust zone + stage description
    authority_stage: str               # current authority stage
    uncertainty_level: str             # none/low/moderate/high/blocking
    uncertainty_explanation: str       # what is uncertain and why
    override_path: str                 # what would change this recommendation
    dissent: str                       # what a reasonable dissent would say
    created_at: str
    source: str = "constitution_engine"


@dataclass
class SignificantRecommendation:
    """A recommendation with constitutional backing."""
    recommendation_id: str
    summary: str
    detail: str
    actor: str
    domain: str
    citation: ConstitutionalCitation
    recommended_action: str
    alternative_actions: list[dict]    # [{action, tradeoff}]
    confidence: float                  # 0.0–1.0
    created_at: str
    source: str = "constitution_engine"

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Constitution engine
# ---------------------------------------------------------------------------

class ConstitutionEngine:
    """Wraps decisions with constitutional citations.

    Usage:
        engine = ConstitutionEngine()
        rec = engine.make_recommendation(
            actor="chris",
            summary="Consolidate three active task lanes into one sprint",
            detail="...",
            domain="work",
            principle_ids=["III.1.mandate_first", "II.2.broad_delegation"],
            authority_stage="sandbox_live",
            uncertainty_level="moderate",
            uncertainty_explanation="Calendar data not yet synced",
            override_path="If deadline moved to Q4, recommendation changes to defer",
            dissent="An alternative view would argue parallelism is worth the overhead",
            recommended_action="Consolidate lanes into unified sprint board",
            alternative_actions=[
                {"action": "Defer all three", "tradeoff": "Loses momentum on active project"},
            ],
            confidence=0.72,
        )
    """

    def __init__(self, audit_path: Path | None = None) -> None:
        self.audit_path = audit_path or _CONSTITUTION_AUDIT_PATH
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def _validate_principle_ids(self, principle_ids: list[str]) -> list[str]:
        valid = [p for p in principle_ids if p in CONSTITUTIONAL_PRINCIPLES]
        return valid if valid else ["III.3.legible_agency"]

    def get_principle(self, principle_id: str) -> dict[str, str]:
        return CONSTITUTIONAL_PRINCIPLES.get(principle_id, {
            "article": "Unknown",
            "title": "Unknown principle",
            "text": f"Principle {principle_id!r} not found in constitution.",
            "implication": "Cite a known principle.",
        })

    def cite(
        self,
        *,
        decision_id: str,
        actor: str,
        recommendation_summary: str,
        principle_ids: list[str] | None = None,
        authority_stage: str = "sandbox_live",
        uncertainty_level: str = "moderate",
        uncertainty_explanation: str = "",
        override_path: str = "",
        dissent: str = "",
    ) -> ConstitutionalCitation:
        """Create a constitutional citation for a decision."""
        import uuid
        valid_ids = self._validate_principle_ids(principle_ids or ["III.3.legible_agency"])
        stage_desc = AUTHORITY_STAGES.get(authority_stage, f"Unknown stage: {authority_stage}")

        citation = ConstitutionalCitation(
            decision_id=decision_id or str(uuid.uuid4()),
            actor=actor,
            recommendation_summary=recommendation_summary,
            principle_ids=valid_ids,
            authority_basis=stage_desc,
            authority_stage=authority_stage,
            uncertainty_level=uncertainty_level,
            uncertainty_explanation=uncertainty_explanation,
            override_path=override_path,
            dissent=dissent,
            created_at=_ts(),
        )
        self._audit_citation(citation)
        return citation

    def make_recommendation(
        self,
        *,
        actor: str,
        summary: str,
        detail: str,
        domain: str,
        principle_ids: list[str] | None = None,
        authority_stage: str = "sandbox_live",
        uncertainty_level: str = "moderate",
        uncertainty_explanation: str = "",
        override_path: str = "",
        dissent: str = "",
        recommended_action: str = "",
        alternative_actions: list[dict] | None = None,
        confidence: float = 0.75,
    ) -> SignificantRecommendation:
        """Build a significant recommendation with constitutional backing."""
        import uuid
        rec_id = str(uuid.uuid4())
        citation = self.cite(
            decision_id=rec_id,
            actor=actor,
            recommendation_summary=summary,
            principle_ids=principle_ids,
            authority_stage=authority_stage,
            uncertainty_level=uncertainty_level,
            uncertainty_explanation=uncertainty_explanation,
            override_path=override_path,
            dissent=dissent,
        )
        confidence = max(0.0, min(1.0, float(confidence)))
        return SignificantRecommendation(
            recommendation_id=rec_id,
            summary=summary,
            detail=detail,
            actor=actor,
            domain=domain,
            citation=citation,
            recommended_action=recommended_action or summary,
            alternative_actions=alternative_actions or [],
            confidence=confidence,
            created_at=_ts(),
        )

    def _audit_citation(self, citation: ConstitutionalCitation) -> None:
        try:
            append_jsonl(self.audit_path, asdict(citation))
        except Exception:
            pass

    def principle_reference_card(self) -> dict[str, Any]:
        """Return a reference card of all constitutional principles."""
        return {
            "source": "JARVIS-CONSTITUTION-FOR-SELF-IMPROVING-INTELLIGENCE.md",
            "principle_count": len(CONSTITUTIONAL_PRINCIPLES),
            "principles": {
                pid: {
                    "article": p["article"],
                    "title": p["title"],
                    "implication": p["implication"],
                }
                for pid, p in CONSTITUTIONAL_PRINCIPLES.items()
            },
            "authority_stages": AUTHORITY_STAGES,
            "uncertainty_levels": list(UNCERTAINTY_LEVELS),
        }

    def wrap_decision(
        self,
        decision: dict[str, Any],
        *,
        actor: str,
        principle_ids: list[str] | None = None,
        authority_stage: str = "sandbox_live",
        uncertainty_level: str = "low",
        override_path: str = "",
    ) -> dict[str, Any]:
        """Add constitutional citation wrapper to any existing decision dict."""
        import uuid
        principles = self._validate_principle_ids(principle_ids or ["III.3.legible_agency"])
        citation = {
            "principle_ids": principles,
            "principles": [
                {"id": pid, "article": CONSTITUTIONAL_PRINCIPLES[pid]["article"],
                 "title": CONSTITUTIONAL_PRINCIPLES[pid]["title"]}
                for pid in principles
            ],
            "authority_stage": authority_stage,
            "authority_basis": AUTHORITY_STAGES.get(authority_stage, ""),
            "uncertainty_level": uncertainty_level,
            "override_path": override_path,
            "constitution_source": "JARVIS-CONSTITUTION-FOR-SELF-IMPROVING-INTELLIGENCE.md",
        }
        return {
            **decision,
            "constitutional_citation": citation,
            "decision_id": str(uuid.uuid4()),
            "cited_at": _ts(),
        }

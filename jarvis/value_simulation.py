"""F3: Value simulation — multi-dimensional decision tradeoff analyzer.

Simulates decisions across:
- time (short-term vs long-term)
- money (immediate cost vs future value)
- health (physical, mental, stress impact)
- faith (alignment with values and calling)
- family (impact on relationships and household)
- risk (probability and severity of negative outcomes)
- opportunity (doors this opens or closes)
- reputation (professional and community standing)
- long-term effects (5-10 year horizon)

Output: comparison of options with recommendation, dissent, uncertainty,
and what would change JARVIS's mind.

This module does NOT call LLMs — it provides the structural scaffolding
for value simulation. Actual LLM synthesis happens at the service layer.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_VS_ROOT = Path("data/value_simulation")
_SIMULATIONS_PATH = _VS_ROOT / "simulations.json"
_SIMULATIONS_LOG = _VS_ROOT / "simulations_log.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Value dimensions
# ---------------------------------------------------------------------------

VALUE_DIMENSIONS = [
    "time",         # short-term vs long-term time investment
    "money",        # financial cost/gain
    "health",       # physical, mental, emotional health impact
    "faith",        # alignment with values and calling
    "family",       # impact on relationships and household
    "risk",         # probability × severity of negative outcomes
    "opportunity",  # doors opened or closed
    "reputation",   # professional and community standing
    "long_term",    # 5-10 year horizon effect
]


@dataclass(slots=True)
class DimensionScore:
    """Score for one value dimension for one option."""
    dimension: str
    score: float         # -1.0 (strongly negative) to +1.0 (strongly positive)
    explanation: str     # why this score
    confidence: float    # 0.0–1.0 confidence in this assessment
    time_horizon: str    # immediate / 1-year / 5-year / 10-year


@dataclass(slots=True)
class SimulatedOption:
    """One option being compared in a value simulation."""
    option_id: str
    label: str
    description: str
    dimension_scores: list[dict]         # list of DimensionScore dicts
    total_score: float                   # weighted sum
    recommendation_strength: str         # strong / moderate / weak / neutral / against
    summary: str                         # one-sentence summary


@dataclass(slots=True)
class ValueSimulation:
    """A complete value simulation comparing multiple options."""
    simulation_id: str
    actor: str
    question: str                        # the decision being analyzed
    context: str                         # relevant context
    options: list[dict]                  # list of SimulatedOption dicts
    recommended_option_id: str
    recommendation_summary: str
    dissent: str                         # what a reasonable dissent says
    uncertainty: str                     # what we don't know
    what_would_change_recommendation: str
    confidence: float
    created_at: str
    domain: str = "general"
    source: str = "value_simulation"


# Default dimension weights (can be overridden per simulation)
DEFAULT_WEIGHTS: dict[str, float] = {
    "time":        0.12,
    "money":       0.12,
    "health":      0.18,
    "faith":       0.15,
    "family":      0.15,
    "risk":        0.12,
    "opportunity": 0.08,
    "reputation":  0.04,
    "long_term":   0.04,
}

RECOMMENDATION_THRESHOLDS = {
    "strong":   0.6,
    "moderate": 0.3,
    "weak":     0.1,
    "neutral":  0.0,
}


def _compute_recommendation_strength(score: float) -> str:
    if score >= RECOMMENDATION_THRESHOLDS["strong"]:
        return "strong"
    if score >= RECOMMENDATION_THRESHOLDS["moderate"]:
        return "moderate"
    if score >= RECOMMENDATION_THRESHOLDS["weak"]:
        return "weak"
    if score >= 0:
        return "neutral"
    return "against"


class ValueSimulationEngine:
    """Builds and persists value simulations."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _VS_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.simulations_path = self.root / "simulations.json"
        self.log_path = self.root / "simulations_log.jsonl"

    def _load(self) -> list[dict]:
        if not self.simulations_path.exists():
            return []
        try:
            import json
            data = json.loads(self.simulations_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.simulations_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.simulations_path, records)

    def score_option(
        self,
        *,
        option_id: str,
        label: str,
        description: str,
        dimension_inputs: dict[str, dict],  # {dimension: {score, explanation, confidence, time_horizon}}
        weights: dict[str, float] | None = None,
    ) -> SimulatedOption:
        """Build a scored SimulatedOption from raw dimension inputs."""
        w = weights or DEFAULT_WEIGHTS
        scores: list[DimensionScore] = []
        weighted_total = 0.0
        weight_sum = 0.0

        for dim in VALUE_DIMENSIONS:
            inp = dimension_inputs.get(dim, {})
            score_val = float(inp.get("score", 0.0))
            score_val = max(-1.0, min(1.0, score_val))
            confidence = float(inp.get("confidence", 0.5))
            ds = DimensionScore(
                dimension=dim,
                score=score_val,
                explanation=str(inp.get("explanation", "")),
                confidence=confidence,
                time_horizon=str(inp.get("time_horizon", "immediate")),
            )
            scores.append(ds)
            dim_weight = w.get(dim, 0.0)
            weighted_total += score_val * dim_weight * confidence
            weight_sum += dim_weight * confidence

        total = weighted_total / weight_sum if weight_sum > 0 else 0.0
        strength = _compute_recommendation_strength(total)

        return SimulatedOption(
            option_id=option_id,
            label=label,
            description=description,
            dimension_scores=[asdict(ds) for ds in scores],
            total_score=round(total, 3),
            recommendation_strength=strength,
            summary=(
                f"'{label}' scores {total:+.2f} overall "
                f"({strength} {'recommendation' if total >= 0 else 'against'})"
            ),
        )

    def simulate(
        self,
        *,
        actor: str,
        question: str,
        context: str = "",
        domain: str = "general",
        options: list[SimulatedOption],
        dissent: str = "",
        uncertainty: str = "",
        what_would_change_recommendation: str = "",
        confidence: float = 0.7,
        weights: dict[str, float] | None = None,
    ) -> ValueSimulation:
        """Run a full value simulation comparing multiple options."""
        if not options:
            raise ValueError("At least one option is required")

        sorted_opts = sorted(options, key=lambda o: o.total_score, reverse=True)
        best = sorted_opts[0]

        # Summarize the recommendation
        if len(sorted_opts) == 1:
            rec_summary = f"Only option is '{best.label}' (score: {best.total_score:+.2f})."
        else:
            second = sorted_opts[1]
            gap = best.total_score - second.total_score
            rec_summary = (
                f"Recommend '{best.label}' over '{second.label}' "
                f"(margin: {gap:+.2f}). "
                f"Strength: {best.recommendation_strength}."
            )

        simulation = ValueSimulation(
            simulation_id=str(uuid.uuid4()),
            actor=actor,
            question=question,
            context=context,
            options=[asdict(o) for o in options],
            recommended_option_id=best.option_id,
            recommendation_summary=rec_summary,
            dissent=dissent,
            uncertainty=uncertainty,
            what_would_change_recommendation=what_would_change_recommendation,
            confidence=max(0.0, min(1.0, float(confidence))),
            created_at=_ts(),
            domain=domain,
        )

        records = self._load()
        records.append(asdict(simulation))
        self._save(records)
        try:
            append_jsonl(self.log_path, asdict(simulation))
        except Exception:
            pass

        return simulation

    def get(self, simulation_id: str) -> dict | None:
        for r in self._load():
            if r.get("simulation_id") == simulation_id:
                return r
        return None

    def list_recent(self, actor: str, limit: int = 20) -> list[dict]:
        records = [r for r in self._load() if r.get("actor") == actor]
        return records[-limit:]

    def compare_summary(self, simulation_id: str) -> dict[str, Any]:
        """Return a human-readable comparison summary for a simulation."""
        sim = self.get(simulation_id)
        if not sim:
            return {"error": "simulation not found", "simulation_id": simulation_id}

        options = sim.get("options", [])
        return {
            "simulation_id": simulation_id,
            "question": sim.get("question"),
            "recommended": sim.get("recommended_option_id"),
            "recommendation_summary": sim.get("recommendation_summary"),
            "dissent": sim.get("dissent"),
            "uncertainty": sim.get("uncertainty"),
            "what_would_change_recommendation": sim.get("what_would_change_recommendation"),
            "confidence": sim.get("confidence"),
            "options_ranked": [
                {
                    "option_id": o.get("option_id"),
                    "label": o.get("label"),
                    "total_score": o.get("total_score"),
                    "recommendation_strength": o.get("recommendation_strength"),
                }
                for o in sorted(options, key=lambda x: x.get("total_score", 0), reverse=True)
            ],
            "dimension_weights": DEFAULT_WEIGHTS,
            "source": "value_simulation",
        }

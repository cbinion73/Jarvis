"""M3: Value-simulation comparison — ranks options against JARVIS constitutional values.

Allows Chris (or any household member) to compare choices against the shared
doctrine values (family, faith, health, financial stewardship, etc.).

Each simulation:
- Scores each option against each value dimension
- Surfaces dissent (where a value scores an option lower than intuition might)
- Provides a "change my mind" path — what would need to be true for rank to change
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_SIMULATOR_ROOT = Path("data/simulations")

VALUE_DIMENSIONS = (
    "family_impact",
    "faith_alignment",
    "health_impact",
    "financial_stewardship",
    "time_cost",
    "reversibility",
    "household_harmony",
)


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(slots=True)
class SimulationOption:
    """A single option in a value simulation."""
    option_id: str
    label: str                              # Short human label
    description: str                        # What this option entails
    scores: dict[str, float]                # value_dimension → [-1.0, 1.0]
    weighted_score: float                   # final weighted rank score
    dissents: list[str]                     # dimensions that scored it low
    change_my_mind: str                     # what would flip this to higher
    rank: int = 0


@dataclass(slots=True)
class ValueSimulation:
    """A full value-simulation comparison across a set of options."""
    simulation_id: str
    actor: str
    question: str                           # what decision is being compared
    context: str                            # situation context
    options: list[dict]                     # list of SimulationOption dicts
    recommended_option_id: str              # highest-ranked option
    dissent_summary: str                    # plain-language dissent notes
    created_at: str
    domain: str = "general"
    source: str = "value_simulation"


DEFAULT_WEIGHTS: dict[str, float] = {
    "family_impact": 0.25,
    "faith_alignment": 0.20,
    "health_impact": 0.15,
    "financial_stewardship": 0.15,
    "time_cost": 0.10,
    "reversibility": 0.10,
    "household_harmony": 0.05,
}


def score_option(
    option_label: str,
    option_description: str,
    raw_scores: dict[str, float],
    weights: dict[str, float] | None = None,
) -> SimulationOption:
    """Score a single option against value dimensions.

    raw_scores: {dimension: float in [-1.0, 1.0]}
    Missing dimensions default to 0.0 (neutral).
    """
    w = weights or DEFAULT_WEIGHTS
    total_weight = sum(w.get(d, 0.0) for d in VALUE_DIMENSIONS)
    weighted = sum(
        raw_scores.get(d, 0.0) * w.get(d, 0.0)
        for d in VALUE_DIMENSIONS
    )
    final_score = weighted / total_weight if total_weight > 0 else 0.0

    dissents = [
        d for d in VALUE_DIMENSIONS
        if raw_scores.get(d, 0.0) < -0.2
    ]

    change_my_mind_parts = []
    for d in dissents:
        score = raw_scores.get(d, 0.0)
        change_my_mind_parts.append(
            f"If {d.replace('_', ' ')} were less impacted (currently {score:.2f}), this option would rank higher."
        )
    change_my_mind = (
        " ".join(change_my_mind_parts)
        if change_my_mind_parts
        else "This option is already strong — no obvious flip condition."
    )

    return SimulationOption(
        option_id=str(uuid.uuid4()),
        label=option_label,
        description=option_description,
        scores={d: raw_scores.get(d, 0.0) for d in VALUE_DIMENSIONS},
        weighted_score=round(final_score, 4),
        dissents=dissents,
        change_my_mind=change_my_mind,
    )


class ValueSimulator:
    """Runs value-simulation comparisons and persists them for review."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _SIMULATOR_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.sims_path = self.root / "simulations.json"
        self.log_path = self.root / "simulations_log.jsonl"

    def _load(self) -> list[dict]:
        if not self.sims_path.exists():
            return []
        try:
            data = json.loads(self.sims_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.sims_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.sims_path, records)

    def compare(
        self,
        *,
        actor: str,
        question: str,
        context: str = "",
        options: list[dict],
        weights: dict[str, float] | None = None,
        domain: str = "general",
    ) -> ValueSimulation:
        """Score and rank all options, identify recommended choice, surface dissent.

        options: list of {label, description, scores: {dimension: float}}
        Returns a persisted ValueSimulation.
        """
        if not options:
            raise ValueError("at least one option is required")

        scored: list[SimulationOption] = []
        for opt in options:
            so = score_option(
                option_label=opt.get("label", "Option"),
                option_description=opt.get("description", ""),
                raw_scores=opt.get("scores", {}),
                weights=weights,
            )
            scored.append(so)

        # Rank by weighted_score descending
        scored.sort(key=lambda x: x.weighted_score, reverse=True)
        for rank, opt in enumerate(scored, 1):
            opt.rank = rank

        recommended = scored[0].option_id if scored else ""

        # Collect all dissents into a summary
        all_dissents: list[str] = []
        for opt in scored:
            for dim in opt.dissents:
                all_dissents.append(
                    f"'{opt.label}' scores low on {dim.replace('_', ' ')} ({opt.scores.get(dim, 0):.2f})"
                )
        dissent_summary = (
            "Dissents: " + "; ".join(all_dissents[:5])
            if all_dissents
            else "No strong dissents found — all values are reasonably aligned."
        )

        sim = ValueSimulation(
            simulation_id=str(uuid.uuid4()),
            actor=actor,
            question=question.strip(),
            context=context.strip(),
            options=[asdict(s) for s in scored],
            recommended_option_id=recommended,
            dissent_summary=dissent_summary,
            created_at=_ts(),
            domain=domain,
        )
        records = self._load()
        records.append(asdict(sim))
        self._save(records)
        try:
            append_jsonl(self.log_path, asdict(sim))
        except Exception:
            pass
        return sim

    def get(self, simulation_id: str) -> dict | None:
        for r in self._load():
            if r.get("simulation_id") == simulation_id:
                return r
        return None

    def list_recent(self, actor: str | None = None, limit: int = 10) -> list[dict]:
        records = self._load()
        if actor:
            records = [r for r in records if r.get("actor") == actor]
        return records[-limit:]

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
import uuid

from .models import PromotionClaim, PromotionThreshold, PromotionVerdict


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class PromotionEngine:
    def threshold_from_stage(self, stage: dict[str, Any] | None) -> PromotionThreshold:
        criteria = dict((stage or {}).get("promotion_criteria") or {})
        stage_id = str((stage or {}).get("stage_id") or "").strip().lower()
        return PromotionThreshold(
            min_runs=max(0, int(criteria.get("minimum_review_count", 0) or 0)),
            min_success=max(0.0, min(1.0, float(criteria.get("minimum_success_rate", 0.0) or 0.0))),
            max_boundary_violations=max(0, int(criteria.get("maximum_boundary_violations", 0) or 0)),
            requires_human_consent=stage_id == "mature_live",
        )

    def new_claim(
        self,
        *,
        subject_kind: str,
        subject_id: str,
        current_stage: str,
        target_stage: str,
        actor: str,
        basis: str = "",
        trust_zone: str = "",
        arena_id: str = "",
        human_consent: bool = False,
        evidence_summary: dict[str, object] | None = None,
    ) -> PromotionClaim:
        return PromotionClaim(
            claim_id=f"claim-{uuid.uuid4().hex[:12]}",
            subject_kind=subject_kind,
            subject_id=subject_id,
            current_stage=current_stage,
            target_stage=target_stage,
            actor=actor,
            basis=basis,
            trust_zone=trust_zone,
            arena_id=arena_id,
            human_consent=human_consent,
            submitted_at=_now_iso(),
            evidence_summary=dict(evidence_summary or {}),
        )

    def evaluate_claim(
        self,
        claim: PromotionClaim,
        reviews: list[dict[str, Any]],
        *,
        threshold: PromotionThreshold,
    ) -> PromotionVerdict:
        normalized = [dict(item) for item in reviews if isinstance(item, dict)]
        approved = [
            item for item in normalized
            if str(item.get("outcome", "")).strip().lower() == "approved"
        ]
        clean_successes = [item for item in approved if not bool(item.get("rollback_executed"))]
        rejected = [
            item for item in normalized
            if str(item.get("outcome", "")).strip().lower() in {"rejected", "denied", "forbidden"}
        ]
        rollbacks = [item for item in normalized if bool(item.get("rollback_executed"))]
        doctrine_ready = [item for item in approved if bool(item.get("doctrine_ready"))]
        boundary_violations = len(rejected) + len(rollbacks)
        total_reviews = len(normalized)
        success_rate = (len(clean_successes) / total_reviews) if total_reviews else 0.0
        metrics = {
            "total_reviews": total_reviews,
            "approved_reviews": len(approved),
            "clean_successes": len(clean_successes),
            "doctrine_ready_reviews": len(doctrine_ready),
            "rejected_reviews": len(rejected),
            "rollback_count": len(rollbacks),
            "boundary_violations": boundary_violations,
            "success_rate": round(success_rate, 4),
        }

        decision = "hold"
        reason = "Promotion evidence is not yet sufficient."
        if threshold.max_boundary_violations >= 0 and boundary_violations > threshold.max_boundary_violations:
            decision = "suspend" if claim.current_stage == "mature_live" else "hold"
            reason = (
                f"Boundary violations ({boundary_violations}) exceed the allowed maximum "
                f"({threshold.max_boundary_violations})."
            )
        elif total_reviews < threshold.min_runs:
            reason = (
                f"Only {total_reviews} reviewed runs exist; {threshold.min_runs} are required "
                "before promotion."
            )
        elif success_rate < threshold.min_success:
            reason = (
                f"Success rate {success_rate:.2%} is below the required "
                f"{threshold.min_success:.2%}."
            )
        elif threshold.requires_human_consent and not claim.human_consent:
            decision = "pending_consent"
            reason = "Promotion evidence is sufficient, but explicit human consent is still required."
        else:
            decision = "promote"
            reason = "Track record satisfies the promotion threshold."

        return PromotionVerdict(
            claim_id=claim.claim_id,
            subject_kind=claim.subject_kind,
            subject_id=claim.subject_id,
            current_stage=claim.current_stage,
            target_stage=claim.target_stage,
            decision=decision,
            reason=reason,
            threshold=threshold,
            metrics=metrics,
            trust_zone=claim.trust_zone,
            arena_id=claim.arena_id,
            human_consent_required=threshold.requires_human_consent,
            human_consent_present=claim.human_consent,
            evaluated_at=_now_iso(),
        )

    @staticmethod
    def to_dict(verdict: PromotionVerdict) -> dict[str, Any]:
        payload = asdict(verdict)
        payload["threshold"] = asdict(verdict.threshold)
        return payload

from __future__ import annotations

from .models import ActionClass, PermissionDecision, UserProfile


HIGH_RISK_KEYWORDS = {
    "unlock",
    "door",
    "garage",
    "order",
    "purchase",
    "post",
    "submit",
}
MEDIUM_RISK_KEYWORDS = {
    "send",
    "message",
    "text",
    "email",
    "calendar",
    "schedule",
}
LOW_RISK_KEYWORDS = {
    "lights",
    "light",
    "scene",
    "music",
    "playlist",
    "reminder",
}
RESTRICTED_CHILD_KEYWORDS = {
    "answer my homework",
    "write my essay",
    "do my project",
    "give me the answer",
    "solve it for me",
    "rewrite this as my final answer",
}
CHILD_BOUNDARY_KEYWORDS = {
    "thermo",
    "confidential",
    "meeting notes",
    "manuscript",
    "executive brief",
    "dad's meeting",
    "mom's message",
}


class PermissionEngine:
    def evaluate(self, actor: UserProfile, request: str) -> PermissionDecision:
        lowered = request.lower()

        if actor.permissions == "child":
            for phrase in RESTRICTED_CHILD_KEYWORDS:
                if phrase in lowered:
                    return PermissionDecision(
                        action_class=ActionClass.RESTRICTED,
                        needs_approval=False,
                        second_factor_required=False,
                        allowed=False,
                        rationale="Child tutoring mode blocks deceptive assignment completion.",
                    )
            for phrase in CHILD_BOUNDARY_KEYWORDS:
                if phrase in lowered:
                    return PermissionDecision(
                        action_class=ActionClass.RESTRICTED,
                        needs_approval=False,
                        second_factor_required=False,
                        allowed=False,
                        rationale="Child profiles may not access adult work data or parent-only household context.",
                    )

        if any(token in lowered for token in HIGH_RISK_KEYWORDS):
            return PermissionDecision(
                action_class=ActionClass.EXECUTE_HIGH_RISK,
                needs_approval=True,
                second_factor_required=True,
                allowed=True,
                rationale="Request affects physical security, commerce, or irreversible external action.",
            )

        if any(token in lowered for token in MEDIUM_RISK_KEYWORDS):
            return PermissionDecision(
                action_class=ActionClass.EXECUTE_MEDIUM_RISK,
                needs_approval=True,
                second_factor_required=False,
                allowed=True,
                rationale="Request changes shared commitments or external communication.",
            )

        if any(token in lowered for token in LOW_RISK_KEYWORDS):
            return PermissionDecision(
                action_class=ActionClass.EXECUTE_LOW_RISK,
                needs_approval=False,
                second_factor_required=False,
                allowed=True,
                rationale="Request is a normal low-risk household action.",
            )

        if any(word in lowered for word in {"draft", "prepare", "summarize", "brief"}):
            return PermissionDecision(
                action_class=ActionClass.PREPARE,
                needs_approval=False,
                second_factor_required=False,
                allowed=True,
                rationale="Request prepares work without committing an external action.",
            )

        return PermissionDecision(
            action_class=ActionClass.SUGGEST,
            needs_approval=False,
            second_factor_required=False,
            allowed=True,
            rationale="Request is advisory or informational.",
        )

from __future__ import annotations

from dataclasses import dataclass

from .canon_registry import CanonAssessment
from .git_inspector import GitInspection
from .phase_rules import PhaseEvaluation
from .report_checker import ReportCheckResult


DECISION_APPROVE = "Approve"
DECISION_REJECT = "Reject"
DECISION_PARTIAL = "Partial Approve"
DECISION_REWORK = "Needs Rework"


@dataclass(frozen=True)
class ReviewResult:
    decision: str
    next_action: str
    markdown: str


def build_review(
    *,
    phase: str,
    git: GitInspection,
    report: ReportCheckResult,
    scope: PhaseEvaluation,
    canon: CanonAssessment,
) -> ReviewResult:
    decision = determine_decision(git=git, report=report, scope=scope)
    next_action = determine_next_action(decision)
    markdown = _render_review(
        phase=phase,
        decision=decision,
        next_action=next_action,
        git=git,
        report=report,
        scope=scope,
        canon=canon,
    )
    return ReviewResult(decision=decision, next_action=next_action, markdown=markdown)


def determine_decision(*, git: GitInspection, report: ReportCheckResult, scope: PhaseEvaluation) -> str:
    if scope.forbidden_hits:
        return DECISION_REJECT if report.complete else DECISION_REWORK
    if not git.is_clean or not git.branch_matches_phase or not report.complete:
        return DECISION_REWORK
    if _missing_evidence(report.text):
        return DECISION_PARTIAL
    return DECISION_APPROVE


def determine_next_action(decision: str) -> str:
    if decision == DECISION_APPROVE:
        return "Proceed"
    if decision == DECISION_PARTIAL:
        return "Revise"
    if decision == DECISION_REJECT:
        return "Stop"
    return "New prompt required"


def _missing_evidence(report_text: str) -> bool:
    lowered = report_text.lower()
    return "not run" in lowered or "missing" in lowered or "todo" in lowered


def _render_review(
    *,
    phase: str,
    decision: str,
    next_action: str,
    git: GitInspection,
    report: ReportCheckResult,
    scope: PhaseEvaluation,
    canon: CanonAssessment,
) -> str:
    clean_status = "clean" if git.is_clean else "dirty"
    status_summary = ", ".join(git.status_lines) if git.status_lines else "clean"
    allowed_summary = _render_list(scope.allowed_hits) or "none observed"
    forbidden_summary = _render_list(scope.forbidden_hits) or "none observed"
    combined_warnings = scope.warning_hits + canon.warnings
    warning_summary = _render_list(combined_warnings) or "none"
    truth_warning_summary = _render_list(canon.truth_warnings) or "none"
    missing_sections = _render_list(report.missing_sections) or "none"
    tests_line = "reported" if "## D. Tests / Validation" in report.present_sections else "missing"
    runtime_line = "reported" if "## E. Runtime Evidence" in report.present_sections else "missing"
    missing_evidence = "possible evidence gaps noted" if _missing_evidence(report.text) else "none detected procedurally"

    lines = [
        "# Architecture Office Review",
        "",
        "## A. Decision",
        decision,
        "",
        "Procedural approval only. Product judgment still belongs to Architecture Office.",
        "",
        "## B. Process Check",
        f"- branch: `{git.branch}`",
        f"- expected phase branch: `{phase}`",
        f"- latest commit: `{git.latest_commit}`",
        f"- git status: {clean_status} ({status_summary})",
        f"- report completeness: {'complete' if report.complete else 'incomplete'}",
        f"- missing report sections: {missing_sections}",
        "",
        "## C. Phase Scope",
        f"- allowed work observed: {allowed_summary}",
        f"- forbidden work observed: {forbidden_summary}",
        f"- warnings: {warning_summary}",
        "",
        "## Canon Sources Checked",
    ]
    lines.extend(_render_bullets(canon.sources_checked, fallback="none"))
    lines.extend(["", "## Chris Canon Sources Checked"])
    lines.extend(_render_bullets(canon.chris_sources_checked, fallback="none"))
    if canon.non_canon_references:
        lines.extend(["", "## Non-Canon References Detected"])
        lines.extend(_render_bullets(canon.non_canon_references, fallback="none"))
    lines.extend(
        [
            "",
            "## D. Evidence Review",
            f"- tests reported: {tests_line}",
            f"- runtime evidence reported: {runtime_line}",
            f"- missing evidence: {missing_evidence}",
            "",
            "## E. Truth Contract",
            f"- fake capability risks: {truth_warning_summary}",
            "- evidence required: pair claims with command output, test output, or file evidence in the report",
            "",
            "## F. Risks",
            f"- repo risks: {'uncommitted changes present' if git.has_uncommitted_changes else 'none detected procedurally'}",
            f"- product risks: {'forbidden scope needs architecture attention' if scope.forbidden_hits else 'none detected procedurally'}",
            f"- phase risks: {'report is incomplete' if not report.complete else 'no immediate phase-gate gaps detected'}",
            "",
            "## G. Next Action",
            next_action,
        ]
    )
    return "\n".join(lines)


def _render_list(values: list[str]) -> str:
    if not values:
        return ""
    return ", ".join(f"`{value}`" for value in _dedupe(values))


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _render_bullets(values: list[str], *, fallback: str) -> list[str]:
    deduped = _dedupe(values)
    if not deduped:
        return [f"- {fallback}"]
    return [f"- `{value}`" for value in deduped]

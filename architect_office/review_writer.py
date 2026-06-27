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
    missing_sections = _render_list(report.missing_sections) or "none"
    tests_line = "reported" if "## D. Tests / Validation" in report.present_sections else "missing"
    runtime_line = "reported" if "## E. Runtime Evidence" in report.present_sections else "missing"
    missing_evidence = "possible evidence gaps noted" if _missing_evidence(report.text) else "none detected procedurally"
    findings = _findings(git=git, report=report, scope=scope, canon=canon)
    risks = _risks(git=git, report=report, scope=scope, canon=canon)
    follow_up = _required_follow_up(
        decision=decision,
        next_action=next_action,
        git=git,
        report=report,
        scope=scope,
        canon=canon,
    )
    truth_warning_summary = _render_list(canon.truth_warnings) or "none"

    lines = [
        "# Architecture Office Review",
        "",
        "## Decision",
        f"- decision: {decision}",
        f"- phase: `{phase}`",
        f"- next action: {next_action}",
        "",
        "Procedural approval only. Product judgment still belongs to Architecture Office.",
        "",
        "## Scope Checked",
        f"- allowed work observed: {allowed_summary}",
        f"- forbidden work observed: {forbidden_summary}",
        f"- branch: `{git.branch}`",
        f"- expected phase branch: `{phase}`",
        f"- latest commit: `{git.latest_commit}`",
        f"- git status: {clean_status} ({status_summary})",
        f"- report completeness: {'complete' if report.complete else 'incomplete'}",
        f"- missing report sections: {missing_sections}",
        "",
        "## Canon Sources Checked",
    ]
    lines.extend(_render_bullets(canon.sources_checked, fallback="none"))
    lines.extend(["", "## Chris Canon Sources Checked"])
    lines.extend(_render_bullets(canon.chris_sources_checked, fallback="none"))
    lines.extend(["", "## Non-Canon References Detected"])
    lines.extend(_render_bullets(canon.non_canon_references, fallback="none"))
    lines.extend(
        [
            "",
            "## Evidence Reviewed",
            f"- tests reported: {tests_line}",
            f"- runtime evidence reported: {runtime_line}",
            f"- missing evidence: {missing_evidence}",
            f"- report path: `{report.path}`",
            "",
            "## Findings",
        ]
    )
    lines.extend(_render_bullets(findings, fallback="none"))
    lines.extend(
        [
            "",
            "## Risks",
            f"- truth risks: {truth_warning_summary}",
        ]
    )
    lines.extend(_render_bullets(risks, fallback="none"))
    lines.extend(["", "## Required Follow-up"])
    lines.extend(_render_bullets(follow_up, fallback=next_action))
    lines.extend(
        [
            "",
            "## Final Judgment",
            f"- judgment: {decision}",
            f"- procedural status: {next_action}",
            "- Architect Office review is procedural governance output only. It does not approve product direction.",
        ]
    )
    return "\n".join(lines)


def _findings(
    *,
    git: GitInspection,
    report: ReportCheckResult,
    scope: PhaseEvaluation,
    canon: CanonAssessment,
) -> list[str]:
    findings: list[str] = []
    if not git.branch_matches_phase:
        findings.append("Branch does not match the requested phase.")
    if not report.complete:
        findings.append("Build Office report is incomplete.")
    findings.extend(canon.warnings)
    if scope.warning_hits:
        findings.extend(f"Phase warning term observed: {item}" for item in scope.warning_hits)
    if not canon.non_canon_references:
        findings.append("No non-canon binding references were detected.")
    return _dedupe(findings)


def _risks(
    *,
    git: GitInspection,
    report: ReportCheckResult,
    scope: PhaseEvaluation,
    canon: CanonAssessment,
) -> list[str]:
    risks: list[str] = []
    if git.has_uncommitted_changes:
        risks.append("Uncommitted changes are present in the repo.")
    if scope.forbidden_hits:
        risks.append("Forbidden scope appears in the reviewed material.")
    if canon.stale_override_references:
        risks.append("Deprecated or stale docs appear to be treated as active authority.")
    if canon.unsupported_capability_claims:
        risks.append("Capability claims appear without supporting proof in the report text.")
    if not report.complete:
        risks.append("Missing report sections weaken procedural review confidence.")
    return _dedupe(risks)


def _required_follow_up(
    *,
    decision: str,
    next_action: str,
    git: GitInspection,
    report: ReportCheckResult,
    scope: PhaseEvaluation,
    canon: CanonAssessment,
) -> list[str]:
    follow_up: list[str] = []
    if not git.is_clean:
        follow_up.append("Clean or explicitly account for current git status before approval review.")
    if not report.complete:
        follow_up.append("Complete all required Build Office report sections.")
    if canon.non_canon_references:
        follow_up.append("Replace non-canon binding references with active canon sources.")
    if canon.stale_override_references:
        follow_up.append("Remove stale or deprecated docs as authority when active phase gates apply.")
    if canon.unsupported_capability_claims:
        follow_up.append("Pair capability claims with command, test, or runtime proof.")
    if scope.forbidden_hits:
        follow_up.append("Narrow the implementation back to the approved phase scope before re-review.")
    if not follow_up:
        follow_up.append(next_action)
    return _dedupe(follow_up)


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

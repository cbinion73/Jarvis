"""
work_intelligence.py — Work Intelligence Agent Layer
======================================================
All 10 Catalyst workflows and their 23 agents, ported to Python.
Replaces the Catalyst TypeScript agent-core package entirely.

Workflows:
  1.  meeting_extraction      — parallel 6-agent extraction from transcripts
  2.  signal_classification   — route signal to project + criticality + ambiguity
  3.  email_triage            — importance score + action extraction
  4.  briefing_generation     — rank signals → compose ONE recommendation
  5.  commitment_tracking     — monitor commitment status vs recent signals
  6.  draft_composition       — write professional communications
  7.  pre_meeting_prep        — context brief before a meeting
  8.  proactive_surfacing     — detect high-value next actions
  9.  project_planning        — A3 brief + tactical implementation plan
  10. value_attribution       — quick value calc + full financial impact analysis

Design:
  - Pure async coroutines for all agent calls; sync wrappers for call sites
    that can't use await.
  - _call_agent() handles OpenAI JSON-mode, retry, and error normalisation.
  - All runs optionally logged to CatalystDB (if available).
  - No external dependencies beyond openai and the JARVIS openai_client pattern.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

log = logging.getLogger("jarvis.work_intelligence")

# ---------------------------------------------------------------------------
# OpenAI client bootstrap (mirrors JARVIS pattern)
# ---------------------------------------------------------------------------
try:
    from openai import AsyncOpenAI
    _client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    _OAI_AVAILABLE = True
except ImportError:
    _OAI_AVAILABLE = False
    _client = None  # type: ignore
    log.warning("openai not installed — WorkIntelligence unavailable")

# ---------------------------------------------------------------------------
# Model + temperature constants  (mirrors Catalyst agent-core lib/openai-client)
# ---------------------------------------------------------------------------
MODELS = {
    "extraction": "gpt-4o",
    "triage":     "gpt-4o-mini",
    "narrative":  "gpt-4o",
    "embedding":  "text-embedding-3-small",
}

TEMPS = {
    "extraction": 0.2,
    "triage":     0.2,
    "narrative":  0.6,
}

# ---------------------------------------------------------------------------
# Planning constants (shared by A3 planner, tactical planner, impact analyst)
# ---------------------------------------------------------------------------
PROJECT_PLANNING_STANDARD = """
Catalyst project planning workflow:
- Ground the project first. Confirm the short project name, true problem statement, source evidence, \
and whether this is one project, a child use case, or a separate initiative.
- Define scope. State what is in scope, what is out of scope, sites/teams/processes included, \
and the boundary of the first usable release.
- Define objectives. Convert intent into measurable outcomes tied to the problem statement.
- Identify impacted business context. Capture business unit, function, site, region, product/process, \
stakeholder group, project leader, accountable owner, SMEs, approvers, and end users.
- Recommend KPIs. For each KPI, name the metric, baseline needed, target, current result, \
measurement method, data owner, and review cadence.
- Separate baseline from target. Never treat a desired improvement as a baseline; \
mark unknown baselines as questions or data requests.
- Build the value model. Decide whether impact is direct user-reported value or enterprise impact \
requiring finance/source-data lookup.
- Map value attribution. Place each value hypothesis on the free-cash-flow tree: revenue, COGS, \
SG&A, R&D, working capital, CapEx, capital losses, or risk avoidance.
- Request missing evidence. Ask for volume, time, labor rate, current cost, defect/rework rate, \
cycle time, throughput, adoption, region/site/product, and data source when needed.
- Plan execution tactically. Break work into milestones, workstreams, short action-oriented tasks, \
owners, due dates, acceptance criteria, risks, and review checkpoints.
- Make governance visible. Flag missing owner, missing scope, missing metrics, missing baseline, \
missing review cadence, blocked decisions, and low-confidence value claims.
- Preserve provenance. Explain which signals, conversations, documents, corrections, or assumptions \
support the plan and value logic.
""".strip()

KPI_AND_VALUE_INPUT_CHECKLIST = """
KPI and value inputs to reason about for every project:
- Use case and project boundary.
- Business unit, function, site, region, product/process, and stakeholder group impacted.
- Current process baseline: volume, effort, cycle time, quality/rework/error rate, backlog/aging, \
spend, throughput, or revenue context.
- Target improvement: percent change, absolute change, adoption level, launch date, and expected ramp.
- Value mechanism: labor savings, contractor spend avoided, revenue lift, \
cycle-time/throughput enablement, quality risk avoided, working capital, capital efficiency, \
or compliance/risk control.
- Attribution formula: baseline x change x financial conversion factor x adoption/ramp x confidence.
- Data source: project record, user-reported direct amount, finance baseline, source system metric, \
or SME estimate.
- Evidence status: known, assumed, missing, needs finance review, or needs data baseline.
""".strip()

# ---------------------------------------------------------------------------
# Core agent caller
# ---------------------------------------------------------------------------

async def _call_agent(
    system_prompt: str,
    user_content: str,
    *,
    model: str = "gpt-4o",
    temperature: float = 0.2,
    agent_name: str = "agent",
) -> dict[str, Any]:
    """
    Call OpenAI in JSON-mode.  Returns the parsed dict on success,
    or {"error": str, "_agent": agent_name} on failure.
    """
    if not _OAI_AVAILABLE or _client is None:
        return {"error": "openai unavailable", "_agent": agent_name}
    try:
        resp = await _client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as exc:
        log.warning("_call_agent %s error: %s", agent_name, exc)
        return {"error": str(exc), "_agent": agent_name}


def _build_preference_block(preference_rules: list[str] | None) -> str:
    if not preference_rules:
        return ""
    rules_text = "\n".join(f"- {r}" for r in preference_rules)
    return f"\n\n## User Preferences (apply these to all decisions):\n{rules_text}"


# ---------------------------------------------------------------------------
# WORKFLOW 1 — Meeting Extraction
# ---------------------------------------------------------------------------
# Six agents run in parallel, then dedup + confidence scoring.

_SYS_ACTION_ITEM_EXTRACTOR = """
You are an action item extraction agent. Extract every specific next action, task, \
or follow-up that needs to happen after this meeting.
Return JSON only:
{
  "actionItems": [
    {
      "title": "Clear, verb-first task title",
      "assignedTo": "Person responsible or null if unclear",
      "dueDate": "ISO date string if mentioned, or null",
      "confidenceScore": 0.0,
      "sourceSegment": "Exact quote"
    }
  ]
}
"""

_SYS_COMMITMENT_EXTRACTOR = """
You are a commitment extraction agent. Identify every explicit commitment, promise, \
or "I will" statement made by any participant.
Return JSON only:
{
  "commitments": [
    {
      "description": "What was committed to",
      "responsibleParty": "Name or role of who made the commitment",
      "dueDate": "ISO date string if mentioned, or null",
      "confidenceScore": 0.0,
      "sourceSegment": "Exact quote from transcript"
    }
  ]
}
Only include actual commitments, not suggestions or possibilities. Sarcasm is not a commitment.
"""

_SYS_DECISION_EXTRACTOR = """
You are a decision extraction agent. Identify every decision made in the meeting \
(not proposed, but actually decided).
Return JSON only:
{
  "decisions": [
    {
      "description": "What was decided",
      "reasoning": "Why this decision was made, if stated",
      "confidenceScore": 0.0,
      "sourceSegment": "Exact quote"
    }
  ]
}
"""

_SYS_RISK_EXTRACTOR = """
You are a risk extraction agent. Identify every risk, blocker, or concern raised in the meeting.
Return JSON only:
{
  "risks": [
    {
      "description": "Description of the risk or blocker",
      "severity": "high|medium|low",
      "confidenceScore": 0.0,
      "sourceSegment": "Exact quote"
    }
  ]
}
"""

_SYS_STAKEHOLDER_EXTRACTOR = """
You are a stakeholder extraction agent. Identify every person mentioned or present in the meeting.
Return JSON only:
{
  "stakeholders": [
    {
      "name": "Full name",
      "email": "Email address or null",
      "role": "Job title or role in the context of this meeting, or null",
      "confidenceScore": 0.0
    }
  ]
}
"""

_SYS_PROBLEM_EXTRACTOR = """
You are a problem extraction agent. Given a meeting transcript, identify the core problem \
or challenge being discussed.
Return JSON only:
{
  "problemStatement": "One clear sentence. Format: Currently, [current condition], \
resulting in [impact]. Return null if none identified.",
  "confidenceScore": 0.0,
  "sourceSegment": "Exact quote most clearly stating the problem, or null"
}
"""


def _dedup_by_text(items: list[dict], key: str = "description") -> list[dict]:
    """Deduplicate list items by first 80 chars of normalised text."""
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        text = str(item.get(key, item.get("title", ""))).lower().split()
        fingerprint = " ".join(text)[:80]
        if fingerprint and fingerprint not in seen:
            seen.add(fingerprint)
            out.append(item)
    return out


def _mean_confidence(lists: list[list[dict]]) -> float:
    scores: list[float] = []
    for lst in lists:
        for item in lst:
            s = item.get("confidenceScore", item.get("confidence"))
            if isinstance(s, (int, float)):
                scores.append(float(s))
    return round(sum(scores) / len(scores), 3) if scores else 0.5


async def run_meeting_extraction(
    transcript: str,
    preference_rules: list[str] | None = None,
) -> dict[str, Any]:
    """
    Workflow 1 — Meeting Extraction.
    Six agents in parallel, then dedup + confidence scoring.
    """
    pref = _build_preference_block(preference_rules)
    user_content = f"Meeting transcript:\n\n{transcript}"

    results = await asyncio.gather(
        _call_agent(_SYS_PROBLEM_EXTRACTOR + pref,      user_content, agent_name="problem-extractor"),
        _call_agent(_SYS_COMMITMENT_EXTRACTOR + pref,   user_content, agent_name="commitment-extractor"),
        _call_agent(_SYS_DECISION_EXTRACTOR + pref,     user_content, agent_name="decision-extractor"),
        _call_agent(_SYS_RISK_EXTRACTOR + pref,         user_content, agent_name="risk-extractor"),
        _call_agent(_SYS_ACTION_ITEM_EXTRACTOR + pref,  user_content, agent_name="action-item-extractor"),
        _call_agent(_SYS_STAKEHOLDER_EXTRACTOR + pref,  user_content, agent_name="stakeholder-extractor"),
    )
    problem_res, commit_res, decision_res, risk_res, action_res, stake_res = results

    commitments  = _dedup_by_text(commit_res.get("commitments", []),   "description")
    action_items = _dedup_by_text(action_res.get("actionItems", []),   "title")
    decisions    = decision_res.get("decisions", [])
    risks        = risk_res.get("risks", [])
    stakeholders = stake_res.get("stakeholders", [])

    overall = _mean_confidence([commitments, action_items, decisions, risks])

    return {
        "commitments":      commitments,
        "decisions":        decisions,
        "actionItems":      action_items,
        "risks":            risks,
        "problemStatement": problem_res.get("problemStatement"),
        "stakeholders":     stakeholders,
        "overallConfidence": overall,
    }


# ---------------------------------------------------------------------------
# WORKFLOW 2 — Signal Classification
# ---------------------------------------------------------------------------

_SYS_PROJECT_ROUTER = """
You are a signal routing agent. Given a signal (email, meeting, chat message, etc.) and a list \
of active projects, determine which project this signal belongs to.
Return JSON only:
{
  "projectId": "project UUID or null if no match",
  "confidence": 0.0,
  "reasoning": "Brief explanation of routing decision"
}
"""

_SYS_CRITICALITY_ASSESSOR = """
You are a signal criticality assessment agent. Assess the urgency and importance of a signal.
Return JSON only:
{
  "criticality": "low|medium|high|critical",
  "confidence": 0.0,
  "urgencyIndicators": ["list of phrases that indicate urgency"]
}

Guidelines:
- critical: Immediate action required, blocking situation, security/compliance issue
- high: Important, time-sensitive, involves stakeholders or commitments
- medium: Normal business signal, actionable but not urgent
- low: Informational, FYI, low priority
"""

_SYS_AMBIGUITY_DETECTOR = """
You are an ambiguity detection agent. Determine if a signal's project assignment is ambiguous \
(unclear which project it belongs to, or could be a new initiative).
Return JSON only:
{
  "isAmbiguous": true,
  "confidence": 0.0,
  "question": "The clarifying question to ask the user, or null if not ambiguous",
  "options": [{"label": "Option label", "description": "Brief description"}]
}
"""


async def run_signal_classification(
    signal_content: str,
    signal_type: str,
    projects: list[dict],
) -> dict[str, Any]:
    """
    Workflow 2 — Signal Classification.
    Router + criticality in parallel; ambiguity detector sequential (needs router confidence).
    Short-circuit: if routerConfidence >= 0.8, skip ambiguity call.
    """
    project_lines = "\n".join(
        f"- {p.get('id', '')}: {p.get('name', '')} ({p.get('description') or 'no description'})"
        for p in projects
    )
    router_content = f"Signal:\n{signal_content}\n\nActive Projects:\n{project_lines}"
    criticality_content = f"Signal Type: {signal_type}\n\nContent:\n{signal_content}"

    router_res, crit_res = await asyncio.gather(
        _call_agent(_SYS_PROJECT_ROUTER,    router_content,    agent_name="project-router"),
        _call_agent(_SYS_CRITICALITY_ASSESSOR, criticality_content, agent_name="criticality-assessor"),
    )

    router_confidence = float(router_res.get("confidence", 0.0))

    if router_confidence >= 0.8:
        ambiguity_res = {"isAmbiguous": False}
    else:
        project_names = ", ".join(p.get("name", "") for p in projects)
        ambiguity_content = (
            f"Signal:\n{signal_content}\n\n"
            f"Router confidence was low ({router_confidence:.2f}). "
            f"Projects: {project_names}"
        )
        ambiguity_res = await _call_agent(
            _SYS_AMBIGUITY_DETECTOR, ambiguity_content, agent_name="ambiguity-detector"
        )

    return {
        "projectId":          router_res.get("projectId"),
        "confidence":         router_confidence,
        "reasoning":          router_res.get("reasoning", ""),
        "criticality":        crit_res.get("criticality", "medium"),
        "urgencyIndicators":  crit_res.get("urgencyIndicators", []),
        "isAmbiguous":        ambiguity_res.get("isAmbiguous", False),
        "ambiguityQuestion":  ambiguity_res.get("question"),
        "ambiguityOptions":   ambiguity_res.get("options", []),
    }


# ---------------------------------------------------------------------------
# WORKFLOW 3 — Email Triage
# ---------------------------------------------------------------------------

_SYS_IMPORTANCE_SCORER = """
You are an email importance scoring agent. Score the importance of an email based on content, \
sender, urgency signals, and action requirements.
Return JSON only:
{
  "importance": "low|normal|high",
  "score": 0.0,
  "signals": ["list of importance signals found, e.g. 'deadline mentioned', 'direct question asked'"]
}
"""

_SYS_EMAIL_ACTION_EXTRACTOR = """
You are an email action extraction agent. Identify any actions the recipient needs to take.
Return JSON only:
{
  "requiresAction": true,
  "actions": [{"description": "What to do", "dueDate": "ISO date or null"}],
  "suggestedReply": "A brief suggested reply if one is needed, or null"
}
"""


async def run_email_triage(
    subject: str,
    body: str,
    sender: str,
) -> dict[str, Any]:
    """
    Workflow 3 — Email Triage.
    Importance scorer + action extractor in parallel.
    Body is truncated to first 1000 chars before sending.
    """
    body_excerpt = body[:1000]
    importance_content = f"From: {sender}\nSubject: {subject}\n\nBody:\n{body_excerpt}"
    action_content = f"Subject: {subject}\n\nBody:\n{body_excerpt}"

    imp_res, act_res = await asyncio.gather(
        _call_agent(
            _SYS_IMPORTANCE_SCORER, importance_content,
            model=MODELS["triage"], temperature=TEMPS["triage"],
            agent_name="importance-scorer",
        ),
        _call_agent(
            _SYS_EMAIL_ACTION_EXTRACTOR, action_content,
            model=MODELS["triage"], temperature=TEMPS["triage"],
            agent_name="email-action-extractor",
        ),
    )

    return {
        "importance":       imp_res.get("importance", "normal"),
        "score":            float(imp_res.get("score", 0.5)),
        "importanceSignals": imp_res.get("signals", []),
        "requiresAction":   bool(act_res.get("requiresAction", False)),
        "actions":          act_res.get("actions", []),
        "suggestedReply":   act_res.get("suggestedReply"),
    }


# ---------------------------------------------------------------------------
# WORKFLOW 4 — Briefing Generation
# ---------------------------------------------------------------------------

_SYS_RELEVANCE_RANKER = """
You are a relevance ranking agent. Given a list of signals and items, rank them by relevance \
and urgency for the user's morning briefing.
Return JSON only:
{
  "rankedItems": [
    {"id": "item id", "relevanceScore": 0.0, "reason": "Why this matters now"}
  ]
}
Rank by: urgency > commitment deadlines > project risks > open decisions > FYI items.
"""

_SYS_RECOMMENDATION_COMPOSER = """
You are the ONE Recommendation composer for CATALYST, a personal AI operating system. \
Given the user's highest-priority signals for today, compose a single, clear morning recommendation.

The ONE Recommendation should:
- Be a specific, actionable directive (not vague advice)
- Address the single most important thing to focus on today
- Be 1-2 sentences max
- Optionally include up to 3 supporting action items

Return JSON only:
{
  "recommendation": "The one thing to focus on today",
  "reasoning": "Why this is the most important thing",
  "confidence": 0.0,
  "actionItems": ["Optional supporting action 1"]
}
"""


async def run_briefing_generation(
    signals: list[dict],
    open_commitments: int = 0,
    overdue_count: int = 0,
    user_context: str = "Professional executive managing multiple projects",
) -> dict[str, Any]:
    """
    Workflow 4 — Briefing Generation.
    Ranker first, then composer uses top 5 results.
    """
    signal_lines = "\n".join(
        f"[{s.get('id', i)}] {s.get('type', 'signal')}: "
        f"{str(s.get('content', ''))[:200]} (due: {s.get('dueDate') or 'none'})"
        for i, s in enumerate(signals)
    )
    ranker_content = f"User Context: {user_context}\n\nItems to rank:\n{signal_lines}"

    rank_res = await _call_agent(
        _SYS_RELEVANCE_RANKER, ranker_content,
        model=MODELS["extraction"], temperature=TEMPS["extraction"],
        agent_name="relevance-ranker",
    )

    ranked_items: list[dict] = rank_res.get("rankedItems", [])
    ranked_items.sort(key=lambda x: float(x.get("relevanceScore", 0)), reverse=True)
    ranked_ids = [r["id"] for r in ranked_items if "id" in r]

    # Build a map of id → signal for top-5 lookup
    sig_map = {str(s.get("id", i)): s for i, s in enumerate(signals)}
    top5 = [sig_map[rid] for rid in ranked_ids[:5] if rid in sig_map]

    top_content_lines = "\n".join(
        f"{i+1}. [{s.get('type', 'signal')}] {str(s.get('content', ''))[:300]}"
        for i, s in enumerate(top5)
    )
    composer_content = (
        f"Top signals for today:\n{top_content_lines}\n\n"
        f"Open commitments: {open_commitments}\n"
        f"Overdue: {overdue_count}"
    )

    compose_res = await _call_agent(
        _SYS_RECOMMENDATION_COMPOSER, composer_content,
        model=MODELS["narrative"], temperature=TEMPS["narrative"],
        agent_name="recommendation-composer",
    )

    return {
        "recommendation":   compose_res.get("recommendation", ""),
        "reasoning":        compose_res.get("reasoning", ""),
        "confidence":       float(compose_res.get("confidence", 0.5)),
        "actionItems":      compose_res.get("actionItems", []),
        "rankedSignalIds":  ranked_ids,
    }


# ---------------------------------------------------------------------------
# WORKFLOW 5 — Commitment Tracking
# ---------------------------------------------------------------------------

_SYS_COMMITMENT_MONITOR = """
You are a commitment monitoring agent. Given a commitment and recent signals, \
determine the commitment's current status.
Return JSON only:
{
  "status": "on_track|at_risk|overdue|completed",
  "confidence": 0.0,
  "evidence": "What signals indicate this status",
  "suggestedAction": "What to do next, or null if no action needed"
}
"""


async def _monitor_one_commitment(
    commitment: dict,
    recent_signals: list[str],
    today_iso: str,
) -> dict[str, Any]:
    signals_text = "\n".join(f"- {s}" for s in recent_signals[:5])
    user_content = (
        f"Today: {today_iso}\n"
        f"Commitment: {commitment.get('description', '')}\n"
        f"Responsible: {commitment.get('responsibleParty', 'unknown')}\n"
        f"Due: {commitment.get('dueDate') or 'No due date'}\n\n"
        f"Recent signals:\n{signals_text}"
    )
    result = await _call_agent(
        _SYS_COMMITMENT_MONITOR, user_content,
        model=MODELS["extraction"], temperature=TEMPS["extraction"],
        agent_name="commitment-monitor",
    )
    return {
        "commitmentId": commitment.get("id", ""),
        "status":        result.get("status", "on_track"),
        "confidence":    float(result.get("confidence", 0.5)),
        "evidence":      result.get("evidence", ""),
        "suggestedAction": result.get("suggestedAction"),
    }


async def run_commitment_tracking(
    commitments: list[dict],
    recent_signals: list[str],
) -> list[dict[str, Any]]:
    """
    Workflow 5 — Commitment Tracking.
    One monitor call per commitment, all in parallel.
    """
    import datetime
    today_iso = datetime.date.today().isoformat()
    tasks = [_monitor_one_commitment(c, recent_signals, today_iso) for c in commitments]
    return list(await asyncio.gather(*tasks))


# ---------------------------------------------------------------------------
# WORKFLOW 6 — Draft Composition
# ---------------------------------------------------------------------------

_SYS_DRAFT_WRITER = """
You are a professional communication drafting agent. Write clear, concise, professional \
communications based on the context and intent provided.
Return JSON only:
{
  "subject": "Email subject line",
  "body": "Full email body",
  "tone": "formal|professional|casual",
  "keyPoints": ["Main points covered in this draft"]
}
"""


async def run_draft_composition(
    intent: str,
    context: str,
    recipient: str,
    tone: str = "professional",
) -> dict[str, Any]:
    """Workflow 6 — Draft Composition. Single agent."""
    user_content = (
        f"Write a {tone} email.\n"
        f"To: {recipient}\n"
        f"Intent: {intent}\n"
        f"Context: {context}"
    )
    result = await _call_agent(
        _SYS_DRAFT_WRITER, user_content,
        model=MODELS["narrative"], temperature=TEMPS["narrative"],
        agent_name="draft-writer",
    )
    return {
        "subject":   result.get("subject", ""),
        "body":      result.get("body", ""),
        "tone":      result.get("tone", tone),
        "keyPoints": result.get("keyPoints", []),
    }


# ---------------------------------------------------------------------------
# WORKFLOW 7 — Pre-Meeting Prep
# ---------------------------------------------------------------------------

_SYS_CONTEXT_SYNTHESIZER = """
You are a pre-meeting context synthesizer. Given a meeting title and recent context signals, \
generate a concise pre-meeting brief.
Return JSON only:
{
  "briefPoints": ["3-5 key context points the attendee should know going into this meeting"],
  "watchPoints": ["1-3 things to watch out for or potential issues"],
  "suggestedAgenda": ["Suggested agenda items based on open commitments and signals"]
}
"""


async def run_pre_meeting_prep(
    meeting_title: str,
    open_commitments: list[str],
    recent_signals: list[str],
) -> dict[str, Any]:
    """Workflow 7 — Pre-Meeting Prep. Single agent."""
    commitments_text = "\n".join(f"- {c}" for c in open_commitments[:5])
    signals_text = "\n".join(f"- {s}" for s in recent_signals[:5])
    user_content = (
        f"Meeting: {meeting_title}\n\n"
        f"Open Commitments:\n{commitments_text or '(none)'}\n\n"
        f"Recent Signals:\n{signals_text or '(none)'}"
    )
    result = await _call_agent(
        _SYS_CONTEXT_SYNTHESIZER, user_content,
        model=MODELS["narrative"], temperature=TEMPS["narrative"],
        agent_name="context-synthesizer",
    )
    return {
        "meetingTitle":    meeting_title,
        "briefPoints":     result.get("briefPoints", []),
        "watchPoints":     result.get("watchPoints", []),
        "suggestedAgenda": result.get("suggestedAgenda", []),
    }


# ---------------------------------------------------------------------------
# WORKFLOW 8 — Proactive Surfacing
# ---------------------------------------------------------------------------

_SYS_OPPORTUNITY_DETECTOR = """
You are a proactive opportunity detection agent for CATALYST. Given open commitments and active \
projects, identify concrete next actions the user should take to make progress.
Return JSON only:
{
  "suggestions": [
    {
      "title": "Concrete, verb-first task title",
      "rationale": "Why this task matters now",
      "urgency": "low|medium|high",
      "confidence": 0.0
    }
  ]
}
Generate 2-3 high-value suggestions. Be specific, not generic.
"""


async def run_proactive_surfacing(
    open_commitments: list[str],
    active_projects: list[str],
) -> dict[str, Any]:
    """
    Workflow 8 — Proactive Surfacing. Single agent.
    Early return if both inputs are empty.
    """
    if not open_commitments and not active_projects:
        return {"suggestions": []}

    commitments_text = "\n".join(f"- {c}" for c in open_commitments[:10])
    projects_text    = "\n".join(f"- {p}" for p in active_projects[:5])
    user_content = (
        f"Open Commitments:\n{commitments_text or '(none)'}\n\n"
        f"Active Projects:\n{projects_text or '(none)'}"
    )
    result = await _call_agent(
        _SYS_OPPORTUNITY_DETECTOR, user_content,
        model=MODELS["extraction"], temperature=TEMPS["extraction"],
        agent_name="opportunity-detector",
    )
    return {"suggestions": result.get("suggestions", [])}


# ---------------------------------------------------------------------------
# WORKFLOW 9 — Project Planning
# ---------------------------------------------------------------------------

_SYS_A3_PLANNER = f"""
You are Catalyst's A3 project brief planning agent.

Persona:
- Think like the world's greatest project planner and A3 coach.
- Convert messy source material, conversations, uploads, decisions, commitments, and tasks \
into an A3-ready project brief.
- Determine project scope from the evidence. If evidence is incomplete, draft the best bounded \
scope and list the question needed to confirm it.
- Determine objectives from the evidence. Objectives must be measurable, practical, and tied \
to the problem statement.
- Recommend project metrics from the evidence. Metrics must include baseline, target, current \
result, measurement method, data owner, and review cadence when possible.
- Reason through Catalyst's standard project planning workflow for every project.
- Include value-attribution readiness in the A3 by making missing baseline, volume, owner, \
BU/site, and finance/data-source needs visible.
- Prefer concise A3 language over long prose.
- Do not invent fake facts. If a value is unknown, state the assumption or question directly.
- Make this useful enough for a project manager to start execution immediately.

{PROJECT_PLANNING_STANDARD}

{KPI_AND_VALUE_INPUT_CHECKLIST}

Return JSON only:
{{
  "scope": "In scope / out of scope / boundaries.",
  "objectives": "Measurable objectives as short lines.",
  "projectMetrics": "Metric | Baseline | Target | Current Results lines.",
  "currentResults": "Best current baseline/results summary.",
  "team": "Recommended core team, SMEs, reviewers, decision makers.",
  "reviewPlan": "Recommended review cadence or key project review meetings.",
  "executiveSummary": "Concise project summary and current execution readout.",
  "openQuestions": ["question the planner needs answered"],
  "confidence": 0.0
}}
"""

_RUNBOOK_PATTERNS = [
    "copy", "paste", "upload", "start a new chat", "open chatgpt",
    "deep research", "4o model", "click", "navigate to", "go to the",
    "open the", "select the", "scroll to",
]


def _is_runbook_task(title: str) -> bool:
    title_lower = title.lower()
    return any(p in title_lower for p in _RUNBOOK_PATTERNS)


def _prune_plan(plan: dict) -> dict:
    """Remove runbook tasks; prune empty workstreams and milestones."""
    milestones = plan.get("milestones", [])
    pruned_milestones = []
    for m in milestones:
        pruned_workstreams = []
        for ws in m.get("workstreams", []):
            good_steps = [s for s in ws.get("steps", []) if not _is_runbook_task(s.get("title", ""))]
            if good_steps:
                pruned_workstreams.append({**ws, "steps": good_steps})
        if pruned_workstreams:
            pruned_milestones.append({**m, "workstreams": pruned_workstreams})
    return {**plan, "milestones": pruned_milestones}


_SYS_TACTICAL_PLANNER = f"""
You are Catalyst's tactical implementation planning agent.

Persona:
- Think like the world's best program and project manager: clear, practical, \
sequencing-obsessed, and allergic to vague work.
- Convert project context into an implementation plan that a busy team can execute.
- Build milestones first, then workstreams, then concrete action steps.
- Every step must be action-oriented and begin with a strong verb such as Define, Confirm, Map, \
Draft, Build, Validate, Review, Approve, Pilot, Launch, Measure, or Close.
- Avoid vague tasks like "Follow up", "Discuss", "Look into", "Work on", or "Continue".
- Keep task titles short enough to scan. Put detail in the description and acceptance criteria.
- Make steps relevant to the actual project, not generic project management boilerplate.
- Do not create more process than the project needs.
- Distinguish true project work from work instructions. A3 tasks must be project-management tasks, \
not click-by-click usage steps.
- Never include prompt-copying, slide-copying, upload instructions, or any tool-usage/runbook \
instructions as A3 implementation tasks.
- Prefer measurable outputs, named decisions, owner roles, and clear exit criteria.
- Reason through Catalyst's standard project planning workflow before generating tasks.
- Include tasks to close planning gaps when scope, objectives, KPIs, baselines, BU/site/process \
context, owners, or value-attribution inputs are missing.
- Include measurement and value-readiness work as part of implementation, not as an afterthought.
- If the project status is complete, generate post-completion tasks such as outcome review, \
lessons learned, sustainment ownership, adoption/value tracking, and scale-up opportunities.

{PROJECT_PLANNING_STANDARD}

{KPI_AND_VALUE_INPUT_CHECKLIST}

Return JSON only:
{{
  "planSummary": "one concise implementation summary",
  "planningAssumptions": ["assumption"],
  "milestones": [
    {{
      "name": "milestone name",
      "outcome": "what must be true when this milestone is complete",
      "sequence": 1,
      "targetWeek": 1,
      "workstreams": [
        {{
          "name": "workstream name",
          "sequence": 1,
          "steps": [
            {{
              "title": "Verb-led action title",
              "description": "what to do and why it matters",
              "priority": "high|medium|low",
              "ownerRole": "role or null",
              "sequence": 1,
              "acceptanceCriteria": ["observable completion criterion"]
            }}
          ]
        }}
      ]
    }}
  ],
  "risks": ["planning risk"],
  "confidence": 0.0
}}
"""


def _build_project_user_content(project_input: dict) -> str:
    lines = [
        f"Project: {project_input.get('projectName', 'Unnamed')}",
        f"Status: {project_input.get('projectStatus') or 'active'}",
        f"Problem Statement: {project_input.get('problemStatement') or 'Not defined'}",
    ]
    a3 = project_input.get("a3") or {}
    if a3:
        for field in ["scope", "objectives", "projectMetrics", "currentResults",
                      "businessUnitImpacted", "executiveSummary"]:
            val = a3.get(field)
            if val:
                lines.append(f"{field}: {val}")

    signals = (project_input.get("signals") or [])[:10]
    if signals:
        lines.append("\nRecent Signals:")
        for s in signals:
            lines.append(f"- [{s.get('signalType', 'signal')}] {str(s.get('content', ''))[:300]}")

    commitments = (project_input.get("commitments") or [])[:12]
    if commitments:
        lines.append("\nOpen Commitments:")
        for c in commitments:
            lines.append(f"- {c.get('description', '')} (due: {c.get('dueDate') or 'no date'})")

    tasks = (project_input.get("existingTasks") or [])[:25]
    if tasks:
        lines.append("\nExisting Tasks:")
        for t in tasks:
            lines.append(f"- [{t.get('status', 'open')}] {t.get('title', '')}")

    return "\n".join(lines)


async def run_a3_project_brief(project_input: dict) -> dict[str, Any]:
    """Workflow 9a — A3 Project Brief Planner. Single agent."""
    user_content = _build_project_user_content(project_input)
    result = await _call_agent(
        _SYS_A3_PLANNER, user_content,
        model=MODELS["narrative"], temperature=TEMPS["narrative"],
        agent_name="a3-project-brief-planner",
    )
    # Cap fields to prevent runaway output
    for field in ["scope", "objectives", "projectMetrics", "currentResults",
                  "team", "reviewPlan", "executiveSummary"]:
        val = result.get(field)
        if isinstance(val, str) and len(val) > 4000:
            result[field] = val[:4000]
    return result


async def run_tactical_implementation_plan(project_input: dict) -> dict[str, Any]:
    """Workflow 9b — Tactical Implementation Planner. Single agent + post-processing."""
    input_copy = dict(project_input)
    input_copy["signals"] = (project_input.get("signals") or [])[:8]
    input_copy["existingTasks"] = (project_input.get("existingTasks") or [])[:20]

    user_content = _build_project_user_content(input_copy)
    result = await _call_agent(
        _SYS_TACTICAL_PLANNER, user_content,
        model=MODELS["narrative"], temperature=TEMPS["narrative"],
        agent_name="tactical-implementation-planner",
    )

    if not result.get("milestones"):
        return result

    pruned = _prune_plan(result)
    if not pruned.get("milestones"):
        status = project_input.get("projectStatus", "active")
        pruned["milestones"] = [{
            "name": "Post-Launch Review" if status == "complete" else "Planning",
            "outcome": "Core planning gaps closed",
            "sequence": 1,
            "targetWeek": 2,
            "workstreams": [{
                "name": "Foundations",
                "sequence": 1,
                "steps": [{
                    "title": "Define project scope and problem statement",
                    "description": "Confirm boundaries, objectives, and success criteria.",
                    "priority": "high",
                    "ownerRole": "Project Lead",
                    "sequence": 1,
                    "acceptanceCriteria": ["Scope document approved by sponsor"],
                }],
            }],
        }]
    return pruned


# ---------------------------------------------------------------------------
# WORKFLOW 10 — Value Attribution
# ---------------------------------------------------------------------------

_SYS_VALUE_CALCULATOR = """
You are a value attribution agent. Estimate the business value of a project or initiative \
based on its description and progress signals.
Return JSON only:
{
  "projectedValue": 0,
  "realizedValue": 0,
  "confidence": 0.0,
  "valueType": "cost_savings|revenue_generation|risk_reduction|efficiency_gain|strategic",
  "reasoning": "Brief explanation of value estimate"
}
Be conservative. If value is speculative, use low confidence.
"""

_FCF_NODES = (
    "revenue | cogs | sga | rnd | other_expense | financial | taxes | "
    "ar | inventory | ap | other_current_liabilities | capex | capital_losses"
)

_SYS_FINANCIAL_IMPACT_ANALYST = f"""
You are Catalyst's senior financial impact analyst.

Persona:
- Think like an exceptional corporate finance partner: rigorous, skeptical, practical, \
and business-literate.
- Separate what is known from what is hypothesized.
- Never invent enterprise baselines. If a baseline is needed, request it from the data layer.
- Use the project database as the system of record for projects, assumptions, and approved \
impact records.
- Treat user-reported dollar values as direct impact when the amount is explicitly supplied.
- Be conservative. A defensible low-confidence estimate is better than a confident guess.
- Reason through Catalyst's standard project planning workflow before proposing value.
- If scope, BU/site/process, volume, baseline, target change, adoption, or financial conversion \
factors are missing, include them in missingInformation and baselineRequests.
- Create no enterprise dollar estimate without a defensible baseline, formula, source, \
and confidence.
- Include a practical example attribution scenario using clearly labeled hypothetical inputs \
when the project does not yet have enough real data. Do not present hypothetical values as \
approved impact.

{PROJECT_PLANNING_STANDARD}

{KPI_AND_VALUE_INPUT_CHECKLIST}

Impact mapping rules:
- Sales lift, conversion lift, price improvement, share gain -> revenue.
- Contractor spend, external services, operational labor reduction -> usually sga unless context \
says R&D, COGS, or production delivery.
- R&D workflow productivity, scientist/engineer time, lab cycle time -> rnd.
- Manufacturing or delivery cost reduction -> cogs.
- Inventory reduction, WIP reduction, finished goods reduction, raw material reduction -> inventory.
- Faster collections -> ar.
- Better payment terms or payable timing -> ap.
- Capital avoidance or reduced investment needs -> capex.
- Avoided write-offs, asset losses, or obsolescence -> capital_losses.

Return JSON only:
{{
  "analystSummary": "short CFO-ready summary",
  "overallConfidence": 0.0,
  "impacts": [
    {{
      "title": "short impact title",
      "impactMode": "direct|enterprise",
      "fcfNode": "{_FCF_NODES}",
      "valueType": "revenue_growth|expense_reduction|working_capital|capital_efficiency|risk_avoidance",
      "hypothesis": "what may change",
      "businessMechanism": "why that creates value",
      "formula": "plain-English formula",
      "baselineMetricNeeded": "metric needed from data source or null",
      "baselineSourcePreference": "databricks|reported_directly|not_required",
      "estimatedChangePercent": null,
      "directAmountUsd": null,
      "confidence": 0.0,
      "evidence": ["evidence from project context"],
      "assumptions": ["assumptions that must be validated"]
    }}
  ],
  "baselineRequests": [
    {{
      "metric": "metric name",
      "businessUnit": "BU or null",
      "product": "product or null",
      "region": "region or null",
      "timePeriod": "time period or null",
      "databricksQuestion": "specific question to ask data source",
      "neededForImpactTitle": "impact title"
    }}
  ],
  "financeReviewQuestions": ["questions finance should answer before approval"],
  "missingInformation": ["inputs needed to strengthen the model"],
  "exampleAttribution": {{
    "scenario": "example scenario name",
    "inputs": ["hypothetical or known input"],
    "formula": "plain-English formula",
    "estimatedAnnualImpactUsd": null,
    "fcfPlacement": "where this rolls up on the FCF tree",
    "notes": "why this is illustrative, pending baseline, or finance review"
  }}
}}
"""


async def _calculate_one_project_value(project: dict) -> dict[str, Any]:
    pct_done = 0.0
    total = project.get("totalTasks", 0)
    completed = project.get("completedTasks", 0)
    if total > 0:
        pct_done = completed / total

    user_content = (
        f"Project: {project.get('name', 'Unnamed')}\n"
        f"Description: {project.get('description', 'No description')}\n"
        f"Progress: {completed}/{total} tasks complete ({pct_done:.0%})"
    )
    result = await _call_agent(
        _SYS_VALUE_CALCULATOR, user_content,
        model=MODELS["extraction"], temperature=TEMPS["extraction"],
        agent_name="value-calculator",
    )
    return {
        "projectId":      project.get("id", ""),
        "projectedValue": float(result.get("projectedValue", 0)),
        "realizedValue":  float(result.get("realizedValue", 0)),
        "confidence":     float(result.get("confidence", 0.3)),
        "valueType":      result.get("valueType", "strategic"),
        "reasoning":      result.get("reasoning", ""),
    }


async def run_value_attribution(projects: list[dict]) -> list[dict[str, Any]]:
    """Workflow 10a — Value Calculator. All projects in parallel."""
    if not projects:
        return []
    tasks = [_calculate_one_project_value(p) for p in projects]
    return list(await asyncio.gather(*tasks))


async def run_financial_impact_analysis(project_input: dict) -> dict[str, Any]:
    """Workflow 10b — Financial Impact Analyst. Single comprehensive agent."""
    lines = [
        f"Project: {project_input.get('projectName', 'Unnamed')}",
        f"Problem Statement: {project_input.get('problemStatement') or 'Not defined'}",
    ]
    if project_input.get("databricksGuidance"):
        lines.append(f"Data Guidance: {project_input['databricksGuidance']}")

    a3 = project_input.get("a3") or {}
    for field in ["businessUnitImpacted", "scope", "objectives", "projectMetrics",
                  "currentResults", "directImpactAmount", "executiveSummary"]:
        val = a3.get(field)
        if val:
            lines.append(f"{field}: {val}")

    signals = (project_input.get("signals") or [])[:8]
    if signals:
        lines.append("\nRecent Signals:")
        for s in signals:
            lines.append(
                f"- [{s.get('signalType', 'signal')}] "
                f"{str(s.get('content', ''))[:300]} "
                f"({s.get('createdAt', '')})"
            )

    memory = (project_input.get("memory") or [])[:10]
    if memory:
        lines.append("\nProject Memory:")
        for m in memory:
            lines.append(f"- [{m.get('memoryType', 'note')}] {m.get('memoryText', '')}")

    pref_rules = (project_input.get("preferenceRules") or [])[:20]
    pref_block = _build_preference_block(pref_rules)

    result = await _call_agent(
        _SYS_FINANCIAL_IMPACT_ANALYST + pref_block,
        "\n".join(lines),
        model=MODELS["narrative"], temperature=TEMPS["narrative"],
        agent_name="financial-impact-analyst",
    )
    return result


# ---------------------------------------------------------------------------
# Sync convenience wrappers
# Uses asyncio.run() — do not call from inside an already-running event loop.
# For use in synchronous JARVIS request handlers.
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine from synchronous context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(asyncio.run, coro)
                return future.result(timeout=120)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def extract_meeting(transcript: str, preference_rules: list[str] | None = None) -> dict:
    return _run(run_meeting_extraction(transcript, preference_rules))


def classify_signal(content: str, signal_type: str, projects: list[dict]) -> dict:
    return _run(run_signal_classification(content, signal_type, projects))


def triage_email(subject: str, body: str, sender: str) -> dict:
    return _run(run_email_triage(subject, body, sender))


def generate_briefing(
    signals: list[dict],
    open_commitments: int = 0,
    overdue_count: int = 0,
) -> dict:
    return _run(run_briefing_generation(signals, open_commitments, overdue_count))


def track_commitments(commitments: list[dict], recent_signals: list[str]) -> list[dict]:
    return _run(run_commitment_tracking(commitments, recent_signals))


def compose_draft(
    intent: str,
    context: str,
    recipient: str,
    tone: str = "professional",
) -> dict:
    return _run(run_draft_composition(intent, context, recipient, tone))


def prep_for_meeting(
    meeting_title: str,
    open_commitments: list[str],
    recent_signals: list[str],
) -> dict:
    return _run(run_pre_meeting_prep(meeting_title, open_commitments, recent_signals))


def surface_opportunities(
    open_commitments: list[str],
    active_projects: list[str],
) -> dict:
    return _run(run_proactive_surfacing(open_commitments, active_projects))


def plan_a3_brief(project_input: dict) -> dict:
    return _run(run_a3_project_brief(project_input))


def plan_tactical(project_input: dict) -> dict:
    return _run(run_tactical_implementation_plan(project_input))


def attribute_values(projects: list[dict]) -> list[dict]:
    return _run(run_value_attribution(projects))


def analyze_financial_impact(project_input: dict) -> dict:
    return _run(run_financial_impact_analysis(project_input))


# ---------------------------------------------------------------------------
# WorkIntelligenceEngine — orchestrates all workflows with DB logging
# ---------------------------------------------------------------------------

class WorkIntelligenceEngine:
    """
    High-level façade over all workflows. Logs runs to CatalystDB.
    This is the class JARVIS agents and API endpoints interact with.
    """

    def __init__(self, db=None, user_id: str = "chris") -> None:
        # db: CatalystDB instance (optional — degrades gracefully if None)
        self._db = db
        self._user_id = user_id

    def _db_log(
        self,
        workflow_name: str,
        status: str = "success",
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        if self._db is None:
            return
        try:
            self._db.log_system_event(
                self._user_id,
                workflow_name,
                status=status,
                latency_ms=latency_ms,
                error_message=error,
            )
        except Exception:
            pass

    def _timed_run(self, workflow_name: str, coro):
        t0 = time.monotonic()
        try:
            result = _run(coro)
            latency = int((time.monotonic() - t0) * 1000)
            self._db_log(workflow_name, "success", latency_ms=latency)
            return result
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            self._db_log(workflow_name, "failed", latency_ms=latency, error=str(exc))
            log.error("WorkIntelligenceEngine %s failed: %s", workflow_name, exc)
            return None

    # Public workflow methods

    def meeting_extraction(self, transcript: str, preference_rules: list[str] | None = None) -> dict | None:
        return self._timed_run("meeting_extraction", run_meeting_extraction(transcript, preference_rules))

    def signal_classification(self, content: str, signal_type: str, projects: list[dict]) -> dict | None:
        return self._timed_run("signal_classification", run_signal_classification(content, signal_type, projects))

    def email_triage(self, subject: str, body: str, sender: str) -> dict | None:
        return self._timed_run("email_triage", run_email_triage(subject, body, sender))

    def briefing_generation(
        self,
        signals: list[dict],
        open_commitments: int = 0,
        overdue_count: int = 0,
    ) -> dict | None:
        return self._timed_run(
            "briefing_generation",
            run_briefing_generation(signals, open_commitments, overdue_count),
        )

    def commitment_tracking(self, commitments: list[dict], recent_signals: list[str]) -> list[dict] | None:
        return self._timed_run("commitment_tracking", run_commitment_tracking(commitments, recent_signals))

    def draft_composition(self, intent: str, context: str, recipient: str, tone: str = "professional") -> dict | None:
        return self._timed_run("draft_composition", run_draft_composition(intent, context, recipient, tone))

    def pre_meeting_prep(self, meeting_title: str, commitments: list[str], signals: list[str]) -> dict | None:
        return self._timed_run("pre_meeting_prep", run_pre_meeting_prep(meeting_title, commitments, signals))

    def proactive_surfacing(self, commitments: list[str], projects: list[str]) -> dict | None:
        return self._timed_run("proactive_surfacing", run_proactive_surfacing(commitments, projects))

    def a3_project_brief(self, project_input: dict) -> dict | None:
        return self._timed_run("a3_project_brief", run_a3_project_brief(project_input))

    def tactical_plan(self, project_input: dict) -> dict | None:
        return self._timed_run("tactical_implementation_plan", run_tactical_implementation_plan(project_input))

    def value_attribution(self, projects: list[dict]) -> list[dict] | None:
        return self._timed_run("value_attribution", run_value_attribution(projects))

    def financial_impact(self, project_input: dict) -> dict | None:
        return self._timed_run("financial_impact_analysis", run_financial_impact_analysis(project_input))

    def get_work_summary(self) -> dict:
        if self._db is None:
            return {}
        return self._db.get_work_summary(self._user_id)

    def get_proactive_suggestions(self) -> list[dict]:
        """Pull open commitments + active projects from DB, then surface opportunities."""
        if self._db is None:
            return []
        try:
            commitments = self._db.list_open_commitments(self._user_id)
            projects    = self._db.list_projects(self._user_id, status="active")
            commit_texts  = [c.get("description", "") for c in commitments[:10]]
            project_names = [p.get("name", "") for p in projects[:5]]
            result = self.proactive_surfacing(commit_texts, project_names)
            return (result or {}).get("suggestions", [])
        except Exception as exc:
            log.warning("get_proactive_suggestions error: %s", exc)
            return []


# ---------------------------------------------------------------------------
# Module-level engine singleton
# ---------------------------------------------------------------------------

_engine: WorkIntelligenceEngine | None = None


def get_work_intelligence(db=None, user_id: str = "chris") -> WorkIntelligenceEngine:
    """Return module-level WorkIntelligenceEngine singleton."""
    global _engine
    if _engine is None:
        _engine = WorkIntelligenceEngine(db=db, user_id=user_id)
    return _engine


def init_work_intelligence(db=None, user_id: str = "chris") -> WorkIntelligenceEngine:
    """Initialise (or reinitialise) the singleton. Call once at JARVIS startup."""
    global _engine
    _engine = WorkIntelligenceEngine(db=db, user_id=user_id)
    log.info("WorkIntelligenceEngine initialised (user=%s, db=%s)", user_id, "yes" if db else "no")
    return _engine

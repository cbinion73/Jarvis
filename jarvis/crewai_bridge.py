from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


def crewai_runtime_available() -> bool:
    try:
        import crewai  # noqa: F401
    except Exception:
        return False
    return True


def _extract_json_block(raw: str, opening: str, closing: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
        else:
            text = "\n".join(lines[1:]).strip()
    start = text.find(opening)
    end = text.rfind(closing)
    if start < 0 or end < start:
        return ""
    return text[start : end + 1]


def _normalize_idea_records(items: Any, *, limit: int) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []
    results: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        idea = str(item.get("idea", "")).strip()
        normalized = title.lower()
        if not title or not idea or normalized in seen_titles:
            continue
        seen_titles.add(normalized)
        results.append({"title": title, "idea": idea})
        if len(results) >= max(1, int(limit)):
            break
    return results


@dataclass(slots=True)
class CrewAIExecutionResult:
    raw: str


class CrewAIPartyModeBridge:
    def __init__(self, *, llm: str | None = None, verbose: bool = False) -> None:
        self.llm = str(llm or os.getenv("CREWAI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
        self.verbose = bool(verbose)

    def dream_passive_income_ideas(self, needed: int) -> list[dict[str, str]]:
        raw = self._run_idea_crew(max(1, int(needed)))
        block = _extract_json_block(raw.raw, "[", "]")
        if not block:
            return []
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            return []
        return _normalize_idea_records(payload, limit=needed)

    def build_research_brief(self, *, title: str, idea: str, domain: str = "passive-income") -> dict[str, str]:
        raw = self._run_research_crew(title=title, idea=idea, domain=domain)
        block = _extract_json_block(raw.raw, "{", "}")
        if not block:
            return {}
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            return {}
        research_notes = str(payload.get("research_notes", "")).strip()
        proposal_text = str(payload.get("proposal_text", "")).strip()
        first_action = str(payload.get("first_action", "")).strip()
        return {
            "research_notes": research_notes,
            "proposal_text": proposal_text,
            "first_action": first_action,
        }

    def _run_idea_crew(self, needed: int) -> CrewAIExecutionResult:
        prompt = (
            "Create realistic passive-income ideas for Chris Binion. "
            f"Return exactly {needed} items as a JSON array with keys title and idea. "
            "Focus on software, digital products, content licensing, or small automated services. "
            "Each idea should be concrete, plausible, and fit a solo software developer."
        )
        return self._run_crew(
            crew_role="Passive Income Foundry",
            crew_goal="Generate and filter realistic passive-income ideas.",
            task_description=prompt,
            expected_output='JSON array like [{"title":"...","idea":"..."}]',
        )

    def _run_research_crew(self, *, title: str, idea: str, domain: str) -> CrewAIExecutionResult:
        prompt = (
            f"Business title: {title}\n"
            f"Domain: {domain}\n"
            f"Origin idea: {idea}\n\n"
            "Produce a compact overnight research brief for JARVIS party mode. "
            "Return a JSON object with keys research_notes, proposal_text, and first_action. "
            "research_notes should summarize opportunity, demand signals, competition, and key risks. "
            "proposal_text should be a short staged pitch for Chris. "
            "first_action should be one concrete first step."
        )
        return self._run_crew(
            crew_role="Overnight Research Steward",
            crew_goal="Prepare a bounded overnight research brief for a single work item.",
            task_description=prompt,
            expected_output='JSON object like {"research_notes":"...","proposal_text":"...","first_action":"..."}',
        )

    def _run_crew(self, *, crew_role: str, crew_goal: str, task_description: str, expected_output: str) -> CrewAIExecutionResult:
        try:
            from crewai import Agent, Crew, Process, Task
        except Exception as exc:
            raise RuntimeError(f"CrewAI runtime unavailable: {exc}") from exc

        agent = Agent(
            role=crew_role,
            goal=crew_goal,
            backstory=(
                "You are an internal JARVIS specialist. "
                "You operate inside a supervised, bounded overnight execution lane. "
                "Be concrete, concise, and output only the requested JSON structure."
            ),
            llm=self.llm,
            verbose=self.verbose,
            allow_delegation=False,
        )
        task = Task(
            description=task_description,
            expected_output=expected_output,
            agent=agent,
        )
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=self.verbose,
        )
        result = crew.kickoff()
        raw = getattr(result, "raw", None)
        if raw is None:
            raw = str(result)
        return CrewAIExecutionResult(raw=str(raw or "").strip())


from __future__ import annotations

import re
from pathlib import Path

from .config import AppConfig
from .openai_tasks import JarvisOpenAIClient
from .persona import build_specialist_prompt


class ExecutiveSupport:
    def __init__(self, config: AppConfig, openai_client: JarvisOpenAIClient) -> None:
        self.config = config
        self.openai_client = openai_client
        self.profile = config.load_json_profile(
            config.executive_profile_path,
            {
                "confidentialTerms": [],
                "meetingBriefStyle": {"sections": []},
                "evidenceTiers": {},
                "ironCladEditor": {"principles": []},
                "ventureBriefStyle": {"sections": []},
            },
        )

    def meeting_brief(self, actor: str, context: str) -> str:
        sections = ", ".join(self.profile.get("meetingBriefStyle", {}).get("sections", []))
        system = build_specialist_prompt(
            "executive brief",
            "Build a concise meeting brief with sections, direct judgment, likely objections, and one clean question to ask.",
            extra_guidance=f"Preferred sections: {sections}.",
        )
        user = (
            f"Actor: {actor}\n"
            "Build a polished meeting brief from the following context.\n\n"
            f"{context}"
        )
        return self.openai_client.prompt_text(system, user, max_output_tokens=500)

    def meeting_followup(self, actor: str, transcript: str) -> str:
        system = build_specialist_prompt(
            "meeting follow-up",
            "Extract commitments, unresolved decisions, owners, hedged language, and next moves.",
            extra_guidance="Be structured and direct.",
        )
        user = (
            f"Actor: {actor}\n"
            "Review this meeting transcript or notes and produce a follow-up matrix.\n\n"
            f"{transcript}"
        )
        return self.openai_client.prompt_text(system, user, max_output_tokens=500)

    def research_summary(self, actor: str, topic: str, notes: str) -> str:
        evidence_tiers = self.profile.get("evidenceTiers", {})
        system = build_specialist_prompt(
            "evidence-tiering",
            "Summarize the topic, separate evidence by tier, state why it matters, and clearly mark uncertainty.",
            extra_guidance=(
                f"Use these tiers: A={evidence_tiers.get('A', '')} "
                f"B={evidence_tiers.get('B', '')} C={evidence_tiers.get('C', '')}."
            ),
        )
        user = (
            f"Actor: {actor}\n"
            f"Topic: {topic}\n"
            "Create a research summary from the source notes below. "
            "Do not invent citations that are not present in the notes.\n\n"
            f"{notes}"
        )
        return self.openai_client.prompt_text(system, user, max_output_tokens=550)

    def decision_framework(self, actor: str, context: str) -> str:
        system = build_specialist_prompt(
            "decision-framework coaching",
            "Convert vague enthusiasm into explicit decision criteria, decision gates, tradeoffs, and one framing question.",
            extra_guidance=(
                "Assume the room may not actually be ready to decide on a solution yet. "
                "Return labeled sections: Situation, Criteria, Tradeoffs, Decision Gates, Room Read, One Clean Question, Next Move."
            ),
        )
        user = (
            f"Actor: {actor}\n"
            "Build a decision framework from the following meeting situation, notes, or draft agenda.\n\n"
            f"{context}"
        )
        return self.openai_client.prompt_text(system, user, max_output_tokens=550)

    def confidentiality_review(self, text: str) -> dict:
        flagged_terms = []
        redacted = text
        for term in self.profile.get("confidentialTerms", []):
            if not term:
                continue
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            if pattern.search(redacted):
                flagged_terms.append(term)
                redacted = pattern.sub("[REDACTED]", redacted)

        email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
        if email_pattern.search(redacted):
            flagged_terms.append("email-address")
            redacted = email_pattern.sub("[REDACTED_EMAIL]", redacted)

        internal_doc_pattern = re.compile(r"\b[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+){1,4} (?:strategy|roadmap|brief|prototype)\b")
        matches = internal_doc_pattern.findall(redacted)
        if matches:
            flagged_terms.extend(sorted(set(matches)))
            redacted = internal_doc_pattern.sub("[REDACTED_INTERNAL_TITLE]", redacted)

        return {
            "flagged_terms": sorted(set(flagged_terms)),
            "redacted_text": redacted,
            "safe_to_share": len(flagged_terms) == 0,
        }

    def manuscript_review(self, actor: str, excerpt: str) -> str:
        system = build_specialist_prompt(
            "manuscript editor",
            "Improve clarity, reduce jargon, and preserve strong executive prose.",
            extra_guidance="Point out where claims outrun evidence.",
        )
        user = (
            f"Actor: {actor}\n"
            "Review the following manuscript excerpt. "
            "Return a concise edit memo and one proposed rewrite for the weakest paragraph.\n\n"
            f"{excerpt}"
        )
        return self.openai_client.prompt_text(system, user, max_output_tokens=500)

    def iron_clad_editor(self, actor: str, excerpt: str) -> str:
        principles = ", ".join(self.profile.get("ironCladEditor", {}).get("principles", []))
        system = build_specialist_prompt(
            "Iron-Clad Executive Editor",
            "Tighten structure, cut inflated language, flag unsupported claims, and preserve the author's authority.",
            extra_guidance=(
                "Be exacting without becoming theatrical. "
                "Return labeled sections: Executive Edit Memo, Cuts or Risks, Stronger Line, Rewrite. "
                f"Editing principles: {principles}."
            ),
        )
        user = (
            f"Actor: {actor}\n"
            "Review the following passage in Iron-Clad Executive Editor mode.\n\n"
            f"{excerpt}"
        )
        return self.openai_client.prompt_text(system, user, max_output_tokens=600)

    def venture_brief(self, actor: str, topic: str, notes: str) -> str:
        sections = ", ".join(self.profile.get("ventureBriefStyle", {}).get("sections", []))
        system = build_specialist_prompt(
            "venture and market-monitoring",
            "Synthesize weak and strong signals into a brief for an executive operator.",
            extra_guidance=(
                "Distinguish real movement from vendor fog, state the pattern, why it matters, and what deserves attention next. "
                f"Preferred sections: {sections}."
            ),
        )
        user = (
            f"Actor: {actor}\n"
            f"Topic: {topic}\n"
            "Build a venture and market-monitoring brief from the following notes. "
            "If the notes are thin, say so plainly.\n\n"
            f"{notes}"
        )
        return self.openai_client.prompt_text(system, user, max_output_tokens=600)

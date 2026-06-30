from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import RequestPlan, UserProfile
from .openai_tasks import OpenAIResult

VOICE_STANDARD = (
    "Direct, warm, practical, concise, slightly playful when helpful, willing to push back, honest about limits."
)

THERAPIST_LANGUAGE_PATTERNS = (
    "your concern is valid",
    "let's explore what this means for you",
    "multidimensional life transition",
    "this is really about",
)

GENERIC_CHATBOT_PATTERNS = (
    "as an ai assistant",
    "i'm here to help with that",
    "i understand how you feel",
)

GENERIC_EMPATHY_PATTERNS = (
    "that sounds hard",
    "that sounds really hard",
    "i'm sorry you're dealing with that",
    "i am sorry you're dealing with that",
    "i'm sorry you're going through that",
    "i am sorry you're going through that",
)

OVEREXPLAINING_PATTERNS = (
    "that's a really good question",
    "that's a good question",
    "that's a thoughtful question",
    "there are a few ways to think about this",
    "it's worth taking a step back",
    "it probably makes sense to start by saying",
    "the important thing here is that",
    "at a high level",
    "in a lot of ways",
)

ABSTRACT_MEANING_PATTERNS = (
    "what this means for you",
    "sense of purpose",
    "life transition",
    "deeper meaning",
    "identity shift",
)

VAGUE_REFLECTIVE_QUESTION_PATTERNS = (
    "how does that feel for you",
    "how does that feel",
    "what would success look like here",
    "what does success look like here",
)

FLAT_DECISION_REPLY_PATTERNS = (
    "it depends what matters most to you",
    "there are pros and cons to both",
    "both have pros and cons",
    "you could make a case for either",
)

HEDGED_PRACTICAL_REPLY_PATTERNS = (
    "maybe start by",
    "it could make sense to",
    "you might want to",
    "probably start by",
    "think about what matters most",
    "take a step back and think about it",
)

SOFT_PLANNING_REPLY_PATTERNS = (
    "let's organize it",
    "see what fits",
    "sort the week",
    "sort it out",
    "prioritize everything",
    "make a list",
    "make a plan",
)

OVERLOADED_PLANNING_REQUEST_TERMS = (
    "week under control",
    "under control",
    "overwhelmed",
    "swamped",
    "too much",
    "behind",
    "priorities",
    "juggling",
    "packed",
    "calendar",
    "schedule",
)

CAPACITY_PUSHBACK_TERMS = (
    "one cut",
    "immovable",
    "cannot fit",
    "can't fit",
    "cannot do all",
    "can't do all",
    "what can slip",
    "what has to drop",
    "what has to move",
)

DECISION_REQUEST_TERMS = (
    "decision",
    "deciding",
    "should i",
    "torn between",
    "choose",
    "choosing",
    "choice",
    "which option",
    "stay or leave",
    "staying and leaving",
    "leave my job",
    "leave this job",
    "quit my job",
    "should quit",
    "need to quit",
    "resign",
    "should resign",
    "need to resign",
    "want out of this job",
    "put in my notice",
    "hand in my notice",
    "walk away from this job",
    "leave this company",
    "take the new job",
    "new job",
)

DECISION_TRADEOFF_TERMS = (
    "money",
    "energy",
    "risk",
    "regret",
    "stability",
    "upside",
    "downside",
    "tradeoff",
    "cost",
    "future",
)

TRUTHFUL_LIMITATION_PATTERNS = (
    "not wired into this conversation yet",
    "i have not saved it",
    "i do not have a finished agent output",
    "i don't have a surface ready for that yet",
    "i can reason through this with you, but",
    "the model path is down right now",
)

RAW_CAPABILITY_LABEL_PATTERNS = (
    "ongoing conversation in this shell",
    "conversation turn persistence",
    "recent conversation continuity",
    "durable profile facts already stored locally",
    "planning and drafting in chat",
    "family calendar summary when available",
    "live weather summary when available",
    "live obsidian retrieval not active in the default conversation path",
    "local obsidian vault retrieval with quoted snippets when notes match",
)

FOLLOW_UP_RESET_PATTERNS = (
    "give me the short version",
    "which part feels off",
    "what's on your mind",
    "what do you want to get done",
    "is this mostly a decision, a conversation, or a plan",
)

GENERIC_TAXONOMY_OPENERS = (
    "is the real work",
    "is this mostly",
    "what part feels off",
    "what's on your mind",
    "what do you want to get done",
    "give me the short version",
)

TRUTH_CONSTRAINTS = [
    "Do not claim you searched, opened, saved, remembered, created, emailed, scheduled, retrieved, or completed anything unless that action actually happened in this turn.",
    "Do not imply Obsidian retrieval, indexing, or citation exists in this conversation path.",
    "Distinguish what you know from the current message, persisted conversation, durable profile facts, and live context.",
    "If context or a tool is unavailable, say so plainly instead of bluffing.",
]

FORBIDDEN_PATTERNS = [
    "therapy language",
    "mystical language",
    "corporate dashboard language",
    "generic chatbot disclaimers",
    "over-explaining",
    "pretending ordinary conversation is a module handoff",
]

OBSIDIAN_STATUS = (
    "Obsidian is a local external source reserved for a later grounding phase. "
    "In the default conversation path, say plainly that live Obsidian retrieval is not wired into this conversation yet."
)

_DOCS_ROOT = Path(__file__).resolve().parents[1] / "docs"
_CHRIS_CONTEXT_CANON_PATH = _DOCS_ROOT / "CHRIS-CONTEXT-CANON.md"
_CHRIS_INTENT_CANON_PATH = _DOCS_ROOT / "CHRIS-INTENT-CANON.md"
_CANON_CACHE: dict[str, str] = {}


def build_context_packet(
    runtime: Any,
    actor: UserProfile,
    room: str,
    request: str,
    *,
    plan: RequestPlan,
    conversation_excerpt: str,
) -> dict[str, Any]:
    correction_context = _correction_context(request, conversation_excerpt)
    effective_request = str((correction_context or {}).get("last_user_message") or request or "").strip()
    known_facts: list[str] = []
    try:
        known_facts = list(runtime._relevant_profile_facts(actor, effective_request, limit=4))
    except Exception:
        known_facts = []

    active_context_blocks: list[str] = []
    if _should_include_live_context(effective_request):
        live_context = _compact_live_context(runtime)
        if live_context:
            active_context_blocks.append(live_context)
    elif _is_operating_status_request(runtime, effective_request):
        status_lines = _live_status_lines(runtime, actor.display_name)
        if status_lines:
            active_context_blocks.append("\n".join(status_lines))
    obsidian_context = _obsidian_context(runtime, effective_request)
    if obsidian_context:
        active_context_blocks.append(obsidian_context)
    active_context = "\n\n".join(block for block in active_context_blocks if str(block).strip()) or None
    topic_brief = _topic_brief(effective_request)
    canon_brief = _canon_brief_for_request(effective_request)
    response_contract = _response_contract_for_request(
        request,
        effective_request=effective_request,
        correction_context=correction_context,
    )

    return {
        "user_message": str(request or "").strip(),
        "effective_user_message": effective_request,
        "conversation_excerpt": str(conversation_excerpt or "").strip(),
        "known_user_profile": {
            "display_name": actor.display_name,
            "role": actor.role,
            "address_as": actor.address_as,
            "priorities": list(actor.priorities or []),
            "known_facts": known_facts,
        },
        "active_context": active_context,
        "relationship_model": "smart, loyal friend with tools",
        "correction_context": correction_context,
        "topic_brief": topic_brief,
        "canon_brief": canon_brief,
        "response_contract": response_contract,
        "available_capabilities": _available_capabilities(runtime),
        "truth_constraints": list(TRUTH_CONSTRAINTS),
        "voice_standard": VOICE_STANDARD,
        "forbidden_patterns": list(FORBIDDEN_PATTERNS),
    }


def build_companion_system_prompt(packet: dict[str, Any]) -> str:
    capabilities = packet.get("available_capabilities", [])
    capabilities_text = "; ".join(str(item) for item in capabilities if str(item).strip())
    truth_text = "\n".join(f"- {item}" for item in packet.get("truth_constraints", []))
    forbidden_text = "\n".join(f"- {item}" for item in packet.get("forbidden_patterns", []))
    return (
        "You are Jarvis, Chris's private AI companion. "
        "Your default posture is one smart, loyal friend with tools.\n\n"
        "Voice standard:\n"
        f"{packet.get('voice_standard', VOICE_STANDARD)}\n\n"
        "Conversation rules:\n"
        "- Stay in normal conversation unless the user explicitly asks for a tool action, module, or workflow.\n"
        "- Be useful fast. Lead with the thought, question, or next move that matters most.\n"
        "- Answer like someone who already knows Chris's life trajectory, not like a fresh-session assistant.\n"
        "- Start with your read of the situation. Give a personalized thesis before you ask for more detail.\n"
        "- Use the context packet to synthesize what you already know about Chris, his goals, and his likely pressure points.\n"
        "- When enough context is already present, do not ask taxonomy questions like 'is the real work...' or 'is this mostly...'.\n"
        "- If you ask a question, it should narrow a real unknown after you have already given useful judgment.\n"
        "- Push back when the user is rationalizing, drifting, or making the plan fuzzy.\n"
        "- Keep the tone human. No therapist voice, no mystical framing, no dashboard theater.\n"
        "- If the user corrects your last answer, absorb that correction and rewrite the answer directly.\n"
        "- Do not defend the old answer, explain your process, or turn the correction into a taxonomy exercise.\n"
        "- If the user asks what you can do, answer from grounded capabilities only.\n"
        "- If context is missing, say that plainly and continue helpfully.\n\n"
        "Truth constraints:\n"
        f"{truth_text}\n\n"
        "Forbidden patterns:\n"
        f"{forbidden_text}\n\n"
        "Grounded capabilities for this path:\n"
        f"- {capabilities_text}\n\n"
        "Obsidian status:\n"
        f"- {OBSIDIAN_STATUS}\n\n"
        "Source distinction:\n"
        "- If active context contains retrieved Obsidian notes, describe them as retrieved note context, not as memory or certainty beyond the note.\n"
        "Keep answers concise by default. Prefer short natural prose over lists unless a list is clearly useful."
    ).strip()


def run_companion_turn(
    runtime: Any,
    actor: UserProfile,
    room: str,
    request: str,
    *,
    plan: RequestPlan,
    continuity_context: str,
) -> OpenAIResult:
    packet = build_context_packet(
        runtime,
        actor,
        room,
        request,
        plan=plan,
        conversation_excerpt=continuity_context,
    )
    system_prompt = build_companion_system_prompt(packet)
    supplemental_context = _packet_to_context(packet)
    result = runtime.openai_client.respond(
        plan,
        supplemental_context=supplemental_context,
        system_prompt_override=system_prompt,
    )
    output_text = str(result.output_text or "").strip()
    if result.provider == "fallback" or not output_text:
        output_text = generate_companion_fallback(request, packet, runtime=runtime)
    else:
        output_text = harden_companion_reply(request, output_text, packet)
    return OpenAIResult(
        provider=result.provider,
        model=result.model,
        output_text=output_text,
    )


def generate_companion_fallback(
    request: str,
    packet: dict[str, Any],
    runtime: Any | None = None,
) -> str:
    cleaned = str(request or "").strip()
    lowered = cleaned.lower()
    correction_reply = _correction_fallback_reply(packet)
    if correction_reply:
        return correction_reply
    follow_up_reply = _fork_follow_up_continuation_reply(cleaned, packet)
    if follow_up_reply:
        return follow_up_reply

    contextual_reply = _contextual_thesis_first_reply(cleaned, packet)
    if contextual_reply:
        return contextual_reply

    if "obsidian" in lowered:
        obsidian_reply = _obsidian_fallback_reply(runtime, request)
        if obsidian_reply:
            return obsidian_reply
        return (
            "I have the Obsidian vault path recorded, but live retrieval is not wired into this conversation yet."
        )
    if re.fullmatch(r"(hey|hi|okay|ok)?[\s,.:;-]*jarvis[\s,.:;-]*", lowered) or lowered in {"hey jarvis", "hi jarvis", "jarvis"}:
        return "Hey. I'm here. What's on your mind, or what do you want to get done?"
    if "don't know if jarvis is working" in lowered or "is jarvis working" in lowered:
        return "Yeah, I'm here. Give me one real decision, plan, or draft and I'll show you the path is alive."
    if "chatbot" in lowered:
        return "Yeah. If I can't help you think or do useful work, I'm just theater. The point is conversation plus real help, not assistant cosplay."
    if any(
        phrase in lowered
        for phrase in (
            "what this means for my life",
            "what this means for you",
            "usually not about vacation",
            "your concern is valid",
        )
    ):
        return (
            "Maybe. But let's keep it practical. Is this really about rest, money, people, "
            "or the fact that work still knows how to climb in the car with you?"
        )
    retirement_document_terms = ("essay", "memo", "chapter", "review", "overview", "outline", "recap")
    is_retirement_document_prompt = "retirement" in lowered and any(term in lowered for term in retirement_document_terms)
    if (
        not is_retirement_document_prompt
        and (
            "retire" in lowered
            or any(
                phrase in lowered
                for phrase in (
                    "step back from work",
                    "step away from work for good",
                    "slow down at work for good",
                    "ease out of work",
                    "wind down my career",
                    "be done working soon",
                )
            )
        )
    ):
        return (
            "For you, I don't think retirement means doing nothing. I think it means getting work out of the driver's seat. "
            "Do you want to think about money, time, or identity first?"
        )
    vacation_document_terms = ("essay", "chapter", "memo", "report", "note", "review", "outline", "summary", "recap", "overview")
    is_vacation_document_prompt = any(term in lowered for term in vacation_document_terms)
    if (
        not is_vacation_document_prompt
        and (
            any(term in lowered for term in ("vacation", "trip", "travel"))
            or "get away" in lowered
            or "go away" in lowered
            or "out of town" in lowered
        )
    ):
        return "Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
    if not is_vacation_document_prompt and any(term in lowered for term in ("hotel", "flight")):
        return "Good. If this is already a logistics problem, give me destination, dates, and who's coming, and I'll help you get it organized."
    book_work_nouns = ("book", "memoir", "manuscript", "novel", "autobiography", "biography")
    if (
        any(f"latest {noun}" in lowered for noun in book_work_nouns)
        or any(f"{noun} chapter" in lowered for noun in book_work_nouns)
        or (
            any(noun in lowered for noun in book_work_nouns)
            and any(
                phrase in lowered
                for phrase in (
                    "work on my",
                    "help with my",
                    "write my",
                    "outline my",
                    "outlining my",
                    "stuck on my",
                    "revise my",
                    "revising my",
                )
            )
        )
    ):
        return "Good. What's the book, and do you need help outlining, writing, revising, or getting unstuck?"
    if _is_presentation_or_proposal_prep_request(cleaned):
        return "Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?"
    if _is_agenda_request(cleaned):
        return "Good. Is the real work what needs to be covered, what can wait, or how to keep the conversation from drifting?"
    if _is_inbox_request(cleaned):
        return (
            "Good. Is the real problem triage, replies you owe, or clearing the pile "
            "without getting sucked into it?"
        )
    if _is_follow_up_request(cleaned):
        return (
            "Good. Is the real work the message you owe, the decision you need before you send it, "
            "or the next move you need to lock in?"
        )
    if _is_meeting_prep_request(cleaned):
        return (
            "Good. Is the real work for this meeting the outcome you need, "
            "how you need to say it, or the agenda you need to walk in with?"
        )
    if _is_constraints_scheduling_request(cleaned):
        return "Good. What is fixed, what actually has to happen, and what can move around those constraints?"
    if _is_tomorrow_planning_request(cleaned):
        return "Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?"
    if "push back on me" in lowered:
        return "Gladly. If you're dodging the hard part, making the plan too pretty, or lying to yourself about capacity, I'll say it."
    if _is_capability_request(cleaned):
        return _grounded_capability_reply(packet)
    if _request_needs_practical_handle(cleaned):
        return _generic_practical_fallback_reply(cleaned)
    if cleaned:
        return _generic_non_practical_fallback_reply(cleaned)
    return "I'm here."


def harden_companion_reply(request: str, reply: str, packet: dict[str, Any]) -> str:
    cleaned_reply = str(reply or "").strip()
    if not cleaned_reply:
        return ""
    if _is_truthful_limitation_reply(cleaned_reply):
        return cleaned_reply
    if _reply_is_generic_taxonomy_opener(cleaned_reply):
        contextual = _contextual_thesis_first_reply(request, packet)
        if contextual:
            return contextual
    follow_up_reply = _fork_follow_up_continuation_reply(request, packet)
    if follow_up_reply and _reply_is_generic_follow_up_reset(cleaned_reply):
        return follow_up_reply
    if _needs_overexplaining_trim(cleaned_reply):
        cleaned_reply = _trim_overexplaining_reply(cleaned_reply)
    if _is_capability_request(request):
        if _needs_capability_answer_grounding(cleaned_reply, packet):
            return _grounded_capability_reply(packet)
        return cleaned_reply
    if _reply_needs_capacity_pushback(request, cleaned_reply):
        return _capacity_pushback_reply(request)
    if not _needs_companion_reply_repair(request, cleaned_reply):
        return cleaned_reply
    repaired = _practical_repair_reply(request, packet)
    return repaired or cleaned_reply


def _packet_to_context(packet: dict[str, Any]) -> str:
    known = list(packet.get("known_user_profile", {}).get("known_facts", []) or [])
    active_context = str(packet.get("active_context", "") or "").strip()
    topic_brief = list(packet.get("topic_brief", []) or [])
    response_contract = list(packet.get("response_contract", []) or [])
    lines = [
        "Companion context packet:",
        f"Relationship model: {packet.get('relationship_model', 'smart, loyal friend with tools')}",
        f"User message: {packet.get('user_message', '')}",
    ]
    effective_user_message = str(packet.get("effective_user_message", "") or "").strip()
    if effective_user_message and effective_user_message != str(packet.get("user_message", "") or "").strip():
        lines.append(f"Effective request to answer: {effective_user_message}")
    if packet.get("conversation_excerpt"):
        lines.append("Conversation excerpt:")
        lines.append(str(packet.get("conversation_excerpt", "")).strip())
    correction_context = dict(packet.get("correction_context") or {})
    if correction_context:
        lines.append("Correction context:")
        if correction_context.get("last_user_message"):
            lines.append(f"- Original user request: {correction_context.get('last_user_message', '')}")
        if correction_context.get("last_assistant_message"):
            lines.append(f"- Last Jarvis reply to correct: {correction_context.get('last_assistant_message', '')}")
        if correction_context.get("feedback"):
            lines.append(f"- User correction: {correction_context.get('feedback', '')}")
    if known:
        lines.append("Known facts most relevant here:")
        lines.extend(f"- {item}" for item in known)
    if topic_brief:
        lines.append("Topic brief for this request:")
        lines.extend(f"- {item}" for item in topic_brief)
    canon_brief = str(packet.get("canon_brief", "") or "").strip()
    if canon_brief:
        lines.append("Canon brief:")
        lines.append(canon_brief)
    if active_context:
        lines.append("Active context:")
        lines.append(active_context)
    if response_contract:
        lines.append("Response contract for this turn:")
        lines.extend(f"- {item}" for item in response_contract)
    lines.append("Machine-readable packet:")
    lines.append(json.dumps(packet, indent=2, ensure_ascii=True))
    return "\n".join(lines)


def _available_capabilities(runtime: Any) -> list[str]:
    capabilities = [
        "ongoing conversation in this shell",
        "conversation turn persistence",
        "recent conversation continuity",
        "durable profile facts already stored locally",
        "planning and drafting in chat",
        "web search for current info when that path is explicitly triggered and results actually come back",
    ]
    if hasattr(runtime, "family_calendar"):
        capabilities.append("family calendar summary when available")
    if hasattr(runtime, "storm_weather_summary"):
        capabilities.append("live weather summary when available")
    obsidian_status = _obsidian_status(runtime)
    if _obsidian_conversation_enabled(runtime) and obsidian_status.get("enabled"):
        capabilities.append("local Obsidian vault retrieval with quoted snippets when notes match")
    else:
        capabilities.append("live Obsidian retrieval not active in the default conversation path")
    return capabilities


def _needs_companion_reply_repair(request: str, reply: str) -> bool:
    lowered_reply = str(reply or "").lower()
    if _reply_is_generic_taxonomy_opener(reply):
        return True
    if any(pattern in lowered_reply for pattern in THERAPIST_LANGUAGE_PATTERNS):
        return True
    if any(pattern in lowered_reply for pattern in GENERIC_CHATBOT_PATTERNS):
        return True
    if any(pattern in lowered_reply for pattern in GENERIC_EMPATHY_PATTERNS) and not _reply_has_practical_handle(reply):
        return True
    if _reply_needs_decision_tradeoff_grounding(request, reply):
        return True
    if _reply_needs_practical_hedge_reduction(request, reply):
        return True
    if _request_needs_practical_handle(request) and any(pattern in lowered_reply for pattern in ABSTRACT_MEANING_PATTERNS):
        return True
    if _request_needs_practical_handle(request) and not _reply_has_practical_handle(reply):
        return True
    return False


def _reply_is_generic_taxonomy_opener(reply: str) -> bool:
    lowered = str(reply or "").strip().lower()
    if not lowered:
        return False
    return any(lowered.startswith(pattern) for pattern in GENERIC_TAXONOMY_OPENERS)


def _contextual_thesis_first_reply(request: str, packet: dict[str, Any]) -> str:
    cleaned = str(request or "").strip()
    lowered = cleaned.lower()
    if not cleaned:
        return ""
    if _correction_feedback(cleaned):
        return ""
    if _is_capability_request(cleaned) or "obsidian" in lowered:
        return ""
    if _is_retirement_income_request(lowered):
        return _retirement_income_reply(packet)
    if _is_future_health_request(lowered):
        return _future_health_reply(cleaned)
    if _is_trip_day_request(lowered):
        return _trip_day_reply(cleaned)
    return ""


def _is_retirement_income_request(lowered_request: str) -> bool:
    return (
        "retir" in lowered_request
        and (
            "passive income" in lowered_request
            or "books" in lowered_request
            or "training" in lowered_request
            or "consult" in lowered_request
        )
    )


def _is_future_health_request(lowered_request: str) -> bool:
    health_markers = (
        "healthy for the future",
        "metabolic syndrome",
        "exercise",
        "live a better life",
        "lose weight",
        "blood sugar",
        "insulin",
        "weight",
    )
    return any(marker in lowered_request for marker in health_markers)


def _is_trip_day_request(lowered_request: str) -> bool:
    if "tomorrow" in lowered_request and "going to" in lowered_request:
        return True
    anchored_terms = ("flight", "hotel", "ferry", "boarding", "departure point")
    if any(term in lowered_request for term in anchored_terms):
        return True
    return "tomorrow" in lowered_request and any(term in lowered_request for term in ("tickets", "entry", "departure"))


def _retirement_income_reply(packet: dict[str, Any]) -> str:
    topic_lines = list(packet.get("topic_brief", []) or [])
    strategic_line = (
        "I do not think you are really chasing retirement in the classic sense. "
        "I think you are trying to get employment out of the driver's seat."
    )
    framing_line = topic_lines[0] if topic_lines else strategic_line
    stack_line = next(
        (
            item for item in topic_lines
            if "authority engine" in item or "revenue engine" in item or "scale engine" in item
        ),
        "Books are an authority engine, training is a revenue engine, and product or software is the scale engine if it becomes real.",
    )
    return (
        f"{strategic_line}\n\n"
        f"{framing_line}\n\n"
        "My read is that this can work for you, but only if you treat it like an asset stack instead of a vague passive-income hope.\n\n"
        f"{stack_line}\n\n"
        "The main risk for you is fragmentation. Too many parallel books, offers, and builds will keep everything half-compounding.\n\n"
        "So I would bias toward one reinforcing stack: the strongest product/platform bet, one flagship training offer, books that build authority into both, and consulting only where it sharpens the system and buys runway."
    )


def _future_health_reply(request: str) -> str:
    weight_match = re.search(r"\b(\d{3})\s?lb", request.lower())
    weight_text = f"At around {weight_match.group(1)} lbs, " if weight_match else ""
    responds_to_exercise = "respond well to exercise" in request.lower()
    opening = (
        f"{weight_text}I would not frame this as a weight-loss project first. "
        "I would frame it as building a body that stays useful for the next 30 years."
    ).strip()
    exercise_line = (
        "The biggest advantage you already named is that exercise works for you, so I would treat muscle, walking, and consistency as your main lever."
        if responds_to_exercise
        else "The biggest lever here is consistent training and eating in a way that lowers insulin resistance."
    )
    return (
        f"{opening}\n\n"
        f"{exercise_line}\n\n"
        "My bias would be simple: lift regularly, walk daily, lose fat slowly, protect sleep, and track the markers that tell you whether you are getting metabolically safer.\n\n"
        "The real goal is not to be lighter. It is to be harder to break as you age so you can keep serving, building, traveling, and showing up with strength."
    )


def _trip_day_reply(request: str) -> str:
    destination_match = re.search(r"going to\s+(.+?)(?:\s+tomorrow|[.?!]|$)", request, flags=re.IGNORECASE)
    destination = destination_match.group(1).strip() if destination_match else "this outing"
    return (
        f"{destination} tomorrow is a real trip day, so the job is to make it smooth rather than improvise it.\n\n"
        "The pressure points I would want locked down tonight are timing, tickets or entry rules, where you are starting from, who is coming, and any walking or stairs that could make the day harder than it needs to be.\n\n"
        "If you already have the booking side handled, the next move is building the day around the real friction points instead of treating it like a casual stop."
    )


def _topic_brief(request: str) -> list[str]:
    lowered = str(request or "").strip().lower()
    lines: list[str] = []
    if _is_retirement_income_request(lowered):
        lines.extend(
            [
                "Chris is usually aiming for freedom and leverage, not classic stop-working retirement.",
                "Books are an authority engine, training is a revenue engine, and product or software is the scale engine if it becomes real.",
                "The strongest recommendation should reduce fragmentation and build a reinforcing asset stack rather than scattered offers.",
            ]
        )
    if _is_future_health_request(lowered):
        lines.extend(
            [
                "Chris treats health as formation and long-term usefulness, not vanity.",
                "If exercise works for him, the answer should lean hard into muscle, walking, and sustainable consistency.",
                "Health advice should connect to family, calling, work freedom, and staying strong enough for the next decades.",
            ]
        )
    if _is_trip_day_request(lowered):
        lines.extend(
            [
                "Travel help should infer likely pressure points like timing, booking, departure point, companions, mobility, and how the outing fits the rest of the day.",
                "Do not ask taxonomy questions first when tomorrow logistics are already the obvious issue.",
            ]
        )
    elif any(term in lowered for term in ("vacation", "trip", "travel", "get away", "go away")):
        lines.extend(
            [
                "Travel planning should begin with the real objective of the trip, then move to constraints and logistics.",
                "Do not drift into meaning-talk when the user is asking for practical travel help.",
            ]
        )
    return lines


def _response_contract_for_request(
    request: str,
    *,
    effective_request: str = "",
    correction_context: dict[str, str] | None = None,
) -> list[str]:
    lowered = str((effective_request or request) or "").strip().lower()
    contract = [
        "Lead with a personalized read before asking for more detail.",
        "Use what you already know about Chris's trajectory and preferences.",
        "Do not open with category-routing questions when a grounded thesis is possible.",
    ]
    if correction_context:
        contract.extend(
            [
                "The user is correcting your last answer, so rewrite it directly instead of defending it.",
                "Use the correction as authoritative guidance for what the answer should have sounded like.",
            ]
        )
        correction_mode = str(correction_context.get("mode", "")).strip().lower()
        if correction_mode == "teach":
            contract.append("The user wants this preference carried into future replies, so acknowledge that briefly and naturally.")
        if correction_mode == "learn":
            contract.append("The user wants this turned into a reusable Jarvis skill, so acknowledge that it will be staged for approval.")
    if _is_retirement_income_request(lowered):
        contract.append("Frame retirement around freedom, leverage, and asset design rather than generic financial planning.")
    if _is_future_health_request(lowered):
        contract.append("Connect health advice to long-horizon usefulness and identity, not just weight loss.")
    if _is_trip_day_request(lowered):
        contract.append("Infer the likely friction points of the outing before you ask for details.")
    return contract


def _correction_command(request: str) -> tuple[str, str]:
    text = str(request or "").strip()
    if not text:
        return ("", "")
    match = re.match(r"^/(correct|teach|learn)(?:\s+|:\s*)(.+)$", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ("", "")
    return (str(match.group(1) or "").strip().lower(), str(match.group(2) or "").strip())


def _correction_feedback(request: str) -> str:
    return _correction_command(request)[1]


def _correction_context(request: str, conversation_excerpt: str) -> dict[str, str] | None:
    mode, feedback = _correction_command(request)
    if not feedback:
        return None
    turns = _recent_turns_from_excerpt(conversation_excerpt)
    last_assistant = ""
    last_user = ""
    for turn in reversed(turns):
        speaker = str(turn.get("speaker", "")).strip().lower()
        text = str(turn.get("text", "")).strip()
        if speaker == "jarvis" and not last_assistant:
            last_assistant = text
        elif speaker != "jarvis" and not _correction_feedback(text):
            last_user = text
            if last_assistant:
                break
    context = {
        "mode": mode or "correct",
        "feedback": feedback,
        "last_user_message": last_user,
        "last_assistant_message": last_assistant,
    }
    return context


def _recent_turns_from_excerpt(conversation_excerpt: str) -> list[dict[str, str]]:
    turns: list[dict[str, str]] = []
    for line in str(conversation_excerpt or "").splitlines():
        stripped = line.strip()
        if not stripped or ": " not in stripped:
            continue
        speaker, text = stripped.split(": ", 1)
        normalized = speaker.strip()
        if normalized in {"JARVIS", "Chris"} and text.strip():
            turns.append({"speaker": normalized, "text": text.strip()})
    return turns


def _correction_fallback_reply(packet: dict[str, Any]) -> str:
    correction_context = dict(packet.get("correction_context") or {})
    if not correction_context:
        return ""
    feedback = str(correction_context.get("feedback", "")).strip()
    mode = str(correction_context.get("mode", "correct") or "correct").strip().lower()
    original_request = str(correction_context.get("last_user_message", "")).strip()
    if not original_request:
        if mode == "teach":
            return "Understood. I can carry that forward, but I need either the original question or a new one to answer in that style."
        if mode == "learn":
            return "Understood. I can stage that as a reusable Jarvis skill, but I need either the original question or a new one to answer in that style."
        return "Understood. Tell me what answer you wanted instead, and I will rewrite it directly."
    adjusted_packet = dict(packet)
    adjusted_packet["correction_context"] = None
    adjusted_packet["effective_user_message"] = original_request
    adjusted_packet["user_message"] = original_request
    revised = _contextual_thesis_first_reply(original_request, adjusted_packet)
    if not revised:
        revised = _practical_repair_reply(original_request, adjusted_packet)
    if not revised:
        return "Understood. I missed the mark. Re-ask the question in one line and I will answer it the way you wanted."
    opener = "Understood. I missed what you were actually asking for."
    if feedback:
        opener = f"Understood. You wanted {feedback}."
    if mode == "teach":
        opener = f"{opener} I'll carry that forward."
    if mode == "learn":
        opener = f"{opener} I'll stage that as a reusable skill for approval."
    return f"{opener}\n\n{revised}".strip()


def _canon_brief_for_request(request: str) -> str:
    lowered = str(request or "").strip().lower()
    snippets: list[str] = []
    for path in (_CHRIS_CONTEXT_CANON_PATH, _CHRIS_INTENT_CANON_PATH):
        text = _load_canon_text(path)
        if not text:
            continue
        if any(token in lowered for token in ("retire", "passive income", "training", "books")):
            snippets.extend(_matching_lines(text, ("retirement", "publishing", "trusted thinking partner", "smart, loyal friend with tools"), limit=4))
        if any(token in lowered for token in ("healthy", "exercise", "metabolic", "weight")):
            snippets.extend(_matching_lines(text, ("health", "useful pushback", "practical problem-solving", "formation"), limit=4))
        if any(token in lowered for token in ("tomorrow", "trip", "travel", "going to")):
            snippets.extend(_matching_lines(text, ("travel", "practical help", "ordinary practical asks", "friend with tools"), limit=4))
    unique: list[str] = []
    seen: set[str] = set()
    for item in snippets:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return " ".join(unique[:4]).strip()


def _load_canon_text(path: Path) -> str:
    cache_key = str(path)
    if cache_key in _CANON_CACHE:
        return _CANON_CACHE[cache_key]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    _CANON_CACHE[cache_key] = text
    return text


def _matching_lines(text: str, keywords: tuple[str, ...], *, limit: int) -> list[str]:
    matches: list[str] = []
    for raw_line in text.splitlines():
        line = str(raw_line).strip()
        lowered = line.lower()
        if not line or line.startswith("#"):
            continue
        if any(keyword in lowered for keyword in keywords):
            matches.append(line.lstrip("-* ").strip())
            if len(matches) >= limit:
                break
    return matches


def _needs_overexplaining_trim(reply: str) -> bool:
    sentences = _split_reply_sentences(reply)
    if len(sentences) < 2:
        return False
    lowered = str(reply or "").strip().lower()
    return any(pattern in lowered for pattern in OVEREXPLAINING_PATTERNS)


def _trim_overexplaining_reply(reply: str) -> str:
    sentences = _split_reply_sentences(reply)
    if len(sentences) < 2:
        return str(reply or "").strip()
    trimmed = list(sentences)
    while len(trimmed) > 1 and _sentence_is_overexplaining_filler(trimmed[0]):
        trimmed.pop(0)
    if not trimmed:
        return str(reply or "").strip()
    return " ".join(trimmed).strip()


def _split_reply_sentences(reply: str) -> list[str]:
    text = str(reply or "").strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _sentence_is_overexplaining_filler(sentence: str) -> bool:
    lowered = str(sentence or "").strip().lower()
    return any(pattern in lowered for pattern in OVEREXPLAINING_PATTERNS)


def _request_needs_practical_handle(request: str) -> bool:
    lowered = str(request or "").lower()
    if not lowered.strip():
        return False
    practical_terms = (
        "help",
        "plan",
        "draft",
        "work through",
        "work on",
        "think through",
        "what should",
        "next step",
        "organize",
        "under control",
        "week",
        "overwhelmed",
        "retire",
        "vacation",
        "trip",
        "travel",
        "talk to",
        "have a conversation",
        "hard conversation",
        "sit down with",
        "say something to",
        "clear the air with",
        "call my",
        "call him",
        "call her",
        "call them",
        "writing an email",
        "writing a follow-up email",
        "writing a follow up email",
        "write to",
        "send a message",
        "send him a message",
        "send her a message",
        "send them a message",
        "send a text",
        "send him a text",
        "send her a text",
        "send a note",
        "send him a note",
        "send her a note",
        "send them a note",
        "send my boss a note",
        "text him",
        "text her",
        "text my",
        "message my",
        "message him",
        "message her",
        "write him a message",
        "write her a message",
        "write them a message",
        "write him back",
        "write her back",
        "email my",
        "email him",
        "email her",
        "book",
        "stuck",
        "write this",
        "write this email",
        "draft a text",
        "draft this",
        "answer this",
        "answer this email",
        "reply to",
        "respond to",
        "send a reply",
        "send a response",
        "send a follow-up email",
        "send a follow up email",
        "write a reply",
        "write a response",
        "text back",
    )
    return _is_decision_shaped_request(request) or any(term in lowered for term in practical_terms)


def _is_meeting_prep_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    meeting_terms = ("meeting", "one-on-one", "1:1", "check-in")
    if not any(term in lowered for term in meeting_terms):
        return False
    direct_phrases = (
        "prep for a meeting",
        "prep for this meeting",
        "prep for the meeting",
        "big meeting tomorrow",
        "think through this meeting",
        "help with this meeting",
        "help with this meeting agenda",
        "meeting agenda",
        "help with my one-on-one",
        "getting ready for my one-on-one",
        "preparing for my one-on-one",
        "help with my 1:1",
        "help with this check-in",
    )
    if any(phrase in lowered for phrase in direct_phrases):
        return True
    if "get ready for" in lowered and "meeting" in lowered:
        return True
    return False


def _is_inbox_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    direct_phrases = (
        "help with my inbox",
        "get through my inbox",
        "inbox triage",
        "clear my inbox",
        "triaging my inbox",
        "triage my inbox",
        "help with my email",
        "getting through email",
        "triaging email",
    )
    return any(phrase in lowered for phrase in direct_phrases)


def _is_follow_up_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    direct_phrases = (
        "help with my follow-up",
        "help with this follow-up",
        "help following up after this meeting",
        "help with the follow-up",
        "help with a follow-up",
        "help with my meeting follow-up",
        "help with this debrief",
        "help after this meeting",
        "help with my notes for this meeting",
        "help with meeting notes",
    )
    return any(phrase in lowered for phrase in direct_phrases)


def _is_presentation_or_proposal_prep_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    direct_phrases = (
        "help with this presentation",
        "help with my presentation",
        "getting ready for this presentation",
        "getting ready for my presentation",
        "help with this proposal",
        "help with my proposal",
        "getting ready for this proposal",
        "getting ready for my proposal",
        "help with this slide deck",
        "help with my slide deck",
        "help with this deck",
        "getting ready for this deck",
        "help with this pitch",
        "help with my pitch",
        "help with this proposal deck",
        "help with my proposal deck",
        "help with my talking points",
        "help with this briefing",
        "help with my briefing",
        "help with a briefing",
        "writing a briefing",
        "preparing a briefing",
        "getting ready for this briefing",
        "getting ready for my briefing",
    )
    return any(phrase in lowered for phrase in direct_phrases)


def _is_agenda_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    if "meeting agenda" in lowered:
        return False
    direct_phrases = (
        "help with this agenda",
        "help setting the agenda",
        "set the agenda with me",
    )
    return any(phrase in lowered for phrase in direct_phrases)


def _is_tomorrow_planning_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    direct_phrases = (
        "help planning tomorrow",
        "help scheduling tomorrow",
        "help organizing tomorrow",
        "map out tomorrow",
        "mapping out tomorrow",
        "planning around two meetings",
        "help preparing for tomorrow",
        "help getting ready for tomorrow",
        "get ready for tomorrow",
        "help with tomorrow",
        "help with tomorrow's plan",
        "help with tomorrow morning",
        "help with my agenda for tomorrow",
        "help setting my agenda for tomorrow",
        "set my agenda for tomorrow",
        "help with my schedule tomorrow",
        "help with my schedule for tomorrow",
        "help with my calendar tomorrow",
        "help with my calendar for tomorrow",
        "help planning around two appointments",
        "help planning around my appointments",
        "help scheduling around appointments",
        "help around my appointments tomorrow",
    )
    return any(phrase in lowered for phrase in direct_phrases)


def _is_constraints_scheduling_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    direct_phrases = (
        "help scheduling around two meetings",
        "help scheduling around constraints",
        "help scheduling around my constraints",
        "help planning around constraints",
    )
    return any(phrase in lowered for phrase in direct_phrases)


def _fork_follow_up_continuation_reply(request: str, packet: dict[str, Any]) -> str:
    lowered = str(request or "").strip().lower()
    if not _is_short_follow_up_request(lowered):
        return ""
    excerpt = str(packet.get("conversation_excerpt") or "").strip().lower()
    if not excerpt:
        return ""
    decision_reply = _decision_follow_up_reply(lowered, excerpt)
    if decision_reply:
        return decision_reply
    practical_reply = _practical_fork_follow_up_reply(lowered, excerpt)
    if practical_reply:
        return practical_reply
    drafting_reply = _drafting_follow_up_reply(lowered, excerpt)
    if drafting_reply:
        return drafting_reply
    vacation_reply = _vacation_follow_up_reply(lowered, excerpt)
    if vacation_reply:
        return vacation_reply
    retirement_reply = _retirement_follow_up_reply(lowered, excerpt)
    if retirement_reply:
        return retirement_reply
    conversation_reply = _conversation_follow_up_reply(lowered, excerpt)
    if conversation_reply:
        return conversation_reply
    capacity_reply = _capacity_follow_up_reply(lowered, excerpt)
    if capacity_reply:
        return capacity_reply
    return ""


def _is_short_follow_up_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    if not lowered:
        return False
    if lowered in {
        "should i do it at all",
        "the hard part is all of it",
        "if i even need to have it",
        "what the trip needs to be",
        "what kind of trip is this",
        "what kind of vacation is this",
        "the point and the hard part",
        "the place or the hard part",
    }:
        return True
    words = re.findall(r"[a-z0-9']+", lowered)
    return len(words) <= 5 and len(lowered) <= 40


def _drafting_follow_up_reply(request: str, conversation_excerpt: str) -> str:
    if not any(
        marker in conversation_excerpt
        for marker in (
            "blunt, warm, or diplomatic",
            "angle first or the actual draft",
            "do you want the angle first or the actual draft",
        )
    ):
        return ""
    if "warm" in request or "gentle" in request:
        return (
            "Good. Keep it warm. Give me who it's to and the one point you need to land, "
            "and I'll draft it."
        )
    if "blunt" in request or "direct" in request:
        return (
            "Good. Keep it blunt. Give me who it's to and the one point you need to land, "
            "and I'll draft it."
        )
    if "diplomatic" in request or "formal" in request or "careful" in request:
        return (
            "Good. Keep it diplomatic. Give me who it's to and the one point you need to land, "
            "and I'll draft it."
        )
    if request in {"short", "keep it short", "brief", "concise"}:
        return "Good. Keep it short. Tell me who it's to and whether you want blunt, warm, or diplomatic, and I'll shape it that way."
    if request in {"longer", "a little longer", "keep it longer"}:
        return "Good. Keep it a little longer. Tell me who it's to and whether you want blunt, warm, or diplomatic, and I'll shape it that way."
    if request.startswith(("for my ", "to my ", "for the ", "to the ")) or request in {"for him", "for her", "for them"}:
        return "Good. If that's the audience, tell me whether you want blunt, warm, or diplomatic, and whether you want the angle first or the actual draft."
    if request.startswith(("just text ", "text ")):
        return "Good. If it's a text, tell me whether you want blunt, warm, or diplomatic, and the one point you need to land, and I'll write it."
    if request in {"either", "both", "kind of both", "both honestly", "not sure", "whatever gets it done"}:
        return "Good. If you want the fast path, tell me whether you want the angle first or the actual draft, and I'll take it from there."
    if request in {"actual draft", "the actual draft", "draft", "just write it", "write it", "just draft it", "just send it", "send it"}:
        return "Good. Give me who it's to, what happened, and the point you need to make, and I'll write the first pass."
    if "angle" in request:
        return "Good. Give me who it's to, what happened, and the outcome you want, and I'll give you the angle first."
    return ""


def _vacation_follow_up_reply(request: str, conversation_excerpt: str) -> str:
    if "where to go, what kind of trip this needs to be, or what is making it hard to land" not in conversation_excerpt:
        return ""
    if (
        request in {
            "all three",
            "honestly all three",
            "all three honestly",
            "some of all three",
            "i do not know",
            "i don't know",
            "not sure",
            "all of it",
            "kind of all three",
            "probably all three",
            "all of those",
            "all of the above",
            "all of them",
            "all of these",
            "both",
            "either",
            "kind of both",
            "some of both",
            "probably both",
            "maybe both",
            "more than one",
            "mixed",
        }
        or (
            (" and " in request or " or " in request)
            and any(term in request for term in ("where", "destination", "place", "point", "trip", "vacation", "hard", "blocker", "timing"))
        )
    ):
        return "Okay. If it's all tangled together, which part is actually blocking the rest right now: where to go, what this trip needs to do for you, or what is making it hard to land?"
    if request in {"where", "where first", "probably where", "where are we going", "the destination", "destination", "maybe where", "the place", "probably the destination"}:
        return "Okay. Are you stuck on the place itself, narrowing the options, or agreeing on what would actually feel worth leaving for?"
    if request in {"the point of it", "maybe the point of it", "what kind of trip", "what kind of trip this needs to be", "the point", "probably the point", "the kind of trip", "what the trip needs to be", "trip purpose", "the purpose", "what kind of trip is this", "what kind of vacation is this"}:
        return "Okay. Does this need to feel like rest, adventure, time together, or just getting out of your normal headspace for a minute?"
    if request in {"what is making it hard", "what's making it hard", "making it hard", "hard to land", "what is making it hard to land", "probably the hard part", "the hard part", "the blocker", "why is it hard"}:
        return "Okay. Is it money, timing, people, or the fact that no option feels worth the effort yet?"
    return ""


def _decision_follow_up_reply(request: str, conversation_excerpt: str) -> str:
    if "money, energy, risk, or which choice you'd regret not taking" not in conversation_excerpt:
        return ""
    if request in {"either", "both", "kind of both", "some of both", "all of it", "all of the above"}:
        return "Okay. If it's mixed, which one would still decide it if the others got a little easier: money, energy, risk, or regret?"
    if request in {"money", "pay", "salary", "upside", "margin"}:
        return "Okay. Is the real question pay now, long-term upside, or how much margin this buys you?"
    if request in {"energy", "burnout", "pace"}:
        return "Okay. Is this about burnout, pace, or whether this choice gives you more actual life back?"
    if request in {"risk", "downside", "reputation", "stuck"}:
        return "Okay. Is the risk more about money, reputation, or ending up stuck in something you already know is wrong?"
    if request in {"regret", "regret not taking", "stability", "future", "the future"}:
        return "Okay. Which miss would bother you more a year from now: losing stability, or not taking the shot?"
    return ""


def _practical_fork_follow_up_reply(request: str, conversation_excerpt: str) -> str:
    if "is this mostly a decision, a conversation, or a plan you need to sort out first" not in conversation_excerpt:
        return ""
    if request == "decision":
        return "Okay. What are the actual options, and is the hard part money, energy, risk, or what you'd regret not taking?"
    if request == "conversation":
        return "Okay. Is the hard part what you need to say, how to say it, or whether to have the conversation at all?"
    if request == "plan":
        return "Okay. Is this mostly too much on the calendar, fuzzy priorities, or a few things you're avoiding?"
    return ""


def _retirement_follow_up_reply(request: str, conversation_excerpt: str) -> str:
    if "money, time, or identity first" not in conversation_excerpt:
        return ""
    if request in {"all three", "all of them", "both", "everything", "probably all three", "all of it", "the whole thing", "not sure", "maybe all three", "kind of all three", "all three honestly", "all of it really", "not sure honestly", "maybe all of them", "probably everything"}:
        return "Okay. If all three matter, which one is actually gating the others right now: money, time, or identity?"
    if request in {"money", "money first", "the money part", "money mostly", "probably money", "maybe money", "the money stuff", "i think money", "probably the money part", "numbers", "the number", "runway", "the runway", "the money side", "money i guess"}:
        return "Okay. Are you trying to figure out the number, the runway, or how much work still has to stay in the picture?"
    if request in {"time", "time first", "probably time", "maybe time", "time mostly", "the time part", "the time stuff", "i think time", "probably the time part", "buy back my days", "my days", "pace", "without work", "the time side", "time i guess"}:
        return "Okay. Are you trying to buy back your days, reduce your pace, or figure out what a week would look like without work driving it?"
    if request in {"identity", "identity first", "identity mostly", "probably identity", "maybe identity", "the identity part", "the identity stuff", "i think identity", "probably the identity part", "who i am", "meaning", "purpose", "the identity side", "identity i guess", "identity stuff"}:
        return "Okay. Is the real question who you are without the work pace, what replaces the pressure, or what you still want to build?"
    return ""


def _conversation_follow_up_reply(request: str, conversation_excerpt: str) -> str:
    if not any(
        marker in conversation_excerpt
        for marker in (
            "what you need to say, how to say it, or whether to have the conversation at all",
            "what to say, how to say it, or whether to have the conversation at all",
        )
    ):
        return ""
    if request in {
        "both",
        "either",
        "kind of both",
        "all of it",
        "the whole thing",
        "all three",
        "not sure",
        "maybe both",
        "all of the above",
        "the hard part is all of it",
    } or request in {"probably both", "all of those", "all of it honestly", "i do not know", "i don't know", "the whole thing honestly"}:
        return "Okay. If it's mixed, which part is actually deciding this: what to say, how to say it, or whether to have the conversation at all?"
    if request in {
        "the conversation itself",
        "whether to have it",
        "whether to have the conversation",
        "whether",
        "should i even have it",
        "if i should do it",
        "do i even need to",
        "actually having it",
        "if i should have it",
        "if i even should",
        "not sure if i should",
        "should i do it at all",
    } or request.startswith("probably whether") or request in {"maybe the conversation itself", "the whole conversation", "whether i even need to", "if i even need to have it", "probably the conversation itself", "maybe whether"}:
        return "Okay. Do you already know you need to do it and need the opening line, or are you still deciding if this is a conversation worth having?"
    if request in {"what i need to say", "what to say", "say it", "wording", "the wording", "what do i even say", "what i actually say", "probably the wording", "maybe wording"} or "what to say" in request:
        return "Okay. Give me the point you need to land and what you cannot afford to say badly, and I'll help you frame it."
    if request in {"how to say it", "tone", "delivery", "the tone", "the delivery", "how i say it", "how i actually say it", "probably the tone", "maybe delivery"} or "how to say it" in request:
        return "Okay. Do you need blunt, calm, or careful, and how much tension is already in the room?"
    return ""


def _capacity_follow_up_reply(request: str, conversation_excerpt: str) -> str:
    if "you do not need a better plan yet. you need one cut. what is actually immovable this week?" not in conversation_excerpt:
        return ""
    if (
        request in {
            "both",
            "either",
            "kind of both",
            "some of both",
            "probably both",
            "maybe both",
            "all of those",
            "all of the above",
            "all of them",
            "all of these",
            "honestly all of them",
            "more than one",
            "mixed",
        }
        or (
            (" and " in request or " or " in request)
            and any(term in request for term in ("calendar", "schedule", "priorit", "avoid", "conversation"))
        )
    ):
        return "Okay. If it's mixed, what's actually driving the overload first: the calendar, fuzzy priorities, something you're avoiding, or one conversation that's clogging the week?"
    if request in {
        "all of it",
        "i do not know",
        "i don't know",
        "not sure",
        "probably all of it",
        "kind of all of it",
        "some of all of it",
        "probably everything",
        "not sure honestly",
        "all of that",
    }:
        return "Okay. If it's all tangled together, what's actually driving the overload first: the calendar, fuzzy priorities, something you're avoiding, or one conversation that's clogging the week?"
    if request in {
        "calendar",
        "the calendar",
        "schedule",
        "too much on the calendar",
        "probably the calendar",
        "the schedule stuff",
        "maybe the calendar",
        "probably schedule",
        "the schedule",
    }:
        return "Okay. What on the calendar is truly fixed, and what are you treating as fixed because it feels easier than cutting it?"
    if request in {"fuzzy priorities", "priorities", "maybe priorities", "the priorities stuff", "probably priorities", "the priorities"}:
        return "Okay. What are the two things that actually matter this week, and what is loud but not important?"
    if request in {"avoiding", "a few things you're avoiding", "the avoiding stuff", "probably avoiding", "maybe avoiding", "the avoidance"}:
        return "Okay. What are you avoiding because it is hard, and what are you avoiding because it should not be on your plate at all?"
    if request in {"conversation", "that conversation", "probably the conversation", "the conversation stuff", "maybe the conversation", "that whole conversation"}:
        return "Okay. If one conversation is clogging the week, who is it with, and do you need the opening line or the decision about whether to have it?"
    if request in {"one cut", "immovable", "what has to drop", "what can slip"}:
        return "Okay. What actually has to happen this week, and what are you pretending is fixed because cutting it feels uncomfortable?"
    return ""


def _is_drafting_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    if not lowered:
        return False
    drafting_terms = (
        "draft a text",
        "draft this",
        "drafting an email",
        "help me draft",
        "write this email",
        "writing an email",
        "writing a follow-up email",
        "writing a follow up email",
        "write to",
        "answer this",
        "answer this email",
        "reply to",
        "respond to",
        "send a reply",
        "send a response",
        "send a message",
        "send him a message",
        "send her a message",
        "send them a message",
        "send a text",
        "send him a text",
        "send her a text",
        "send a note",
        "send him a note",
        "send her a note",
        "send them a note",
        "send my boss a note",
        "text him",
        "text her",
        "text back",
        "message my",
        "message him",
        "message her",
        "write him a message",
        "write her a message",
        "write them a message",
        "write a reply",
        "write a response",
        "write him back",
        "write her back",
        "email my",
        "email him",
        "email her",
        "text my",
        "write an email",
        "follow-up email",
        "follow up email",
    )
    return any(term in lowered for term in drafting_terms)


def _is_decision_shaped_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    if not lowered:
        return False
    decision_document_terms = (
        "memo",
        "outline",
        "review",
        "summary",
        "recap",
        "overview",
        "chapter",
        "log",
        "notes",
    )
    if "decision" in lowered and any(term in lowered for term in decision_document_terms):
        return False
    return any(term in lowered for term in DECISION_REQUEST_TERMS)


def _reply_has_practical_handle(reply: str) -> bool:
    lowered = str(reply or "").lower()
    if _reply_is_vague_reflective_question(lowered):
        return False
    if "?" in reply:
        return True
    practical_starts = (
        "want me to",
        "let's",
        "give me",
        "pick",
        "start with",
        "tell me",
        "what's",
        "where are",
        "do you want",
        "first",
    )
    if any(marker in lowered for marker in practical_starts):
        return True
    return False


def _reply_is_generic_follow_up_reset(reply: str) -> bool:
    lowered = str(reply or "").strip().lower()
    return any(pattern in lowered for pattern in FOLLOW_UP_RESET_PATTERNS)


def _reply_needs_decision_tradeoff_grounding(request: str, reply: str) -> bool:
    lowered_reply = str(reply or "").strip().lower()
    if not _is_decision_shaped_request(request):
        return False
    if _reply_has_decision_tradeoff_handle(reply):
        return False
    return any(pattern in lowered_reply for pattern in FLAT_DECISION_REPLY_PATTERNS)


def _reply_has_decision_tradeoff_handle(reply: str) -> bool:
    lowered = str(reply or "").strip().lower()
    return _reply_has_practical_handle(reply) and any(term in lowered for term in DECISION_TRADEOFF_TERMS)


def _reply_needs_practical_hedge_reduction(request: str, reply: str) -> bool:
    lowered_reply = str(reply or "").strip().lower()
    if not _request_needs_practical_handle(request):
        return False
    if _reply_has_practical_handle(reply):
        return False
    return any(pattern in lowered_reply for pattern in HEDGED_PRACTICAL_REPLY_PATTERNS)


def _reply_needs_capacity_pushback(request: str, reply: str) -> bool:
    lowered_reply = str(reply or "").strip().lower()
    if not _is_overloaded_planning_request(request):
        return False
    if _reply_has_capacity_pushback(reply):
        return False
    return any(pattern in lowered_reply for pattern in SOFT_PLANNING_REPLY_PATTERNS)


def _is_overloaded_planning_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    if not lowered:
        return False
    return any(term in lowered for term in OVERLOADED_PLANNING_REQUEST_TERMS)


def _reply_has_capacity_pushback(reply: str) -> bool:
    lowered = str(reply or "").strip().lower()
    return any(term in lowered for term in CAPACITY_PUSHBACK_TERMS)


def _capacity_pushback_reply(request: str) -> str:
    lowered = str(request or "").strip().lower()
    if any(term in lowered for term in ("week", "calendar", "schedule")):
        return "You do not need a better plan yet. You need one cut. What is actually immovable this week?"
    return "You do not need a better plan yet. You need one cut. What actually has to happen, and what can slip?"


def _reply_is_vague_reflective_question(reply: str) -> bool:
    lowered = str(reply or "").strip().lower()
    if "?" not in lowered:
        return False
    return any(pattern in lowered for pattern in VAGUE_REFLECTIVE_QUESTION_PATTERNS)


def _is_truthful_limitation_reply(reply: str) -> bool:
    lowered = str(reply or "").lower()
    return any(pattern in lowered for pattern in TRUTHFUL_LIMITATION_PATTERNS)


def _is_capability_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    if not lowered:
        return False
    prompts = (
        "what can you actually do right now",
        "what can you do right now",
        "what can you actually do",
        "what can you do",
    )
    return any(prompt in lowered for prompt in prompts)


def _needs_capability_answer_grounding(reply: str, packet: dict[str, Any]) -> bool:
    lowered = str(reply or "").strip().lower()
    if not lowered:
        return True
    if any(pattern in lowered for pattern in RAW_CAPABILITY_LABEL_PATTERNS):
        return True
    if _capability_boundary_required(packet) and "obsidian" not in lowered:
        return True
    if not _reply_has_practical_handle(reply):
        return True
    grounded_markers = (
        "talk this through",
        "think through",
        "help you plan",
        "help you draft",
        "keep continuity",
        "use the context",
    )
    return not any(marker in lowered for marker in grounded_markers)


def _grounded_capability_reply(packet: dict[str, Any]) -> str:
    capabilities = [str(item) for item in packet.get("available_capabilities", []) if str(item).strip()]
    pieces = [
        "Right now I can talk things through with you, help you think through decisions, help you plan or draft, and keep continuity in this conversation.",
    ]
    if any("durable profile facts" in item for item in capabilities):
        pieces.append("I can also use the profile context I already have locally when it's relevant.")
    if any("web search for current info" in item for item in capabilities):
        pieces.append("For current web info, I can use a web-search path when the request actually needs it, and I'll be explicit about whether I really searched or I'm reasoning from local context.")
    if any("family calendar summary" in item for item in capabilities) or any("live weather summary" in item for item in capabilities):
        pieces.append("If calendar or weather context is available in this path, I can use that too.")
    if _capability_boundary_required(packet):
        pieces.append("I'm not doing live Obsidian retrieval in this default conversation path yet.")
    pieces.append("If you want, give me one decision, plan, or draft and I'll help with it now.")
    return " ".join(pieces)


def _capability_boundary_required(packet: dict[str, Any]) -> bool:
    capabilities = [str(item).lower() for item in packet.get("available_capabilities", [])]
    return any("live obsidian retrieval not active in the default conversation path" in item for item in capabilities)


def _generic_practical_fallback_reply(request: str) -> str:
    lowered = str(request or "").strip().lower()
    conversation_terms = (
        "brother",
        "sister",
        "mom",
        "dad",
        "wife",
        "husband",
        "partner",
        "friend",
        "coworker",
        "boss",
        "conversation",
        "talk",
        "say",
        "clear the air",
        "text",
        "argument",
    )
    call_terms = (
        "call my",
        "call him",
        "call her",
        "call them",
    )
    def _matches_conversation_term(term: str) -> bool:
        if " " in term:
            return term in lowered
        return bool(re.search(rf"\b{re.escape(term)}\b", lowered))

    planning_terms = (
        "week",
        "day",
        "calendar",
        "schedule",
        "under control",
        "overwhelmed",
        "swamped",
        "too much",
        "behind",
        "priorities",
        "organized",
        "organize",
        "juggling",
        "packed",
    )
    if _is_overloaded_planning_request(request):
        return _capacity_pushback_reply(request)
    if _is_decision_shaped_request(request):
        return "Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
    if _is_drafting_request(request):
        return "Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
    if any(term in lowered for term in call_terms):
        return "Let's make it concrete. Is the hard part what you need to say, how to say it, or whether to have the conversation at all?"
    if any(_matches_conversation_term(term) for term in conversation_terms):
        return "Let's make it concrete. Is the hard part what you need to say, how to say it, or whether to have the conversation at all?"
    if any(term in lowered for term in planning_terms):
        return "Let's get your week back under control. Is the real problem too much on the calendar, fuzzy priorities, or a few things you're avoiding?"
    return "Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?"


def _generic_non_practical_fallback_reply(request: str) -> str:
    lowered = str(request or "").strip().lower()
    if any(term in lowered for term in ("weird day", "off today", "rough day", "strange day", "bad day")):
        return "I'm here. Do you want to tell me what happened, or do you want help figuring out what to do with the rest of the day?"
    return "I'm here. Give me the short version, or tell me which part feels off."


def _practical_repair_reply(request: str, packet: dict[str, Any]) -> str:
    repaired = generate_companion_fallback(request, packet, runtime=None)
    if repaired and "The model path is down right now" not in repaired:
        return repaired
    return "Let's make it practical. What's the one decision, draft, or next move you want to nail first?"


def _should_include_live_context(request: str) -> bool:
    lowered = str(request or "").lower()
    keywords = (
        "today",
        "weather",
        "forecast",
        "calendar",
        "schedule",
        "travel",
        "vacation",
        "trip",
        "meeting",
    )
    return any(keyword in lowered for keyword in keywords)


def _compact_live_context(runtime: Any) -> str | None:
    try:
        from .graphs import _build_live_context

        live_context = str(_build_live_context(runtime) or "").strip()
        return live_context or None
    except Exception:
        return None


def _is_operating_status_request(runtime: Any, request: str) -> bool:
    checker = getattr(runtime, "_is_operating_status_request", None)
    if callable(checker):
        try:
            return bool(checker(request))
        except Exception:
            return False
    return False


def _live_status_lines(runtime: Any, actor_name: str) -> list[str]:
    getter = getattr(runtime, "_live_operating_status_context", None)
    if callable(getter):
        try:
            return list(getter(actor_name) or [])
        except Exception:
            return []
    return []


def _obsidian_context(runtime: Any, request: str) -> str:
    support = getattr(runtime, "obsidian_support", None)
    if (
        support is None
        or not getattr(support, "enabled", False)
        or not _obsidian_conversation_enabled(runtime)
    ):
        return ""
    try:
        return str(support.conversation_context(request, limit=3) or "").strip()
    except Exception:
        return ""


def _obsidian_status(runtime: Any) -> dict[str, Any]:
    support = getattr(runtime, "obsidian_support", None)
    if support is None:
        return {"enabled": False}
    try:
        return dict(support.status())
    except Exception:
        return {"enabled": False}


def _obsidian_fallback_reply(runtime: Any, request: str) -> str:
    support = getattr(runtime, "obsidian_support", None)
    if (
        support is None
        or not getattr(support, "enabled", False)
        or not _obsidian_conversation_enabled(runtime)
    ):
        return ""
    try:
        hits = list(support.retrieve(request, limit=2))
    except Exception:
        return ""
    if not hits:
        return ""
    lead = "I pulled two relevant Obsidian notes." if len(hits) > 1 else "I pulled one relevant Obsidian note."
    lines = [lead]
    for hit in hits:
        lines.append(f"{hit['title']}: {hit['snippet']}")
    return " ".join(lines)


def _obsidian_conversation_enabled(runtime: Any) -> bool:
    config = getattr(runtime, "config", None)
    if config is None:
        return False
    return bool(getattr(config, "obsidian_conversation_enabled", False))

from __future__ import annotations

import json
import re
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
    "should i",
    "torn between",
    "choose",
    "choice",
    "which option",
    "stay or leave",
    "staying and leaving",
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


def build_context_packet(
    runtime: Any,
    actor: UserProfile,
    room: str,
    request: str,
    *,
    plan: RequestPlan,
    conversation_excerpt: str,
) -> dict[str, Any]:
    known_facts: list[str] = []
    try:
        known_facts = list(runtime._relevant_profile_facts(actor, request, limit=4))
    except Exception:
        known_facts = []

    active_context_blocks: list[str] = []
    if _should_include_live_context(request):
        live_context = _compact_live_context(runtime)
        if live_context:
            active_context_blocks.append(live_context)
    elif _is_operating_status_request(runtime, request):
        status_lines = _live_status_lines(runtime, actor.display_name)
        if status_lines:
            active_context_blocks.append("\n".join(status_lines))
    obsidian_context = _obsidian_context(runtime, request)
    if obsidian_context:
        active_context_blocks.append(obsidian_context)
    active_context = "\n\n".join(block for block in active_context_blocks if str(block).strip()) or None

    return {
        "user_message": str(request or "").strip(),
        "conversation_excerpt": str(conversation_excerpt or "").strip(),
        "known_user_profile": {
            "display_name": actor.display_name,
            "role": actor.role,
            "address_as": actor.address_as,
            "priorities": list(actor.priorities or []),
            "known_facts": known_facts,
        },
        "active_context": active_context,
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
        "- Push back when the user is rationalizing, drifting, or making the plan fuzzy.\n"
        "- Keep the tone human. No therapist voice, no mystical framing, no dashboard theater.\n"
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
    follow_up_reply = _fork_follow_up_continuation_reply(cleaned, packet)
    if follow_up_reply:
        return follow_up_reply

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
    if "retire" in lowered:
        return (
            "For you, I don't think retirement means doing nothing. I think it means getting work out of the driver's seat. "
            "Do you want to think about money, time, or identity first?"
        )
    if any(term in lowered for term in ("vacation", "trip", "travel", "hotel", "flight")):
        return "Nice. Where are we going, what dates, and who's coming? I'll help you get it organized."
    if "latest book" in lowered or ("book" in lowered and "work on" in lowered):
        return "Good. What's the book, and do you need help outlining, writing, revising, or getting unstuck?"
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
    return (
        "Companion context packet:\n"
        + json.dumps(packet, indent=2, ensure_ascii=True)
    )


def _available_capabilities(runtime: Any) -> list[str]:
    capabilities = [
        "ongoing conversation in this shell",
        "conversation turn persistence",
        "recent conversation continuity",
        "durable profile facts already stored locally",
        "planning and drafting in chat",
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
        "book",
        "stuck",
        "write this",
        "write this email",
        "draft a text",
        "draft this",
        "answer this",
        "answer this email",
        "reply to",
        "text back",
    )
    return _is_decision_shaped_request(request) or any(term in lowered for term in practical_terms)


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
    retirement_reply = _retirement_follow_up_reply(lowered, excerpt)
    if retirement_reply:
        return retirement_reply
    conversation_reply = _conversation_follow_up_reply(lowered, excerpt)
    if conversation_reply:
        return conversation_reply
    return ""


def _is_short_follow_up_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    if not lowered:
        return False
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
    if request in {"warm", "blunt", "diplomatic"}:
        return (
            f"Good. Keep it {request}. Give me who it's to and the one point you need to land, "
            "and I'll draft it."
        )
    if request in {"actual draft", "the actual draft", "draft"}:
        return "Good. Give me who it's to, what happened, and the point you need to make, and I'll write the first pass."
    if request in {"angle", "the angle", "angle first", "the angle first"}:
        return "Good. Give me who it's to, what happened, and the outcome you want, and I'll give you the angle first."
    return ""


def _decision_follow_up_reply(request: str, conversation_excerpt: str) -> str:
    if "money, energy, risk, or which choice you'd regret not taking" not in conversation_excerpt:
        return ""
    if request == "money":
        return "Okay. Is the real question pay now, long-term upside, or how much margin this buys you?"
    if request == "energy":
        return "Okay. Is this about burnout, pace, or whether this choice gives you more actual life back?"
    if request == "risk":
        return "Okay. Is the risk more about money, reputation, or ending up stuck in something you already know is wrong?"
    if request in {"regret", "regret not taking"}:
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
    if request in {"money", "money first"}:
        return "Okay. Are you trying to figure out the number, the runway, or how much work still has to stay in the picture?"
    if request in {"time", "time first"}:
        return "Okay. Are you trying to buy back your days, reduce your pace, or figure out what a week would look like without work driving it?"
    if request in {"identity", "identity first"}:
        return "Okay. Is the real question who you are without the work pace, what replaces the pressure, or what you still want to build?"
    return ""


def _conversation_follow_up_reply(request: str, conversation_excerpt: str) -> str:
    if "what you need to say, how to say it, or whether to have the conversation at all" not in conversation_excerpt:
        return ""
    if request in {"the conversation itself", "whether to have it", "whether to have the conversation"}:
        return "Okay. Do you already know you need to do it and need the opening line, or are you still deciding if this is a conversation worth having?"
    if request in {"what i need to say", "what to say"}:
        return "Okay. Give me the point you need to land and what you cannot afford to say badly, and I'll help you frame it."
    if request == "how to say it":
        return "Okay. Do you need blunt, calm, or careful, and how much tension is already in the room?"
    return ""


def _is_drafting_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    if not lowered:
        return False
    drafting_terms = (
        "draft a text",
        "draft this",
        "help me draft",
        "write this email",
        "write this",
        "answer this",
        "answer this email",
        "reply to",
        "text back",
        "write an email",
    )
    return any(term in lowered for term in drafting_terms)


def _is_decision_shaped_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    if not lowered:
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
        "text",
        "call",
        "argument",
        "conflict",
        "boundary",
    )
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
    if _is_decision_shaped_request(request):
        return "Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
    if _is_drafting_request(request):
        return "Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
    if any(term in lowered for term in conversation_terms):
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

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.companion_spine import (
    build_companion_system_prompt,
    build_context_packet,
    generate_companion_fallback,
    harden_companion_reply,
    run_companion_turn,
)
from jarvis.runtime import JarvisRuntime
from jarvis.models import (
    ActionClass,
    PrivacyLevel,
    RequestPlan,
    RiskLevel,
    RoutingTier,
    TaskClass,
    UserProfile,
)
from jarvis.openai_tasks import OpenAIResult


ROOT = Path(__file__).resolve().parents[1]


def _plan(request: str) -> RequestPlan:
    return RequestPlan(
        request_id="req-1",
        actor="Chris",
        room="office",
        request=request,
        mode="ambient-associate",
        module="conversation",
        workstream="conversation",
        task_class=TaskClass.AMBIENT,
        preferred_provider="openai",
        context_lane="conversation",
        model="gpt-5.4-mini",
        routing_tier=RoutingTier.USER_FACING_DELIVERY,
        privacy_level=PrivacyLevel.CLOUD_OK,
        risk_level=RiskLevel.LOW,
        action_class=ActionClass.SUGGEST,
        allowed=True,
        needs_approval=False,
        second_factor_required=False,
        rationale="conversation",
    )


class _StubOpenAIClient:
    def __init__(self, result: OpenAIResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    def respond(self, plan, supplemental_context: str = "", system_prompt_override: str = "") -> OpenAIResult:
        self.calls.append(
            {
                "plan": plan,
                "supplemental_context": supplemental_context,
                "system_prompt_override": system_prompt_override,
            }
        )
        return self.result


class _StubRuntime:
    def __init__(self, result: OpenAIResult, *, obsidian_conversation_enabled: bool = False) -> None:
        self.openai_client = _StubOpenAIClient(result)
        self.family_calendar = SimpleNamespace(summary=lambda: {"events": []})
        self.config = SimpleNamespace(obsidian_conversation_enabled=obsidian_conversation_enabled)
        self.obsidian_support = SimpleNamespace(
            enabled=True,
            status=lambda: {"enabled": True},
            conversation_context=lambda query, limit=3: (
                "Retrieved Obsidian notes:\n"
                "- Retirement Vision (Monday/Retirement/Retirement Vision.md): Retirement means freedom to build at a healthier pace."
            )
            if "retire" in query.lower()
            else "",
            retrieve=lambda query, limit=2: [
                {
                    "title": "Retirement Vision",
                    "rel_path": "Monday/Retirement/Retirement Vision.md",
                    "snippet": "Retirement means freedom to build at a healthier pace.",
                }
            ]
            if "obsidian" in query.lower() or "retire" in query.lower()
            else [],
        )

    def _relevant_profile_facts(self, actor: UserProfile, request: str, limit: int = 4) -> list[str]:
        return ["Chris is building Jarvis carefully.", "Chris values truthful product behavior."][:limit]

    def _is_operating_status_request(self, request: str) -> bool:
        return "status" in request.lower()

    def _live_operating_status_context(self, actor_name: str) -> list[str]:
        return [f"{actor_name}: command surface healthy"]

    def storm_weather_summary(self) -> dict:
        return {"available": False}


class _StubRuntimeNoObsidian(_StubRuntime):
    def __init__(self, result: OpenAIResult) -> None:
        super().__init__(result)
        self.obsidian_support = SimpleNamespace(
            enabled=False,
            status=lambda: {"enabled": False},
            conversation_context=lambda query, limit=3: "",
            retrieve=lambda query, limit=2: [],
        )


class CompanionSpineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actor = UserProfile(
            user_id="chris",
            display_name="Chris",
            address_as="Chris",
            role="primary",
            permissions="admin",
            priorities=["build", "family"],
        )

    def test_context_packet_matches_phase_1_contract(self) -> None:
        runtime = _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Ready."))
        packet = build_context_packet(
            runtime,
            self.actor,
            "office",
            "Help me think through vacation.",
            plan=_plan("Help me think through vacation."),
            conversation_excerpt="Chris: Help me think through vacation.",
        )
        self.assertEqual(
            set(packet.keys()),
            {
                "user_message",
                "conversation_excerpt",
                "known_user_profile",
                "active_context",
                "available_capabilities",
                "truth_constraints",
                "voice_standard",
                "forbidden_patterns",
            },
        )
        self.assertEqual(packet["user_message"], "Help me think through vacation.")
        self.assertIn("Chris is building Jarvis carefully.", packet["known_user_profile"]["known_facts"])
        self.assertIn("live Obsidian retrieval not active in the default conversation path", packet["available_capabilities"])

    def test_system_prompt_sets_friend_with_tools_boundary(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "truth_constraints": ["Do not fake actions."],
            "voice_standard": "Direct, warm, practical.",
            "forbidden_patterns": ["therapy language", "corporate dashboard language"],
        }
        prompt = build_companion_system_prompt(packet)
        self.assertIn("smart, loyal friend with tools", prompt)
        self.assertIn("Do not fake actions.", prompt)
        self.assertIn("live Obsidian retrieval is not wired into this conversation yet", prompt)
        self.assertIn("Stay in normal conversation unless the user explicitly asks", prompt)

    def test_run_companion_turn_uses_override_prompt_and_packet(self) -> None:
        runtime = _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Nice. Let's map it."))
        result = run_companion_turn(
            runtime,
            self.actor,
            "office",
            "Help me think through vacation.",
            plan=_plan("Help me think through vacation."),
            continuity_context="Chris: Help me think through vacation.",
        )
        self.assertEqual(result.output_text, "Nice. Let's map it.")
        self.assertEqual(len(runtime.openai_client.calls), 1)
        call = runtime.openai_client.calls[0]
        self.assertIn("smart, loyal friend with tools", call["system_prompt_override"])
        self.assertIn('"user_message": "Help me think through vacation."', call["supplemental_context"])

    def test_companion_fallback_handles_required_prompts(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        runtime = _StubRuntime(OpenAIResult(provider="fallback", model="fallback", output_text=""))
        self.assertIn(
            "live retrieval is not wired into this conversation yet",
            generate_companion_fallback("What do you know from Obsidian about retirement?", packet, runtime=runtime),
        )
        self.assertIn(
            "Retirement Vision",
            generate_companion_fallback(
                "What do you know from Obsidian about retirement?",
                packet,
                runtime=_StubRuntime(
                    OpenAIResult(provider="fallback", model="fallback", output_text=""),
                    obsidian_conversation_enabled=True,
                ),
            ),
        )
        self.assertIn("Where are we going", generate_companion_fallback("Help me think through vacation.", packet))
        self.assertIn("theater", generate_companion_fallback("This still feels like a chatbot.", packet))
        self.assertIn("driver's seat", generate_companion_fallback("I want to retire.", packet))
        self.assertIn(
            "let's keep it practical",
            generate_companion_fallback(
                "Your concern is valid, but vacation is usually not about vacation. Help me understand what this means for my life.",
                packet,
            ).lower(),
        )

    def test_greeting_prompt_gets_warmer_useful_opening(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Hey Jarvis", packet)
        self.assertIn("i'm here", reply.lower())
        self.assertIn("what's on your mind", reply.lower())
        self.assertNotIn("as an ai assistant", reply.lower())

    def test_proof_of_life_prompt_gets_plain_invitation(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Is Jarvis working?", packet)
        self.assertIn("yeah, i'm here", reply.lower())
        self.assertIn("decision, plan, or draft", reply.lower())
        self.assertIn("path is alive", reply.lower())

    def test_unmatched_practical_conversation_request_gets_concrete_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me think through a hard conversation with my brother", packet)
        self.assertIn("let's make it concrete", reply.lower())
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_unmatched_practical_week_planning_request_gets_concrete_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to get my week under control", packet)
        self.assertIn("let's get your week back under control", reply.lower())
        self.assertIn("too much on the calendar", reply.lower())
        self.assertIn("fuzzy priorities", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_drafting_text_request_gets_concrete_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me draft a text to my brother", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_drafting_email_request_gets_concrete_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to answer this email", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_drafting_follow_up_warm_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("warm", packet)
        self.assertIn("keep it warm", reply.lower())
        self.assertIn("who it's to", reply.lower())
        self.assertIn("i'll draft it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_drafting_follow_up_actual_draft_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to answer this email\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("actual draft", packet)
        self.assertIn("who it's to", reply.lower())
        self.assertIn("what happened", reply.lower())
        self.assertIn("write the first pass", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_decision_shaped_job_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Should I take the new job?", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_decision_shaped_torn_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I'm torn between staying and leaving.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_decision_follow_up_energy_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Should I take the new job?\n"
                "Jarvis: Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
            ),
        }
        reply = generate_companion_fallback("energy", packet)
        self.assertIn("burnout", reply.lower())
        self.assertIn("pace", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_decision_follow_up_risk_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I'm torn between staying and leaving.\n"
                "Jarvis: Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
            ),
        }
        reply = generate_companion_fallback("risk", packet)
        self.assertIn("money", reply.lower())
        self.assertIn("reputation", reply.lower())
        self.assertIn("stuck", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_unmatched_non_practical_prompt_gets_human_handle(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I've had a weird day", packet)
        self.assertIn("i'm here", reply.lower())
        self.assertIn("what happened", reply.lower())
        self.assertIn("rest of the day", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_unmatched_ambiguous_prompt_gets_simple_handle(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I'm kind of off today", packet)
        self.assertIn("i'm here", reply.lower())
        self.assertIn("what happened", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_retirement_follow_up_money_first_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("money first", packet)
        self.assertIn("the number", reply.lower())
        self.assertIn("the runway", reply.lower())
        self.assertNotIn("which part feels off", reply.lower())

    def test_conversation_follow_up_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what you need to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("the conversation itself", packet)
        self.assertIn("opening line", reply.lower())
        self.assertIn("worth having", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_practical_fork_follow_up_plan_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me untangle this mess\n"
                "Jarvis: Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?"
            ),
        }
        reply = generate_companion_fallback("plan", packet)
        self.assertIn("too much on the calendar", reply.lower())
        self.assertIn("fuzzy priorities", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_practical_fork_follow_up_conversation_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me untangle this mess\n"
                "Jarvis: Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?"
            ),
        }
        reply = generate_companion_fallback("conversation", packet)
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_generic_sympathy_reply_is_repaired(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "I've had a weird day",
            "I'm sorry you're dealing with that.",
            packet,
        )
        self.assertNotEqual(repaired, "I'm sorry you're dealing with that.")
        self.assertIn("what happened", repaired.lower())

    def test_thin_validation_reply_is_repaired(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "I'm kind of off today",
            "That sounds hard.",
            packet,
        )
        self.assertNotEqual(repaired, "That sounds hard.")
        self.assertIn("what happened", repaired.lower())

    def test_good_non_practical_handle_reply_passes_through_unchanged(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = "I'm here. Want to tell me what happened, or do you want to shake it off and talk about something else?"
        self.assertEqual(
            harden_companion_reply("I've had a weird day", reply, packet),
            reply,
        )

    def test_overexplaining_reply_gets_trimmed_to_useful_point(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = (
            "That's a really good question. There are a few ways to think about this. "
            "The real issue is that you're overloaded and trying to carry too many priorities at once."
        )
        repaired = harden_companion_reply("I've had a weird day", reply, packet)
        self.assertNotIn("that's a really good question", repaired.lower())
        self.assertNotIn("there are a few ways to think about this", repaired.lower())
        self.assertIn("you're overloaded", repaired.lower())

    def test_padded_practical_reply_gets_trimmed_but_keeps_handle(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = (
            "That's a thoughtful question. It's worth taking a step back for a second. "
            "The useful place to start is your week. What is actually immovable, and what only feels immovable?"
        )
        repaired = harden_companion_reply("I need to get my week under control", reply, packet)
        self.assertNotIn("that's a thoughtful question", repaired.lower())
        self.assertNotIn("it's worth taking a step back", repaired.lower())
        self.assertIn("what is actually immovable", repaired.lower())

    def test_good_concise_trim_candidate_passes_through_unchanged(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = "The real issue is that you're overloaded. What is actually immovable this week?"
        self.assertEqual(
            harden_companion_reply("I need to get my week under control", reply, packet),
            reply,
        )

    def test_missing_obsidian_fails_plainly(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell"]}
        runtime = _StubRuntimeNoObsidian(OpenAIResult(provider="fallback", model="fallback", output_text=""))
        reply = generate_companion_fallback(
            "What does Obsidian say about retirement?",
            packet,
            runtime=runtime,
        )
        self.assertIn("live retrieval is not wired into this conversation yet", reply)

    def test_runtime_converse_uses_companion_spine_boundary(self) -> None:
        text = (ROOT / "jarvis" / "runtime.py").read_text(encoding="utf-8")
        self.assertIn("result = run_companion_turn(", text)
        self.assertIn("def _try_handle_conversation_intercepts(", text)
        self.assertIn("reminder_result = self._try_handle_reminder(request)", text)
        self.assertIn("task_result = self._try_handle_task_creation(request)", text)

    def test_runtime_conversation_mission_intercept_is_narrowed_to_explicit_planning_language(self) -> None:
        self.assertTrue(JarvisRuntime._should_allow_conversation_mission_intercept(None, "Track this in mission control."))
        self.assertTrue(JarvisRuntime._should_allow_conversation_mission_intercept(None, "Build a plan for retirement."))
        self.assertFalse(JarvisRuntime._should_allow_conversation_mission_intercept(None, "I need to work on my latest book."))

    def test_runtime_explicit_packet_request_only_opens_on_explicit_surface_language(self) -> None:
        self.assertEqual(JarvisRuntime._explicit_packet_request(None, "Open mission control"), "mission-control")
        self.assertEqual(JarvisRuntime._explicit_packet_request(None, "Take me to Catalyst email"), "catalyst")
        self.assertEqual(JarvisRuntime._explicit_packet_request(None, "Help me think through vacation."), "")

    def test_voice_ui_does_not_auto_open_packets_after_chat_reply(self) -> None:
        text = (ROOT / "jarvis" / "voice_ui.py").read_text(encoding="utf-8")
        self.assertNotIn(
            '      const suggestedPacket = packetFromRequest(request);\n'
            '      if (suggestedPacket) {{\n'
            '        if (suggestedPacket === "catalyst") {{\n'
            '          state.catalystPage = catalystPageFromRequest(request);\n'
            '        }}\n'
            '        openPacket(suggestedPacket);\n'
            '      }}\n',
            text,
        )
        self.assertIn("if (data.requested_packet) {{", text)
        self.assertIn("openPacket(data.requested_packet);", text)

    def test_obsidian_context_is_distinguished_in_active_context(self) -> None:
        runtime = _StubRuntime(
            OpenAIResult(provider="openai", model="gpt", output_text="Ready."),
            obsidian_conversation_enabled=True,
        )
        packet = build_context_packet(
            runtime,
            self.actor,
            "office",
            "What does Obsidian say about retirement?",
            plan=_plan("What does Obsidian say about retirement?"),
            conversation_excerpt="Chris: What does Obsidian say about retirement?",
        )
        self.assertIn("Retrieved Obsidian notes:", packet["active_context"])
        self.assertIn("Retirement Vision", packet["active_context"])

    def test_default_context_packet_does_not_include_obsidian_context(self) -> None:
        runtime = _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Ready."))
        packet = build_context_packet(
            runtime,
            self.actor,
            "office",
            "What does Obsidian say about retirement?",
            plan=_plan("What does Obsidian say about retirement?"),
            conversation_excerpt="Chris: What does Obsidian say about retirement?",
        )
        self.assertNotIn("Retrieved Obsidian notes:", packet["active_context"] or "")

    def test_therapist_language_reply_is_repaired(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "Help me think through vacation.",
            "Your concern is valid. Let's explore what this means for you.",
            packet,
        )
        self.assertNotIn("Your concern is valid", repaired)
        self.assertIn("Where are we going", repaired)

    def test_abstract_meaning_reply_becomes_practical_next_step(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "Help me think through retirement.",
            "This is really about identity and the deeper meaning of your life transition.",
            packet,
        )
        self.assertIn("money, time, or identity first", repaired)

    def test_reply_without_practical_handle_gets_actionable_next_move(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "Help me work on my latest book.",
            "This matters a lot and there's a lot going on here.",
            packet,
        )
        self.assertIn("What's the book", repaired)

    def test_vague_reflective_question_is_repaired(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "Help me think through vacation.",
            "How does that feel for you?",
            packet,
        )
        self.assertNotEqual(repaired, "How does that feel for you?")
        self.assertIn("Where are we going", repaired)

    def test_success_question_is_repaired_for_practical_request(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "I want to retire.",
            "What would success look like here?",
            packet,
        )
        self.assertNotEqual(repaired, "What would success look like here?")
        self.assertIn("money, time, or identity first", repaired)

    def test_flat_decision_reply_is_repaired_into_tradeoff_fork(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "Should I take the new job?",
            "It depends what matters most to you.",
            packet,
        )
        self.assertNotEqual(repaired, "It depends what matters most to you.")
        self.assertIn("money, energy, risk", repaired.lower())
        self.assertIn("regret not taking", repaired.lower())

    def test_pros_and_cons_decision_reply_is_repaired_into_tradeoff_fork(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "I'm torn between staying and leaving.",
            "There are pros and cons to both.",
            packet,
        )
        self.assertNotEqual(repaired, "There are pros and cons to both.")
        self.assertIn("money, energy, risk", repaired.lower())
        self.assertIn("regret not taking", repaired.lower())

    def test_good_concise_decision_tradeoff_reply_passes_through_unchanged(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = "This feels like upside versus stability. Which one matters more right now?"
        self.assertEqual(
            harden_companion_reply("Should I take the new job?", reply, packet),
            reply,
        )

    def test_hedged_practical_reply_is_repaired_into_concrete_next_move(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "I need to get my week under control",
            "Maybe start by thinking about what matters most.",
            packet,
        )
        self.assertNotEqual(repaired, "Maybe start by thinking about what matters most.")
        self.assertIn("too much on the calendar", repaired.lower())
        self.assertIn("fuzzy priorities", repaired.lower())

    def test_noncommittal_practical_reply_is_repaired_into_concrete_next_move(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "Help me think through a hard conversation with my brother",
            "It could make sense to take a step back and think about it.",
            packet,
        )
        self.assertNotEqual(repaired, "It could make sense to take a step back and think about it.")
        self.assertIn("what you need to say", repaired.lower())
        self.assertIn("whether to have the conversation", repaired.lower())

    def test_good_concise_practical_reply_passes_through_unchanged(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = "Start with the week. What is actually immovable?"
        self.assertEqual(
            harden_companion_reply("I need to get my week under control", reply, packet),
            reply,
        )

    def test_overloaded_planning_reply_gets_capacity_pushback(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "I need to get my week under control",
            "Let's organize it and see what fits.",
            packet,
        )
        self.assertNotEqual(repaired, "Let's organize it and see what fits.")
        self.assertIn("one cut", repaired.lower())
        self.assertIn("immovable", repaired.lower())

    def test_overloaded_week_reply_that_avoids_cuts_gets_narrowing_move(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "I'm overwhelmed and behind this week.",
            "Let's make a list and prioritize everything.",
            packet,
        )
        self.assertNotEqual(repaired, "Let's make a list and prioritize everything.")
        self.assertIn("one cut", repaired.lower())
        self.assertIn("what is actually immovable", repaired.lower())

    def test_good_concise_capacity_pushback_reply_passes_through_unchanged(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = "You do not need a better plan yet. You need one cut. What is actually immovable this week?"
        self.assertEqual(
            harden_companion_reply("I need to get my week under control", reply, packet),
            reply,
        )

    def test_good_concise_drafting_reply_passes_through_unchanged(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = "Do you want blunt, warm, or diplomatic?"
        self.assertEqual(
            harden_companion_reply("Help me write this email", reply, packet),
            reply,
        )

    def test_standalone_vacation_prompt_remains_unchanged(self) -> None:
        packet = {
            "available_capabilities": ["planning and drafting in chat"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("Help me think through vacation.", packet)
        self.assertIn("where are we going", reply.lower())
        self.assertIn("who's coming", reply.lower())

    def test_existing_drafting_follow_up_family_remains_unchanged(self) -> None:
        packet = {
            "available_capabilities": ["planning and drafting in chat"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("warm", packet)
        self.assertEqual(
            reply,
            "Good. Keep it warm. Give me who it's to and the one point you need to land, and I'll draft it.",
        )

    def test_capability_reply_is_grounded_without_raw_internal_labels(self) -> None:
        packet = {
            "available_capabilities": [
                "ongoing conversation in this shell",
                "conversation turn persistence",
                "recent conversation continuity",
                "durable profile facts already stored locally",
                "planning and drafting in chat",
                "live Obsidian retrieval not active in the default conversation path",
            ]
        }
        repaired = harden_companion_reply(
            "What can you actually do right now?",
            (
                "Right now I can help with ongoing conversation in this shell, conversation turn persistence, "
                "recent conversation continuity, durable profile facts already stored locally, planning and "
                "drafting in chat, and live Obsidian retrieval not active in the default conversation path."
            ),
            packet,
        )
        self.assertNotIn("ongoing conversation in this shell", repaired)
        self.assertNotIn("conversation turn persistence", repaired)
        self.assertIn("talk things through with you", repaired)
        self.assertIn("help you plan or draft", repaired)

    def test_capability_reply_describes_unavailable_capabilities_plainly_and_truthfully(self) -> None:
        packet = {
            "available_capabilities": [
                "planning and drafting in chat",
                "live Obsidian retrieval not active in the default conversation path",
            ]
        }
        reply = generate_companion_fallback("What can you do?", packet)
        self.assertIn("not doing live Obsidian retrieval", reply)
        self.assertNotIn("live Obsidian retrieval not active in the default conversation path", reply)

    def test_capability_reply_adds_practical_offer(self) -> None:
        packet = {
            "available_capabilities": [
                "planning and drafting in chat",
                "live Obsidian retrieval not active in the default conversation path",
            ]
        }
        reply = generate_companion_fallback("What can you actually do right now?", packet)
        self.assertIn("give me one decision, plan, or draft", reply)

    def test_good_concise_friend_style_reply_passes_through_unchanged(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = "Nice. Where are we going, what dates, and who's coming?"
        self.assertEqual(
            harden_companion_reply("Help me think through vacation.", reply, packet),
            reply,
        )

    def test_good_grounded_capability_reply_passes_through_unchanged(self) -> None:
        packet = {
            "available_capabilities": [
                "planning and drafting in chat",
                "live Obsidian retrieval not active in the default conversation path",
            ]
        }
        reply = (
            "Right now I can help you think through decisions, help you plan or draft, and keep continuity "
            "in this conversation. I'm not doing live Obsidian retrieval in this default conversation path yet. "
            "If you want, give me one decision, plan, or draft and I'll help with it now."
        )
        self.assertEqual(
            harden_companion_reply("What can you actually do right now?", reply, packet),
            reply,
        )

    def test_truthful_limitation_reply_is_preserved(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        reply = "I have the Obsidian vault path recorded, but live retrieval is not wired into this conversation yet."
        self.assertEqual(
            harden_companion_reply("What does Obsidian say?", reply, packet),
            reply,
        )


if __name__ == "__main__":
    unittest.main()

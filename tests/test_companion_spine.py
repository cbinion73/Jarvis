from __future__ import annotations

import tempfile
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
                "effective_user_message",
                "conversation_excerpt",
                "known_user_profile",
                "active_context",
                "relationship_model",
                "correction_context",
                "topic_brief",
                "canon_brief",
                "response_contract",
                "available_capabilities",
                "truth_constraints",
                "voice_standard",
                "forbidden_patterns",
            },
        )
        self.assertEqual(packet["user_message"], "Help me think through vacation.")
        self.assertEqual(packet["effective_user_message"], "Help me think through vacation.")
        self.assertIn("Chris is building Jarvis carefully.", packet["known_user_profile"]["known_facts"])
        self.assertEqual(packet["relationship_model"], "smart, loyal friend with tools")
        self.assertIsNone(packet["correction_context"])
        self.assertTrue(packet["topic_brief"])
        self.assertTrue(packet["response_contract"])
        self.assertIn("live Obsidian retrieval not active in the default conversation path", packet["available_capabilities"])

    def test_context_packet_captures_correction_command_against_last_reply(self) -> None:
        runtime = _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Ready."))
        packet = build_context_packet(
            runtime,
            self.actor,
            "office",
            "/correct I wanted a more practical answer about timing and walking.",
            plan=_plan("/correct I wanted a more practical answer about timing and walking."),
            conversation_excerpt=(
                "Active conversation with Chris in office.\n"
                "Recent turns:\n"
                "Chris: I am going to the Statue of Liberty tomorrow.\n"
                "JARVIS: Is this real work timing or ferry logistics?\n"
                "Chris: /correct I wanted a more practical answer about timing and walking."
            ),
        )
        self.assertEqual(packet["effective_user_message"], "I am going to the Statue of Liberty tomorrow.")
        self.assertEqual(
            packet["correction_context"],
            {
                "mode": "correct",
                "feedback": "I wanted a more practical answer about timing and walking.",
                "last_user_message": "I am going to the Statue of Liberty tomorrow.",
                "last_assistant_message": "Is this real work timing or ferry logistics?",
            },
        )
        self.assertTrue(packet["topic_brief"])
        self.assertTrue(any("rewrite it directly" in item.lower() for item in packet["response_contract"]))

    def test_context_packet_captures_teach_command_against_last_reply(self) -> None:
        runtime = _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Ready."))
        packet = build_context_packet(
            runtime,
            self.actor,
            "office",
            "/teach be more practical about timing and walking",
            plan=_plan("/teach be more practical about timing and walking"),
            conversation_excerpt=(
                "Active conversation with Chris in office.\n"
                "Recent turns:\n"
                "Chris: I am going to the Statue of Liberty tomorrow.\n"
                "JARVIS: Is this real work timing or ferry logistics?\n"
                "Chris: /teach be more practical about timing and walking"
            ),
        )
        self.assertEqual(packet["effective_user_message"], "I am going to the Statue of Liberty tomorrow.")
        self.assertEqual(packet["correction_context"]["mode"], "teach")
        self.assertIn("future replies", " ".join(packet["response_contract"]).lower())

    def test_context_packet_captures_learn_command_against_last_reply(self) -> None:
        runtime = _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Ready."))
        packet = build_context_packet(
            runtime,
            self.actor,
            "office",
            "/learn be more practical about timing and walking",
            plan=_plan("/learn be more practical about timing and walking"),
            conversation_excerpt=(
                "Active conversation with Chris in office.\n"
                "Recent turns:\n"
                "Chris: I am going to the Statue of Liberty tomorrow.\n"
                "JARVIS: Is this real work timing or ferry logistics?\n"
                "Chris: /learn be more practical about timing and walking"
            ),
        )
        self.assertEqual(packet["effective_user_message"], "I am going to the Statue of Liberty tomorrow.")
        self.assertEqual(packet["correction_context"]["mode"], "learn")
        self.assertIn("reusable jarvis skill", " ".join(packet["response_contract"]).lower())

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
        self.assertIn("Start with your read of the situation", prompt)
        self.assertIn("do not ask taxonomy questions", prompt)
        self.assertIn("rewrite the answer directly", prompt)

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
        self.assertIn("Companion context packet:", call["supplemental_context"])
        self.assertIn("User message: Help me think through vacation.", call["supplemental_context"])
        self.assertIn("Topic brief for this request:", call["supplemental_context"])

    def test_run_companion_turn_carries_correction_context_into_prompt_packet(self) -> None:
        runtime = _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Here is the better version."))
        result = run_companion_turn(
            runtime,
            self.actor,
            "office",
            "/correct I wanted a more practical answer focused on timing and walking.",
            plan=_plan("/correct I wanted a more practical answer focused on timing and walking."),
            continuity_context=(
                "Active conversation with Chris in office.\n"
                "Recent turns:\n"
                "Chris: I am going to the Statue of Liberty tomorrow.\n"
                "JARVIS: Is this real work timing or ferry logistics?\n"
                "Chris: /correct I wanted a more practical answer focused on timing and walking."
            ),
        )
        self.assertEqual(result.output_text, "Here is the better version.")
        call = runtime.openai_client.calls[0]
        self.assertIn("Correction context:", call["supplemental_context"])
        self.assertIn("Last Jarvis reply to correct:", call["supplemental_context"])
        self.assertIn("Effective request to answer: I am going to the Statue of Liberty tomorrow.", call["supplemental_context"])

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
        self.assertIn(
            "where to go, what kind of trip this needs to be, or what is making it hard to land",
            generate_companion_fallback("Help me think through vacation.", packet).lower(),
        )
        self.assertIn("theater", generate_companion_fallback("This still feels like a chatbot.", packet))
        self.assertIn("driver's seat", generate_companion_fallback("I want to retire.", packet))
        self.assertIn(
            "let's keep it practical",
            generate_companion_fallback(
                "Your concern is valid, but vacation is usually not about vacation. Help me understand what this means for my life.",
                packet,
            ).lower(),
        )

    def test_correction_command_fallback_rewrites_using_prior_request_shape(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "correction_context": {
                "feedback": "a more practical answer focused on timing and walking",
                "last_user_message": "I am going to the Statue of Liberty tomorrow.",
                "last_assistant_message": "Is this real work timing or ferry logistics?",
            },
            "topic_brief": [
                "Travel help should infer likely pressure points like timing, booking, departure point, companions, mobility, and how the outing fits the rest of the day.",
            ],
            "response_contract": ["The user is correcting your last answer, so rewrite it directly instead of defending it."],
        }
        reply = generate_companion_fallback("/correct a more practical answer focused on timing and walking", packet)
        self.assertIn("you wanted a more practical answer focused on timing and walking", reply.lower())
        self.assertIn("real trip day", reply.lower())
        self.assertIn("timing", reply.lower())

    def test_teach_command_fallback_rewrites_and_promises_carry_forward(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "correction_context": {
                "mode": "teach",
                "feedback": "be more practical about timing and walking",
                "last_user_message": "I am going to the Statue of Liberty tomorrow.",
                "last_assistant_message": "Is this real work timing or ferry logistics?",
            },
            "topic_brief": [
                "Travel help should infer likely pressure points like timing, booking, departure point, companions, mobility, and how the outing fits the rest of the day.",
            ],
            "response_contract": ["The user wants this preference carried into future replies, so acknowledge that briefly and naturally."],
        }
        reply = generate_companion_fallback("/teach be more practical about timing and walking", packet)
        self.assertIn("i'll carry that forward", reply.lower())
        self.assertIn("real trip day", reply.lower())

    def test_learn_command_fallback_rewrites_and_stages_skill(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "correction_context": {
                "mode": "learn",
                "feedback": "be more practical about timing and walking",
                "last_user_message": "I am going to the Statue of Liberty tomorrow.",
                "last_assistant_message": "Is this real work timing or ferry logistics?",
            },
            "topic_brief": [
                "Travel help should infer likely pressure points like timing, booking, departure point, companions, mobility, and how the outing fits the rest of the day.",
            ],
            "response_contract": ["The user wants this turned into a reusable Jarvis skill, so acknowledge that it will be staged for approval."],
        }
        reply = generate_companion_fallback("/learn be more practical about timing and walking", packet)
        self.assertIn("reusable skill for approval", reply.lower())
        self.assertIn("real trip day", reply.lower())

    def test_runtime_record_conversation_teaching_stores_instruction_preference(self) -> None:
        runtime = SimpleNamespace()
        remembered: list[dict] = []
        runtime.conversation_store = SimpleNamespace(update_thread=lambda *args, **kwargs: None)

        def _remember(*args, **kwargs):
            remembered.append({"args": args, "kwargs": kwargs})
            return {
                "stored": True,
                "needs_approval": False,
                "entry": {"entry_id": "entry-1"},
                "profile_promotion": {"fact": {"fact_id": "fact-1"}},
            }

        runtime.remember = _remember
        runtime._conversation_teaching_command = JarvisRuntime._conversation_teaching_command.__get__(runtime, JarvisRuntime)
        runtime._conversation_teaching_context = JarvisRuntime._conversation_teaching_context.__get__(runtime, JarvisRuntime)
        runtime._teaching_preference_summary = JarvisRuntime._teaching_preference_summary.__get__(runtime, JarvisRuntime)
        runtime._conversation_signal_key = JarvisRuntime._conversation_signal_key.__get__(runtime, JarvisRuntime)
        result = JarvisRuntime._record_conversation_teaching(
            runtime,
            self.actor,
            "conv-1",
            "office",
            "/teach be more practical about timing and walking",
            thread={
                "memory_signals": [],
                "turns": [
                    {"role": "user", "text": "I am going to the Statue of Liberty tomorrow."},
                    {"role": "assistant", "text": "Is this real work timing or ferry logistics?"},
                    {"role": "user", "text": "/teach be more practical about timing and walking"},
                ],
            },
        )
        self.assertTrue(result["stored"])
        self.assertEqual(result["fact_id"], "fact-1")
        self.assertEqual(len(remembered), 1)
        self.assertEqual(remembered[0]["kwargs"]["provenance"], "instruction")
        self.assertIn("teach-jarvis", remembered[0]["kwargs"]["tags"])

    def test_runtime_record_conversation_teaching_ignores_learn_command(self) -> None:
        runtime = SimpleNamespace()
        remembered: list[dict] = []
        runtime.conversation_store = SimpleNamespace(update_thread=lambda *args, **kwargs: None)

        def _remember(*args, **kwargs):
            remembered.append({"args": args, "kwargs": kwargs})
            return {
                "stored": True,
                "needs_approval": False,
                "entry": {"entry_id": "entry-1"},
                "profile_promotion": {"fact": {"fact_id": "fact-1"}},
            }

        runtime.remember = _remember
        runtime._conversation_teaching_command = JarvisRuntime._conversation_teaching_command.__get__(runtime, JarvisRuntime)
        runtime._conversation_teaching_context = JarvisRuntime._conversation_teaching_context.__get__(runtime, JarvisRuntime)
        runtime._teaching_preference_summary = JarvisRuntime._teaching_preference_summary.__get__(runtime, JarvisRuntime)
        runtime._conversation_signal_key = JarvisRuntime._conversation_signal_key.__get__(runtime, JarvisRuntime)
        result = JarvisRuntime._record_conversation_teaching(
            runtime,
            self.actor,
            "conv-1",
            "office",
            "/learn be more practical about timing and walking",
            thread={
                "memory_signals": [],
                "turns": [
                    {"role": "user", "text": "I am going to the Statue of Liberty tomorrow."},
                    {"role": "assistant", "text": "Is this real work timing or ferry logistics?"},
                    {"role": "user", "text": "/learn be more practical about timing and walking"},
                ],
            },
        )
        self.assertEqual(result, {})
        self.assertEqual(remembered, [])

    def test_runtime_relevant_profile_facts_surfaces_conversation_style_preferences(self) -> None:
        runtime = SimpleNamespace()
        runtime.memory_support = SimpleNamespace(
            profile_facts=lambda actor, subject_user_id="": [
                {"summary": "Chris prefers Jarvis replies that are practical and thesis-first", "tags": ["conversation-style", "teach-jarvis"]},
                {"summary": "Chris responds well to exercise", "tags": ["health"]},
            ],
            store=SimpleNamespace(retrieve_by_situation=lambda actor, situation_context: []),
        )
        runtime._conversation_signal_key = JarvisRuntime._conversation_signal_key.__get__(runtime, JarvisRuntime)
        facts = JarvisRuntime._relevant_profile_facts(runtime, self.actor, "I am planning a trip tomorrow", limit=4)
        self.assertIn("Chris prefers Jarvis replies that are practical and thesis-first", facts)

    def test_runtime_stage_conversation_skill_learning_creates_approval_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = SimpleNamespace()
            runtime.self_improvement_store = __import__("jarvis.self_improvement", fromlist=["SelfImprovementStore"]).SelfImprovementStore(Path(tmp))
            runtime._repo_root = lambda: Path(tmp)
            runtime._conversation_teaching_command = JarvisRuntime._conversation_teaching_command.__get__(runtime, JarvisRuntime)
            runtime._conversation_teaching_context = JarvisRuntime._conversation_teaching_context.__get__(runtime, JarvisRuntime)
            runtime._learned_skill_slug = JarvisRuntime._learned_skill_slug.__get__(runtime, JarvisRuntime)
            runtime._learned_skill_directory = JarvisRuntime._learned_skill_directory.__get__(runtime, JarvisRuntime)
            runtime._conversation_signal_key = JarvisRuntime._conversation_signal_key.__get__(runtime, JarvisRuntime)
            runtime._slugify_runtime_text = JarvisRuntime._slugify_runtime_text.__get__(runtime, JarvisRuntime)
            result = JarvisRuntime._stage_conversation_skill_learning(
                runtime,
                self.actor,
                "conv-2",
                "office",
                "/learn be more practical about timing and walking",
                thread={
                    "turns": [
                        {"role": "user", "text": "I am going to the Statue of Liberty tomorrow."},
                        {"role": "assistant", "text": "Is this real work timing or ferry logistics?"},
                        {"role": "user", "text": "/learn be more practical about timing and walking"},
                    ]
                },
            )
            self.assertEqual(result["mode"], "learn")
            self.assertEqual(result["status"], "approval-required")
            stored = runtime.self_improvement_store.get_job(result["proposal_id"])
            self.assertEqual(stored["job_type"], "learned_skill")
            self.assertEqual(stored["status"], "approval-required")

    def test_runtime_stage_conversation_skill_learning_refreshes_existing_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = SimpleNamespace()
            runtime.self_improvement_store = __import__("jarvis.self_improvement", fromlist=["SelfImprovementStore"]).SelfImprovementStore(Path(tmp))
            runtime._repo_root = lambda: Path(tmp)
            runtime._conversation_teaching_command = JarvisRuntime._conversation_teaching_command.__get__(runtime, JarvisRuntime)
            runtime._conversation_teaching_context = JarvisRuntime._conversation_teaching_context.__get__(runtime, JarvisRuntime)
            runtime._learned_skill_slug = JarvisRuntime._learned_skill_slug.__get__(runtime, JarvisRuntime)
            runtime._learned_skill_directory = JarvisRuntime._learned_skill_directory.__get__(runtime, JarvisRuntime)
            runtime._conversation_signal_key = JarvisRuntime._conversation_signal_key.__get__(runtime, JarvisRuntime)
            runtime._slugify_runtime_text = JarvisRuntime._slugify_runtime_text.__get__(runtime, JarvisRuntime)
            runtime.self_improvement_store.upsert_job(
                {
                    "job_id": "existing-job",
                    "job_key": JarvisRuntime._conversation_signal_key(runtime, "chris|learned-skill|be more practical about timing and walking"),
                    "job_type": "learned_skill",
                    "status": "approval-required",
                    "title": "Learned skill: be more practical about timing and walking",
                    "summary": "Promote a reusable Jarvis skill from live conversation feedback: be more practical about timing and walking",
                    "created_at": "2026-06-30T00:00:00+00:00",
                    "updated_at": "2026-06-30T00:00:00+00:00",
                    "requested_by": "Chris",
                    "actor_user_id": "chris",
                    "room": "office",
                    "conversation_id": "old-conv",
                    "feedback": "be more practical about timing and walking",
                    "original_request": "",
                    "original_reply": "",
                    "skill_slug": "jarvis-learned-be-more-practical-about-timing-and-walking",
                    "target_path": str(Path(tmp) / ".agents" / "skills" / "jarvis-learned-be-more-practical-about-timing-and-walking" / "SKILL.md"),
                    "source": "conversation-learn",
                }
            )
            result = JarvisRuntime._stage_conversation_skill_learning(
                runtime,
                self.actor,
                "conv-2",
                "office",
                "/learn be more practical about timing and walking",
                thread={
                    "turns": [
                        {"role": "user", "text": "I am going to the Statue of Liberty tomorrow."},
                        {"role": "assistant", "text": "Is this real work timing or ferry logistics?"},
                        {"role": "user", "text": "/learn be more practical about timing and walking"},
                    ]
                },
            )
            self.assertTrue(result["existing"])
            stored = runtime.self_improvement_store.get_job("existing-job")
            self.assertEqual(stored["original_request"], "I am going to the Statue of Liberty tomorrow.")
            self.assertEqual(stored["original_reply"], "Is this real work timing or ferry logistics?")
            self.assertEqual(stored["conversation_id"], "conv-2")

    def test_runtime_resolve_learning_proposal_materializes_skill_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = SimpleNamespace()
            root = Path(tmp)
            runtime.self_improvement_store = __import__("jarvis.self_improvement", fromlist=["SelfImprovementStore"]).SelfImprovementStore(root / "self_improvement")
            runtime.memory_support = SimpleNamespace(resolve_proposal=lambda proposal_id, decision: (_ for _ in ()).throw(KeyError(proposal_id)))
            runtime._repo_root = lambda: root
            runtime._slugify_runtime_text = JarvisRuntime._slugify_runtime_text.__get__(runtime, JarvisRuntime)
            runtime._learned_skill_directory = JarvisRuntime._learned_skill_directory.__get__(runtime, JarvisRuntime)
            runtime._learned_skill_slug = JarvisRuntime._learned_skill_slug.__get__(runtime, JarvisRuntime)
            runtime._learned_skill_markdown = JarvisRuntime._learned_skill_markdown.__get__(runtime, JarvisRuntime)
            runtime._materialize_learned_skill = JarvisRuntime._materialize_learned_skill.__get__(runtime, JarvisRuntime)
            proposal = {
                "job_id": "job-1",
                "job_key": "skill-alpha",
                "job_type": "learned_skill",
                "status": "approval-required",
                "title": "Learned skill: practical travel replies",
                "feedback": "be more practical about timing and walking",
                "original_request": "I am going to the Statue of Liberty tomorrow.",
                "original_reply": "Is this real work timing or ferry logistics?",
                "skill_slug": "jarvis-learned-practical-travel-replies",
                "created_at": "2026-06-30T00:00:00+00:00",
            }
            runtime.self_improvement_store.upsert_job(proposal)
            runtime.resolve_memory_proposal = lambda proposal_id, decision: (_ for _ in ()).throw(KeyError(proposal_id))
            result = JarvisRuntime.resolve_learning_proposal(runtime, "job-1", "approved")
            self.assertEqual(result["proposal_type"], "learned_skill")
            skill_path = Path(result["skill"]["skill_path"])
            self.assertTrue(skill_path.exists())
            self.assertIn("Specific learned preference", skill_path.read_text(encoding="utf-8"))

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

    def test_help_with_my_inbox_prompt_gets_concrete_inbox_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my inbox.", packet)
        self.assertIn("real problem", reply.lower())
        self.assertIn("triage", reply.lower())
        self.assertIn("replies you owe", reply.lower())
        self.assertIn("clearing the pile", reply.lower())

    def test_get_through_my_inbox_prompt_gets_concrete_inbox_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to get through my inbox.", packet)
        self.assertIn("real problem", reply.lower())
        self.assertIn("triage", reply.lower())
        self.assertIn("clearing the pile", reply.lower())

    def test_inbox_triage_prompt_gets_concrete_inbox_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my inbox triage.", packet)
        self.assertIn("real problem", reply.lower())
        self.assertIn("triage", reply.lower())
        self.assertIn("replies you owe", reply.lower())

    def test_clear_my_inbox_prompt_gets_concrete_inbox_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to clear my inbox.", packet)
        self.assertIn("real problem", reply.lower())
        self.assertIn("clearing the pile", reply.lower())

    def test_triaging_my_inbox_prompt_gets_concrete_inbox_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help triaging my inbox.", packet)
        self.assertIn("real problem", reply.lower())
        self.assertIn("triage", reply.lower())
        self.assertIn("replies you owe", reply.lower())

    def test_help_with_my_email_prompt_gets_concrete_inbox_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my email.", packet)
        self.assertIn("real problem", reply.lower())
        self.assertIn("triage", reply.lower())
        self.assertIn("replies you owe", reply.lower())

    def test_getting_through_email_prompt_gets_concrete_inbox_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting through email.", packet)
        self.assertIn("real problem", reply.lower())
        self.assertIn("triage", reply.lower())
        self.assertIn("clearing the pile", reply.lower())

    def test_triaging_email_prompt_gets_concrete_inbox_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help triaging email.", packet)
        self.assertIn("real problem", reply.lower())
        self.assertIn("triage", reply.lower())
        self.assertIn("replies you owe", reply.lower())

    def test_help_with_my_follow_up_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my follow-up.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("decision you need before you send it", reply.lower())
        self.assertIn("next move you need to lock in", reply.lower())

    def test_help_with_this_follow_up_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this follow-up.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("decision you need before you send it", reply.lower())

    def test_help_following_up_after_this_meeting_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help following up after this meeting.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("next move you need to lock in", reply.lower())

    def test_help_with_the_follow_up_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with the follow-up.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("decision you need before you send it", reply.lower())

    def test_help_with_a_follow_up_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with a follow-up.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("next move you need to lock in", reply.lower())

    def test_help_with_my_meeting_follow_up_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my meeting follow-up.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("decision you need before you send it", reply.lower())

    def test_help_with_this_debrief_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this debrief.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("next move you need to lock in", reply.lower())

    def test_help_after_this_meeting_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help after this meeting.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("next move you need to lock in", reply.lower())

    def test_help_with_my_notes_for_this_meeting_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my notes for this meeting.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("next move you need to lock in", reply.lower())

    def test_help_with_meeting_notes_prompt_gets_concrete_follow_up_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with meeting notes.", packet)
        self.assertIn("message you owe", reply.lower())
        self.assertIn("next move you need to lock in", reply.lower())

    def test_help_with_this_presentation_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this presentation.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_my_presentation_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my presentation.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_getting_ready_for_this_presentation_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting ready for this presentation.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_getting_ready_for_my_presentation_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting ready for my presentation.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_this_proposal_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this proposal.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())

    def test_help_with_my_proposal_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my proposal.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())

    def test_getting_ready_for_this_proposal_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting ready for this proposal.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_getting_ready_for_my_proposal_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting ready for my proposal.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_this_slide_deck_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this slide deck.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_my_slide_deck_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my slide deck.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_this_deck_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this deck.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_getting_ready_for_this_deck_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting ready for this deck.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_my_talking_points_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my talking points.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_this_pitch_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this pitch.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_my_pitch_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my pitch.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_my_proposal_deck_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my proposal deck.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_this_briefing_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this briefing.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_my_briefing_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my briefing.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_a_briefing_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with a briefing.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_writing_a_briefing_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help writing a briefing.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_preparing_a_briefing_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help preparing a briefing.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("the structure", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_getting_ready_for_this_briefing_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting ready for this briefing.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_getting_ready_for_my_briefing_prompt_gets_concrete_prep_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting ready for my briefing.", packet)
        self.assertIn("the point you need to land", reply.lower())
        self.assertIn("deliver it cleanly", reply.lower())

    def test_help_with_this_agenda_prompt_gets_concrete_agenda_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this agenda.", packet)
        self.assertIn("what needs to be covered", reply.lower())
        self.assertIn("what can wait", reply.lower())
        self.assertIn("conversation from drifting", reply.lower())

    def test_help_setting_the_agenda_prompt_gets_concrete_agenda_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help setting the agenda.", packet)
        self.assertIn("what needs to be covered", reply.lower())
        self.assertIn("what can wait", reply.lower())

    def test_set_the_agenda_with_me_prompt_gets_concrete_agenda_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Set the agenda with me.", packet)
        self.assertIn("what needs to be covered", reply.lower())
        self.assertIn("conversation from drifting", reply.lower())

    def test_help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help planning tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what actually has to happen", reply.lower())
        self.assertIn("what is fixed", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_help_scheduling_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help scheduling tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_help_organizing_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help organizing tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_help_with_my_schedule_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my schedule tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_help_with_my_schedule_for_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my schedule for tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_help_with_my_schedule_this_week_prompt_keeps_capacity_pushback(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my schedule this week.", packet)
        self.assertIn("you do not need a better plan yet", reply.lower())
        self.assertIn("immovable this week", reply.lower())

    def test_help_with_my_calendar_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my calendar tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_help_with_my_calendar_for_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my calendar for tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_help_with_my_calendar_this_week_prompt_keeps_capacity_pushback(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my calendar this week.", packet)
        self.assertIn("you do not need a better plan yet", reply.lower())
        self.assertIn("immovable this week", reply.lower())

    def test_planning_around_two_meetings_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help planning around two meetings.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_planning_around_two_appointments_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help planning around two appointments.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_planning_around_my_appointments_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help planning around my appointments.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_scheduling_around_appointments_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help scheduling around appointments.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_help_around_my_appointments_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help around my appointments tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_help_preparing_for_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help preparing for tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what actually has to happen", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_help_getting_ready_for_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting ready for tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_help_me_get_ready_for_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me get ready for tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_need_to_get_ready_for_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to get ready for tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_help_with_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what actually has to happen", reply.lower())

    def test_help_with_tomorrows_plan_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with tomorrow's plan.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_help_with_tomorrow_morning_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with tomorrow morning.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_mapping_out_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help mapping out tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_map_out_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me map out tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_mapping_out_tomorrow_morning_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help mapping out tomorrow morning.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what actually has to happen", reply.lower())

    def test_mapping_out_tomorrow_afternoon_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help mapping out tomorrow afternoon.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_help_with_my_agenda_for_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my agenda for tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what actually has to happen", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_help_setting_my_agenda_for_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help setting my agenda for tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what can slip", reply.lower())

    def test_set_my_agenda_for_tomorrow_prompt_gets_concrete_tomorrow_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me set my agenda for tomorrow.", packet)
        self.assertIn("for tomorrow", reply.lower())
        self.assertIn("what is fixed", reply.lower())

    def test_scheduling_around_two_meetings_prompt_gets_constraints_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help scheduling around two meetings.", packet)
        self.assertIn("what is fixed", reply.lower())
        self.assertIn("what actually has to happen", reply.lower())
        self.assertIn("what can move around those constraints", reply.lower())

    def test_scheduling_around_constraints_prompt_gets_constraints_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help scheduling around constraints.", packet)
        self.assertIn("what is fixed", reply.lower())
        self.assertIn("what actually has to happen", reply.lower())
        self.assertIn("what can move around those constraints", reply.lower())

    def test_scheduling_around_my_constraints_prompt_gets_constraints_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help scheduling around my constraints.", packet)
        self.assertIn("what is fixed", reply.lower())
        self.assertIn("what actually has to happen", reply.lower())
        self.assertIn("what can move around those constraints", reply.lower())

    def test_planning_around_constraints_prompt_gets_constraints_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help planning around constraints.", packet)
        self.assertIn("what is fixed", reply.lower())
        self.assertIn("what actually has to happen", reply.lower())
        self.assertIn("what can move around those constraints", reply.lower())

    def test_prep_for_meeting_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to prep for a meeting.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("outcome you need", reply.lower())
        self.assertIn("agenda you need to walk in with", reply.lower())

    def test_big_meeting_tomorrow_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I have a big meeting tomorrow.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("how you need to say it", reply.lower())

    def test_get_ready_for_meeting_with_boss_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to get ready for this meeting with my boss.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("agenda you need to walk in with", reply.lower())

    def test_think_through_this_meeting_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me think through this meeting.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("outcome you need", reply.lower())

    def test_meeting_agenda_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this meeting agenda.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("agenda you need to walk in with", reply.lower())

    def test_help_with_this_meeting_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this meeting.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("how you need to say it", reply.lower())

    def test_help_with_my_one_on_one_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my one-on-one.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("outcome you need", reply.lower())

    def test_getting_ready_for_my_one_on_one_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help getting ready for my one-on-one.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("agenda you need to walk in with", reply.lower())

    def test_preparing_for_my_one_on_one_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help preparing for my one-on-one.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("outcome you need", reply.lower())

    def test_help_with_my_one_on_one_numeric_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my 1:1.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("how you need to say it", reply.lower())

    def test_help_with_this_check_in_prompt_gets_concrete_meeting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this check-in.", packet)
        self.assertIn("real work for this meeting", reply.lower())
        self.assertIn("agenda you need to walk in with", reply.lower())

    def test_unmatched_practical_conversation_request_gets_concrete_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me think through a hard conversation with my brother", packet)
        self.assertIn("let's make it concrete", reply.lower())
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_talk_to_brother_prompt_gets_concrete_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to talk to my brother.", packet)
        self.assertIn("let's make it concrete", reply.lower())
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_have_conversation_with_sister_prompt_gets_concrete_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to have a conversation with my sister.", packet)
        self.assertIn("let's make it concrete", reply.lower())
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_hard_conversation_prompt_gets_concrete_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to have a hard conversation.", packet)
        self.assertIn("let's make it concrete", reply.lower())
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_sit_down_with_brother_prompt_gets_concrete_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to sit down with my brother.", packet)
        self.assertIn("let's make it concrete", reply.lower())
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_say_something_to_dad_prompt_gets_concrete_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to say something to my dad.", packet)
        self.assertIn("let's make it concrete", reply.lower())
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_clear_the_air_with_boss_prompt_gets_concrete_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to clear the air with my boss.", packet)
        self.assertIn("let's make it concrete", reply.lower())
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_should_clear_the_air_with_her_prompt_gets_concrete_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I should clear the air with her.", packet)
        self.assertIn("let's make it concrete", reply.lower())
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_collection_of_essays_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my collection of essays.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_essay_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this essay.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_essays_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my essays.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_essay_collection_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this essay collection.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_textbook_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this textbook.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_callback_draft_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this callback draft.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_smalltalk_scene_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this smalltalk scene.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_boundary_notes_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my boundary notes.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_conflict_essay_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my conflict essay.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_boundary_with_mom_prompt_still_gets_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help setting a boundary with my mom.", packet)
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_call_sheet_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my call sheet.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_call_notes_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my call notes.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_call_log_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this call log.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_call_my_mom_prompt_gets_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to call my mom.", packet)
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_call_my_brother_prompt_gets_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to call my brother.", packet)
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_should_call_my_dad_prompt_gets_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I should call my dad.", packet)
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_call_her_prompt_gets_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to call her.", packet)
        self.assertIn("what you need to say", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

    def test_text_prompt_does_not_get_conversation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to text my brother.", packet)
        self.assertNotIn("whether to have the conversation", reply.lower())

    def test_unmatched_practical_week_planning_request_gets_concrete_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to get my week under control", packet)
        self.assertIn("you do not need a better plan yet", reply.lower())
        self.assertIn("one cut", reply.lower())
        self.assertIn("immovable", reply.lower())
        self.assertNotIn("the model path is down right now", reply.lower())

    def test_overloaded_week_prompt_gets_decisive_capacity_pushback_in_fallback(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I'm overwhelmed and behind this week", packet)
        self.assertIn("you do not need a better plan yet", reply.lower())
        self.assertIn("one cut", reply.lower())
        self.assertIn("what is actually immovable", reply.lower())
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

    def test_writing_email_to_boss_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help writing an email to my boss.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_drafting_email_to_boss_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help drafting an email to my boss.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_writing_follow_up_email_after_meeting_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help writing a follow-up email after this meeting.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_send_follow_up_email_after_meeting_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to send a follow-up email after this meeting.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_send_message_to_brother_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to send a message to my brother.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_should_probably_send_him_a_message_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I should probably send him a message.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_text_my_brother_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to text my brother.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_should_probably_text_him_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I should probably text him.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_message_my_brother_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to message my brother.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_write_him_back_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to write him back.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_email_my_boss_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to email my boss.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_send_note_to_brother_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I should send a note to my brother.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_write_her_a_message_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to write her a message.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_send_my_boss_a_note_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to send my boss a note.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_respond_to_her_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to respond to her.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_send_a_reply_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to send a reply.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_write_a_response_prompt_gets_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to write a response.", packet)
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertIn("actual draft", reply.lower())

    def test_write_this_down_prompt_does_not_get_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to write this down.", packet)
        self.assertNotIn("blunt, warm, or diplomatic", reply.lower())

    def test_write_this_in_my_notes_prompt_does_not_get_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to write this in my notes.", packet)
        self.assertNotIn("blunt, warm, or diplomatic", reply.lower())

    def test_write_this_into_the_doc_prompt_does_not_get_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to write this into the doc.", packet)
        self.assertNotIn("blunt, warm, or diplomatic", reply.lower())

    def test_talk_to_brother_prompt_does_not_get_drafting_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to talk to my brother.", packet)
        self.assertNotIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("whether to have the conversation", reply.lower())

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

    def test_drafting_follow_up_warmer_alias_stays_inside_drafting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("a little warmer", packet)
        self.assertIn("keep it warm", reply.lower())
        self.assertIn("who it's to", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_drafting_follow_up_write_it_alias_stays_inside_drafting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to answer this email\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("just write it", packet)
        self.assertIn("who it's to", reply.lower())
        self.assertIn("what happened", reply.lower())
        self.assertIn("write the first pass", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_drafting_follow_up_formal_alias_stays_inside_drafting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to answer this email\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("formal", packet)
        self.assertIn("keep it diplomatic", reply.lower())
        self.assertIn("who it's to", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_drafting_follow_up_audience_only_stays_inside_drafting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("for my boss", packet)
        self.assertIn("if that's the audience", reply.lower())
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("actual draft", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_drafting_follow_up_length_only_stays_inside_drafting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("short", packet)
        self.assertIn("keep it short", reply.lower())
        self.assertIn("who it's to", reply.lower())
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_drafting_follow_up_text_alias_stays_inside_drafting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("just text him", packet)
        self.assertIn("if it's a text", reply.lower())
        self.assertIn("blunt, warm, or diplomatic", reply.lower())
        self.assertIn("i'll write it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_drafting_follow_up_both_stays_inside_drafting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("both", packet)
        self.assertIn("fast path", reply.lower())
        self.assertIn("angle first or the actual draft", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_drafting_follow_up_maybe_the_angle_stays_inside_drafting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("maybe the angle", packet)
        self.assertIn("what happened", reply.lower())
        self.assertIn("outcome you want", reply.lower())
        self.assertIn("angle first", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_drafting_follow_up_send_it_alias_stays_inside_drafting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to answer this email\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("just send it", packet)
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

    def test_quit_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I think I should quit.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_leave_my_job_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I think I should leave my job.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_resign_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I think I should resign.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_should_probably_resign_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I should probably resign.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_quit_my_job_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to quit my job.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_put_in_my_notice_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I think I need to put in my notice.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_hand_in_my_notice_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I think I need to hand in my notice.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_walk_away_from_this_job_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I might need to walk away from this job.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_leave_this_company_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I may need to leave this company.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_job_decision_memo_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this job decision memo.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_decision_memo_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this decision memo.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_decision_outline_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this decision outline.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_decision_review_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this decision review.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_decision_summary_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this decision summary.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_decision_recap_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this decision recap.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_decision_overview_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this decision overview.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_decision_chapter_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this decision chapter.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_decision_log_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this decision log.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_decision_notes_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this decision notes.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_deciding_between_two_jobs_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help deciding between two jobs.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_help_choosing_prompt_gets_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help choosing.", packet)
        self.assertIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, energy, risk", reply.lower())
        self.assertIn("regret not taking", reply.lower())

    def test_burned_out_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I am burned out at work.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())

    def test_retire_prompt_does_not_get_decision_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to retire.", packet)
        self.assertNotIn("let's make the decision concrete", reply.lower())
        self.assertIn("money, time, or identity first", reply.lower())

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

    def test_decision_follow_up_pay_alias_stays_inside_money_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Should I take the new job?\n"
                "Jarvis: Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
            ),
        }
        reply = generate_companion_fallback("pay", packet)
        self.assertIn("pay now", reply.lower())
        self.assertIn("long-term upside", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_decision_follow_up_stability_alias_stays_inside_regret_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I'm torn between staying and leaving.\n"
                "Jarvis: Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
            ),
        }
        reply = generate_companion_fallback("stability", packet)
        self.assertIn("losing stability", reply.lower())
        self.assertIn("not taking the shot", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_decision_follow_up_burnout_alias_stays_inside_energy_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Should I take the new job?\n"
                "Jarvis: Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
            ),
        }
        reply = generate_companion_fallback("burnout", packet)
        self.assertIn("burnout", reply.lower())
        self.assertIn("pace", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_decision_follow_up_reputation_alias_stays_inside_risk_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I'm torn between staying and leaving.\n"
                "Jarvis: Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
            ),
        }
        reply = generate_companion_fallback("reputation", packet)
        self.assertIn("money", reply.lower())
        self.assertIn("reputation", reply.lower())
        self.assertIn("stuck", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_decision_follow_up_both_stays_inside_decision_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Should I take the new job?\n"
                "Jarvis: Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
            ),
        }
        reply = generate_companion_fallback("both", packet)
        self.assertIn("if it's mixed", reply.lower())
        self.assertIn("money, energy, risk, or regret", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_decision_follow_up_either_stays_inside_decision_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I'm torn between staying and leaving.\n"
                "Jarvis: Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?"
            ),
        }
        reply = generate_companion_fallback("either", packet)
        self.assertIn("if it's mixed", reply.lower())
        self.assertIn("money, energy, risk, or regret", reply.lower())
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

    def test_retirement_follow_up_time_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("probably time", packet)
        self.assertIn("buy back your days", reply.lower())
        self.assertIn("without work driving it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_money_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("the money part", packet)
        self.assertIn("the number", reply.lower())
        self.assertIn("the runway", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_identity_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("identity mostly", packet)
        self.assertIn("without the work pace", reply.lower())
        self.assertIn("what replaces the pressure", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_all_three_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("all three", packet)
        self.assertIn("if all three matter", reply.lower())
        self.assertIn("money, time, or identity", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_softened_mixed_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("probably all three", packet)
        self.assertIn("if all three matter", reply.lower())
        self.assertIn("money, time, or identity", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_softened_time_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("i think time", packet)
        self.assertIn("buy back your days", reply.lower())
        self.assertIn("without work driving it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_softened_identity_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("the identity stuff", packet)
        self.assertIn("without the work pace", reply.lower())
        self.assertIn("what replaces the pressure", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_money_detail_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("numbers", packet)
        self.assertIn("the number", reply.lower())
        self.assertIn("the runway", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_time_detail_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("buy back my days", packet)
        self.assertIn("buy back your days", reply.lower())
        self.assertIn("without work driving it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_identity_detail_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("who i am", packet)
        self.assertIn("without the work pace", reply.lower())
        self.assertIn("what replaces the pressure", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_retirement_follow_up_mixed_detail_alias_stays_inside_retirement_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I want to retire.\n"
                "Jarvis: For you, I don't think retirement means doing nothing. "
                "I think it means getting work out of the driver's seat. "
                "Do you want to think about money, time, or identity first?"
            ),
        }
        reply = generate_companion_fallback("kind of all three", packet)
        self.assertIn("if all three matter", reply.lower())
        self.assertIn("money, time, or identity", reply.lower())
        self.assertNotIn("short version", reply.lower())

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

    def test_conversation_follow_up_wording_alias_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("wording", packet)
        self.assertIn("point you need to land", reply.lower())
        self.assertIn("cannot afford to say badly", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_tone_alias_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("tone", packet)
        self.assertIn("blunt, calm, or careful", reply.lower())
        self.assertIn("tension", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_whether_alias_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("should i even have it", packet)
        self.assertIn("opening line", reply.lower())
        self.assertIn("worth having", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_hedged_wording_alias_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("what do i even say", packet)
        self.assertIn("point you need to land", reply.lower())
        self.assertIn("cannot afford to say badly", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_article_tone_alias_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("the tone", packet)
        self.assertIn("blunt, calm, or careful", reply.lower())
        self.assertIn("tension", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_hedged_whether_alias_gets_concrete_continuation(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("should i do it at all", packet)
        self.assertIn("opening line", reply.lower())
        self.assertIn("worth having", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_mixed_alias_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("both", packet)
        self.assertIn("if it's mixed", reply.lower())
        self.assertIn("what to say, how to say it, or whether to have the conversation", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_probably_how_to_say_it_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("probably how to say it", packet)
        self.assertIn("blunt, calm, or careful", reply.lower())
        self.assertIn("tension", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_probably_whether_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("probably whether", packet)
        self.assertIn("opening line", reply.lower())
        self.assertIn("worth having", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_all_of_it_phrase_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("the hard part is all of it", packet)
        self.assertIn("if it's mixed", reply.lower())
        self.assertIn("what to say, how to say it, or whether to have the conversation", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_probably_both_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("probably both", packet)
        self.assertIn("if it's mixed", reply.lower())
        self.assertIn("what to say, how to say it, or whether to have the conversation", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_probably_the_wording_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("probably the wording", packet)
        self.assertIn("point you need to land", reply.lower())
        self.assertIn("cannot afford to say badly", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_probably_the_tone_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("probably the tone", packet)
        self.assertIn("blunt, calm, or careful", reply.lower())
        self.assertIn("tension", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_conversation_follow_up_if_i_even_need_to_have_it_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through a hard conversation with my brother\n"
                "Jarvis: Let's make it concrete. Is the hard part what to say, "
                "how to say it, or whether to have the conversation at all?"
            ),
        }
        reply = generate_companion_fallback("if i even need to have it", packet)
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

    def test_capacity_follow_up_calendar_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to get my week under control\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("calendar", packet)
        self.assertIn("truly fixed", reply.lower())
        self.assertIn("treating as fixed", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_fuzzy_priorities_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I'm overwhelmed and behind this week\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("fuzzy priorities", packet)
        self.assertIn("actually matter", reply.lower())
        self.assertIn("loud but not important", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_conversation_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to get my week under control\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("conversation", packet)
        self.assertIn("clogging the week", reply.lower())
        self.assertIn("opening line", reply.lower())
        self.assertIn("whether to have it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_schedule_alias_stays_inside_calendar_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to get my week under control\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("schedule", packet)
        self.assertIn("truly fixed", reply.lower())
        self.assertIn("cutting it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_cut_alias_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I'm overwhelmed and behind this week\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("what can slip", packet)
        self.assertIn("actually has to happen", reply.lower())
        self.assertIn("pretending is fixed", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_conversation_alias_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to get my week under control\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("that conversation", packet)
        self.assertIn("clogging the week", reply.lower())
        self.assertIn("whether to have it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_probably_calendar_alias_stays_inside_calendar_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to get my week under control\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("probably the calendar", packet)
        self.assertIn("truly fixed", reply.lower())
        self.assertIn("treating as fixed", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_schedule_stuff_alias_stays_inside_calendar_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to get my week under control\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("the schedule stuff", packet)
        self.assertIn("truly fixed", reply.lower())
        self.assertIn("treating as fixed", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_maybe_priorities_alias_stays_inside_priorities_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I'm overwhelmed and behind this week\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("maybe priorities", packet)
        self.assertIn("actually matter", reply.lower())
        self.assertIn("loud but not important", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_probably_conversation_alias_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: I need to get my week under control\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("probably the conversation", packet)
        self.assertIn("clogging the week", reply.lower())
        self.assertIn("whether to have it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_all_of_it_alias_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("all of it", packet)
        self.assertIn("what's actually driving the overload first", reply.lower())
        self.assertIn("calendar, fuzzy priorities", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_i_do_not_know_alias_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("i do not know", packet)
        self.assertIn("what's actually driving the overload first", reply.lower())
        self.assertIn("calendar, fuzzy priorities", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_maybe_calendar_alias_stays_inside_calendar_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("maybe the calendar", packet)
        self.assertIn("truly fixed", reply.lower())
        self.assertIn("treating as fixed", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_priorities_stuff_alias_stays_inside_priorities_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("the priorities stuff", packet)
        self.assertIn("actually matter", reply.lower())
        self.assertIn("loud but not important", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_avoiding_stuff_alias_stays_inside_avoiding_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("the avoiding stuff", packet)
        self.assertIn("avoiding because it is hard", reply.lower())
        self.assertIn("should not be on your plate", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_maybe_conversation_alias_stays_inside_conversation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("maybe the conversation", packet)
        self.assertIn("clogging the week", reply.lower())
        self.assertIn("whether to have it", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_kind_of_all_of_it_alias_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("kind of all of it", packet)
        self.assertIn("what's actually driving the overload first", reply.lower())
        self.assertIn("calendar, fuzzy priorities", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_probably_everything_alias_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("probably everything", packet)
        self.assertIn("what's actually driving the overload first", reply.lower())
        self.assertIn("calendar, fuzzy priorities", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_both_alias_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("both", packet)
        self.assertIn("if it's mixed", reply.lower())
        self.assertIn("calendar, fuzzy priorities", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_all_of_those_alias_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("all of those", packet)
        self.assertIn("if it's mixed", reply.lower())
        self.assertIn("calendar, fuzzy priorities", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_calendar_and_priorities_alias_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("calendar and priorities", packet)
        self.assertIn("if it's mixed", reply.lower())
        self.assertIn("calendar, fuzzy priorities", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_capacity_follow_up_mixed_alias_stays_inside_cutting_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: My week is a mess\n"
                "Jarvis: You do not need a better plan yet. You need one cut. What is actually immovable this week?"
            ),
        }
        reply = generate_companion_fallback("mixed", packet)
        self.assertIn("if it's mixed", reply.lower())
        self.assertIn("calendar, fuzzy priorities", reply.lower())
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
        self.assertIn("where to go", repaired.lower())

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

    def test_help_with_my_book_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my book.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_write_my_book_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to write my book.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_outline_my_book_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help outlining my book.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_stuck_on_my_book_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I'm stuck on my book.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_revise_my_book_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to revise my book.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_book_chapter_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me with this book chapter.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_help_with_my_memoir_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my memoir.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_help_with_my_manuscript_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my manuscript.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_help_with_my_novel_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my novel.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_help_with_my_nonfiction_book_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my nonfiction book.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_memoir_chapter_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me with this memoir chapter.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_help_with_my_autobiography_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my autobiography.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_autobiography_chapter_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me with this autobiography chapter.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_revise_my_autobiography_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to revise my autobiography.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_help_with_my_biography_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my biography.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_biography_chapter_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("Help me with this biography chapter.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_revise_my_biography_prompt_gets_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to revise my biography.", packet)
        self.assertIn("What's the book", reply)
        self.assertIn("outlining, writing, revising, or getting unstuck", reply)

    def test_article_prompt_does_not_get_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help writing this article.", packet)
        self.assertNotIn("What's the book", reply)

    def test_newsletter_prompt_does_not_get_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this newsletter.", packet)
        self.assertNotIn("What's the book", reply)

    def test_short_story_prompt_does_not_get_book_work_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my short story.", packet)
        self.assertNotIn("What's the book", reply)

    def test_vague_reflective_question_is_repaired(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "Help me think through vacation.",
            "How does that feel for you?",
            packet,
        )
        self.assertNotEqual(repaired, "How does that feel for you?")
        self.assertIn("where to go", repaired.lower())

    def test_success_question_is_repaired_for_practical_request(self) -> None:
        packet = {"available_capabilities": ["planning and drafting in chat"]}
        repaired = harden_companion_reply(
            "I want to retire.",
            "What would success look like here?",
            packet,
        )
        self.assertNotEqual(repaired, "What would success look like here?")
        self.assertIn("money, time, or identity first", repaired)

    def test_step_back_from_work_prompt_gets_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I might step back from work.", packet)
        self.assertIn("getting work out of the driver's seat", reply)
        self.assertIn("money, time, or identity first", reply)

    def test_slow_down_at_work_for_good_prompt_gets_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to slow down at work for good.", packet)
        self.assertIn("getting work out of the driver's seat", reply)
        self.assertIn("money, time, or identity first", reply)

    def test_step_away_from_work_for_good_prompt_gets_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I think I am ready to step away from work for good.", packet)
        self.assertIn("getting work out of the driver's seat", reply)
        self.assertIn("money, time, or identity first", reply)

    def test_ease_out_of_work_prompt_gets_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to ease out of work.", packet)
        self.assertIn("getting work out of the driver's seat", reply)
        self.assertIn("money, time, or identity first", reply)

    def test_wind_down_my_career_prompt_gets_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to wind down my career for good.", packet)
        self.assertIn("getting work out of the driver's seat", reply)
        self.assertIn("money, time, or identity first", reply)

    def test_be_done_working_soon_prompt_gets_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to be done working soon.", packet)
        self.assertIn("getting work out of the driver's seat", reply)
        self.assertIn("money, time, or identity first", reply)

    def test_work_less_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to work less.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_burned_out_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I am burned out at work.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_end_my_career_soon_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to end my career soon.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_retirement_essay_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this retirement essay.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_retirement_memo_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this retirement memo.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_retirement_chapter_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this retirement chapter.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_retirement_review_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this retirement review.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_retirement_overview_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this retirement overview.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_retirement_outline_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this retirement outline.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_retirement_recap_prompt_does_not_get_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this retirement recap.", packet)
        self.assertNotIn("money, time, or identity first", reply)

    def test_planning_retirement_prompt_gets_retirement_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help planning retirement.", packet)
        self.assertIn("getting work out of the driver's seat", reply)
        self.assertIn("money, time, or identity first", reply)

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
        self.assertIn("one cut", repaired.lower())
        self.assertIn("immovable", repaired.lower())

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

    def test_retirement_taxonomy_opener_is_rewritten_into_thesis_first_reply(self) -> None:
        packet = build_context_packet(
            _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Ready.")),
            self.actor,
            "office",
            "I am thinking of retiring early through passive income growth. I am writing books, building training. Thoughts?",
            plan=_plan("I am thinking of retiring early through passive income growth. I am writing books, building training. Thoughts?"),
            conversation_excerpt="",
        )
        repaired = harden_companion_reply(
            "I am thinking of retiring early through passive income growth. I am writing books, building training. Thoughts?",
            "Is the real work whether books, training, or passive income matters most here?",
            packet,
        )
        self.assertNotIn("Is the real work", repaired)
        self.assertIn("employment out of the driver's seat", repaired)
        self.assertIn("authority engine", repaired)

    def test_health_taxonomy_opener_is_rewritten_into_thesis_first_reply(self) -> None:
        packet = build_context_packet(
            _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Ready.")),
            self.actor,
            "office",
            "I want to be healthy for the future. I weigh 230lbs. I have metabolic syndrome. I respond well to exercise. What should I do to live a better life?",
            plan=_plan("I want to be healthy for the future. I weigh 230lbs. I have metabolic syndrome. I respond well to exercise. What should I do to live a better life?"),
            conversation_excerpt="",
        )
        repaired = harden_companion_reply(
            "I want to be healthy for the future. I weigh 230lbs. I have metabolic syndrome. I respond well to exercise. What should I do to live a better life?",
            "What part feels off most right now: food, exercise, or motivation?",
            packet,
        )
        self.assertNotIn("What part feels off", repaired)
        self.assertIn("230", repaired)
        self.assertIn("30 years", repaired)
        self.assertIn("exercise works for you", repaired)

    def test_trip_day_taxonomy_opener_is_rewritten_into_thesis_first_reply(self) -> None:
        packet = build_context_packet(
            _StubRuntime(OpenAIResult(provider="openai", model="gpt", output_text="Ready.")),
            self.actor,
            "office",
            "I am going to the Statue of Liberty tomorrow.",
            plan=_plan("I am going to the Statue of Liberty tomorrow."),
            conversation_excerpt="",
        )
        repaired = harden_companion_reply(
            "I am going to the Statue of Liberty tomorrow.",
            "Is this mostly timing, tickets, ferry logistics, or the rest of tomorrow?",
            packet,
        )
        self.assertNotIn("Is this mostly", repaired)
        self.assertIn("trip day", repaired)
        self.assertIn("timing", repaired)
        self.assertIn("walking or stairs", repaired)

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

    def test_standalone_vacation_prompt_gets_concrete_fork(self) -> None:
        packet = {
            "available_capabilities": ["planning and drafting in chat"],
            "conversation_excerpt": (
                "Chris: Help me draft a text to my brother\n"
                "Jarvis: Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?"
            ),
        }
        reply = generate_companion_fallback("Help me think through vacation.", packet)
        self.assertIn("where to go", reply.lower())
        self.assertIn("what kind of trip this needs to be", reply.lower())
        self.assertIn("what is making it hard to land", reply.lower())

    def test_trip_planning_prompt_gets_concrete_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to plan a trip.", packet)
        self.assertIn("where to go", reply.lower())
        self.assertIn("what kind of trip this needs to be", reply.lower())
        self.assertIn("what is making it hard to land", reply.lower())

    def test_uncertain_vacation_prompt_gets_concrete_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need a vacation but I do not know what I need.", packet)
        self.assertIn("where to go", reply.lower())
        self.assertIn("what kind of trip this needs to be", reply.lower())
        self.assertIn("what is making it hard to land", reply.lower())

    def test_get_away_prompt_gets_concrete_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I want to get away for a few days.", packet)
        self.assertIn("where to go", reply.lower())
        self.assertIn("what kind of trip this needs to be", reply.lower())
        self.assertIn("what is making it hard to land", reply.lower())

    def test_go_away_prompt_gets_concrete_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to go away for a bit.", packet)
        self.assertIn("where to go", reply.lower())
        self.assertIn("what kind of trip this needs to be", reply.lower())
        self.assertIn("what is making it hard to land", reply.lower())

    def test_get_out_of_town_prompt_gets_concrete_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need to get out of town.", packet)
        self.assertIn("where to go", reply.lower())
        self.assertIn("what kind of trip this needs to be", reply.lower())
        self.assertIn("what is making it hard to land", reply.lower())

    def test_travel_essay_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this travel essay.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_travel_chapter_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this travel chapter.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_travel_memo_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this travel memo.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_trip_report_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this trip report.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_vacation_note_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this vacation note.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_hotel_review_prompt_does_not_get_logistics_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this hotel review.", packet)
        self.assertNotIn("destination, dates, and who's coming", reply.lower())

    def test_vacation_review_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with my vacation review.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_trip_outline_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this trip outline.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_travel_summary_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this travel summary.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_vacation_recap_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this vacation recap.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_travel_overview_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this travel overview.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_trip_overview_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this trip overview.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_vacation_overview_prompt_does_not_get_vacation_fork(self) -> None:
        packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
        reply = generate_companion_fallback("I need help with this vacation overview.", packet)
        self.assertNotIn("where to go", reply.lower())
        self.assertNotIn("what kind of trip this needs to be", reply.lower())

    def test_vacation_follow_up_where_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("where are we going", packet)
        self.assertIn("stuck on the place itself", reply.lower())
        self.assertIn("narrowing the options", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_hard_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("what is making it hard", packet)
        self.assertIn("money, timing, people", reply.lower())
        self.assertIn("worth the effort", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_destination_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("the destination", packet)
        self.assertIn("stuck on the place itself", reply.lower())
        self.assertIn("narrowing the options", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_point_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("maybe the point of it", packet)
        self.assertIn("feel like rest", reply.lower())
        self.assertIn("time together", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_mixed_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("honestly all three", packet)
        self.assertIn("if it's all tangled together", reply.lower())
        self.assertIn("where to go, what this trip needs to do for you", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_i_do_not_know_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("i do not know", packet)
        self.assertIn("if it's all tangled together", reply.lower())
        self.assertIn("where to go, what this trip needs to do for you", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_maybe_where_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("maybe where", packet)
        self.assertIn("stuck on the place itself", reply.lower())
        self.assertIn("narrowing the options", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_place_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("the place", packet)
        self.assertIn("stuck on the place itself", reply.lower())
        self.assertIn("narrowing the options", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_probably_the_point_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("probably the point", packet)
        self.assertIn("feel like rest", reply.lower())
        self.assertIn("time together", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_what_trip_needs_to_be_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("what the trip needs to be", packet)
        self.assertIn("feel like rest", reply.lower())
        self.assertIn("time together", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_hard_part_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("the hard part", packet)
        self.assertIn("money, timing, people", reply.lower())
        self.assertIn("worth the effort", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_all_of_it_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("all of it", packet)
        self.assertIn("if it's all tangled together", reply.lower())
        self.assertIn("where to go, what this trip needs to do for you", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_both_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("both", packet)
        self.assertIn("if it's all tangled together", reply.lower())
        self.assertIn("where to go, what this trip needs to do for you", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_all_three_honestly_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("all three honestly", packet)
        self.assertIn("if it's all tangled together", reply.lower())
        self.assertIn("where to go, what this trip needs to do for you", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_destination_and_point_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("the destination and the point", packet)
        self.assertIn("if it's all tangled together", reply.lower())
        self.assertIn("where to go, what this trip needs to do for you", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_trip_purpose_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("trip purpose", packet)
        self.assertIn("feel like rest", reply.lower())
        self.assertIn("time together", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_what_kind_of_trip_is_this_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("what kind of trip is this", packet)
        self.assertIn("feel like rest", reply.lower())
        self.assertIn("time together", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_blocker_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("the blocker", packet)
        self.assertIn("money, timing, people", reply.lower())
        self.assertIn("worth the effort", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_point_and_hard_part_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("the point and the hard part", packet)
        self.assertIn("if it's all tangled together", reply.lower())
        self.assertIn("where to go, what this trip needs to do for you", reply.lower())
        self.assertNotIn("short version", reply.lower())

    def test_vacation_follow_up_place_or_hard_part_alias_stays_inside_vacation_thread(self) -> None:
        packet = {
            "available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"],
            "conversation_excerpt": (
                "Chris: Help me think through vacation.\n"
                "Jarvis: Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?"
            ),
        }
        reply = generate_companion_fallback("the place or the hard part", packet)
        self.assertIn("if it's all tangled together", reply.lower())
        self.assertIn("where to go, what this trip needs to do for you", reply.lower())
        self.assertNotIn("short version", reply.lower())

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

    def test_capability_reply_does_not_imply_search_without_search_capability(self) -> None:
        packet = {
            "available_capabilities": [
                "planning and drafting in chat",
                "live Obsidian retrieval not active in the default conversation path",
            ]
        }
        reply = generate_companion_fallback("What can you actually do right now?", packet)
        self.assertNotIn("I searched", reply)
        self.assertNotIn("current web info", reply)

    def test_capability_reply_describes_web_search_truthfully(self) -> None:
        packet = {
            "available_capabilities": [
                "planning and drafting in chat",
                "web search for current info when that path is explicitly triggered and results actually come back",
                "live Obsidian retrieval not active in the default conversation path",
            ]
        }
        reply = generate_companion_fallback("What can you actually do right now?", packet)
        self.assertIn("current web info", reply)
        self.assertIn("when the request actually needs it", reply)
        self.assertIn("whether I really searched", reply)
        self.assertNotIn("I always search", reply)

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

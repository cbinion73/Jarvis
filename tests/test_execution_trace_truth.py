from __future__ import annotations

import unittest

from jarvis.openai_tasks import JarvisOpenAIClient, OpenAIResult
from jarvis.runtime import _build_action_truth_summary


class ExecutionTraceTruthTests(unittest.TestCase):
    def test_browser_search_trace_is_visible_and_compact(self) -> None:
        client = JarvisOpenAIClient(object())
        result = OpenAIResult(
            provider="openai",
            model="gpt-test",
            output_text="Here is the answer.",
            execution_trace=[
                {
                    "type": "search",
                    "status": "completed",
                    "source": "live_browser_web_search",
                    "result_count": client._count_browser_search_results(
                        "**Result A**\nhttps://example.com/a\nA.\n\n**Result B**\nhttps://example.com/b\nB."
                    ),
                    "detail": "2 web result summaries returned in this turn.",
                }
            ],
        )

        summary = _build_action_truth_summary(result=result)

        trace = list(summary.get("execution_trace") or [])
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0].get("type"), "search")
        self.assertEqual(trace[0].get("status"), "completed")
        self.assertEqual(trace[0].get("result_count"), 2)
        self.assertFalse(bool(summary.get("reasoning_only")))

    def test_creation_and_open_traces_are_visible(self) -> None:
        result = OpenAIResult(
            provider="conversation",
            model="test",
            output_text="Built it.",
            created_checklist={
                "object_kind": "checklist",
                "creation_proof": {
                    "persisted_locally": True,
                    "standalone_file_written": False,
                    "external_save_used": False,
                    "storage_mode": "persisted_local_object_record",
                },
            },
        )
        summary = _build_action_truth_summary(
            result=result,
            requested_packet="mission-control",
        )

        trace = list(summary.get("execution_trace") or [])
        self.assertEqual(trace[0].get("type"), "create")
        self.assertEqual(trace[0].get("target"), "checklist")
        self.assertEqual(trace[1].get("type"), "open")
        self.assertEqual(trace[1].get("status"), "requested_not_completed")

    def test_degraded_trace_is_visible(self) -> None:
        result = OpenAIResult(
            provider="fallback",
            model="fallback",
            output_text="Fallback reply.",
            execution_trace=[
                {
                    "type": "degraded",
                    "status": "unavailable",
                    "source": "manual_ai_fallback",
                    "detail": "OPENAI_API_KEY is missing.",
                }
            ],
        )

        summary = _build_action_truth_summary(result=result)

        trace = list(summary.get("execution_trace") or [])
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0].get("type"), "degraded")
        self.assertEqual(trace[0].get("status"), "unavailable")
        self.assertFalse(bool(summary.get("reasoning_only")))

    def test_reasoning_only_path_has_no_fake_trace_entries(self) -> None:
        result = OpenAIResult(
            provider="conversation",
            model="conversation",
            output_text="I can help you think it through from here.",
        )

        summary = _build_action_truth_summary(result=result)

        self.assertEqual(summary.get("execution_trace"), [])
        self.assertTrue(bool(summary.get("reasoning_only")))


if __name__ == "__main__":
    unittest.main()

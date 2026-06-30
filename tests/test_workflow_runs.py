from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from jarvis.graphs import run_response_graph
from jarvis.models import ActionClass, PrivacyLevel, RequestPlan, RiskLevel, RoutingTier, TaskClass
from jarvis.openai_tasks import OpenAIResult
from jarvis.runtime import JarvisRuntime
from jarvis.workflow_runs import WorkflowRunStore


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


class _RuntimeLike(SimpleNamespace):
    _workflow_plan_summary = JarvisRuntime._workflow_plan_summary
    _created_objects_from_result = JarvisRuntime._created_objects_from_result
    _workflow_run_already_recorded = JarvisRuntime._workflow_run_already_recorded
    _workflow_active_nodes_for_result = JarvisRuntime._workflow_active_nodes_for_result
    _active_nodes_for = JarvisRuntime._active_nodes_for
    record_workflow_run = JarvisRuntime.record_workflow_run
    _record_interactive_result_run = JarvisRuntime._record_interactive_result_run
    _record_artifact_creation_result = JarvisRuntime._record_artifact_creation_result


class WorkflowRunStoreTests(unittest.TestCase):
    def test_store_records_and_summarizes_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowRunStore(Path(tmp) / "data" / "workflow_runs")

            record = store.record_run(
                workflow_kind="response_graph",
                actor="Chris",
                room="office",
                request="Help me think through this.",
                status="completed",
                provider="openai",
                model="gpt-5.4-mini",
                graph_name="response_graph",
                runtime_surface="graph",
                active_nodes=["response_graph", "conversation"],
                nodes_planned=["load_context", "generate"],
                step_events=[{"node": "load_context", "status": "completed"}],
                execution_trace=[{"type": "search", "status": "completed"}],
                created_objects=[{"object_kind": "plan", "title": "Trip plan"}],
                plan_summary={"module": "conversation"},
                result_summary={"created_object_count": 1},
                output_text="Done.",
                metadata={"smoke": True},
            )

            fetched = store.get_run(record["run_id"])
            summary = store.summary()

            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["workflow_kind"], "response_graph")
            self.assertEqual(summary["total_runs"], 1)
            self.assertEqual(summary["counts_by_workflow"]["response_graph"], 1)

    def test_artifact_creation_helper_records_real_created_object_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowRunStore(Path(tmp) / "data" / "workflow_runs")
            runtime = _RuntimeLike(
                workflow_run_store=store,
                plan_request=lambda actor_name, room, request: _plan(request),
            )

            result = OpenAIResult(
                provider="plan-engine",
                model="plan-engine",
                output_text="Created a real plan.",
                created_plan={
                    "plan_id": "plan-1",
                    "object_kind": "plan",
                    "title": "Trip plan",
                },
            )

            recorded = runtime._record_artifact_creation_result("Chris", "office", "Make me a trip plan.", result)
            runs = store.list_runs()

            self.assertIs(recorded, result)
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["workflow_kind"], "artifact_creation")
            self.assertEqual(runs[0]["created_objects"][0]["object_kind"], "plan")
            self.assertEqual(runs[0]["created_objects"][0]["title"], "Trip plan")
            self.assertTrue(any(item.get("type") == "workflow_run" for item in result.execution_trace))

    def test_response_graph_records_replayable_workflow_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkflowRunStore(Path(tmp) / "data" / "workflow_runs")
            runtime = _RuntimeLike(
                workflow_run_store=store,
                openviking_support=SimpleNamespace(enabled=False),
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
                storm_weather_summary=lambda: {"available": False},
                family_calendar=SimpleNamespace(summary=lambda: {}),
            )
            result = OpenAIResult(
                provider="openai",
                model="gpt-5.4-mini",
                output_text="Here is the next step.",
                created_plan={
                    "plan_id": "plan-2",
                    "object_kind": "plan",
                    "title": "Tomorrow plan",
                },
            )

            with patch("jarvis.graphs.run_companion_turn", return_value=result), patch("jarvis.graphs._build_live_context", return_value=""):
                returned = run_response_graph(runtime, _plan("Help me plan tomorrow."))

            runs = store.list_runs()

            self.assertIs(returned, result)
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["workflow_kind"], "response_graph")
            self.assertEqual([item["node"] for item in runs[0]["step_events"]], ["load_context", "generate"])
            self.assertEqual(runs[0]["created_objects"][0]["object_kind"], "plan")
            self.assertTrue(any(item.get("type") == "workflow_run" for item in returned.execution_trace))


if __name__ == "__main__":
    unittest.main()

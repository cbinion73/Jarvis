from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.autonomy_state import AutonomyStateStore
from jarvis.runtime import JarvisRuntime


class _RuntimeLike(SimpleNamespace):
    _autonomy_truth_contract = JarvisRuntime._autonomy_truth_contract
    create_autonomy_state = JarvisRuntime.create_autonomy_state
    add_autonomy_action_plan = JarvisRuntime.add_autonomy_action_plan
    apply_autonomy_control_action = JarvisRuntime.apply_autonomy_control_action
    apply_autonomy_readiness_state = JarvisRuntime.apply_autonomy_readiness_state
    trigger_autonomy_local_follow_through = JarvisRuntime.trigger_autonomy_local_follow_through
    autonomy_state_snapshot = JarvisRuntime.autonomy_state_snapshot
    autonomy_state_queue_snapshot = JarvisRuntime.autonomy_state_queue_snapshot


class AutonomyStateTests(unittest.TestCase):
    def test_store_creates_and_lists_real_autonomy_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")

            created = store.create_state(
                actor="Chris",
                title="Retirement workshop watch",
                objective="Keep the retirement workshop lane visible for later supervised follow-through.",
                status="queued",
                current_focus="Waiting for explicit next evidence.",
                next_step="Recheck the workshop brief before any follow-through.",
                requested_scope="Hold the objective visible and staged for later review only.",
                initiation_reason="Chris wants the lane preserved without starting autonomous work.",
            )

            listed = store.list_states()

            self.assertEqual(created["status"], "queued")
            self.assertEqual(created["object_kind"], "autonomy_state")
            self.assertFalse(bool(created["autonomous_execution_recorded"]))
            self.assertEqual(created["approval_state"], "required")
            self.assertEqual(created["allowed_action_boundary"], "record_visibility_only")
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["autonomy_id"], created["autonomy_id"])
            self.assertTrue(store.index_path.exists())

    def test_runtime_records_approval_aware_proposed_action_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            created = runtime.create_autonomy_state(
                "Chris",
                title="Retirement workshop follow-through",
                objective="Keep a bounded autonomy record for later supervised planning.",
                requested_scope="Hold the lane visibly until approval is explicit.",
                initiation_reason="Chris wants inspectable autonomy planning without execution.",
            )
            planned = runtime.add_autonomy_action_plan(
                created["autonomy_state"]["autonomy_id"],
                planning_note="These are next possible moves only if Chris explicitly wants them reviewed.",
                proposed_actions=[
                    {
                        "title": "Draft three follow-up questions for the workshop decision.",
                        "rationale": "Clarify what approval would need before any real follow-through exists.",
                        "approval_needed": True,
                    }
                ],
            )
            snapshot = runtime.autonomy_state_snapshot(created["autonomy_state"]["autonomy_id"])

            self.assertIn("proposed only", planned["message"].lower())
            self.assertEqual(planned["autonomy_state"]["planned_action_count"], 1)
            self.assertTrue(bool(planned["autonomy_state"]["has_proposed_plan"]))
            self.assertEqual(
                snapshot["autonomy_state"]["proposed_actions"][0]["execution_status"],
                "proposed_not_run",
            )
            self.assertEqual(
                snapshot["autonomy_state"]["proposed_actions"][0]["approval_state"],
                "required",
            )

    def test_runtime_records_pause_resume_abort_as_recorded_control_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            created = runtime.create_autonomy_state(
                "Chris",
                title="Retirement workshop follow-through",
                objective="Keep a bounded autonomy record for later supervised review.",
                requested_scope="Hold the lane visibly until approval is explicit.",
                initiation_reason="Chris wants inspectable autonomy state without execution.",
            )
            paused = runtime.apply_autonomy_control_action(
                "Chris",
                created["autonomy_state"]["autonomy_id"],
                action="pause",
                control_reason="Hold the record while Chris reviews the current scope.",
            )
            resumed = runtime.apply_autonomy_control_action(
                "Chris",
                created["autonomy_state"]["autonomy_id"],
                action="resume",
                control_reason="Return the record to recorded active posture for later review.",
            )
            aborted = runtime.apply_autonomy_control_action(
                "Chris",
                created["autonomy_state"]["autonomy_id"],
                action="abort",
                control_reason="Chris no longer wants this recorded autonomy lane kept open.",
            )
            snapshot = runtime.autonomy_state_snapshot(created["autonomy_state"]["autonomy_id"])

            self.assertIn("recorded", paused["message"].lower())
            self.assertEqual(paused["autonomy_state"]["current_control_posture"], "paused")
            self.assertEqual(resumed["autonomy_state"]["current_control_posture"], "recorded_active")
            self.assertEqual(aborted["autonomy_state"]["current_control_posture"], "aborted")
            self.assertEqual(snapshot["autonomy_state"]["last_control_action"], "abort")
            self.assertEqual(len(snapshot["autonomy_state"]["control_history"]), 3)
            self.assertFalse(bool(snapshot["autonomy_state"]["autonomous_execution_recorded"]))

    def test_runtime_records_approval_gated_readiness_without_claiming_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            created = runtime.create_autonomy_state(
                "Chris",
                title="Retirement workshop readiness",
                objective="Keep a bounded autonomy record for later supervised follow-through.",
                requested_scope="Hold the lane visibly until approval is explicit.",
                initiation_reason="Chris wants inspectable readiness without execution.",
            )
            pending = runtime.apply_autonomy_readiness_state(
                "Chris",
                created["autonomy_state"]["autonomy_id"],
                readiness_state="ready_pending_approval",
                readiness_reason="The scope is defined, but explicit approval is still required.",
            )
            ready_runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )
            ready_runtime.create_autonomy_state = runtime.create_autonomy_state
            ready_runtime.add_autonomy_action_plan = runtime.add_autonomy_action_plan
            ready_runtime.apply_autonomy_control_action = runtime.apply_autonomy_control_action
            ready_runtime.apply_autonomy_readiness_state = runtime.apply_autonomy_readiness_state
            # Reuse the same record but flip approval at the storage layer through create-time approved case.
            approved_store = store
            snapshot_before = approved_store.get_state(created["autonomy_state"]["autonomy_id"])
            assert snapshot_before is not None
            payload = approved_store.load()
            payload["autonomy_states"][created["autonomy_state"]["autonomy_id"]]["approval_state"] = "approved"
            approved_store.save(payload)
            ready = runtime.apply_autonomy_readiness_state(
                "Chris",
                created["autonomy_state"]["autonomy_id"],
                readiness_state="ready_within_boundary",
                readiness_reason="Approval is now satisfied and the record is ready within the stored boundary.",
            )
            snapshot = runtime.autonomy_state_snapshot(created["autonomy_state"]["autonomy_id"])

            self.assertIn("stored approval-gated readiness posture only", pending["message"].lower())
            self.assertEqual(pending["autonomy_state"]["readiness_state"], "ready_pending_approval")
            self.assertEqual(pending["autonomy_state"]["approval_gate_status"], "approval_pending")
            self.assertEqual(ready["autonomy_state"]["readiness_state"], "ready_within_boundary")
            self.assertEqual(ready["autonomy_state"]["approval_gate_status"], "within_boundary")
            self.assertEqual(len(snapshot["autonomy_state"]["readiness_history"]), 2)
            self.assertFalse(bool(snapshot["autonomy_state"]["autonomous_execution_recorded"]))

    def test_runtime_triggers_one_local_follow_through_proof_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            created = runtime.create_autonomy_state(
                "Chris",
                title="Retirement workshop local proof",
                objective="Keep a bounded autonomy record for later supervised follow-through.",
                requested_scope="Hold the lane visibly until approval is explicit.",
                initiation_reason="Chris wants one local proof-of-follow-through only.",
                approval_state="approved",
            )
            runtime.apply_autonomy_readiness_state(
                "Chris",
                created["autonomy_state"]["autonomy_id"],
                readiness_state="ready_within_boundary",
                readiness_reason="Approval is already satisfied and this lane is ready within the stored boundary.",
            )
            result = runtime.trigger_autonomy_local_follow_through(
                "Chris",
                created["autonomy_state"]["autonomy_id"],
                trigger_note="Write the smallest inspectable proof packet only.",
            )
            snapshot = runtime.autonomy_state_snapshot(created["autonomy_state"]["autonomy_id"])
            artifact_path = Path(snapshot["autonomy_state"]["last_follow_through_artifact_path"])

            self.assertIn("one bounded local proof action only", result["message"].lower())
            self.assertEqual(snapshot["autonomy_state"]["local_follow_through_status"], "local_proof_created")
            self.assertEqual(snapshot["autonomy_state"]["last_follow_through_effect"], "local_status_packet_written")
            self.assertTrue(artifact_path.exists())
            content = artifact_path.read_text(encoding="utf-8")
            self.assertIn("Autonomy Local Follow-Through Proof", content)
            self.assertIn("No invisible or background execution started.", content)
            self.assertIn("No multi-agent or workforce orchestration occurred.", content)
            self.assertFalse(bool(snapshot["autonomy_state"]["autonomous_execution_recorded"]))

    def test_runtime_autonomy_responses_share_the_full_truth_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            created = runtime.create_autonomy_state(
                "Chris",
                title="Autonomy contract check",
                objective="Keep the full autonomy lane contract aligned across mutation responses.",
                requested_scope="Visibility only until explicit review says otherwise.",
                initiation_reason="Close out the lane with one shared inspectable contract.",
                approval_state="approved",
            )
            autonomy_id = created["autonomy_state"]["autonomy_id"]
            planned = runtime.add_autonomy_action_plan(
                autonomy_id,
                planning_note="Record one proposed action without running it.",
                proposed_actions=[
                    {
                        "title": "Review the stored autonomy contract.",
                        "rationale": "Closeout should show the same allowed state families everywhere.",
                        "approval_needed": False,
                    }
                ],
            )
            controlled = runtime.apply_autonomy_control_action(
                "Chris",
                autonomy_id,
                action="pause",
                control_reason="Check the recorded control contract before resuming.",
            )
            runtime.apply_autonomy_control_action(
                "Chris",
                autonomy_id,
                action="resume",
                control_reason="Return to recorded active posture for readiness and follow-through checks.",
            )
            ready = runtime.apply_autonomy_readiness_state(
                "Chris",
                autonomy_id,
                readiness_state="ready_within_boundary",
                readiness_reason="Approval is satisfied and the record stays within its stored boundary.",
            )
            followed_through = runtime.trigger_autonomy_local_follow_through(
                "Chris",
                autonomy_id,
                trigger_note="Write one local proof packet only.",
            )
            snapshot = runtime.autonomy_state_snapshot(autonomy_id)
            queue = runtime.autonomy_state_queue_snapshot()

            contract_keys = {
                "allowed_statuses",
                "allowed_approval_states",
                "allowed_plan_action_statuses",
                "allowed_control_actions",
                "allowed_control_postures",
                "allowed_readiness_states",
                "allowed_follow_through_statuses",
            }
            expected_contract = {key: snapshot[key] for key in contract_keys}

            for payload in (created, planned, controlled, ready, followed_through, queue):
                observed_contract = {key: payload[key] for key in contract_keys}
                self.assertEqual(observed_contract, expected_contract)

    def test_runtime_creates_visibility_only_autonomy_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = runtime.create_autonomy_state(
                "Chris",
                title="Pool robot follow-up watch",
                objective="Hold the pool robot follow-up as visible autonomy state only.",
                current_focus="Visibility only until explicit follow-through is requested.",
                next_step="Keep the next question visible.",
                requested_scope="Track the follow-up as proposed visibility only.",
                initiation_reason="Chris wants the follow-up held for later review.",
            )
            queue = runtime.autonomy_state_queue_snapshot()
            snapshot = runtime.autonomy_state_snapshot(result["autonomy_state"]["autonomy_id"])

            self.assertEqual(result["autonomy_state"]["status"], "queued")
            self.assertEqual(result["autonomy_effect"], "visibility_only")
            self.assertIn("initiation-boundary record only", result["message"].lower())
            self.assertEqual(queue["total_states"], 1)
            self.assertEqual(queue["counts_by_status"]["queued"], 1)
            self.assertEqual(snapshot["autonomy_state"]["title"], "Pool robot follow-up watch")
            self.assertFalse(bool(snapshot["autonomy_state"]["background_execution_claimed"]))
            self.assertEqual(snapshot["autonomy_state"]["requested_scope"], "Track the follow-up as proposed visibility only.")
            self.assertEqual(snapshot["autonomy_state"]["approval_state"], "required")

    def test_runtime_rejects_missing_objective(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            with self.assertRaisesRegex(ValueError, "objective is required"):
                runtime.create_autonomy_state(
                    "Chris",
                    title="Broken autonomy state",
                    objective="",
                    requested_scope="Visibility only.",
                    initiation_reason="Preserve context.",
                )

    def test_runtime_rejects_missing_requested_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            with self.assertRaisesRegex(ValueError, "requested_scope is required"):
                runtime.create_autonomy_state(
                    "Chris",
                    title="Missing scope",
                    objective="Hold this objective visibly.",
                    requested_scope="",
                    initiation_reason="Preserve context.",
                )

    def test_runtime_rejects_empty_proposed_action_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )
            created = runtime.create_autonomy_state(
                "Chris",
                title="Missing plan",
                objective="Keep the record inspectable.",
                requested_scope="Visibility only.",
                initiation_reason="Preserve context.",
            )

            with self.assertRaisesRegex(ValueError, "at least one proposed action is required"):
                runtime.add_autonomy_action_plan(
                    created["autonomy_state"]["autonomy_id"],
                    planning_note="No real plan items yet.",
                    proposed_actions=[],
                )

    def test_runtime_rejects_resume_after_abort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )
            created = runtime.create_autonomy_state(
                "Chris",
                title="Aborted lane",
                objective="Keep the record inspectable.",
                requested_scope="Visibility only.",
                initiation_reason="Preserve context.",
            )
            runtime.apply_autonomy_control_action(
                "Chris",
                created["autonomy_state"]["autonomy_id"],
                action="abort",
                control_reason="Chris closed the lane.",
            )

            with self.assertRaisesRegex(ValueError, "aborted autonomy state cannot be resumed"):
                runtime.apply_autonomy_control_action(
                    "Chris",
                    created["autonomy_state"]["autonomy_id"],
                    action="resume",
                    control_reason="Try to reopen it.",
                )

    def test_runtime_rejects_ready_within_boundary_without_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )
            created = runtime.create_autonomy_state(
                "Chris",
                title="Not approved lane",
                objective="Keep the record inspectable.",
                requested_scope="Visibility only.",
                initiation_reason="Preserve context.",
            )

            with self.assertRaisesRegex(ValueError, "ready_within_boundary requires approval to be satisfied or not required"):
                runtime.apply_autonomy_readiness_state(
                    "Chris",
                    created["autonomy_state"]["autonomy_id"],
                    readiness_state="ready_within_boundary",
                    readiness_reason="Try to mark it fully ready too early.",
                )

    def test_runtime_rejects_follow_through_when_not_ready_within_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomyStateStore(Path(tmp) / "data" / "autonomy_states")
            runtime = _RuntimeLike(
                autonomy_state_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )
            created = runtime.create_autonomy_state(
                "Chris",
                title="Not ready follow-through",
                objective="Keep the record inspectable.",
                requested_scope="Visibility only.",
                initiation_reason="Preserve context.",
            )

            with self.assertRaisesRegex(ValueError, "local follow-through trigger requires readiness_state=ready_within_boundary"):
                runtime.trigger_autonomy_local_follow_through(
                    "Chris",
                    created["autonomy_state"]["autonomy_id"],
                    trigger_note="Try to run it too early.",
                )


if __name__ == "__main__":
    unittest.main()

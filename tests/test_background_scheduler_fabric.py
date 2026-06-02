from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jarvis.agentic import AgentRegistry, BackgroundStateStore, BackgroundTaskScheduler
from jarvis.models import AttentionDisposition, TriggerType


def _scheduler(tmp_path):
    store = BackgroundStateStore(tmp_path / "agents")
    registry = AgentRegistry()
    return BackgroundTaskScheduler(store, registry)


def test_threshold_events_dedupe_within_window(tmp_path) -> None:
    scheduler = _scheduler(tmp_path)
    now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    first = scheduler.publish_event(
        {
            "trigger_type": TriggerType.THRESHOLD.value,
            "topic": "forecast change",
            "source": "weather-engine",
            "dedupe_key": "storm-risk:family",
            "dedupe_window_seconds": 600,
            "payload": {"changed_fields": ["forecast change"]},
        },
        now=now,
    )
    second = scheduler.publish_event(
        {
            "trigger_type": TriggerType.THRESHOLD.value,
            "topic": "forecast change",
            "source": "weather-engine",
            "dedupe_key": "storm-risk:family",
            "dedupe_window_seconds": 600,
            "payload": {"changed_fields": ["forecast change"]},
        },
        now=now + timedelta(minutes=5),
    )

    assert first is not None
    assert second is None
    assert scheduler.scheduler_fabric_snapshot()["event_bus"]["total_events"] == 1


def test_handoff_event_routes_to_staged_background_agent(tmp_path) -> None:
    scheduler = _scheduler(tmp_path)
    now = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)

    snapshot = scheduler.tick(
        active_mode="work-mode",
        integration_status=[{"name": "openai", "ok": True}],
        recent_activity=[{"module": "executive-work"}],
        quiet_hours=("22:00", "06:00"),
        external_events=[
            {
                "trigger_type": TriggerType.HANDOFF.value,
                "topic": "meeting prep",
                "source": "executive-watch",
                "target_agents": ["catalyst-personal"],
                "attention_hint": AttentionDisposition.STAGED.value,
                "payload": {"changed_fields": ["meeting prep"]},
            }
        ],
        presence={"attention_state": "passive"},
        now=now,
    )

    staged = snapshot["attention"]["staged"]
    assert any(item["agent_id"] == "catalyst-personal" for item in staged)
    assert all(item["attention"] == AttentionDisposition.STAGED.value for item in staged)


def test_human_interrupt_brings_front_door_forward(tmp_path) -> None:
    scheduler = _scheduler(tmp_path)
    now = datetime(2026, 6, 1, 14, 0, tzinfo=UTC)

    snapshot = scheduler.tick(
        active_mode="ambient-associate",
        integration_status=[],
        recent_activity=[],
        quiet_hours=("22:00", "06:00"),
        external_events=[
            {
                "trigger_type": TriggerType.HUMAN_INTERRUPT.value,
                "topic": "voice request",
                "source": "user",
                "attention_hint": AttentionDisposition.FOREGROUND.value,
                "target_agents": ["ambient-router"],
            }
        ],
        presence={"attention_state": "foreground", "conversation_active": True},
        now=now,
    )

    foreground = snapshot["attention"]["foreground"]
    assert any(item["agent_id"] == "ambient-router" for item in foreground)
    router_status = next(item for item in snapshot["statuses"] if item["agent_id"] == "ambient-router")
    assert router_status["attention_mode"] == AttentionDisposition.FOREGROUND.value

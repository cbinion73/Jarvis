from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_REGISTRY_PATH = REPO_ROOT / "data" / "agents" / "jarvis_agent_registry.v1.json"
MISSION_MODEL_PATH = REPO_ROOT / "data" / "missions" / "jarvis_mission_model.v1.json"
AGENT_REGISTRY_SCHEMA_PATH = REPO_ROOT / "schemas" / "jarvis-agent-registry.v1.json"
MISSION_MODEL_SCHEMA_PATH = REPO_ROOT / "schemas" / "jarvis-mission-model.v1.json"

EXPECTED_POSTURE = {
    "system_mode": "always-on-orchestrator",
    "interaction_mode": "oversight-and-steering",
    "voice_mode": "voice-enabled-not-primary",
    "registry_mode": "operational-contract",
}
ALLOWED_AGENT_STATUSES = {"active", "paused", "retired"}
ALLOWED_AUTONOMY_POSTURES = {"bounded-autonomy", "approval-required", "observe-only"}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing required contract file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Contract file must contain a JSON object: {path}")
    return payload


def _is_iso_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


@dataclass(slots=True)
class ContractBundle:
    registry: dict[str, Any]
    mission_model: dict[str, Any]

    def snapshot(self) -> dict[str, Any]:
        stages = _as_str_list([item.get("stage_id", "") for item in self.mission_model.get("authority_stages", []) if isinstance(item, dict)])
        agents = list(self.registry.get("agents", []))
        return {
            "registry_id": self.registry.get("registry_id", ""),
            "mission_model_id": self.mission_model.get("model_id", ""),
            "schema_version": self.registry.get("schema_version", ""),
            "agent_count": len(agents),
            "domains": sorted({str(item.get("operating_domain", "")).strip() for item in agents if isinstance(item, dict) and str(item.get("operating_domain", "")).strip()}),
            "authority_stages": stages,
            "posture": dict(self.registry.get("canonical_posture", {})),
        }


def _require_keys(payload: dict[str, Any], required: tuple[str, ...], context: str, errors: list[str]) -> None:
    for key in required:
        if key not in payload:
            errors.append(f"{context}: missing required key '{key}'")


def _validate_posture(payload: dict[str, Any], context: str, errors: list[str]) -> None:
    posture = payload.get("canonical_posture")
    if not isinstance(posture, dict):
        errors.append(f"{context}: canonical_posture must be an object")
        return
    for key, expected in EXPECTED_POSTURE.items():
        actual = str(posture.get(key, "")).strip()
        if actual != expected:
            errors.append(f"{context}: canonical_posture.{key} must be '{expected}'")


def _validate_mission_model(payload: dict[str, Any], errors: list[str]) -> None:
    _require_keys(
        payload,
        (
            "schema_version",
            "model_id",
            "generated_at",
            "canonical_posture",
            "operator_principals",
            "authority_stages",
            "mission_statuses",
            "ownership_roles",
            "escalation_targets",
            "escalation_reasons",
            "lane_taxonomy",
            "handoff_kinds",
            "registry_invariants",
        ),
        "mission model",
        errors,
    )
    if str(payload.get("schema_version", "")).strip() != "1.0":
        errors.append("mission model: schema_version must be '1.0'")
    if not _is_iso_datetime(payload.get("generated_at")):
        errors.append("mission model: generated_at must be an ISO 8601 datetime")
    _validate_posture(payload, "mission model", errors)

    principals = payload.get("operator_principals")
    if not isinstance(principals, list) or not principals:
        errors.append("mission model: operator_principals must be a non-empty array")
    else:
        for index, item in enumerate(principals):
            if not isinstance(item, dict):
                errors.append(f"mission model: operator_principals[{index}] must be an object")
                continue
            _require_keys(item, ("principal_id", "display_name", "role"), f"mission model operator_principals[{index}]", errors)

    stages = payload.get("authority_stages")
    if not isinstance(stages, list) or not stages:
        errors.append("mission model: authority_stages must be a non-empty array")
    else:
        seen_stage_ids: set[str] = set()
        last_sequence = -1
        for index, item in enumerate(stages):
            if not isinstance(item, dict):
                errors.append(f"mission model: authority_stages[{index}] must be an object")
                continue
            _require_keys(item, ("stage_id", "sequence", "summary", "human_approval_required"), f"mission model authority_stages[{index}]", errors)
            stage_id = str(item.get("stage_id", "")).strip()
            if stage_id in seen_stage_ids:
                errors.append(f"mission model: duplicate authority stage '{stage_id}'")
            seen_stage_ids.add(stage_id)
            sequence = item.get("sequence")
            if not isinstance(sequence, int):
                errors.append(f"mission model: authority_stages[{index}].sequence must be an integer")
            elif sequence <= last_sequence:
                errors.append("mission model: authority stages must be strictly ordered by sequence")
            else:
                last_sequence = sequence

    for key in ("mission_statuses", "ownership_roles", "escalation_targets", "escalation_reasons", "lane_taxonomy", "handoff_kinds", "registry_invariants"):
        items = _as_str_list(payload.get(key))
        if not items:
            errors.append(f"mission model: {key} must be a non-empty array of strings")


def _validate_registry(payload: dict[str, Any], mission_model: dict[str, Any], errors: list[str]) -> None:
    _require_keys(
        payload,
        (
            "schema_version",
            "registry_id",
            "mission_model_id",
            "mission_model_version",
            "generated_at",
            "canonical_posture",
            "ownership_defaults",
            "agents",
        ),
        "agent registry",
        errors,
    )
    if str(payload.get("schema_version", "")).strip() != "1.0":
        errors.append("agent registry: schema_version must be '1.0'")
    if str(payload.get("mission_model_id", "")).strip() != str(mission_model.get("model_id", "")).strip():
        errors.append("agent registry: mission_model_id must match mission model model_id")
    if str(payload.get("mission_model_version", "")).strip() != str(mission_model.get("schema_version", "")).strip():
        errors.append("agent registry: mission_model_version must match mission model schema_version")
    if not _is_iso_datetime(payload.get("generated_at")):
        errors.append("agent registry: generated_at must be an ISO 8601 datetime")
    _validate_posture(payload, "agent registry", errors)

    ownership_defaults = payload.get("ownership_defaults")
    if not isinstance(ownership_defaults, dict):
        errors.append("agent registry: ownership_defaults must be an object")
    else:
        _require_keys(ownership_defaults, ("principal_id", "operator_role", "default_escalation_target"), "agent registry ownership_defaults", errors)

    agents = payload.get("agents")
    if not isinstance(agents, list) or not agents:
        errors.append("agent registry: agents must be a non-empty array")
        return

    principal_ids = {str(item.get("principal_id", "")).strip() for item in mission_model.get("operator_principals", []) if isinstance(item, dict)}
    authority_stage_ids = {str(item.get("stage_id", "")).strip() for item in mission_model.get("authority_stages", []) if isinstance(item, dict)}
    escalation_targets = set(_as_str_list(mission_model.get("escalation_targets")))
    escalation_reasons = set(_as_str_list(mission_model.get("escalation_reasons")))
    lane_taxonomy = set(_as_str_list(mission_model.get("lane_taxonomy")))
    ownership_roles = set(_as_str_list(mission_model.get("ownership_roles")))

    agent_ids: set[str] = set()
    labels: set[str] = set()
    raw_agents: list[dict[str, Any]] = []
    for index, item in enumerate(agents):
        if not isinstance(item, dict):
            errors.append(f"agent registry: agents[{index}] must be an object")
            continue
        raw_agents.append(item)
        _require_keys(
            item,
            (
                "agent_id",
                "label",
                "title",
                "agent_class",
                "status",
                "promotion_status",
                "operating_domain",
                "purpose",
                "mission_statement",
                "lane_ownership",
                "primary_lane",
                "mission_roles",
                "cadence_minutes",
                "triggers",
                "dependencies",
                "memory_scope",
                "trust_zone",
                "authority_stage",
                "autonomy_posture",
                "quiet_hours_behavior",
                "allowed_tools",
                "success_metrics",
                "ownership",
                "escalation",
            ),
            f"agent registry agents[{index}]",
            errors,
        )
        agent_id = str(item.get("agent_id", "")).strip()
        label = str(item.get("label", "")).strip()
        if not agent_id:
            errors.append(f"agent registry: agents[{index}].agent_id is required")
        elif agent_id in agent_ids:
            errors.append(f"agent registry: duplicate agent_id '{agent_id}'")
        else:
            agent_ids.add(agent_id)
        if not label:
            errors.append(f"agent registry: agents[{index}].label is required")
        elif label in labels:
            errors.append(f"agent registry: duplicate label '{label}'")
        else:
            labels.add(label)

        if not str(item.get("purpose", "")).strip():
            errors.append(f"agent registry: {agent_id or f'agents[{index}]'} purpose is required")
        if not str(item.get("mission_statement", "")).strip():
            errors.append(f"agent registry: {agent_id or f'agents[{index}]'} mission_statement is required")

        status = str(item.get("status", "")).strip()
        if status not in ALLOWED_AGENT_STATUSES:
            errors.append(f"agent registry: {agent_id} status '{status}' is invalid")

        cadence = item.get("cadence_minutes")
        if not isinstance(cadence, int) or cadence <= 0:
            errors.append(f"agent registry: {agent_id} cadence_minutes must be a positive integer")

        authority_stage = str(item.get("authority_stage", "")).strip()
        if authority_stage not in authority_stage_ids:
            errors.append(f"agent registry: {agent_id} authority_stage '{authority_stage}' is not defined by the mission model")

        autonomy_posture = str(item.get("autonomy_posture", "")).strip()
        if autonomy_posture not in ALLOWED_AUTONOMY_POSTURES:
            errors.append(f"agent registry: {agent_id} autonomy_posture '{autonomy_posture}' is invalid")

        lane_ownership = _as_str_list(item.get("lane_ownership"))
        primary_lane = str(item.get("primary_lane", "")).strip()
        if not lane_ownership:
            errors.append(f"agent registry: {agent_id} must declare lane_ownership")
        if primary_lane not in lane_ownership:
            errors.append(f"agent registry: {agent_id} primary_lane must appear in lane_ownership")
        for lane in lane_ownership:
            if lane not in lane_taxonomy:
                errors.append(f"agent registry: {agent_id} lane '{lane}' is not defined in the mission model")

        ownership = item.get("ownership")
        if not isinstance(ownership, dict):
            errors.append(f"agent registry: {agent_id} ownership must be an object")
        else:
            principal_id = str(ownership.get("principal_id", "")).strip()
            role = str(ownership.get("role", "")).strip()
            if principal_id not in principal_ids:
                errors.append(f"agent registry: {agent_id} principal_id '{principal_id}' is not declared in the mission model")
            if role not in ownership_roles:
                errors.append(f"agent registry: {agent_id} ownership role '{role}' is not defined in the mission model")

        escalation = item.get("escalation")
        if not isinstance(escalation, dict):
            errors.append(f"agent registry: {agent_id} escalation must be an object")
        else:
            default_target = str(escalation.get("default_target", "")).strip()
            if default_target not in escalation_targets:
                errors.append(f"agent registry: {agent_id} default escalation target '{default_target}' is invalid")
            for reason in _as_str_list(escalation.get("immediate_reasons")) + _as_str_list(escalation.get("review_reasons")):
                if reason not in escalation_reasons:
                    errors.append(f"agent registry: {agent_id} escalation reason '{reason}' is not defined in the mission model")

    for item in raw_agents:
        agent_id = str(item.get("agent_id", "")).strip()
        ownership = item.get("ownership") if isinstance(item.get("ownership"), dict) else {}
        escalation = item.get("escalation") if isinstance(item.get("escalation"), dict) else {}
        steward_agent_id = str(ownership.get("steward_agent_id", "")).strip()
        supervisor_agent_id = str(escalation.get("supervisor_agent_id", "")).strip()
        if steward_agent_id and steward_agent_id not in agent_ids:
            errors.append(f"agent registry: {agent_id} steward_agent_id '{steward_agent_id}' does not exist in the registry")
        if supervisor_agent_id and supervisor_agent_id not in agent_ids:
            errors.append(f"agent registry: {agent_id} supervisor_agent_id '{supervisor_agent_id}' does not exist in the registry")


def validate_contract_bundle(registry: dict[str, Any], mission_model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _validate_mission_model(mission_model, errors)
    _validate_registry(registry, mission_model, errors)
    return errors


def load_contract_bundle(*, validate: bool = True) -> ContractBundle:
    registry = _load_json(AGENT_REGISTRY_PATH)
    mission_model = _load_json(MISSION_MODEL_PATH)
    if validate:
        errors = validate_contract_bundle(registry, mission_model)
        if errors:
            message = "\n".join(f"- {error}" for error in errors)
            raise ValueError(f"JARVIS agent registry contract is invalid:\n{message}")
    return ContractBundle(registry=registry, mission_model=mission_model)


def contract_paths() -> dict[str, str]:
    return {
        "agent_registry": str(AGENT_REGISTRY_PATH),
        "mission_model": str(MISSION_MODEL_PATH),
        "agent_registry_schema": str(AGENT_REGISTRY_SCHEMA_PATH),
        "mission_model_schema": str(MISSION_MODEL_SCHEMA_PATH),
    }

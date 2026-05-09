from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class ActionClass(IntEnum):
    OBSERVE = 0
    SUGGEST = 1
    PREPARE = 2
    EXECUTE_LOW_RISK = 3
    EXECUTE_MEDIUM_RISK = 4
    EXECUTE_HIGH_RISK = 5
    RESTRICTED = 6


@dataclass(slots=True)
class UserProfile:
    user_id: str
    display_name: str
    address_as: str
    role: str
    permissions: str
    priorities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RoomProfile:
    room_id: str
    mode_bias: str


@dataclass(slots=True)
class HouseholdProfile:
    household_name: str
    location_label: str
    quiet_start: str
    quiet_end: str
    users: dict[str, UserProfile]
    rooms: dict[str, RoomProfile]
    modes: list[str]


@dataclass(slots=True)
class SnapshotCard:
    title: str
    status: str
    summary: str
    details: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FamilyEvent:
    time: str
    owner: str
    title: str
    note: str


@dataclass(slots=True)
class HouseholdSnapshot:
    day_label: str
    weather: str
    house_note: str
    body: SnapshotCard
    home: SnapshotCard
    mission: SnapshotCard
    events: list[FamilyEvent]
    family_focus: dict[str, list[str]]
    watch_items: list[str]


@dataclass(slots=True)
class PermissionDecision:
    action_class: ActionClass
    needs_approval: bool
    second_factor_required: bool
    allowed: bool
    rationale: str


@dataclass(slots=True)
class RequestPlan:
    request_id: str
    actor: str
    room: str
    request: str
    mode: str
    module: str
    workstream: str
    model: str
    action_class: ActionClass
    allowed: bool
    needs_approval: bool
    second_factor_required: bool
    rationale: str


@dataclass(slots=True)
class ApprovalRequest:
    request_id: str
    actor: str
    room: str
    request: str
    action_class: str
    second_factor_required: bool
    status: str
    rationale: str


@dataclass(slots=True)
class VoiceSatelliteProfile:
    satellite_id: str
    device_name: str
    room: str
    default_speaker: str = ""


@dataclass(slots=True)
class VoiceContextProfile:
    wake_words: list[str]
    satellites: list[VoiceSatelliteProfile] = field(default_factory=list)


@dataclass(slots=True)
class InferredContext:
    actor: str
    room: str
    wake_word_detected: bool
    cleaned_request: str
    source_device: str = ""
    quiet_mode: bool = False
    whisper_mode: bool = False
    speaker_confidence: str = "heuristic"


@dataclass(slots=True)
class OpenClawBridgeEnvelope:
    gateway_url: str
    actor: str
    room: str
    raw_request: str
    cleaned_request: str
    wake_word_detected: bool
    module: str
    mode: str
    model: str
    needs_approval: bool
    second_factor_required: bool
    rationale: str
    output_text: str = ""


@dataclass(slots=True)
class ModeState:
    mode: str
    status: str
    reason: str
    actor: str
    timestamp: str


@dataclass(slots=True)
class MessageDraft:
    draft_id: str
    actor: str
    audience: str
    purpose: str
    tone: str
    context: str
    body: str
    status: str
    timestamp: str


@dataclass(slots=True)
class TutoringSession:
    session_id: str
    actor: str
    subject: str
    request: str
    coaching_mode: str
    response_text: str
    parent_summary: str
    boundary_status: str
    encouragement: str
    follow_up: str
    frustration_signal: str
    timestamp: str


@dataclass(slots=True)
class PrinterStatus:
    printer_id: str
    name: str
    status: str
    material: str
    active_job: str
    progress_percent: int
    note: str
    timestamp: str


@dataclass(slots=True)
class WorkshopInspection:
    inspection_id: str
    actor: str
    part_name: str
    request: str
    observations: str
    goals: str
    diagnosis: str
    recommended_material: str
    recommended_process: str
    safety_notes: list[str]
    next_steps: list[str]
    image_path: str
    timestamp: str


@dataclass(slots=True)
class VendorPrep:
    prep_id: str
    actor: str
    part_name: str
    vendor_target: str
    process: str
    material: str
    package_summary: str
    approval_request_id: str
    status: str
    timestamp: str


@dataclass(slots=True)
class VoiceNoteTask:
    note_id: str
    actor: str
    source: str
    note: str
    tasks: list[str]
    status: str
    timestamp: str


@dataclass(slots=True)
class DeviceBoundaryRoutine:
    routine_id: str
    actor: str
    window_label: str
    checklist: list[str]
    device_expectation: str
    reminder_text: str
    status: str
    timestamp: str


@dataclass(slots=True)
class MaterialRecommendation:
    recommendation_id: str
    actor: str
    part_name: str
    use_case: str
    recommended_material: str
    rationale: str
    backup_materials: list[str]
    timestamp: str


@dataclass(slots=True)
class CadPackage:
    package_id: str
    actor: str
    part_name: str
    summary: str
    parameters: list[str]
    openscad_stub: str
    fit_checks: list[str]
    timestamp: str


@dataclass(slots=True)
class PrintPrep:
    prep_id: str
    actor: str
    part_name: str
    printer_id: str
    material: str
    profile_name: str
    layer_height: str
    infill: str
    supports: str
    handoff_notes: str
    status: str
    timestamp: str


@dataclass(slots=True)
class SafetyCheck:
    check_id: str
    actor: str
    operation: str
    allowed: bool
    warnings: list[str]
    required_interlocks: list[str]
    recommendation: str
    timestamp: str


@dataclass(slots=True)
class InventoryItem:
    item_id: str
    name: str
    category: str
    quantity: str
    status: str
    restock_note: str


@dataclass(slots=True)
class SecurityIncident:
    incident_id: str
    category: str
    severity: str
    source: str
    headline: str
    detail: str
    recommended_action: str
    needs_ack: bool
    timestamp: str


@dataclass(slots=True)
class WeatherAdvisory:
    advisory_id: str
    actor: str
    context: str
    current_weather: str
    risk_level: str
    safe_timing: str
    recommendation: str
    follow_ups: list[str]
    timestamp: str


@dataclass(slots=True)
class ArrivalEvent:
    event_id: str
    actor: str
    location: str
    status: str
    detail: str
    next_steps: list[str]
    timestamp: str


@dataclass(slots=True)
class UnlockAssessment:
    assessment_id: str
    actor: str
    target: str
    requested_by_voice: bool
    second_factor_present: bool
    allowed: bool
    rationale: str
    required_next_step: str
    timestamp: str


@dataclass(slots=True)
class MemoryEntry:
    entry_id: str
    memory_type: str
    scope: str
    owner: str
    project: str
    title: str
    summary: str
    tags: list[str]
    sensitivity: str
    approval_status: str
    cloud_excluded: bool
    encrypted_payload: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class MemoryProposal:
    proposal_id: str
    actor: str
    memory_type: str
    scope: str
    owner: str
    project: str
    title: str
    summary: str
    tags: list[str]
    sensitivity: str
    payload: dict
    status: str
    rationale: str
    created_at: str

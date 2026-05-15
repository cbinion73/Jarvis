from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum


class ActionClass(IntEnum):
    OBSERVE = 0
    SUGGEST = 1
    PREPARE = 2
    EXECUTE_LOW_RISK = 3
    EXECUTE_MEDIUM_RISK = 4
    EXECUTE_HIGH_RISK = 5
    RESTRICTED = 6


class TaskClass(StrEnum):
    AMBIENT = "ambient"
    FAMILY = "family"
    EXECUTIVE = "executive"
    FORMATION = "formation"
    WORKSHOP = "workshop"
    TUTORING = "tutoring"
    RESEARCH = "research"
    SENSITIVE_DRAFTING = "sensitive-drafting"
    PARTY_MODE = "party-mode"
    BACKGROUND = "background"


class RoutingTier(StrEnum):
    BACKGROUND_DETECTION = "background-detection"
    LOCAL_SYNTHESIS = "local-synthesis"
    HIGH_QUALITY_REASONING = "high-quality-reasoning"
    USER_FACING_DELIVERY = "user-facing-delivery"


class PrivacyLevel(StrEnum):
    LOCAL_ONLY = "local-only"
    PREFER_LOCAL = "prefer-local"
    CLOUD_OK = "cloud-ok"
    RESTRICTED = "restricted"


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class AutonomyMode(StrEnum):
    AUTONOMOUS = "autonomous"
    STAGED = "staged"
    APPROVAL_REQUIRED = "approval-required"
    FORBIDDEN = "forbidden"


class WorkLifecycleStage(StrEnum):
    SIGNAL = "signal"
    HYPOTHESIS = "hypothesis"
    PROJECT_BRIEF = "project-brief"
    IMPLEMENTATION_PLAN = "implementation-plan"
    STAGED_ACTION = "staged-action"
    REVIEW = "review"
    OUTCOME = "outcome"


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
class ModelRoutingPolicy:
    tier: RoutingTier
    provider: str
    model: str
    privacy_level: PrivacyLevel
    risk_level: RiskLevel
    summary: str


@dataclass(slots=True)
class AutonomyPolicy:
    domain: str
    lane: str
    owner_agent: str
    risk_level: RiskLevel
    autonomy_mode: AutonomyMode
    review_level: str
    allowed_actions: list[str] = field(default_factory=list)
    requires_approval: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass(slots=True)
class WorkLifecycleRecord:
    work_id: str
    actor: str
    title: str
    domain: str
    lane: str
    owner_agent: str
    stage: WorkLifecycleStage
    status: str
    artifact_type: str
    source: str
    review_level: str
    rationale: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class RequestPlan:
    request_id: str
    actor: str
    room: str
    request: str
    mode: str
    module: str
    workstream: str
    task_class: TaskClass
    preferred_provider: str
    context_lane: str
    model: str
    routing_tier: RoutingTier
    privacy_level: PrivacyLevel
    risk_level: RiskLevel
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
    domain: str = ""
    lane: str = ""
    owner_agent: str = ""
    lifecycle_work_id: str = ""


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
    request_id: str = ""
    arena_id: str = ""
    mailbox_id: str = ""
    thread_id: str = ""
    source_message_id: str = ""
    source_subject: str = ""
    stage_status: str = ""
    alert_status: str = ""
    draft_folder: str = "drafts"
    approval_request_id: str = ""
    work_id: str = ""
    provider: str = ""
    mailbox_account_id: str = ""
    external_draft_id: str = ""
    external_message_id: str = ""
    external_thread_id: str = ""
    sync_status: str = ""
    sync_error: str = ""


@dataclass(slots=True)
class TrustZone:
    zone_id: str
    name: str
    zone_type: str
    resource_scope: dict[str, object]
    allowed_actions: list[str]
    approval_mode: str
    audit_mode: str
    promotion_rules: dict[str, object]
    demotion_rules: dict[str, object]
    status: str
    description: str = ""
    reporting_cadence: str = "on_request"
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class ResourceArena:
    arena_id: str
    name: str
    resource_type: str
    linked_zone_id: str
    owner_principal: str
    risk_class: str
    limits: dict[str, object]
    pause_conditions: list[str]
    status: str
    description: str = ""
    resource_refs: dict[str, object] = field(default_factory=dict)
    promotion_eligibility: dict[str, object] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class AuthorityStage:
    stage_id: str
    name: str
    sequence: int
    allowed_action_types: list[str]
    approval_requirements: dict[str, object]
    reporting_requirements: dict[str, object]
    promotion_criteria: dict[str, object]
    demotion_triggers: list[str]
    status: str
    description: str = ""


@dataclass(slots=True)
class EmailDraftStagingRequest:
    request_id: str
    arena_id: str
    principal_id: str
    source_message: dict[str, object]
    draft_intent: dict[str, object]
    stage_policy: dict[str, object]
    context_refs: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class EmailDraftStagingResponse:
    request_id: str
    draft_id: str
    arena_id: str
    stage_status: str
    draft_location: dict[str, object]
    alert: dict[str, object]
    audit_ref: str
    promotion_signal: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class StagedActionQueueItem:
    request_id: str
    arena_id: str
    action_type: str
    status: str
    created_at: str
    draft_id: str = ""
    principal_id: str = ""


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
    family: str
    summary: str
    parameters: list[str]
    openscad_stub: str
    fit_checks: list[str]
    artifact_dir: str
    script_path: str
    cadquery_script_path: str
    model_path: str
    step_path: str
    mesh_3mf_path: str
    slicer_pack_dir: str
    creative_profile: str
    export_status: str
    export_detail: str
    export_engine: str
    timestamp: str


@dataclass(slots=True)
class ConceptStudioSession:
    session_id: str
    actor: str
    object_type: str
    silhouette_preference: str
    title: str
    goals: str
    constraints: str
    concept_summary: str
    design_direction: str
    suggested_silhouette: str
    suggested_family: str
    suggested_part_name: str
    suggested_dimensions: str
    suggested_constraints: str
    print_strategy: str
    questions: list[str]
    next_step: str
    capture_id: str
    image_path: str
    vision_object_label: str
    vision_contour_confidence: str
    vision_asymmetry_hint: str
    vision_dimension_seed: str
    variants: list[dict[str, str]]
    transcript: list[dict[str, str]]
    status: str
    created_at: str
    updated_at: str


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
    subject_user_id: str = ""
    access_policy: str = "personal"
    boundary_label: str = ""
    source_type: str = "user-stated"
    confidence: str = "confirmed"


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
    subject_user_id: str = ""
    access_policy: str = "personal"
    boundary_label: str = ""
    source_type: str = "user-stated"
    confidence: str = "confirmed"


@dataclass(slots=True)
class MemoryProfileFact:
    fact_id: str
    subject_user_id: str
    subject_display_name: str
    lane: str
    title: str
    summary: str
    tags: list[str]
    source_entry_ids: list[str]
    confidence: str
    status: str
    source_type: str
    boundary_label: str
    created_at: str
    updated_at: str

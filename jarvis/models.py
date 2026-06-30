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


class TriggerType(StrEnum):
    CADENCE = "cadence"
    STATE_CHANGE = "state-change"
    SIGNAL = "signal"
    THRESHOLD = "threshold"
    HANDOFF = "handoff"
    HUMAN_INTERRUPT = "human-interrupt"


class UserAttentionState(StrEnum):
    AWAY = "away"
    PASSIVE = "passive"
    FOREGROUND = "foreground"
    DO_NOT_DISTURB = "do-not-disturb"


class AttentionDisposition(StrEnum):
    SILENT = "silent"
    STAGED = "staged"
    FOREGROUND = "foreground"
    INTERRUPT = "interrupt"


class InterruptionLevel(StrEnum):
    NEVER = "never"
    PASSIVE = "passive"
    IMPORTANT = "important"
    URGENT = "urgent"


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
    authority_stage: str
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
class PromotionRecord:
    record_id: str
    event_type: str
    subject_kind: str
    subject_id: str
    status: str
    actor: str
    basis: str
    trust_zone: str = ""
    arena_id: str = ""
    authority_stage: str = ""
    evidence: dict[str, object] = field(default_factory=dict)
    created_at: str = ""


@dataclass(slots=True)
class PromotionThreshold:
    min_runs: int
    min_success: float
    max_boundary_violations: int = 0
    requires_human_consent: bool = False


@dataclass(slots=True)
class PromotionClaim:
    claim_id: str
    subject_kind: str
    subject_id: str
    current_stage: str
    target_stage: str
    actor: str
    basis: str = ""
    trust_zone: str = ""
    arena_id: str = ""
    human_consent: bool = False
    submitted_at: str = ""
    evidence_summary: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PromotionVerdict:
    claim_id: str
    subject_kind: str
    subject_id: str
    current_stage: str
    target_stage: str
    decision: str
    reason: str
    threshold: PromotionThreshold
    metrics: dict[str, object] = field(default_factory=dict)
    trust_zone: str = ""
    arena_id: str = ""
    human_consent_required: bool = False
    human_consent_present: bool = False
    evaluated_at: str = ""


@dataclass(slots=True)
class MissionActionDecision:
    action_type: str
    trust_zone: str
    resolution: str
    rationale: str
    approval_required: bool
    approval_request_id: str = ""


@dataclass(slots=True)
class MissionSubtask:
    subtask_id: str
    title: str
    description: str
    status: str
    owner_agent: str
    domain: str
    trust_zone: str
    action_type: str
    resolution: str
    dependencies: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MissionEvidence:
    evidence_id: str
    source_agent: str
    source_system: str
    kind: str
    title: str
    summary: str
    detail: str
    timestamp: str
    refs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MissionOutput:
    output_id: str
    kind: str
    title: str
    summary: str
    status: str
    timestamp: str
    payload_ref: str = ""


@dataclass(slots=True)
class AgentTaskRef:
    task_id: str
    title: str
    status: str
    summary: str = ""
    source: str = ""
    updated_at: str = ""
    dependencies: list[str] = field(default_factory=list)
    handoff_id: str = ""


@dataclass(slots=True)
class AgentMessage:
    entry_id: str
    kind: str
    status: str
    from_agent: str
    to_agent: str
    subject: str
    summary: str
    task_id: str = ""
    created_at: str = ""
    acknowledged_at: str = ""


@dataclass(slots=True)
class AgentDecisionRecord:
    decision_id: str
    summary: str
    rationale: str
    task_id: str = ""
    created_at: str = ""


@dataclass(slots=True)
class AgentHypothesisRecord:
    hypothesis_id: str
    summary: str
    confidence: str = "working"
    status: str = "active"
    task_id: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class AgentWorkState:
    agent_id: str
    mission_id: str
    role: str
    status: str
    ownership_mode: str = "supporting"
    current_focus: str = ""
    inbox: list[AgentMessage] = field(default_factory=list)
    outbox: list[AgentMessage] = field(default_factory=list)
    active_tasks: list[AgentTaskRef] = field(default_factory=list)
    blocked_tasks: list[AgentTaskRef] = field(default_factory=list)
    pending_reviews: list[AgentTaskRef] = field(default_factory=list)
    recent_decisions: list[AgentDecisionRecord] = field(default_factory=list)
    current_hypotheses: list[AgentHypothesisRecord] = field(default_factory=list)
    last_handoff_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class AgentHandoffRecord:
    handoff_id: str
    mission_id: str
    from_agent: str
    to_agent: str
    task_id: str
    handoff_kind: str
    status: str
    summary: str
    context: str
    partial_work: str = ""
    duplicate_key: str = ""
    requires_acceptance: bool = True
    created_at: str = ""
    acknowledged_at: str = ""
    completed_at: str = ""


@dataclass(slots=True)
class AgentDelegationRecord:
    delegation_id: str
    mission_id: str
    delegator_agent: str
    delegate_agent: str
    task_id: str
    scope: str
    rationale: str
    expected_result: str
    status: str = "active"
    handoff_id: str = ""
    created_at: str = ""
    resolved_at: str = ""


@dataclass(slots=True)
class DelegationReportRecord:
    report_id: str
    mission_id: str
    delegation_id: str
    producer_agent: str
    title: str
    summary: str
    detail: str
    key_output: str = ""
    next_step: str = ""
    evidence_note: str = ""
    status: str = "completed-with-output"
    handoff_id: str = ""
    delegator_agent: str = ""
    delegate_agent: str = ""
    created_at: str = ""
    output_id: str = ""
    artifact_ref: str = ""


@dataclass(slots=True)
class AgentEscalationRecord:
    escalation_id: str
    mission_id: str
    from_agent: str
    to_agent: str
    task_id: str
    severity: str
    rationale: str
    requested_action: str
    status: str = "open"
    created_at: str = ""
    resolved_at: str = ""


@dataclass(slots=True)
class OwnershipTransferRecord:
    transfer_id: str
    mission_id: str
    task_id: str
    from_agent: str
    to_agent: str
    reason: str
    status: str = "pending-acceptance"
    safe_to_release: bool = False
    continuity_notes: str = ""
    created_at: str = ""
    accepted_at: str = ""


@dataclass(slots=True)
class DuplicateWorkSuppressionRecord:
    suppression_id: str
    mission_id: str
    duplicate_key: str
    task_id: str
    winning_agent: str
    suppressed_agent: str
    rationale: str
    status: str = "suppressed"
    created_at: str = ""


@dataclass(slots=True)
class TaskAgentProfile:
    agent_id: str
    label: str
    class_type: str
    origin: str
    mission_id: str
    template_id: str
    domain: str
    trust_zone: str
    autonomy_level: str
    promotion_status: str
    purpose: str
    mission_roles: list[str]
    allowed_tools: list[str] = field(default_factory=list)
    approval_triggers: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)
    status: str = "active"
    usage_count: int = 0
    success_count: int = 0
    last_used_at: str = ""
    memory_boundary: str = ""
    created_at: str = ""
    updated_at: str = ""
    promoted_at: str = ""


@dataclass(slots=True)
class MissionDossier:
    mission_id: str
    actor: str
    room: str
    request: str
    title: str
    brief: str
    status: str
    primary_domain: str
    trust_zone: str
    autonomy_posture: str
    owner_agent: str
    selected_agents: list[str]
    subtasks: list[MissionSubtask] = field(default_factory=list)
    action_decisions: list[MissionActionDecision] = field(default_factory=list)
    evidence: list[MissionEvidence] = field(default_factory=list)
    approvals: list[str] = field(default_factory=list)
    outputs: list[MissionOutput] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    agent_work_states: dict[str, AgentWorkState] = field(default_factory=dict)
    handoffs: list[AgentHandoffRecord] = field(default_factory=list)
    delegations: list[AgentDelegationRecord] = field(default_factory=list)
    delegation_reports: list[DelegationReportRecord] = field(default_factory=list)
    escalations: list[AgentEscalationRecord] = field(default_factory=list)
    ownership_transfers: list[OwnershipTransferRecord] = field(default_factory=list)
    duplicate_suppressions: list[DuplicateWorkSuppressionRecord] = field(default_factory=list)
    memory_snapshot: dict[str, object] = field(default_factory=dict)
    family_impact: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    origin: str = "conversation"
    objective: str = ""
    mission_type: str = ""
    why_this_matters: str = ""
    success_definition: str = ""
    time_horizon: str = "ongoing"
    momentum: str = "unknown"
    milestones: list[dict[str, object]] = field(default_factory=list)
    next_actions: list[dict[str, object]] = field(default_factory=list)
    next_step: str = ""
    recommendation: str = ""
    risks: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    accountability_cadence: str = ""
    progress_signal: str = ""
    support_message: str = ""
    workspace_route: str = "/mission-board"
    brief_summary: dict[str, object] = field(default_factory=dict)
    truth_labels: dict[str, str] = field(default_factory=dict)
    target_metrics: list[str] = field(default_factory=list)
    due_date: str = ""
    secondary_domains: list[str] = field(default_factory=list)
    linked_memories: list[str] = field(default_factory=list)
    background_prepared_outputs: list[dict[str, object]] = field(default_factory=list)


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
    work_id: str = ""
    updated_at: str = ""
    review_level: str = ""
    sandbox_status: str = ""
    sandbox_run_id: str = ""
    sandbox_message: str = ""
    sandbox_report_path: str = ""
    sandbox_patch_bundle_path: str = ""
    sandbox_workspace_path: str = ""
    sandbox_generated_at: str = ""


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


# Memory provenance taxonomy values (D9)
MEMORY_PROVENANCE_OBSERVED_FACT = "observed_fact"
MEMORY_PROVENANCE_INSTRUCTION = "instruction"
MEMORY_PROVENANCE_INFERENCE = "inference"
MEMORY_PROVENANCE_TENTATIVE_PATTERN = "tentative_pattern"
MEMORY_PROVENANCE_APPROVED_BELIEF = "approved_belief"
MEMORY_PROVENANCE_RETIRED_BELIEF = "retired_belief"
MEMORY_PROVENANCE_VALUES = frozenset({
    MEMORY_PROVENANCE_OBSERVED_FACT,
    MEMORY_PROVENANCE_INSTRUCTION,
    MEMORY_PROVENANCE_INFERENCE,
    MEMORY_PROVENANCE_TENTATIVE_PATTERN,
    MEMORY_PROVENANCE_APPROVED_BELIEF,
    MEMORY_PROVENANCE_RETIRED_BELIEF,
})

# Memory correction loop status values (D10)
MEMORY_CORRECTION_STATUS_CORRECTED = "corrected"
MEMORY_CORRECTION_STATUS_DISPUTED = "disputed"
MEMORY_CORRECTION_STATUS_RETIRED = "retired"
MEMORY_CORRECTION_STATUS_SUPERSEDED = "superseded"
MEMORY_CORRECTION_STATUS_DO_NOT_USE = "do_not_use"
MEMORY_CORRECTION_STATUSES = frozenset({
    MEMORY_CORRECTION_STATUS_CORRECTED,
    MEMORY_CORRECTION_STATUS_DISPUTED,
    MEMORY_CORRECTION_STATUS_RETIRED,
    MEMORY_CORRECTION_STATUS_SUPERSEDED,
    MEMORY_CORRECTION_STATUS_DO_NOT_USE,
})
# I3: All non-active statuses are excluded from reasoning.
# - corrected: user flagged as wrong; excluded until re-approved
# - disputed: user questions accuracy; excluded while under dispute
# - retired: permanently removed from use
# - superseded: replaced by a newer fact; old version must not surface
# - do_not_use: explicitly blocked
MEMORY_EXCLUDED_FROM_REASONING = frozenset({
    MEMORY_CORRECTION_STATUS_CORRECTED,
    MEMORY_CORRECTION_STATUS_DISPUTED,
    MEMORY_CORRECTION_STATUS_RETIRED,
    MEMORY_CORRECTION_STATUS_SUPERSEDED,
    MEMORY_CORRECTION_STATUS_DO_NOT_USE,
})


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
    provenance: str = "observed_fact"


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
    provenance: str = "observed_fact"
    correction_note: str = ""
    superseded_by: str = ""

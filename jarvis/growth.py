from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


GROWTH_SCHEMA_VERSION = "2026-05-11"


@dataclass(slots=True)
class GrowthDomainDefinition:
    id: str
    label: str
    description: str
    metric_keys: list[str] = field(default_factory=list)
    signal_types: list[str] = field(default_factory=list)
    source_adapter_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "metric_keys": list(self.metric_keys),
            "signal_types": list(self.signal_types),
            "source_adapter_ids": list(self.source_adapter_ids),
        }


@dataclass(slots=True)
class GrowthAdapterDefinition:
    id: str
    label: str
    description: str
    source_kind: str
    domain_ids: list[str] = field(default_factory=list)
    status: str = "planned"
    live: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "source_kind": self.source_kind,
            "domain_ids": list(self.domain_ids),
            "status": self.status,
            "live": self.live,
            "note": self.note,
        }


@dataclass(slots=True)
class GrowthLaneDefinition:
    id: str
    label: str
    description: str
    domain_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "domain_ids": list(self.domain_ids),
        }


@dataclass(slots=True)
class GrowthDomainSnapshot:
    id: str
    label: str
    description: str
    pressure: str
    confidence: str
    summary: str
    latest: str = ""
    latest_timestamp: str = ""
    live: bool = False
    source_adapter_id: str = ""
    source_count: int = 0
    metrics: dict[str, Any] = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)
    next_moves: list[str] = field(default_factory=list)
    truth_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "pressure": self.pressure,
            "confidence": self.confidence,
            "summary": self.summary,
            "latest": self.latest,
            "latest_timestamp": self.latest_timestamp,
            "live": self.live,
            "source_adapter_id": self.source_adapter_id,
            "source_count": self.source_count,
            "metrics": dict(self.metrics),
            "signals": list(self.signals),
            "next_moves": list(self.next_moves),
            "truth_note": self.truth_note,
        }


@dataclass(slots=True)
class GrowthLaneSnapshot:
    id: str
    label: str
    pressure: str
    confidence: str
    summary: str
    latest: str = ""
    latest_timestamp: str = ""
    domain_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "pressure": self.pressure,
            "confidence": self.confidence,
            "summary": self.summary,
            "latest": self.latest,
            "latest_timestamp": self.latest_timestamp,
            "domain_ids": list(self.domain_ids),
        }


@dataclass(slots=True)
class GrowthAdapterSnapshot:
    id: str
    label: str
    source_kind: str
    domain_ids: list[str]
    status: str
    live: bool
    record_count: int = 0
    latest_timestamp: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "source_kind": self.source_kind,
            "domain_ids": list(self.domain_ids),
            "status": self.status,
            "live": self.live,
            "record_count": self.record_count,
            "latest_timestamp": self.latest_timestamp,
            "note": self.note,
        }


def growth_schema_snapshot() -> dict[str, Any]:
    domains = [
        GrowthDomainDefinition(
            id="finance",
            label="Finance",
            description="Cash posture, runway, revenue-adjacent progress, and ROI lessons.",
            metric_keys=["recent_runs", "opportunity_theses", "roi_lessons"],
            signal_types=["opportunity-thesis", "roi-lesson", "wealth-run"],
            source_adapter_ids=["revenue", "opportunity-theses"],
        ),
        GrowthDomainDefinition(
            id="pipeline",
            label="Pipeline",
            description="Sales pipeline movement, project briefs, and implementation readiness.",
            metric_keys=["signals", "project_briefs", "implementation_plans"],
            signal_types=["pipeline-signal", "project-brief", "implementation-plan"],
            source_adapter_ids=["pipeline"],
        ),
        GrowthDomainDefinition(
            id="marketing",
            label="Marketing",
            description="Audience-facing momentum, campaign readiness, and market-facing visibility.",
            metric_keys=["queued_assets", "exported_assets", "live_assets", "audience_signals"],
            signal_types=["campaign-concept", "audience-signal", "content-performance"],
            source_adapter_ids=["content-output", "audience-growth"],
        ),
        GrowthDomainDefinition(
            id="content",
            label="Content",
            description="Operational content production state from queued through live.",
            metric_keys=["queued_assets", "scripted_assets", "exported_assets", "live_assets"],
            signal_types=["content-queue", "content-export", "content-live"],
            source_adapter_ids=["content-output"],
        ),
        GrowthDomainDefinition(
            id="experiments",
            label="Experiments",
            description="Leverage-building experiments, tests in flight, and recent findings.",
            metric_keys=["experiments_in_flight", "recent_runs", "roi_lessons"],
            signal_types=["experiment", "roi-lesson", "next-move"],
            source_adapter_ids=["experiments"],
        ),
        GrowthDomainDefinition(
            id="offers",
            label="Offers",
            description="Offer hypotheses, opportunity theses, and packaged next moves worth testing.",
            metric_keys=["tracked_offers", "recommended_focus", "project_briefs"],
            signal_types=["offer-hypothesis", "recommended-focus", "opportunity-thesis"],
            source_adapter_ids=["offers", "opportunity-theses"],
        ),
    ]
    adapters = [
        GrowthAdapterDefinition(
            id="revenue",
            label="Revenue Adapter",
            description="Canonical finance/revenue source adapter for cash posture and revenue-adjacent progress.",
            source_kind="wealth-workflows",
            domain_ids=["finance"],
            status="inferred",
            live=False,
            note="Currently inferred from local wealth workflows until live financial telemetry is wired.",
        ),
        GrowthAdapterDefinition(
            id="pipeline",
            label="Pipeline Adapter",
            description="Canonical pipeline source adapter for Catalyst signals, project briefs, and implementation plans.",
            source_kind="catalyst",
            domain_ids=["pipeline"],
            status="inferred",
            live=False,
            note="Currently inferred from local Catalyst artifacts instead of a CRM feed.",
        ),
        GrowthAdapterDefinition(
            id="content-output",
            label="Content Output Adapter",
            description="Canonical content operations adapter for queued, scripted, exported, and live assets.",
            source_kind="content-ops",
            domain_ids=["content", "marketing"],
            status="live-local",
            live=True,
            note="Local content operations are live inside JARVIS even though external distribution telemetry is still limited.",
        ),
        GrowthAdapterDefinition(
            id="audience-growth",
            label="Audience Growth Adapter",
            description="Canonical marketing telemetry adapter for audience growth and performance signals.",
            source_kind="audience-telemetry",
            domain_ids=["marketing"],
            status="planned",
            live=False,
            note="No live ad-platform or audience-growth connector is wired yet.",
        ),
        GrowthAdapterDefinition(
            id="experiments",
            label="Experiments Adapter",
            description="Canonical experiments adapter for leverage tests and outcome loops.",
            source_kind="wealth-workflows",
            domain_ids=["experiments"],
            status="inferred",
            live=False,
            note="Experiments are currently inferred from local wealth workflows and recommendation traces.",
        ),
        GrowthAdapterDefinition(
            id="offers",
            label="Offers Adapter",
            description="Canonical offers adapter for offer hypotheses and packaged recommendations.",
            source_kind="wealth-plus-catalyst",
            domain_ids=["offers"],
            status="inferred",
            live=False,
            note="Offers are currently inferred from opportunity theses and Catalyst focus recommendations.",
        ),
        GrowthAdapterDefinition(
            id="opportunity-theses",
            label="Opportunity Thesis Adapter",
            description="Canonical opportunity-thesis adapter for durable leverage ideas worth revisiting.",
            source_kind="wealth-workflows",
            domain_ids=["finance", "offers"],
            status="inferred",
            live=False,
            note="Opportunity theses are currently harvested from local wealth workflow memory.",
        ),
    ]
    lanes = [
        GrowthLaneDefinition(
            id="financial",
            label="Financial Independence",
            description="Finance, experiments, and offers that compound toward financial independence.",
            domain_ids=["finance", "experiments", "offers"],
        ),
        GrowthLaneDefinition(
            id="marketing",
            label="Content and Marketing Engine",
            description="Content output and market-facing momentum that turn ideas into audience movement.",
            domain_ids=["content", "marketing"],
        ),
        GrowthLaneDefinition(
            id="pipeline",
            label="Sales and Pipeline Posture",
            description="Pipeline movement and offer readiness across briefs, opportunities, and follow-up.",
            domain_ids=["pipeline", "offers"],
        ),
    ]
    return {
        "version": GROWTH_SCHEMA_VERSION,
        "domains": [item.to_dict() for item in domains],
        "adapters": [item.to_dict() for item in adapters],
        "lanes": [item.to_dict() for item in lanes],
        "pressure_levels": ["quiet", "warming", "active"],
        "notes": [
            "This schema defines the canonical telemetry contract even when some adapters are still inference-based.",
            "Live external finance, CRM, and audience connectors can populate the same domain and adapter ids later without changing consumers.",
        ],
    }

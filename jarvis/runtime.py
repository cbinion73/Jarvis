from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid

from .accounts import AccountRegistry
from .adaptation import AdaptationStore
from .assistant_core import AssistantCoreStore
from .agentic import AgentRegistry, BackgroundStateStore, BackgroundTaskScheduler, LifeAgentStudioStore, MemoryCurator
from .audit import ApprovalStore, AuditLog
from .briefing import build_morning_brief
from .catalyst import CatalystStore, CatalystSupport
from .chronicle import ChronicleStore, ChronicleSupport
from .config import AppConfig
from .content_ops import ContentOpsStore, ContentOpsSupport
from .executive import ExecutiveSupport
from .family_calendar import FamilyCalendarSupport
from .family import FamilyStore, FamilySupport
from .first_light import FirstLightStore
from .graphs import run_background_cycle_graph, run_party_mode_graph, run_response_graph, run_wealth_leverage_graph
from .google_workspace import GoogleWorkspaceSupport
from .growth import GrowthAdapterSnapshot, GrowthDomainSnapshot, GrowthLaneSnapshot, growth_schema_snapshot
from .home import HomeStore, HomeSupport
from .identity import IdentityRegistry
from .memory import MemoryStore, MemorySupport
from .models import ApprovalRequest, HouseholdProfile, RequestPlan, UserProfile
from .models import HouseholdSnapshot
from .openai_tasks import JarvisOpenAIClient, OpenAIResult
from .orchestrator import JarvisOrchestrator
from .openviking_context import OpenVikingSupport
from .perception import PerceptionStore, PerceptionSupport
from .permissions import PermissionEngine
from .security import SecurityStore, SecuritySupport
from .tutoring import TutoringStore, TutoringSupport
from .wealth import WealthLeverageStore, WealthLeverageSupport
from .workshop import WorkshopStore, WorkshopSupport


def _merge_unique(values: list[str], extras: list[str], limit: int = 6) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in [*values, *extras]:
        item = str(value).strip(" -\n\t")
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


@dataclass(slots=True)
class JarvisRuntime:
    config: AppConfig
    household: HouseholdProfile
    snapshot: HouseholdSnapshot
    orchestrator: JarvisOrchestrator
    audit_log: AuditLog
    approval_store: ApprovalStore
    openai_client: JarvisOpenAIClient
    executive_support: ExecutiveSupport
    chronicle_support: ChronicleSupport
    family_support: FamilySupport
    tutoring_support: TutoringSupport
    workshop_support: WorkshopSupport
    security_support: SecuritySupport
    home_support: HomeSupport
    perception_support: PerceptionSupport
    memory_support: MemorySupport
    openviking_support: OpenVikingSupport
    catalyst_support: CatalystSupport
    content_ops: ContentOpsSupport
    google_workspace: GoogleWorkspaceSupport
    family_calendar: FamilyCalendarSupport
    wealth_support: WealthLeverageSupport
    account_registry: AccountRegistry
    identity_registry: IdentityRegistry
    agent_registry: AgentRegistry
    life_agent_store: LifeAgentStudioStore
    background_scheduler: BackgroundTaskScheduler
    memory_curator: MemoryCurator
    first_light_store: FirstLightStore
    adaptation_store: AdaptationStore
    assistant_core_store: AssistantCoreStore
    service_role: str = "interactive"
    process_started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    process_id: int = field(default_factory=os.getpid)
    startup_build: dict[str, object] = field(default_factory=dict, repr=False)
    _snapshot_cache: dict[str, dict] = field(default_factory=dict, repr=False)
    _snapshot_cache_ttls: dict[str, int] = field(
        default_factory=lambda: {
            "dashboard": 30,
            "today_board": 30,
            "cadence_review": 30,
            "finance_review": 60,
            "finance_state": 60,
            "marketing_review": 60,
            "marketing_state": 60,
            "pipeline_review": 60,
            "pipeline_state": 60,
            "world_graph": 30,
            "vision_state": 30,
            "environment_status": 30,
            "cognitive": 30,
            "world_state": 30,
            "first_light": 90,
        },
        repr=False,
    )

    @classmethod
    def from_env(cls) -> "JarvisRuntime":
        config = AppConfig.from_env()
        household = config.load_household()
        permissions = PermissionEngine()
        orchestrator = JarvisOrchestrator(config, permissions)
        data_root = Path("data")
        openai_client = JarvisOpenAIClient(config)
        account_registry = AccountRegistry(household)
        identity_registry = IdentityRegistry(household)
        family_support = FamilySupport(config, openai_client, FamilyStore(data_root / "family"))
        tutoring_support = TutoringSupport(config, openai_client, TutoringStore(data_root / "tutoring"))
        workshop_support = WorkshopSupport(config, openai_client, WorkshopStore(data_root / "workshop"))
        security_support = SecuritySupport(config, openai_client, SecurityStore(data_root / "security"))
        home_support = HomeSupport(config, HomeStore(data_root / "home"))
        perception_support = PerceptionSupport(config, PerceptionStore(data_root / "perception"))
        memory_support = MemorySupport(config, MemoryStore(data_root / "memory"), identity_registry=identity_registry)
        openviking_support = OpenVikingSupport(config)
        catalyst_support = CatalystSupport(config, openai_client, CatalystStore(data_root / "catalyst"))
        content_ops = ContentOpsSupport(config, openai_client, ContentOpsStore(data_root / "content"))
        google_workspace = GoogleWorkspaceSupport(config)
        family_calendar = FamilyCalendarSupport()
        wealth_support = WealthLeverageSupport(
            WealthLeverageStore(data_root / "wealth"),
            openai_client,
        )
        agent_registry = AgentRegistry()
        life_agent_store = LifeAgentStudioStore(data_root / "agents")
        background_scheduler = BackgroundTaskScheduler(
            BackgroundStateStore(data_root / "agents"),
            agent_registry,
        )
        runtime = cls(
            config=config,
            household=household,
            snapshot=config.load_snapshot(),
            orchestrator=orchestrator,
            audit_log=AuditLog(data_root / "logs"),
            approval_store=ApprovalStore(data_root / "approvals"),
            openai_client=openai_client,
            executive_support=ExecutiveSupport(config, openai_client),
            chronicle_support=ChronicleSupport(
                config,
                openai_client,
                ChronicleStore(data_root / "chronicle"),
            ),
            family_support=family_support,
            tutoring_support=tutoring_support,
            workshop_support=workshop_support,
            security_support=security_support,
            home_support=home_support,
            perception_support=perception_support,
            memory_support=memory_support,
            openviking_support=openviking_support,
            catalyst_support=catalyst_support,
            content_ops=content_ops,
            google_workspace=google_workspace,
            family_calendar=family_calendar,
            wealth_support=wealth_support,
            account_registry=account_registry,
            identity_registry=identity_registry,
            agent_registry=agent_registry,
            life_agent_store=life_agent_store,
            background_scheduler=background_scheduler,
            memory_curator=MemoryCurator(),
            first_light_store=FirstLightStore(),
            adaptation_store=AdaptationStore(),
            assistant_core_store=AssistantCoreStore(),
            service_role=os.getenv("JARVIS_SERVICE_ROLE", "interactive").strip().lower() or "interactive",
        )
        runtime.startup_build = runtime._service_build_snapshot()
        runtime._record_service_runtime_startup()
        return runtime

    def get_actor(self, actor_name: str) -> UserProfile:
        actor_key = actor_name.strip().lower()
        if actor_key in self.household.users:
            return self.household.users[actor_key]
        for profile in self.household.users.values():
            if profile.display_name.lower() == actor_key:
                return profile
        raise KeyError(f"Unknown actor: {actor_name}")

    def _cache_key(self, surface: str, actor_name: str, **parts: object) -> str:
        suffix = "|".join(
            f"{key}={parts[key]}"
            for key in sorted(parts)
            if str(parts[key]).strip()
        )
        base = f"{surface}:{actor_name.strip().lower()}"
        return f"{base}|{suffix}" if suffix else base

    def _snapshot_cache_get(self, key: str, *, ttl_seconds: int) -> tuple[dict | None, dict]:
        now = time.monotonic()
        record = self._snapshot_cache.get(key)
        if not record:
            return None, {
                "cached": False,
                "cache_key": key,
                "ttl_seconds": ttl_seconds,
                "cached_at": "",
                "expires_at": "",
                "age_seconds": 0.0,
            }
        age_seconds = max(0.0, now - float(record.get("stored_at_monotonic", now)))
        metadata = {
            "cached": age_seconds <= ttl_seconds,
            "cache_key": key,
            "ttl_seconds": ttl_seconds,
            "cached_at": str(record.get("cached_at", "")),
            "expires_at": str(record.get("expires_at", "")),
            "age_seconds": round(age_seconds, 3),
        }
        if age_seconds > ttl_seconds:
            self._snapshot_cache.pop(key, None)
            return None, metadata
        payload = record.get("payload")
        return dict(payload) if isinstance(payload, dict) else payload, metadata

    def _snapshot_cache_put(self, key: str, payload: dict, *, ttl_seconds: int) -> dict:
        cached_at = datetime.now(timezone.utc)
        expires_at = cached_at + timedelta(seconds=ttl_seconds)
        self._snapshot_cache[key] = {
            "payload": dict(payload),
            "stored_at_monotonic": time.monotonic(),
            "cached_at": cached_at.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        return {
            "cached": False,
            "cache_key": key,
            "ttl_seconds": ttl_seconds,
            "cached_at": cached_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "age_seconds": 0.0,
        }

    def _persist_last_good_surface(self, key: str, payload: dict) -> None:
        self.assistant_core_store.save_surface_snapshot(key, payload)

    def _last_good_surface(self, key: str) -> dict | None:
        record = self.assistant_core_store.surface_snapshot(key)
        payload = record.get("payload") if isinstance(record, dict) else None
        if isinstance(payload, dict):
            return dict(payload)
        return None

    def _with_freshness(self, payload: dict, surface: str, metadata: dict) -> dict:
        result = dict(payload)
        existing = dict(result.get("freshness") or {})
        result["freshness"] = {
            **existing,
            "surface": surface,
            "cached": bool(metadata.get("cached")),
            "cache_key": str(metadata.get("cache_key", "")),
            "ttl_seconds": int(metadata.get("ttl_seconds", 0) or 0),
            "cached_at": str(metadata.get("cached_at", "")),
            "expires_at": str(metadata.get("expires_at", "")),
            "age_seconds": float(metadata.get("age_seconds", 0.0) or 0.0),
            "fallback": bool(metadata.get("fallback")),
        }
        if metadata.get("degraded"):
            result["degraded"] = dict(metadata["degraded"])
        return result

    def _cached_surface(self, surface: str, actor_name: str, builder, **parts: object) -> dict:
        ttl_seconds = int(self._snapshot_cache_ttls.get(surface, 30))
        key = self._cache_key(surface, actor_name, **parts)
        cached_payload, metadata = self._snapshot_cache_get(key, ttl_seconds=ttl_seconds)
        if cached_payload is not None:
            return self._with_freshness(cached_payload, surface, metadata)
        try:
            payload = builder()
        except Exception as exc:
            fallback = self._last_good_surface(key)
            if fallback is None:
                raise
            degraded = {
                "active": True,
                "reason": f"Live {surface.replace('_', ' ')} refresh failed.",
                "detail": str(exc),
                "source": "last-good-snapshot",
            }
            fallback_metadata = {
                "cached": True,
                "cache_key": key,
                "ttl_seconds": ttl_seconds,
                "cached_at": str((fallback.get("freshness") or {}).get("cached_at", "")),
                "expires_at": str((fallback.get("freshness") or {}).get("expires_at", "")),
                "age_seconds": float((fallback.get("freshness") or {}).get("age_seconds", 0.0) or 0.0),
                "fallback": True,
                "degraded": degraded,
            }
            return self._with_freshness(fallback, surface, fallback_metadata)
        self._persist_last_good_surface(key, payload)
        metadata = self._snapshot_cache_put(key, payload, ttl_seconds=ttl_seconds)
        return self._with_freshness(payload, surface, metadata)

    def _invalidate_snapshot_cache(self, actor_name: str = "", *, surfaces: tuple[str, ...] | None = None) -> None:
        actor_prefix = f":{actor_name.strip().lower()}" if actor_name.strip() else ""
        allowed_surfaces = set(surfaces or ())
        keys_to_remove: list[str] = []
        for key in self._snapshot_cache:
            surface = key.split(":", 1)[0]
            if allowed_surfaces and surface not in allowed_surfaces:
                continue
            if actor_prefix and actor_prefix not in key:
                continue
            keys_to_remove.append(key)
        for key in keys_to_remove:
            self._snapshot_cache.pop(key, None)

    def _is_degraded_payload(self, payload: dict | None) -> bool:
        if not isinstance(payload, dict):
            return False
        degraded = payload.get("degraded")
        freshness = payload.get("freshness")
        return bool(
            (isinstance(degraded, dict) and degraded.get("active"))
            or (isinstance(freshness, dict) and freshness.get("fallback"))
        )

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    def _service_build_paths(self) -> list[Path]:
        root = self._repo_root()
        return [
            root / "jarvis" / "runtime.py",
            root / "jarvis" / "service.py",
            root / "jarvis" / "voice_ui.py",
            root / "jarvis" / "main.py",
            root / "jarvis" / "assistant_core.py",
            root / "ops" / "install_launchd_services.sh",
            root / "ops" / "launchd" / "com.jarvis.runtime.plist.template",
            root / "ops" / "launchd" / "com.jarvis.assistant-autonomy.plist.template",
        ]

    def _service_build_snapshot(self) -> dict[str, object]:
        digest = hashlib.sha256()
        files: list[dict[str, object]] = []
        for path in self._service_build_paths():
            if not path.exists():
                continue
            stat = path.stat()
            relative = str(path.relative_to(self._repo_root()))
            digest.update(relative.encode("utf-8"))
            digest.update(str(int(stat.st_mtime_ns)).encode("utf-8"))
            digest.update(str(int(stat.st_size)).encode("utf-8"))
            digest.update(path.read_bytes())
            files.append(
                {
                    "path": relative,
                    "mtime_ns": int(stat.st_mtime_ns),
                    "size": int(stat.st_size),
                }
            )
        return {
            "fingerprint": digest.hexdigest(),
            "files": files,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _record_service_runtime_startup(self) -> None:
        if self.service_role not in {"runtime", "assistant-autonomy"}:
            return
        self.assistant_core_store.save_service_runtime(
            self.service_role,
            {
                "pid": int(self.process_id),
                "started_at": str(self.process_started_at),
                "cwd": str(Path.cwd()),
                "build_fingerprint": str(self.startup_build.get("fingerprint", "")),
                "build_generated_at": str(self.startup_build.get("generated_at", "")),
            },
        )

    def _service_probe(self, url: str) -> dict[str, object]:
        target = str(url).strip()
        if not target:
            return {"ok": False, "url": "", "detail": "No target configured."}
        try:
            request = urllib.request.Request(target, method="GET")
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return {
                "ok": True,
                "url": target,
                "payload": payload,
            }
        except Exception as exc:
            return {
                "ok": False,
                "url": target,
                "detail": str(exc),
            }

    def service_runtime_snapshot(self, *, include_probe: bool = True) -> dict:
        current_build = self._service_build_snapshot()
        startup_fingerprint = str(self.startup_build.get("fingerprint", ""))
        current_fingerprint = str(current_build.get("fingerprint", ""))
        startup_record = self.assistant_core_store.service_runtime_record(self.service_role) or {}
        role_records = {
            role: self.assistant_core_store.service_runtime_record(role)
            for role in ("runtime", "assistant-autonomy")
        }
        history = self.assistant_core_store.list_service_runtime_history(limit=12)
        service_plan = dict(self.identity_overview().get("service", {}))
        probe_url = str(service_plan.get("lan_url", "")).strip() or "http://127.0.0.1:8787/health"
        live_probe = self._service_probe(probe_url) if include_probe else {"ok": False, "url": probe_url, "detail": "probe skipped"}
        live_payload = dict(live_probe.get("payload", {})) if isinstance(live_probe.get("payload"), dict) else {}
        live_runtime = dict(live_payload.get("runtime", {})) if isinstance(live_payload.get("runtime"), dict) else {}
        live_fingerprint = str(live_runtime.get("build_fingerprint", ""))
        return {
            "role": self.service_role,
            "pid": int(self.process_id),
            "started_at": str(self.process_started_at),
            "current_time": datetime.now(timezone.utc).isoformat(),
            "cwd": str(Path.cwd()),
            "startup_record": startup_record,
            "startup_build": {
                "fingerprint": startup_fingerprint,
                "generated_at": str(self.startup_build.get("generated_at", "")),
            },
            "current_build": {
                "fingerprint": current_fingerprint,
                "generated_at": str(current_build.get("generated_at", "")),
                "file_count": len(list(current_build.get("files", []))),
            },
            "drift": {
                "startup_vs_disk": bool(startup_fingerprint and current_fingerprint and startup_fingerprint != current_fingerprint),
                "live_probe_vs_disk": bool(include_probe and live_fingerprint and current_fingerprint and live_fingerprint != current_fingerprint),
                "live_probe_vs_startup": bool(include_probe and live_fingerprint and startup_fingerprint and live_fingerprint != startup_fingerprint),
            },
            "live_probe": {
                "ok": bool(live_probe.get("ok")),
                "url": probe_url,
                "runtime": live_runtime,
                "detail": str(live_probe.get("detail", "")),
            },
            "roles": role_records,
            "restart_history": history,
        }

    def identity_overview(self) -> dict:
        return self.identity_registry.describe()

    def save_identity_member(self, payload: dict) -> dict:
        member = self.identity_registry.save_member(payload)
        self._invalidate_snapshot_cache()
        return {"ok": True, "member": member.to_dict(), "identity": self.identity_overview()}

    def save_identity_device(self, payload: dict) -> dict:
        device = self.identity_registry.save_device(payload)
        self._invalidate_snapshot_cache()
        return {"ok": True, "device": device.to_dict(), "identity": self.identity_overview()}

    def bind_identity_session(self, payload: dict) -> dict:
        result = self.identity_registry.bind_session_device(payload)
        persona_snapshot = None
        if result.get("resolved_actor_label"):
            persona_snapshot = self.build_persona_snapshot(
                str(result.get("resolved_actor_label", "")),
                device_id=str(result.get("device", {}).get("device_id", "")),
                refresh=True,
            )
        return {"ok": True, **result, "persona_snapshot": persona_snapshot, "identity": self.identity_overview()}

    def save_service_identity(self, payload: dict) -> dict:
        service = self.identity_registry.update_service(payload)
        self._invalidate_snapshot_cache()
        return {"ok": True, "service": service, "identity": self.identity_overview()}

    def runtime_service_status(self) -> dict:
        identity = self.identity_overview()
        service_plan = dict(identity.get("service", {}))
        launch_agents_root = Path.home() / "Library" / "LaunchAgents"
        runtime_plist = launch_agents_root / "com.jarvis.runtime.plist"
        openviking_plist = launch_agents_root / "com.jarvis.openviking.plist"
        assistant_plist = launch_agents_root / "com.jarvis.assistant-autonomy.plist"
        runtime_snapshot = self.service_runtime_snapshot()

        def plist_status(path: Path, label: str) -> dict:
            installed = path.exists()
            loaded = False
            detail = "not installed"
            pid = None
            last_exit_status = None
            try:
                result = subprocess.run(
                    ["launchctl", "list", label],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0 and result.stdout:
                    loaded = True
                    detail = "loaded"
                    for line in result.stdout.splitlines():
                        stripped = line.strip()
                        if stripped.startswith("\"PID\" ="):
                            try:
                                pid = int(stripped.split("=", 1)[1].strip().rstrip(";"))
                            except ValueError:
                                pid = None
                        elif stripped.startswith("\"LastExitStatus\" ="):
                            try:
                                last_exit_status = int(stripped.split("=", 1)[1].strip().rstrip(";"))
                            except ValueError:
                                last_exit_status = None
                elif installed:
                    detail = "installed but not loaded"
            except Exception as exc:
                detail = f"status unavailable: {exc}"
            return {
                "label": label,
                "installed": installed,
                "loaded": loaded,
                "path": str(path),
                "detail": detail,
                "pid": pid,
                "last_exit_status": last_exit_status,
            }

        return {
            "service_plan": service_plan,
            "runtime": plist_status(runtime_plist, "com.jarvis.runtime"),
            "openviking": plist_status(openviking_plist, "com.jarvis.openviking"),
            "assistant_autonomy": plist_status(assistant_plist, "com.jarvis.assistant-autonomy"),
            "service_runtime": runtime_snapshot,
            "health": {
                "jarvis": self.status(),
                "openviking": self.openviking_status(),
                "assistant_notifications": self.assistant_notifications("Chris", limit=6),
            },
            "lan_url": service_plan.get("lan_url", ""),
            "hostname": service_plan.get("hostname", "jarvis.local"),
        }

    def connected_devices_snapshot(self) -> dict:
        identity = self.identity_overview()
        members_by_id = {
            str(item.get("user_id", "")).strip().lower(): item
            for item in identity.get("members", [])
        }
        devices = list(identity.get("devices", []))
        devices.sort(key=lambda item: str(item.get("last_seen_at", "")), reverse=True)

        enriched_devices: list[dict[str, object]] = []
        mapped_count = 0
        shared_count = 0
        suggested_count = 0
        personal_count = 0
        unassigned_count = 0
        high_confidence_count = 0
        medium_confidence_count = 0
        low_confidence_count = 0

        for device in devices:
            owner_id = str(device.get("owner_user_id", "")).strip().lower()
            default_actor_id = str(device.get("default_actor_id", "")).strip().lower()
            shared = bool(device.get("shared", False))
            suggested_default = str(device.get("suggested_default_actor_id", "")).strip().lower()
            owner = members_by_id.get(owner_id)
            default_actor = members_by_id.get(default_actor_id)
            last_actor = members_by_id.get(str(device.get("last_actor_id", "")).strip().lower())
            mapped = bool(owner_id or default_actor_id)

            if shared:
                shared_count += 1
            else:
                personal_count += 1
            if mapped:
                mapped_count += 1
            else:
                unassigned_count += 1
            if suggested_default:
                suggested_count += 1

            if shared:
                posture = "shared-device"
            elif mapped:
                posture = "mapped"
            elif suggested_default:
                posture = "suggested-default-ready"
            else:
                posture = "unassigned"

            owner_confidence = self._device_owner_confidence_snapshot(device, members_by_id)
            confidence_label = str(owner_confidence.get("confidence", "low")).strip().lower()
            if confidence_label == "high":
                high_confidence_count += 1
            elif confidence_label == "medium":
                medium_confidence_count += 1
            else:
                low_confidence_count += 1

            enriched_devices.append(
                {
                    **device,
                    "owner_display_name": owner.get("display_name", "") if owner else "",
                    "default_actor_display_name": default_actor.get("display_name", "") if default_actor else "",
                    "last_actor_display_name": last_actor.get("display_name", "") if last_actor else "",
                    "has_fingerprint": bool(str(device.get("fingerprint", "")).strip()),
                    "mapped": mapped,
                    "posture": posture,
                    "owner_confidence": owner_confidence,
                }
            )

        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total": len(enriched_devices),
                "mapped": mapped_count,
                "unassigned": unassigned_count,
                "shared": shared_count,
                "personal": personal_count,
                "suggested_defaults": suggested_count,
                "high_confidence": high_confidence_count,
                "medium_confidence": medium_confidence_count,
                "low_confidence": low_confidence_count,
            },
            "devices": enriched_devices,
            "owners": identity.get("owners", []),
            "device_types": identity.get("device_types", []),
            "trust_levels": identity.get("trust_levels", []),
        }

    def _actor_member(self, actor: UserProfile):
        return self.identity_registry.member(actor.user_id)

    def _device_record(self, device_id: str) -> dict[str, object] | None:
        if not device_id:
            return None
        for item in self.identity_overview().get("devices", []):
            if str(item.get("device_id", "")).strip() == device_id.strip():
                return item
        return None

    def _confidence_label(self, score: int) -> str:
        if score >= 7:
            return "high"
        if score >= 4:
            return "medium"
        return "low"

    def _presence_signal_strength(self, state: str) -> tuple[int, str]:
        normalized = str(state or "").strip().lower()
        if normalized in {"home", "present", "here", "in-room"}:
            return 3, normalized or "present"
        if normalized in {"arriving", "nearby", "approaching", "home-boundary"}:
            return 2, normalized
        if normalized in {"away", "departed", "offline"}:
            return 0, normalized
        if normalized:
            return 1, normalized
        return 0, "unknown"

    def _device_owner_confidence_snapshot(
        self,
        device: dict[str, object],
        members_by_id: dict[str, dict[str, object]],
    ) -> dict[str, Any]:
        owner_id = str(device.get("owner_user_id", "")).strip().lower()
        default_actor_id = str(device.get("default_actor_id", "")).strip().lower()
        last_actor_id = str(device.get("last_actor_id", "")).strip().lower()
        suggested_default_actor_id = str(device.get("suggested_default_actor_id", "")).strip().lower()
        shared = bool(device.get("shared", False))
        score = 0
        evidence: list[str] = []

        likely_actor_id = owner_id or default_actor_id or last_actor_id or suggested_default_actor_id
        likely_actor = members_by_id.get(likely_actor_id, {})

        if owner_id:
            score += 4
            evidence.append("Owner is explicitly mapped.")
        if default_actor_id:
            score += 3
            evidence.append("Default actor is configured for this device.")
        if last_actor_id:
            score += 2
            evidence.append("Recent session history points to a known actor.")
        if suggested_default_actor_id and not default_actor_id:
            score += 1
            evidence.append("Recent session pattern suggests a default actor.")
        if str(device.get("fingerprint", "")).strip():
            score += 1
            evidence.append("A stable browser fingerprint is available.")

        age_bucket = self._age_bucket(str(device.get("last_seen_at", "")))
        if age_bucket == "fresh":
            score += 1
            evidence.append("The device was seen recently.")
        elif age_bucket == "aged" and score > 0:
            score = max(0, score - 1)
            evidence.append("The last device sighting is old.")

        if shared and score < 7:
            score = min(score, 3)
            evidence.append("Shared-device posture lowers owner certainty.")
        if not likely_actor_id:
            evidence.append("No owner, default actor, or recent actor is mapped yet.")

        return {
            "likely_actor_id": likely_actor_id,
            "likely_actor_display_name": str(likely_actor.get("display_name", "")).strip(),
            "confidence": self._confidence_label(score),
            "score": score,
            "shared": shared,
            "age_bucket": age_bucket,
            "evidence": evidence[:4],
        }

    def _likely_present_people_snapshot(self, perception: dict[str, object]) -> list[dict[str, Any]]:
        identity = self.identity_overview()
        members = list(identity.get("members", []))
        devices = list(identity.get("devices", []))
        actor_presence = dict(perception.get("actor_presence") or {})
        room_presence = dict(perception.get("room_presence") or {})
        microphones = list(perception.get("microphone_events") or [])

        likely_here: list[dict[str, Any]] = []
        for member in members:
            actor_id = str(member.get("user_id", "")).strip().lower()
            actor_name = str(member.get("display_name", "")).strip()
            if not actor_id or not actor_name:
                continue
            score = 0
            evidence: list[str] = []
            likely_room = ""

            presence_state = str(actor_presence.get(actor_name, "unknown"))
            state_score, state_label = self._presence_signal_strength(presence_state)
            score += state_score * 2
            if state_label != "unknown":
                evidence.append(f"Phone presence currently reads {state_label}.")

            primary_rooms = [str(item).strip() for item in member.get("primary_rooms", []) if str(item).strip()]
            morning_room = str(member.get("morning_room", "")).strip()
            candidate_rooms = primary_rooms + ([morning_room] if morning_room else [])
            for room in candidate_rooms:
                if room_presence.get(room):
                    score += 2
                    likely_room = likely_room or room
                    evidence.append(f"{room} is occupied and matches this person's usual space.")
                    break

            matching_devices = [
                item for item in devices
                if actor_id in {
                    str(item.get("owner_user_id", "")).strip().lower(),
                    str(item.get("default_actor_id", "")).strip().lower(),
                    str(item.get("last_actor_id", "")).strip().lower(),
                }
            ]
            matching_devices.sort(key=lambda item: str(item.get("last_seen_at", "")), reverse=True)
            if matching_devices:
                latest_device = matching_devices[0]
                device_age_bucket = self._age_bucket(str(latest_device.get("last_seen_at", "")))
                if device_age_bucket == "fresh":
                    score += 2
                    evidence.append("A mapped device was seen very recently.")
                elif device_age_bucket == "today":
                    score += 1
                    evidence.append("A mapped device was seen earlier today.")
                likely_room = likely_room or str(latest_device.get("room", "")).strip()

            recent_mic = next(
                (
                    event for event in microphones
                    if str(event.get("actor_hint", "")).strip().lower() == actor_name.lower()
                ),
                None,
            )
            if recent_mic:
                score += 1
                likely_room = likely_room or str(recent_mic.get("room", "")).strip()
                evidence.append("Recent microphone activity hinted at this speaker.")

            if score <= 0:
                continue
            likely_here.append(
                {
                    "actor_id": actor_id,
                    "actor": actor_name,
                    "confidence": self._confidence_label(score),
                    "score": score,
                    "presence_state": state_label,
                    "likely_room": likely_room,
                    "evidence": evidence[:4],
                }
            )

        likely_here.sort(key=lambda item: (int(item.get("score", 0)), item.get("actor", "")), reverse=True)
        return likely_here[:4]

    def _presence_event_history(
        self,
        actor: UserProfile,
        member,
        perception: dict[str, object],
        *,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        actor_name = actor.display_name.strip().lower()
        primary_rooms = set(str(item).strip().lower() for item in getattr(member, "primary_rooms", []) if str(item).strip())
        morning_room = str(getattr(member, "morning_room", "") or "").strip().lower()
        if morning_room:
            primary_rooms.add(morning_room)

        items: list[dict[str, Any]] = []
        for event in perception.get("phone_presence", []) or []:
            if str(event.get("actor", "")).strip().lower() != actor_name:
                continue
            state = str(event.get("state", "unknown")).strip() or "unknown"
            zone = str(event.get("zone", "")).strip() or "unknown"
            items.append(
                {
                    "timestamp": str(event.get("timestamp", "")).strip(),
                    "source": "phone",
                    "summary": f"Phone presence reported {state} near {zone}.",
                    "detail": str(event.get("detail", "")).strip(),
                }
            )

        for event in perception.get("microphone_events", []) or []:
            actor_hint = str(event.get("actor_hint", "")).strip().lower()
            room = str(event.get("room", "")).strip().lower()
            if actor_hint != actor_name and room not in primary_rooms:
                continue
            transcript = str(event.get("transcript", "")).strip()
            summary = f"Microphone activity in {room or 'unknown room'}."
            if transcript:
                summary = f"Heard in {room or 'unknown room'}: {transcript[:64]}"
            items.append(
                {
                    "timestamp": str(event.get("timestamp", "")).strip(),
                    "source": "microphone",
                    "summary": summary,
                    "detail": str(event.get("device_name", "")).strip(),
                }
            )

        for event in perception.get("presence_events", []) or []:
            room = str(event.get("room", "")).strip().lower()
            if room not in primary_rooms:
                continue
            occupied = bool(event.get("occupied"))
            summary = f"{room or 'room'} was marked {'occupied' if occupied else 'clear'}."
            items.append(
                {
                    "timestamp": str(event.get("timestamp", "")).strip(),
                    "source": "room",
                    "summary": summary,
                    "detail": str(event.get("detail", "")).strip(),
                }
            )

        items.sort(
            key=lambda item: self._parse_timestamp(str(item.get("timestamp", ""))) or datetime.fromtimestamp(0, timezone.utc),
            reverse=True,
        )
        return items[:limit]

    def _presence_identity_snapshot(
        self,
        actor: UserProfile,
        member,
        perception: dict[str, object],
        *,
        device_id: str = "",
    ) -> dict[str, Any]:
        actor_presence_map = dict(perception.get("actor_presence") or {})
        room_presence = dict(perception.get("room_presence") or {})
        actor_presence = str(actor_presence_map.get(actor.display_name, "unknown"))
        occupied_rooms = [room for room, occupied in room_presence.items() if occupied][:6]
        primary_rooms = [str(item).strip() for item in getattr(member, "primary_rooms", []) if str(item).strip()]
        morning_room = str(getattr(member, "morning_room", "") or "").strip()
        active_device = self._device_record(device_id)

        identity = self.identity_overview()
        members_by_id = {
            str(item.get("user_id", "")).strip().lower(): item
            for item in identity.get("members", [])
        }
        devices = list(identity.get("devices", []))
        device_confidences = [
            {
                "device_id": str(item.get("device_id", "")).strip(),
                "label": str(item.get("label", "")).strip(),
                "room": str(item.get("room", "")).strip(),
                **self._device_owner_confidence_snapshot(item, members_by_id),
            }
            for item in devices
            if actor.user_id in {
                str(item.get("owner_user_id", "")).strip().lower(),
                str(item.get("default_actor_id", "")).strip().lower(),
                str(item.get("last_actor_id", "")).strip().lower(),
                str(item.get("suggested_default_actor_id", "")).strip().lower(),
            }
        ]
        device_confidences.sort(key=lambda item: (int(item.get("score", 0)), str(item.get("label", ""))), reverse=True)

        active_device_confidence = (
            self._device_owner_confidence_snapshot(active_device, members_by_id)
            if active_device else {}
        )
        likely_here_now = self._likely_present_people_snapshot(perception)

        room_confidence: list[dict[str, Any]] = []
        presence_events = list(perception.get("presence_events") or [])
        candidate_rooms = _merge_unique(primary_rooms, ([morning_room] if morning_room else []) + occupied_rooms, limit=6)
        for room in candidate_rooms:
            last_event = next(
                (
                    event for event in presence_events
                    if str(event.get("room", "")).strip().lower() == room.strip().lower()
                ),
                None,
            )
            score = 1
            evidence: list[str] = []
            if room_presence.get(room):
                score += 3
                evidence.append("The latest room signal says this room is occupied.")
            else:
                evidence.append("There is no active occupied signal for this room right now.")
            if room in primary_rooms or room == morning_room:
                score += 1
                evidence.append("This room is part of the actor's known routine.")
            if last_event:
                age_bucket = self._age_bucket(str(last_event.get("timestamp", "")))
                if age_bucket in {"fresh", "today"}:
                    score += 1
                    evidence.append("The room signal is reasonably recent.")
                room_confidence.append(
                    {
                        "room": room,
                        "occupied": bool(room_presence.get(room)),
                        "confidence": self._confidence_label(score),
                        "score": score,
                        "age_bucket": age_bucket,
                        "evidence": evidence[:4],
                    }
                )
            else:
                room_confidence.append(
                    {
                        "room": room,
                        "occupied": bool(room_presence.get(room)),
                        "confidence": self._confidence_label(score),
                        "score": score,
                        "age_bucket": "unknown",
                        "evidence": evidence[:4],
                    }
                )

        active_resolution_score = 0
        active_resolution_evidence: list[str] = []
        resolved_actor_now = ""
        active_device_room = str((active_device or {}).get("room", "")).strip()

        if str(active_device_confidence.get("likely_actor_id", "")).strip().lower() == actor.user_id:
            active_resolution_score += 4
            resolved_actor_now = actor.display_name
            active_resolution_evidence.append("The active device is mapped back to this actor.")
        elif str(active_device_confidence.get("likely_actor_display_name", "")).strip():
            resolved_actor_now = str(active_device_confidence.get("likely_actor_display_name", "")).strip()
            active_resolution_evidence.append("The active device currently points to another likely actor.")

        presence_score, presence_state = self._presence_signal_strength(actor_presence)
        active_resolution_score += presence_score * 2
        if presence_state != "unknown":
            active_resolution_evidence.append(f"Phone presence currently reads {presence_state}.")

        likely_actor_entry = next(
            (item for item in likely_here_now if str(item.get("actor_id", "")).strip().lower() == actor.user_id),
            None,
        )
        if likely_actor_entry:
            active_resolution_score += max(1, int(likely_actor_entry.get("score", 0)) // 2)
            resolved_actor_now = resolved_actor_now or actor.display_name
            active_resolution_evidence.append("Household presence signals still make this actor plausible right now.")

        if active_device_room and active_device_room in set(primary_rooms + ([morning_room] if morning_room else [])):
            active_resolution_score += 1
            active_resolution_evidence.append("The active device is sitting in one of this actor's usual rooms.")

        if not resolved_actor_now and likely_here_now:
            resolved_actor_now = str(likely_here_now[0].get("actor", "")).strip()
        if not resolved_actor_now:
            resolved_actor_now = actor.display_name

        if active_resolution_score >= 7 and resolved_actor_now == actor.display_name:
            active_resolution_state = "matched"
        elif active_resolution_score >= 4:
            active_resolution_state = "plausible"
        else:
            active_resolution_state = "uncertain"

        return {
            "primary_rooms": primary_rooms,
            "morning_room": morning_room,
            "actor_presence": actor_presence,
            "occupied_rooms": occupied_rooms,
            "room_confidence": room_confidence[:6],
            "presence_event_history": self._presence_event_history(actor, member, perception, limit=8),
            "likely_here_now": likely_here_now,
            "active_user_resolution": {
                "target_actor": actor.display_name,
                "resolved_actor_now": resolved_actor_now,
                "device_id": device_id,
                "confidence": self._confidence_label(active_resolution_score),
                "score": active_resolution_score,
                "state": active_resolution_state,
                "evidence": active_resolution_evidence[:4],
            },
            "device_owner_confidence": {
                "active_device": {
                    "device_id": str((active_device or {}).get("device_id", "")).strip(),
                    "label": str((active_device or {}).get("label", "")).strip(),
                    **active_device_confidence,
                } if active_device else {},
                "relevant_devices": device_confidences[:4],
            },
        }

    def _persona_likely_needs(
        self,
        actor: UserProfile,
        member,
        latest_first_light: dict[str, object] | None,
        profile_facts: list[dict],
        perception: dict[str, object],
    ) -> list[str]:
        def safe_actions(actions: list[str]) -> list[str]:
            blocked = ("unlock", "purchase", "approve", "approval", "payment", "transfer", "security")
            return [item for item in actions if not any(word in item.lower() for word in blocked)]

        needs: list[str] = []
        morning_room = getattr(member, "morning_room", "") if member else ""
        if morning_room:
            occupied = bool((perception.get("room_presence") or {}).get(morning_room))
            if occupied:
                needs.append(f"{actor.display_name} is already in the usual morning room: {morning_room}.")
            else:
                needs.append(f"First useful handoff likely belongs in {morning_room}.")
        first20 = safe_actions(list((latest_first_light or {}).get("first_20_minutes", []) or []))
        if first20:
            needs.append("First Light is already leaning toward: " + "; ".join(first20[:3]))
        if actor.priorities:
            needs.append("Core priorities still pulling strongest: " + ", ".join(actor.priorities[:3]))
        actor_events = self._actor_calendar_events(actor, limit=3)
        if actor_events:
            needs.append("Near-term calendar pressure: " + "; ".join(str(item.get("summary", "")).strip() for item in actor_events[:2] if str(item.get("summary", "")).strip()))
        pending_approvals = self.list_pending_approvals()[:6]
        if pending_approvals:
            needs.append(f"There are {len(pending_approvals)} approval items waiting in the system.")
        if profile_facts:
            needs.append("Stable pattern memory is available for this profile and should bias recommendations.")
        if not needs:
            needs.append("This profile still needs more approved memory and First Light history before anticipation gets sharp.")
        return needs[:4]

    def _personalization_subject(self, viewer_name: str, subject_user_id: str = "") -> tuple[UserProfile, UserProfile]:
        viewer = self.get_actor(viewer_name)
        subject_id = subject_user_id.strip().lower() or viewer.user_id
        subject = self.get_actor(subject_id)
        if viewer.permissions != "adult" and viewer.user_id != subject.user_id:
            raise PermissionError("Child-safe personalization review only allows a child to view their own profile.")
        return viewer, subject

    def _personalization_snapshot(
        self,
        actor: UserProfile,
        *,
        member=None,
        profile_facts: list[dict] | None = None,
        device_id: str = "",
        first_light_history: list[dict] | None = None,
    ) -> dict[str, Any]:
        settings = self.adaptation_store.personalization_settings(actor.user_id)
        outcomes = self.assistant_core_store.outcome_history(actor.display_name, limit=80)
        tuning = self.recommendation_tuning_snapshot(actor.display_name, device_id=device_id)
        device_counts: dict[str, int] = {}
        timing_counts: dict[str, int] = {}
        domain_counts: dict[str, int] = {}
        for item in outcomes:
            device_key = str(item.get("device_id", "")).strip()
            if device_key:
                device_counts[device_key] = int(device_counts.get(device_key, 0) or 0) + 1
            timing_key = str(item.get("timing_quality", "")).strip().lower()
            if timing_key:
                timing_counts[timing_key] = int(timing_counts.get(timing_key, 0) or 0) + 1
            domain_key = str(item.get("domain", "")).strip().lower()
            if domain_key:
                domain_counts[domain_key] = int(domain_counts.get(domain_key, 0) or 0) + 1
        if first_light_history is None:
            first_light_history = [
                item for item in self.first_light_store.load().get("history", [])
                if str(item.get("user_id", "")).strip().lower() == actor.user_id
            ][-8:]
        facts = list(profile_facts or [])
        suppressed = {str(item).strip() for item in list(settings.get("suppressed_insights", []) or []) if str(item).strip()}
        top_device_id = max(device_counts, key=device_counts.get) if device_counts else ""
        top_device_label = ""
        if top_device_id:
            device = self._device_record(top_device_id)
            top_device_label = str((device or {}).get("label", "")).strip() or top_device_id
        dominant_domain = max(domain_counts, key=domain_counts.get) if domain_counts else ""
        first_light_times = [
            str(item.get("local_time", "")).strip()
            for item in first_light_history
            if str(item.get("local_time", "")).strip()
        ]
        latest_first_light_time = first_light_times[-1] if first_light_times else ""
        likely_rhythm = ""
        if len(first_light_times) >= 3:
            likely_rhythm = f"Morning briefings usually land around {latest_first_light_time or 'the same window'}."
        elif latest_first_light_time:
            likely_rhythm = f"The latest First Light rhythm landed around {latest_first_light_time}."
        summary = tuning.get("summary") or {}
        interrupt_delta = int(summary.get("interrupt_threshold_delta", 0) or 0)
        cooldown_delta = int(summary.get("cooldown_delta_minutes", 0) or 0)
        queue_bias = int(summary.get("queue_bias", 0) or 0)
        sample_size = int(summary.get("sample_size", 0) or 0)
        raw_insights = [
            {
                "insight_id": "briefing-rhythm",
                "title": "Briefing rhythm",
                "summary": likely_rhythm or "First Light history is still too sparse to lock a rhythm.",
                "confidence": "medium" if len(first_light_times) >= 3 else "low",
                "source": "first-light-history",
                "reversible": True,
            },
            {
                "insight_id": "interrupt-tolerance",
                "title": "Interrupt tolerance",
                "summary": (
                    "Recent outcomes support a slightly quieter surfacing posture."
                    if queue_bias > 0 or interrupt_delta > 0 or cooldown_delta > 0
                    else "Recent outcomes support the current balance between interrupting and queueing."
                ),
                "confidence": "medium" if sample_size >= 3 else "low",
                "source": "outcome-tuning",
                "reversible": True,
            },
            {
                "insight_id": "device-affinity",
                "title": "Device affinity",
                "summary": (
                    f"Recent interaction outcomes cluster most often around {top_device_label}."
                    if top_device_label
                    else "No device has enough outcome history yet to claim affinity."
                ),
                "confidence": "medium" if device_counts.get(top_device_id, 0) >= 2 else "low",
                "source": "device-outcomes",
                "reversible": True,
            },
            {
                "insight_id": "dominant-domain",
                "title": "Domain preference",
                "summary": (
                    f"Most recent learning pressure has come from the {dominant_domain} lane."
                    if dominant_domain
                    else "No single work lane dominates recent learning yet."
                ),
                "confidence": "medium" if domain_counts.get(dominant_domain, 0) >= 2 else "low",
                "source": "outcome-history",
                "reversible": True,
            },
        ]
        insights: list[dict[str, Any]] = []
        for item in raw_insights:
            insight_id = str(item.get("insight_id", "")).strip()
            if not insight_id:
                continue
            status = "suppressed" if insight_id in suppressed else ("active" if bool(settings.get("enabled", True)) else "paused")
            insights.append({**item, "status": status})
        active_insights = [item for item in insights if str(item.get("status", "")).strip() == "active"]
        rhythms = [
            str(item.get("summary", "")).strip()
            for item in active_insights
            if str(item.get("insight_id", "")).strip() == "briefing-rhythm" and str(item.get("summary", "")).strip()
        ]
        if member and str(getattr(member, "morning_room", "") or "").strip():
            rhythms.append(f"Morning room preference is still set to {str(getattr(member, 'morning_room', '')).strip()}.")
        learned_preferences = [
            str(item.get("summary", "")).strip()
            for item in facts[:3]
            if str(item.get("summary", "")).strip()
        ]
        if queue_bias > 0 or interrupt_delta > 0 or cooldown_delta > 0:
            learned_preferences.append("Lean quieter unless the signal is strong enough to justify interruption.")
        if top_device_label:
            learned_preferences.append(f"Favor {top_device_label} when choosing where to surface follow-ups.")
        history = self.adaptation_store.personalization_history(actor.user_id, limit=8)
        return {
            "settings": settings,
            "governance": {
                "visible": True,
                "reversible": True,
                "review_required": bool(settings.get("review_required", True)),
                "enabled": bool(settings.get("enabled", True)),
            },
            "signals": {
                "outcome_samples": len(outcomes),
                "profile_facts": len(facts),
                "first_light_runs": len(first_light_history),
                "device_samples": sum(device_counts.values()),
                "timing_mix": timing_counts,
            },
            "rhythms": rhythms[:4],
            "learned_preferences": learned_preferences[:5],
            "insights": insights,
            "history": history,
        }

    def update_personalization_settings(self, viewer_name: str, subject_user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        viewer, subject = self._personalization_subject(viewer_name, subject_user_id)
        if viewer.permissions != "adult":
            raise PermissionError("Only adult reviewers can change personalization governance.")
        settings = self.adaptation_store.update_personalization_settings(
            subject.user_id,
            updates,
            actor=viewer.display_name,
        )
        self._invalidate_snapshot_cache(subject.display_name, surfaces=("dashboard", "today_board", "cadence_review", "cognitive", "world_state"))
        persona = self.build_persona_snapshot(subject.display_name, refresh=True)
        return {"ok": True, "subject_user_id": subject.user_id, "settings": settings, "persona_snapshot": persona}

    def update_personalization_insight_status(
        self,
        viewer_name: str,
        subject_user_id: str,
        insight_id: str,
        status: str,
    ) -> dict[str, Any]:
        viewer, subject = self._personalization_subject(viewer_name, subject_user_id)
        if viewer.permissions != "adult":
            raise PermissionError("Only adult reviewers can change personalization insights.")
        insight = self.adaptation_store.update_personalization_insight(
            subject.user_id,
            insight_id,
            status,
            actor=viewer.display_name,
        )
        self._invalidate_snapshot_cache(subject.display_name, surfaces=("dashboard", "today_board", "cadence_review", "cognitive", "world_state"))
        persona = self.build_persona_snapshot(subject.display_name, refresh=True)
        return {"ok": True, "subject_user_id": subject.user_id, "insight": insight, "persona_snapshot": persona}

    def _sanitize_first20_actions(self, actions: list[str]) -> list[str]:
        blocked = ("unlock", "purchase", "approve", "approval", "payment", "transfer", "security")
        cleaned = [item.strip() for item in actions if item and item.strip()]
        safe = [item for item in cleaned if not any(word in item.lower() for word in blocked)]
        fallback = [
            "check unread emails and flag the two most time-sensitive",
            "review today’s departure checklist and stage backpacks, devices, slips, water, and folders",
            "pick the one important work block and protect it before inbox drift",
            "take a steady ten-minute pass at the highest-value draft or decision",
        ]
        merged = list(safe)
        for item in fallback:
            if item not in merged:
                merged.append(item)
        return merged[:4]

    def build_persona_snapshot(self, actor_name: str, *, device_id: str = "", refresh: bool = True) -> dict:
        actor = self.get_actor(actor_name)
        member = self._actor_member(actor)
        latest_first_light = self.first_light_store.latest_packet(actor.user_id) or {}
        first_light_history = [
            item for item in self.first_light_store.load().get("history", [])
            if str(item.get("user_id", "")).strip().lower() == actor.user_id
        ][-8:]
        profile_facts = self.memory_support.profile_facts(actor, subject_user_id=actor.user_id)[:8]
        perception = self.perception_support.perception_overview()
        owned_devices = [
            item for item in self.identity_overview().get("devices", [])
            if str(item.get("owner_user_id", "")).strip().lower() == actor.user_id
            or str(item.get("default_actor_id", "")).strip().lower() == actor.user_id
            or str(item.get("last_actor_id", "")).strip().lower() == actor.user_id
        ]
        active_device = self._device_record(device_id)
        stable_preferences = [str(item.get("summary", "")).strip() for item in profile_facts if str(item.get("summary", "")).strip()][:5]
        morning_pattern = {
            "briefing_style": getattr(member, "briefing_style", "first-light") if member else "first-light",
            "anticipation_style": getattr(member, "anticipation_style", "quietly proactive") if member else "quietly proactive",
            "morning_room": getattr(member, "morning_room", "") if member else "",
            "latest_first_light_local_time": str(latest_first_light.get("local_time", "")),
            "watch_line": str(latest_first_light.get("watch_line", "")),
        }
        voice_identity = {
            "preferred_voice": getattr(member, "preferred_voice", "") if member else "",
            "voice_aliases": list(getattr(member, "voice_aliases", []) or []),
            "source": "profile-backed",
            "biometric": False,
        }
        presence_identity = self._presence_identity_snapshot(actor, member, perception, device_id=device_id)
        personalization = self._personalization_snapshot(
            actor,
            member=member,
            profile_facts=profile_facts,
            device_id=device_id,
            first_light_history=first_light_history,
        )
        device_identity = {
            "active_device": active_device,
            "owned_devices": owned_devices,
            "suggested_defaults": [
                {
                    "device_id": item.get("device_id", ""),
                    "label": item.get("label", ""),
                    "suggested_default_actor_id": item.get("suggested_default_actor_id", ""),
                }
                for item in owned_devices
                if str(item.get("suggested_default_actor_id", "")).strip()
            ],
        }
        likely_needs = self._persona_likely_needs(actor, member, latest_first_light, profile_facts, perception)
        snapshot = {
            "user_id": actor.user_id,
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "voice_identity": voice_identity,
            "presence_identity": presence_identity,
            "personalization": personalization,
            "morning_pattern": morning_pattern,
            "device_identity": device_identity,
            "stable_preferences": stable_preferences,
            "signal_counts": {
                "profile_facts": len(profile_facts),
                "first_light_runs": len(
                    [
                        item for item in self.first_light_store.load().get("history", [])
                        if str(item.get("user_id", "")).strip().lower() == actor.user_id
                    ]
                ),
                "owned_devices": len(owned_devices),
                "personalization_insights": len(personalization.get("insights", [])),
            },
            "digital_twin": {
                "headline": (
                    f"{actor.display_name} is best served with "
                    f"{morning_pattern['briefing_style']} briefings and "
                    f"{morning_pattern['anticipation_style']} anticipation."
                ),
                "likely_next_needs": likely_needs,
                "stable_preferences": stable_preferences,
                "limits": [
                    "Voice identity is profile-backed and device-aware, not biometric.",
                    "Presence is only as good as the connected room and phone signals.",
                    "Active-user resolution is confidence-based and should not be treated as biometric proof.",
                ],
            },
        }
        return self.adaptation_store.record_profile(actor.user_id, snapshot)

    def morning_brief(self, actor_name: str) -> str:
        actor = self.get_actor(actor_name)
        base = build_morning_brief(self.household, actor)
        calendar_line = self.merged_calendar_brief(limit=3)
        strategic = self.daily_strategic_brief(actor.display_name)
        return f"{base} Calendar: {calendar_line} Strategic brief: {strategic}"

    def _timezone_name(self) -> str:
        return os.getenv("JARVIS_TIMEZONE") or os.getenv("TZ") or "America/New_York"

    def _local_now(self, timezone_name: str | None = None) -> datetime:
        return self.first_light_store.local_now(timezone_name or self._timezone_name())

    def _parse_clock(self, value: str, default_hour: int) -> tuple[int, int]:
        raw = str(value or "").strip()
        if ":" not in raw:
            return default_hour, 0
        hour_text, minute_text = raw.split(":", 1)
        try:
            hour = max(0, min(23, int(hour_text)))
            minute = max(0, min(59, int(minute_text)))
            return hour, minute
        except ValueError:
            return default_hour, 0

    def _quiet_hours_active(self, timezone_name: str | None = None) -> bool:
        local_now = self._local_now(timezone_name)
        start_hour, start_minute = self._parse_clock(getattr(self.household, "quiet_start", "22:00"), 22)
        end_hour, end_minute = self._parse_clock(getattr(self.household, "quiet_end", "06:00"), 6)
        current_minutes = local_now.hour * 60 + local_now.minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        if start_minutes == end_minutes:
            return False
        if start_minutes < end_minutes:
            return start_minutes <= current_minutes < end_minutes
        return current_minutes >= start_minutes or current_minutes < end_minutes

    def _actor_accounts(self, actor: UserProfile) -> list[dict]:
        accounts = self.google_workspace_summary().get("accounts", [])
        return [
            item for item in accounts
            if str((item.get("account") or {}).get("owner_user_id", "")).strip().lower() == actor.user_id
        ]

    def _actor_calendar_events(self, actor: UserProfile, limit: int = 8) -> list[dict]:
        events = self.merged_calendar_events(limit=20)
        actor_name = actor.display_name.lower()
        filtered = [
            item for item in events
            if actor_name in str(item.get("summary", "")).lower()
            or str(item.get("source", "")).lower() == "google"
        ]
        return filtered[:limit]

    def _first_light_deltas(
        self,
        actor: UserProfile,
        current_events: list[dict],
        unread_count: int,
        *,
        growth_state: dict | None = None,
        growth_lane_signals: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        latest = self.first_light_store.latest_packet(actor.user_id)
        world_events = self.assistant_core_store.list_world_events(actor.display_name, limit=3)
        growth_state = growth_state or {}
        growth_lane_signals = list(growth_lane_signals or [])
        def clean_labels(values: list[str], *, limit: int = 2) -> list[str]:
            cleaned: list[str] = []
            seen: set[str] = set()
            for raw in values:
                label = str(raw or "").strip()
                normalized = label.lower()
                if not label or "browser" in normalized:
                    continue
                if normalized in seen:
                    continue
                seen.add(normalized)
                cleaned.append(label)
                if len(cleaned) >= limit:
                    break
            return cleaned
        if not latest:
            deltas = ["This is the first First Light run for this profile, so today becomes the new baseline."]
            if world_events:
                newest = next((item for item in world_events if list(item.get("added_labels", []))), world_events[0])
                added = clean_labels(list(newest.get("added_labels", [])))
                if added:
                    deltas.append("New world signals are already visible: " + "; ".join(added))
            return deltas[:3]
        previous_titles = {str(item.get("summary", "")).strip() for item in latest.get("calendar_events", []) if str(item.get("summary", "")).strip()}
        current_titles = {str(item.get("summary", "")).strip() for item in current_events if str(item.get("summary", "")).strip()}
        new_titles = [title for title in current_titles if title not in previous_titles][:3]
        deltas: list[str] = []
        if new_titles:
            deltas.append("New on the calendar: " + "; ".join(new_titles))
        previous_unread = int(latest.get("unread_emails", 0) or 0)
        if unread_count != previous_unread:
            direction = "up" if unread_count > previous_unread else "down"
            deltas.append(f"Inbox pressure is {direction}: {unread_count} unread versus {previous_unread} last First Light.")
        if world_events:
            newest = next(
                (
                    item
                    for item in world_events
                    if list(item.get("added_labels", [])) or list(item.get("removed_labels", []))
                ),
                world_events[0],
            )
            added = clean_labels(list(newest.get("added_labels", [])))
            removed = clean_labels(list(newest.get("removed_labels", [])), limit=1)
            if added:
                deltas.append("World model picked up new pressure: " + "; ".join(added))
            elif removed:
                deltas.append("Some pressure fell away: " + "; ".join(removed))
        previous_growth_state = latest.get("growth_state") if isinstance(latest, dict) else {}
        previous_lane_pressures = {
            str(item.get("id", "")).strip().lower(): str(item.get("pressure", "quiet")).strip().lower()
            for item in list((previous_growth_state or {}).get("lanes", []))
            if str(item.get("id", "")).strip()
        }
        escalated_growth = [
            str(item.get("lane_label", "")).strip()
            for item in growth_lane_signals
            if bool(item.get("due_now"))
            or previous_lane_pressures.get(str(item.get("lane_id", "")).strip().lower(), "quiet")
            != str(item.get("pressure", "quiet")).strip().lower()
        ]
        if escalated_growth:
            deltas.append("Growth review wants attention in: " + "; ".join(_merge_unique([], escalated_growth, limit=2)))
        if not deltas:
            deltas.append("No major overnight change signals stood out versus the last First Light snapshot.")
        return deltas[:3]

    def _loop_guidance(self, actor: UserProfile, *, open_loops: dict | None = None) -> dict:
        open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=10)
        cognition = self.cognitive_snapshot(actor.display_name, include_graph=False, open_loops=open_loops)
        cadence = dict(cognition.get("cadence") or {})
        active_loop = next((item for item in list(cadence.get("loops", [])) if str(item.get("state", "")).strip() == "active"), None) or {}
        world_state = dict(cognition.get("world_state") or {})
        return {
            "phase": str(cadence.get("phase", "")),
            "active_loop": str(active_loop.get("label", cadence.get("suggested_loop", "Autonomy Sweep"))),
            "active_purpose": str(active_loop.get("purpose", cadence.get("rationale", ""))),
            "world_pressure": str(world_state.get("pressure", "steady")),
            "world_delta": dict(world_state.get("delta", {})) if isinstance(world_state.get("delta", {}), dict) else {},
        }

    def _growth_loop_guidance(
        self,
        actor: UserProfile,
        *,
        growth_state: dict | None = None,
        cadence: dict | None = None,
    ) -> dict:
        growth_state = growth_state or self.growth_state_snapshot(actor.display_name)
        cadence = cadence or self.cognitive_cadence_snapshot(actor.display_name)
        pressure = str((growth_state.get("summary") or {}).get("pressure", "quiet")).strip().lower()
        phase = str(cadence.get("phase", "watch")).strip().lower()
        next_moves = list(growth_state.get("next_moves", []))[:3]
        top_signals = list(growth_state.get("top_signals", []))[:3]

        label = "Growth Watch"
        summary = "No strong leverage signal is asking for attention right now."
        focus = next_moves or top_signals or ["Keep monitoring for the next credible leverage move."]
        if phase == "morning":
            label = "Morning Leverage Check"
            summary = (
                "Choose one leverage-bearing move before the day fragments."
                if pressure in {"active", "warming"}
                else "Protect the morning and keep growth work light unless a signal becomes clearer."
            )
        elif phase == "midday":
            label = "Midday Growth Review"
            summary = (
                "Check whether pipeline, content, or wealth experiments are drifting."
                if pressure in {"active", "warming"}
                else "Use midday for a quick drift check, then stay with the main day."
            )
        elif phase == "pre-transition":
            label = "Pre-Transition Opportunity Check"
            summary = "Before the day turns relational again, preserve one clear growth next step."
        elif phase == "evening":
            label = "Evening Leverage Review"
            summary = (
                "Collapse open leverage loops and leave tomorrow one compounding step closer."
                if pressure in {"active", "warming"}
                else "Keep the evening review light and capture only the next worthwhile move."
            )
        elif phase == "night":
            label = "Growth Quiet Watch"
            summary = "Quiet hours are for curation, not pushing growth work."

        return {
            "phase": phase,
            "label": label,
            "summary": summary,
            "pressure": pressure,
            "focus": focus,
        }

    def _growth_packet_for_lane(self, lane_id: str) -> str:
        normalized = str(lane_id or "").strip().lower()
        return {
            "financial": "finance",
            "pipeline": "pipeline",
            "marketing": "marketing",
        }.get(normalized, "review")

    def _growth_lane_operating_signal(
        self,
        actor_name: str,
        lane_id: str,
        *,
        growth_state: dict | None = None,
        finance_state: dict | None = None,
        pipeline_state: dict | None = None,
        marketing_state: dict | None = None,
    ) -> dict[str, Any]:
        growth_state = growth_state or self.growth_state_snapshot(actor_name)
        lane = next(
            (
                item
                for item in list(growth_state.get("lanes", []))
                if str(item.get("id", "")).strip().lower() == str(lane_id or "").strip().lower()
            ),
            {},
        )
        lane_id_normalized = str(lane.get("id", lane_id)).strip().lower()
        lane_label = str(lane.get("label", "Growth Lane")).strip() or "Growth Lane"
        packet = self._growth_packet_for_lane(lane_id_normalized)
        pressure = str(lane.get("pressure", "quiet")).strip().lower() or "quiet"
        next_moves = list(growth_state.get("next_moves", []))[:4]
        signal: dict[str, Any] = {
            "lane_id": lane_id_normalized,
            "lane_label": lane_label,
            "packet": packet,
            "pressure": pressure,
            "due_now": False,
            "high_pressure": False,
            "title": lane_label,
            "summary": str(lane.get("summary", "")).strip(),
            "why_now": (
                f"{lane_label} is {pressure}, so JARVIS should keep one leverage move legible."
                if pressure in {"active", "warming"}
                else f"{lane_label} is quiet enough to stay in the background for now."
            ),
            "next_action": "review the next leverage move",
            "recommended_next_move": str((next_moves[:1] or [""])[0]).strip(),
        }
        if lane_id_normalized == "financial":
            finance_state = finance_state or self.finance_state_snapshot(actor_name)
            weekly = dict(finance_state.get("weekly_review") or {})
            thresholds = dict(finance_state.get("thresholds") or {})
            warning_components = [
                str(component.get("summary", "")).strip()
                for component in [
                    thresholds.get("low_cash_warning") or {},
                    thresholds.get("unusual_spend") or {},
                    thresholds.get("goal_progress") or {},
                ]
                if str(component.get("status", "")).strip().lower() == "warning"
            ]
            due_now = bool(weekly.get("due")) or bool(warning_components)
            recommended = str(self.finance_review(actor_name).get("recommended_next_move", "")).strip()
            signal.update(
                {
                    "due_now": due_now,
                    "high_pressure": bool(warning_components),
                    "title": str(weekly.get("label", "")).strip() or lane_label,
                    "summary": warning_components[0] if warning_components else str(weekly.get("summary", "")).strip() or signal["summary"],
                    "why_now": (
                        warning_components[0]
                        if warning_components
                        else (
                            "Weekly money review is due, so JARVIS should put financial posture back in front of you."
                            if bool(weekly.get("due"))
                            else signal["why_now"]
                        )
                    ),
                    "next_action": "review the weekly money posture" if due_now else signal["next_action"],
                    "recommended_next_move": recommended or signal["recommended_next_move"],
                }
            )
        elif lane_id_normalized == "pipeline":
            pipeline_state = pipeline_state or self.pipeline_state_snapshot(actor_name)
            daily = dict(pipeline_state.get("daily_followup_loop") or {})
            weekly = dict(pipeline_state.get("weekly_review") or {})
            stalled = list(pipeline_state.get("stalled_opportunities") or [])
            recommended = list(pipeline_state.get("recommended_actions") or [])
            due_now = bool(daily.get("due")) or bool(weekly.get("due")) or bool(stalled)
            signal.update(
                {
                    "due_now": due_now,
                    "high_pressure": bool(stalled),
                    "title": str(daily.get("label", "")).strip() or lane_label,
                    "summary": (
                        f"{len(stalled)} stalled opportunity(ies) need attention before they cool further."
                        if stalled
                        else str(daily.get("summary", "")).strip()
                        or str(weekly.get("summary", "")).strip()
                        or signal["summary"]
                    ),
                    "why_now": (
                        f"{len(stalled)} stalled opportunity(ies) are sitting in the pipeline, so JARVIS should surface the next revenue move now."
                        if stalled
                        else (
                            "Daily pipeline follow-up is due, so JARVIS should put the next revenue move back in front of you."
                            if bool(daily.get("due"))
                            else signal["why_now"]
                        )
                    ),
                    "next_action": "refresh the next pipeline move" if due_now else signal["next_action"],
                    "recommended_next_move": str((recommended[:1] or [""])[0]).strip() or signal["recommended_next_move"],
                }
            )
        elif lane_id_normalized == "marketing":
            marketing_state = marketing_state or self.marketing_state_snapshot(actor_name)
            weekly = dict(marketing_state.get("weekly_review") or {})
            stale_campaigns = list(marketing_state.get("stale_campaigns") or [])
            recommended = list(marketing_state.get("recommended_actions") or [])
            due_now = bool(weekly.get("due")) or bool(stale_campaigns)
            signal.update(
                {
                    "due_now": due_now,
                    "high_pressure": bool(stale_campaigns),
                    "title": str(weekly.get("label", "")).strip() or lane_label,
                    "summary": (
                        f"{len(stale_campaigns)} campaign(s) are stale enough to refresh before momentum decays."
                        if stale_campaigns
                        else str(weekly.get("summary", "")).strip() or signal["summary"]
                    ),
                    "why_now": (
                        f"{len(stale_campaigns)} campaign(s) have gone stale, so JARVIS should bring marketing momentum back into view."
                        if stale_campaigns
                        else (
                            "Weekly marketing review is due, so JARVIS should surface the next audience-facing move."
                            if bool(weekly.get("due"))
                            else signal["why_now"]
                        )
                    ),
                    "next_action": "refresh the next campaign move" if due_now else signal["next_action"],
                    "recommended_next_move": str((recommended[:1] or [""])[0]).strip() or signal["recommended_next_move"],
                }
            )
        return signal

    def _cadence_completion_criteria(
        self,
        phase: str,
        *,
        open_loops: dict,
        growth_guidance: dict,
        assistant_inbox: dict,
        top_task: dict | None = None,
    ) -> list[str]:
        summary = dict(open_loops.get("summary", {}))
        waiting = int(summary.get("waiting_on_you", 0) or 0)
        revisit = int(summary.get("needs_revisit", 0) or 0)
        unread = int((assistant_inbox.get("summary") or {}).get("unread", 0) or 0)
        task_title = str((top_task or {}).get("title", "the top item")).strip() or "the top item"
        growth_focus = str((list(growth_guidance.get("focus", []))[:1] or ["the next leverage move"])[0]).strip() or "the next leverage move"
        if phase == "morning":
            return [
                "First Light is visible and the first 20 minutes are staged.",
                f"The morning blocker around {task_title} is either acted on or intentionally deferred.",
                "Assistant inbox pressure is understood before the day fragments.",
            ]
        if phase == "midday":
            return [
                "No aging item is quietly poisoning the afternoon.",
                f"The drift around {task_title} is either surfaced, deferred, or cleared.",
                f"{growth_focus} is either preserved or intentionally dropped for the rest of the day.",
            ]
        if phase == "pre-transition":
            return [
                f"The transition-heavy item around {task_title} is surfaced before the handoff.",
                "The next meaningful step is preserved across the transition.",
                "Approval and family pressure will not blindside the next room or relationship shift.",
            ]
        if phase == "evening":
            return [
                "Loose ends are either closed or explicitly carried into tomorrow.",
                f"The next unresolved item around {task_title} is no longer vague.",
                f"{growth_focus} is either captured for tomorrow or intentionally parked.",
            ]
        if phase == "night":
            return [
                "Unread assistant pressure is low enough that the system can stay quiet.",
                "Open loops are queued instead of interrupting people after hours.",
                "Learning and curation can proceed without creating new noise.",
            ]
        return [
            f"{waiting} waiting item(s) and {revisit} revisit item(s) are inside a governed loop.",
            "The next move is explicit enough that JARVIS does not need to guess.",
            f"Assistant inbox pressure is readable ({unread} unread).",
        ]

    def _cadence_outcome_summary(
        self,
        phase: str,
        *,
        open_loops: dict,
        growth_guidance: dict,
        assistant_inbox: dict,
    ) -> str:
        summary = dict(open_loops.get("summary", {}))
        waiting = int(summary.get("waiting_on_you", 0) or 0)
        revisit = int(summary.get("needs_revisit", 0) or 0)
        unread = int((assistant_inbox.get("summary") or {}).get("unread", 0) or 0)
        growth_focus = str((list(growth_guidance.get("focus", []))[:1] or ["the next leverage move"])[0]).strip() or "the next leverage move"
        if phase == "morning":
            return f"Morning loop is settled when the first 20 minutes are clear, {waiting} waiting item(s) feel intentional, and inbox pressure ({unread}) is understood."
        if phase == "midday":
            return f"Midday loop is healthy when aging pressure drops below {max(revisit, 1)} and {growth_focus} is either protected or consciously paused."
        if phase == "pre-transition":
            return f"Handoff loop is complete when the next move survives the transition and {waiting} waiting item(s) will not ambush family time."
        if phase == "evening":
            return f"Evening collapse is credible when {revisit} revisit item(s) are either closed or intentionally carried and {growth_focus} is captured cleanly."
        if phase == "night":
            return f"Night watch is complete when inbox pressure is quiet ({unread} unread) and the system can curate without interrupting."
        return f"JARVIS is watching {waiting} waiting item(s), {revisit} revisit item(s), and {unread} unread assistant item(s)."

    def _recent_cadence_history(self, actor_name: str, *, limit: int = 5) -> list[dict]:
        return self.assistant_core_store.list_cadence_history(actor_name, limit=limit)

    def _should_emit_cadence_notification(
        self,
        actor_name: str,
        *,
        phase: str,
        digest: str,
        current_phase_changed: bool,
    ) -> bool:
        if not phase:
            return False
        if current_phase_changed:
            return True
        latest = self.assistant_core_store.latest_cadence_record(actor_name, phase)
        if not latest:
            return True
        latest_generated = self._parse_timestamp(str(latest.get("generated_at", "")))
        if latest_generated is None:
            return True
        if str(latest.get("digest", "")).strip() != digest.strip():
            return True
        return latest_generated <= datetime.now(timezone.utc) - timedelta(hours=6)

    def _first_light_script(self, actor: UserProfile, context: dict) -> dict:
        member = self.identity_registry.member(actor.user_id)
        preferred_tone = member.preferred_tone if member else "calm and direct"
        briefing_style = member.briefing_style if member else "first-light"
        anticipation_style = member.anticipation_style if member else "quietly proactive"
        prompt = (
            f"You are JARVIS preparing the First Light protocol for {actor.display_name}. "
            f"Tone should be {preferred_tone}. "
            f"Use a {briefing_style} structure and a {anticipation_style} anticipation posture. "
            "Keep the first 20 minutes practical, low-risk, and human. "
            "Do not recommend unlocks, security actions, purchases, or other high-risk operations in First20. "
            "Return exactly four lines with these prefixes and nothing else: "
            "Opening: ... "
            "First20: action one | action two | action three | action four "
            "Formation: ... "
            "Watch: ..."
        )
        raw = self.openai_client.prompt_text(prompt, json.dumps(context, indent=2), max_output_tokens=220).strip()
        parsed = {"opening": "", "first20": [], "formation": "", "watch": ""}
        for line in raw.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key == "opening":
                parsed["opening"] = value
            elif key == "first20":
                parsed["first20"] = [item.strip() for item in value.split("|") if item.strip()][:4]
            elif key == "formation":
                parsed["formation"] = value
            elif key == "watch":
                parsed["watch"] = value
        return parsed

    def _build_first_light_packet(self, actor_name: str, *, device_id: str = "", timezone_name: str | None = None) -> dict:
        actor = self.get_actor(actor_name)
        timezone_name = timezone_name or self._timezone_name()
        local_now = self.first_light_store.local_now(timezone_name)
        accounts = self._actor_accounts(actor)
        unread_count = sum(int((item.get("counts") or {}).get("unread_emails", 0) or 0) for item in accounts)
        actor_events = self._actor_calendar_events(actor, limit=8)
        likely_meetings = self.likely_meetings(limit=4)
        departure = self.family_support.departure_checklist()
        strategic = self.daily_strategic_brief(actor.display_name)
        systems_note = self.cross_domain_synthesis_brief(actor.display_name, "first light for today")
        open_loops = self.unified_open_loops(actor.display_name, limit=10)
        assistant_inbox = self.assistant_notifications(actor.display_name, limit=4, unread_only=True)
        loop_guidance = self._loop_guidance(actor, open_loops=open_loops)
        growth_state = self.growth_state_snapshot(actor.display_name)
        growth_guidance = self._growth_loop_guidance(
            actor,
            growth_state=growth_state,
            cadence={"phase": loop_guidance.get("phase", "watch")},
        )
        growth_lane_signals = [
            self._growth_lane_operating_signal(
                actor.display_name,
                str(lane.get("id", "")).strip(),
                growth_state=growth_state,
            )
            for lane in list(growth_state.get("lanes", []))
            if str(lane.get("id", "")).strip() in {"financial", "pipeline", "marketing"}
        ]
        formation_themes = (self.chronicle_theme_summary(limit=6) or {}).get("themes", [])[:3]
        weather_summary = "Live weather is not connected yet."
        weather_truth_state = "unavailable"
        weather_detail = "Source unavailable; weather connector not live yet."
        if self.list_weather_advisories(limit=1):
            latest_weather = self.list_weather_advisories(limit=1)[0]
            weather_summary = str(latest_weather.get("recommendation") or latest_weather.get("current_weather") or weather_summary)
            weather_truth_state = "staged"
            weather_detail = "Source: staged advisory, not a live weather connector."
        approvals = self.list_pending_approvals()[:5]
        family_focus = self.snapshot.family_focus.get(actor.display_name, []) or self.snapshot.family_focus.get(actor.user_id, [])
        delta_lines = self._first_light_deltas(
            actor,
            actor_events,
            unread_count,
            growth_state=growth_state,
            growth_lane_signals=growth_lane_signals,
        )
        morning_criteria = self._cadence_completion_criteria(
            "morning",
            open_loops=open_loops,
            growth_guidance=growth_guidance,
            assistant_inbox=assistant_inbox,
            top_task=dict(open_loops.get("top_item") or {}),
        )
        morning_outcome = self._cadence_outcome_summary(
            "morning",
            open_loops=open_loops,
            growth_guidance=growth_guidance,
            assistant_inbox=assistant_inbox,
        )
        script_context = {
            "actor": actor.display_name,
            "local_time": local_now.isoformat(),
            "calendar_events": actor_events,
            "likely_meetings": likely_meetings,
            "unread_emails": unread_count,
            "family_focus": family_focus,
            "departure_checklist": departure,
            "strategic_brief": strategic,
            "systems_note": systems_note,
            "deltas": delta_lines,
            "formation_themes": formation_themes,
            "approvals": approvals,
            "weather_summary": weather_summary,
            "assistant_core": open_loops,
            "assistant_inbox": assistant_inbox,
            "loop_guidance": loop_guidance,
            "growth_state": growth_state,
            "growth_guidance": growth_guidance,
        }
        try:
            script = self._first_light_script(actor, script_context)
        except Exception:
            script = {
                "opening": "The day looks manageable if we protect the morning and sequence it cleanly.",
                "first20": ["Water", "Calendar scan", "One priority check", "Start cleanly"],
                "formation": "Move slower than the pressure wants.",
                "watch": "The day will reward sequencing more than speed.",
            }

        packet_id = str(uuid.uuid4())
        schedule_lines = [
            f"{item.get('summary', '(Untitled event)')} · {item.get('start', 'unknown time')}"
            for item in actor_events[:5]
        ] or ["No near-term schedule pressure is currently connected for this profile."]
        family_lines = family_focus[:4] + departure[:3]
        if not family_lines:
            family_lines = ["No explicit family friction signals are staged right now."]
        mission_lines = [strategic, systems_note]
        if loop_guidance.get("active_loop"):
            mission_lines.append(f"Active loop: {loop_guidance.get('active_loop')} - {loop_guidance.get('active_purpose')}")
        if loop_guidance.get("world_pressure") and loop_guidance.get("world_pressure") != "steady":
            mission_lines.append(f"World pressure is {loop_guidance.get('world_pressure')}, so JARVIS should bias toward live coordination.")
        if str(growth_guidance.get("pressure", "quiet")) in {"active", "warming"}:
            mission_lines.append(f"{growth_guidance.get('label')}: {growth_guidance.get('summary')}")
        if approvals:
            mission_lines.append(f"{len(approvals)} approval item(s) are pending.")
        unread_notifications = int((assistant_inbox.get("summary") or {}).get("unread", 0) or 0)
        if unread_notifications:
            mission_lines.append(f"{unread_notifications} assistant inbox item(s) are already waiting.")
        mission_lines.extend(list(open_loops.get("briefing_lines", []))[:2])
        assistant_inbox_items = list(assistant_inbox.get("items", []))
        assistant_inbox_details = [
            " · ".join(
                part
                for part in [
                    str(item.get("title", "")).strip(),
                    str(item.get("detail", "")).strip(),
                ]
                if part
            )
            for item in assistant_inbox_items
        ]
        first20 = self._sanitize_first20_actions(
            list(script.get("first20") or ["Water", "Calendar scan", "Protect the first meaningful block."])
        )
        spoken_summary = " ".join(
            [
                script.get("opening", ""),
                f"Schedule: {schedule_lines[0]}",
                f"Watch: {script.get('watch', '')}",
            ]
        ).strip()
        return {
            "packet_id": packet_id,
            "user_id": actor.user_id,
            "actor": actor.display_name,
            "device_id": device_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "local_time": local_now.isoformat(),
            "title": "First Light",
            "opening": script.get("opening", ""),
            "spoken_summary": spoken_summary,
            "what_changed": delta_lines,
            "first_20_minutes": first20,
            "formation_cue": script.get("formation", ""),
            "watch_line": script.get("watch", ""),
            "unread_emails": unread_count,
            "calendar_events": actor_events,
            "sections": [
                {
                    "id": "day-shape",
                    "title": "Day Shape",
                    "summary": script.get("opening", ""),
                    "details": delta_lines,
                    "truth_state": "interpreted",
                },
                {
                    "id": "weather",
                    "title": "Weather",
                    "summary": weather_summary,
                    "details": [weather_detail],
                    "truth_state": weather_truth_state,
                },
                {
                    "id": "schedule",
                    "title": "Schedule",
                    "summary": schedule_lines[0],
                    "details": schedule_lines[1:5],
                    "truth_state": "live" if actor_events else "connected-empty",
                },
                {
                    "id": "family",
                    "title": "Family",
                    "summary": family_lines[0],
                    "details": family_lines[1:6],
                    "truth_state": "mixed",
                },
                {
                    "id": "mission",
                    "title": "Mission",
                    "summary": strategic,
                    "details": mission_lines[1:4],
                    "truth_state": "interpreted",
                },
                {
                    "id": "assistant-core",
                    "title": "Assistant Core",
                    "summary": f"{open_loops.get('summary', {}).get('waiting_on_you', 0)} item(s) are waiting on you. {open_loops.get('summary', {}).get('needs_revisit', 0)} need a revisit.",
                    "details": list(open_loops.get("briefing_lines", []))[:4] or ["No assistant-core follow-up pressure is surfaced right now."],
                    "truth_state": "live",
                },
                {
                    "id": "growth-review",
                    "title": "Growth Review",
                    "summary": f"{growth_guidance.get('label', 'Growth Watch')} · {growth_guidance.get('pressure', 'quiet')}",
                    "details": [
                        growth_guidance.get("summary", "No strong growth guidance is staged right now."),
                        *list(growth_guidance.get("focus", []))[:3],
                    ],
                    "truth_state": "interpreted",
                },
                {
                    "id": "active-loop",
                    "title": "Active Loop",
                    "summary": f"{loop_guidance.get('active_loop', 'Autonomy Sweep')} · {loop_guidance.get('world_pressure', 'steady')}",
                    "details": [
                        loop_guidance.get("active_purpose", "JARVIS is maintaining the current operating loop."),
                        f"Completion: {morning_outcome}",
                        *[
                            f"New signal: {item}"
                            for item in list((loop_guidance.get("world_delta") or {}).get("added_labels", []))[:2]
                        ],
                    ] or ["No additional loop detail is available right now."],
                    "truth_state": "interpreted",
                },
                {
                    "id": "assistant-inbox",
                    "title": "Assistant Inbox",
                    "summary": (
                        f"{unread_notifications} unread assistant item(s) are staged."
                        if unread_notifications
                        else "No unread assistant inbox items are waiting right now."
                    ),
                    "details": assistant_inbox_details[:4] or ["No unread assistant inbox items are waiting right now."],
                    "truth_state": "live",
                },
                {
                    "id": "completion-criteria",
                    "title": "Completion Criteria",
                    "summary": morning_outcome,
                    "details": morning_criteria,
                    "truth_state": "interpreted",
                },
                {
                    "id": "formation",
                    "title": "Formation",
                    "summary": script.get("formation", ""),
                    "details": [
                        f"{item.get('theme', '')} · {item.get('count', 0)} mention(s)"
                        for item in formation_themes
                    ] or ["No strong formation theme is surfaced yet."],
                    "truth_state": "interpreted",
                },
            ],
        }

    def first_light_check(
        self,
        actor_name: str,
        *,
        device_id: str = "",
        force: bool = False,
        after_hour: int = 6,
        timezone_name: str | None = None,
    ) -> dict:
        def builder() -> dict:
            actor = self.get_actor(actor_name)
            zone_name = timezone_name or self._timezone_name()
            status = self.first_light_store.status(actor.user_id, zone_name, after_hour=after_hour)
            if not force and not status.get("eligible"):
                return {
                    "ok": True,
                    "eligible": False,
                    "actor": actor.display_name,
                    "reason": "already_presented" if status.get("already_presented_today") else "before_window",
                    "status": status,
                }
            packet = self._build_first_light_packet(actor.display_name, device_id=device_id, timezone_name=zone_name)
            if status.get("eligible"):
                self.first_light_store.mark_presented(actor.user_id, packet, zone_name)
                self.build_persona_snapshot(actor.display_name, device_id=device_id, refresh=True)
            elif force:
                self.build_persona_snapshot(actor.display_name, device_id=device_id, refresh=True)
            return {
                "ok": True,
                "eligible": True,
                "actor": actor.display_name,
                "packet": packet,
                "status": self.first_light_store.status(actor.user_id, zone_name, after_hour=after_hour),
            }

        if not force:
            return builder()
        return self._cached_surface(
            "first_light",
            actor_name,
            builder,
            device_id=device_id.strip(),
            force="true",
            timezone=timezone_name or self._timezone_name(),
            after_hour=after_hour,
        )

    def plan_request(self, actor_name: str, room: str, request: str) -> RequestPlan:
        actor = self.get_actor(actor_name)
        plan = self.orchestrator.route(actor, room, request)
        plan = self.tutoring_support.apply_child_boundaries(actor, plan)
        self.audit_log.log_plan(plan)
        if plan.needs_approval and plan.allowed:
            self.approval_store.add(
                ApprovalRequest(
                    request_id=plan.request_id,
                    actor=plan.actor,
                    room=plan.room,
                    request=plan.request,
                    action_class=plan.action_class.name,
                    second_factor_required=plan.second_factor_required,
                    status="pending",
                    rationale=plan.rationale,
                )
            )
        return plan

    def list_pending_approvals(self) -> list[dict]:
        return self.approval_store.list_pending()

    def approval_history(self) -> list[dict]:
        return self.approval_store.list_all()

    def status(self) -> list[dict]:
        items: list[dict] = []

        items.append(
            {
                "name": "openai-api",
                "ok": bool(self.config.openai_api_key),
                "state": "connected" if self.config.openai_api_key else "missing",
                "detail": "OpenAI API key is configured." if self.config.openai_api_key else "OPENAI_API_KEY is missing.",
            }
        )

        second_brain = self.openai_client.second_brain_status()
        second_ok = bool(second_brain.get("enabled") and second_brain.get("healthy") and second_brain.get("model_available"))
        items.append(
            {
                "name": "local-brain",
                "ok": second_ok,
                "state": "connected" if second_ok else ("configured" if second_brain.get("enabled") else "disabled"),
                "detail": (
                    f"{second_brain.get('provider', 'local')} · {second_brain.get('model', '--')} ready"
                    if second_ok
                    else f"{second_brain.get('provider', 'local')} · {second_brain.get('model', '--')} not ready"
                ),
            }
        )

        google_accounts = self.google_workspace_summary().get("accounts", [])
        connected_google = [entry for entry in google_accounts if entry.get("status", {}).get("connected")]
        items.append(
            {
                "name": "google-workspace",
                "ok": bool(connected_google),
                "state": "connected" if connected_google else "disconnected",
                "detail": (
                    f"{len(connected_google)} connected account(s): "
                    + ", ".join(
                        str(entry.get("account", {}).get("label") or entry.get("account", {}).get("owner_display_name") or "Google account")
                        for entry in connected_google
                    )
                    if connected_google
                    else "No Google accounts are currently connected."
                ),
            }
        )

        family_calendar = self.family_calendar_summary()
        family_ok = bool(family_calendar.get("configured")) and not family_calendar.get("error")
        items.append(
            {
                "name": "family-calendar",
                "ok": family_ok,
                "state": "connected" if family_ok else "disconnected",
                "detail": str(family_calendar.get("detail", "Family shared calendar is not configured.")),
            }
        )

        openviking = self.openviking_status()
        items.append(
            {
                "name": "openviking",
                "ok": bool(openviking.get("ok")),
                "state": "connected" if openviking.get("ok") else ("configured" if openviking.get("enabled") else "disabled"),
                "detail": str(openviking.get("detail", "")),
            }
        )

        home_live = self.home_support.adapter.live
        items.append(
            {
                "name": "home-assistant",
                "ok": home_live,
                "state": "connected" if home_live else "disconnected",
                "detail": (
                    "Home Assistant credentials are configured, but live verification is not yet surfaced here."
                    if home_live
                    else "Home Assistant is not connected."
                ),
            }
        )

        return items

    def recent_activity(self, limit: int = 25) -> list[dict]:
        responses = self.audit_log.list_recent(limit=limit, entry_type="response")
        if responses:
            return responses
        return self.audit_log.list_recent(limit=limit, entry_type="plan")

    def _assistant_action_confidence(self, policy: dict) -> str:
        action_class = str(policy.get("action_class", "")).strip().lower()
        if action_class in {"defer", "package"}:
            return "high"
        if action_class in {"refresh-brief", "prepare-summary"}:
            return "medium"
        if policy.get("allowed"):
            return "medium"
        return "low"

    def _assistant_action_result_summary(self, result: dict) -> str:
        if not isinstance(result, dict):
            return "Result unavailable."
        if result.get("deferred"):
            deferred = dict(result.get("deferred") or {})
            return f"Deferred until {str(deferred.get('until', '')).strip() or 'the next scheduled window'}."
        record = result.get("record")
        if isinstance(record, dict):
            if "workflow" in record and "lane_label" in record:
                return f"{str(record.get('workflow', '')).strip()} completed for {str(record.get('lane_label', '')).strip()}."
            if "ok" in record and "record" in record:
                inner = dict(record.get("record") or {})
                status = str(inner.get("status", "")).strip()
                if status:
                    return f"Updated record status to {status}."
                return "Action completed and the record updated."
            message = str(record.get("message", "")).strip()
            if message:
                return message
            inner_record = dict(record.get("record") or {})
            status = str(inner_record.get("status", "")).strip()
            if status:
                return f"Updated record status to {status}."
        if result.get("ok") is True:
            return "Action completed successfully."
        return "Action did not complete cleanly."

    def _assistant_action_succeeded(self, result: dict) -> bool:
        if not isinstance(result, dict):
            return False
        if result.get("ok") is False:
            return False
        record = result.get("record")
        if isinstance(record, dict) and record.get("ok") is False:
            return False
        return True

    def _notification_timing_quality(self, record: dict, status: str) -> str:
        normalized_status = str(status or "").strip().lower()
        created_at = self._parse_timestamp(str(record.get("created_at", "")).strip())
        surfaced_at = self._parse_timestamp(str(record.get("surfaced_at", "")).strip()) or created_at
        event_at = self._parse_timestamp(
            str(
                record.get("opened_at", "")
                or record.get("acted_at", "")
                or record.get("ignored_at", "")
                or record.get("expired_at", "")
                or record.get("updated_at", "")
            ).strip()
        )
        if surfaced_at is None or event_at is None:
            return ""
        delay_minutes = max(0, int((event_at - surfaced_at).total_seconds() // 60))
        if normalized_status == "opened":
            if delay_minutes <= 15:
                return "right-time"
            if delay_minutes >= 90:
                return "late"
            return "acceptable"
        if normalized_status == "acted":
            if delay_minutes <= 30:
                return "right-time"
            if delay_minutes >= 180:
                return "late"
            return "acceptable"
        if normalized_status == "ignored":
            if delay_minutes <= 15:
                return "too-early"
            return "not-useful"
        if normalized_status == "expired":
            return "too-late"
        if normalized_status == "surfaced":
            return "queued"
        return ""

    def _recommendation_tuning_profile(
        self,
        actor_name: str,
        *,
        domain: str = "",
        device_id: str = "",
    ) -> dict[str, Any]:
        outcomes = self.assistant_core_store.outcome_history(actor_name, limit=240)
        domain_key = str(domain or "").strip().lower()
        device_key = str(device_id or "").strip()

        def _score(records: list[dict[str, Any]]) -> dict[str, Any]:
            if not records:
                return {
                    "sample_size": 0,
                    "opened": 0,
                    "acted": 0,
                    "ignored": 0,
                    "expired": 0,
                    "right_time": 0,
                    "too_early": 0,
                    "too_late": 0,
                    "acceptable": 0,
                    "interrupt_threshold_delta": 0,
                    "cooldown_delta_minutes": 0,
                    "queue_bias": 0,
                }
            stats = {
                "sample_size": len(records),
                "opened": 0,
                "acted": 0,
                "ignored": 0,
                "expired": 0,
                "right_time": 0,
                "too_early": 0,
                "too_late": 0,
                "acceptable": 0,
            }
            for item in records:
                status = str(item.get("status", "")).strip().lower()
                timing = str(item.get("timing_quality", "")).strip().lower()
                if status in stats:
                    stats[status] += 1
                if timing == "right-time":
                    stats["right_time"] += 1
                elif timing in {"too-early", "not-useful"}:
                    stats["too_early"] += 1
                elif timing in {"too-late", "late"}:
                    stats["too_late"] += 1
                elif timing == "acceptable":
                    stats["acceptable"] += 1
            interrupt_threshold_delta = 0
            cooldown_delta_minutes = 0
            queue_bias = 0
            if stats["sample_size"] >= 2:
                if stats["ignored"] + stats["too_early"] >= max(2, stats["sample_size"] // 2):
                    interrupt_threshold_delta += 1
                    cooldown_delta_minutes += 30
                    queue_bias += 1
                if stats["expired"] + stats["too_late"] >= max(2, stats["sample_size"] // 3):
                    cooldown_delta_minutes -= 15
                    interrupt_threshold_delta -= 1
                if stats["acted"] + stats["right_time"] >= max(2, stats["sample_size"] // 2):
                    interrupt_threshold_delta -= 1
                if stats["opened"] >= max(2, stats["sample_size"] // 2):
                    cooldown_delta_minutes -= 10
            stats["interrupt_threshold_delta"] = max(-2, min(2, interrupt_threshold_delta))
            stats["cooldown_delta_minutes"] = max(-30, min(90, cooldown_delta_minutes))
            stats["queue_bias"] = max(0, min(2, queue_bias))
            return stats

        actor_records = [
            item
            for item in outcomes
            if str(item.get("source", "")).strip().lower() in {"notification", "task-action", "assistant-action"}
        ]
        domain_records = [
            item for item in actor_records if not domain_key or str(item.get("domain", "")).strip().lower() == domain_key
        ]
        device_records = [
            item for item in domain_records if not device_key or str(item.get("device_id", "")).strip() == device_key
        ]
        actor_stats = _score(actor_records)
        domain_stats = _score(domain_records)
        device_stats = _score(device_records)
        interrupt_delta = actor_stats["interrupt_threshold_delta"] + domain_stats["interrupt_threshold_delta"] + device_stats["interrupt_threshold_delta"]
        cooldown_delta = actor_stats["cooldown_delta_minutes"] + domain_stats["cooldown_delta_minutes"] + device_stats["cooldown_delta_minutes"]
        queue_bias = actor_stats["queue_bias"] + domain_stats["queue_bias"] + device_stats["queue_bias"]
        return {
            "actor": actor_name,
            "domain": domain_key,
            "device_id": device_key,
            "sample_size": int(actor_stats["sample_size"] + domain_stats["sample_size"] + device_stats["sample_size"]),
            "actor_profile": actor_stats,
            "domain_profile": domain_stats,
            "device_profile": device_stats,
            "interrupt_threshold_delta": max(-3, min(3, interrupt_delta)),
            "cooldown_delta_minutes": max(-45, min(120, cooldown_delta)),
            "queue_bias": max(0, min(3, queue_bias)),
        }

    def _parse_timestamp(self, value: str) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _run_local_probe(self, command: list[str], *, timeout: int = 3) -> str:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except Exception:
            return ""
        if result.returncode != 0 and not result.stdout.strip():
            return ""
        return result.stdout.strip()

    def _age_bucket(self, timestamp: str) -> str:
        parsed = self._parse_timestamp(timestamp)
        if parsed is None:
            return "unknown"
        delta = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
        hours = delta.total_seconds() / 3600
        if hours < 6:
            return "fresh"
        if hours < 24:
            return "today"
        if hours < 72:
            return "stale"
        return "aged"

    def _approval_threshold_for_domain(self, domain: str) -> dict:
        thresholds = {
            "family": {"level": "review-before-send", "summary": "Family-facing changes should be staged and reviewed before sending."},
            "workshop": {"level": "review-before-external", "summary": "Workshop work can be staged locally, but external vendor actions need approval."},
            "memory": {"level": "review-sensitive", "summary": "Sensitive or personal learning proposals should be reviewed before they become durable memory."},
            "content": {"level": "review-before-publish", "summary": "Content can be developed automatically, but live publishing should be explicit."},
            "growth": {"level": "review-before-commit", "summary": "Growth work can be monitored and staged automatically, but commitments and spend still deserve explicit review."},
            "approvals": {"level": "decision-required", "summary": "This item is waiting on a direct yes or no decision."},
        }
        return thresholds.get(domain, {"level": "review-as-needed", "summary": "JARVIS may stage this work, then surface it for review when appropriate."})

    def _task_lane_for_domain(self, domain: str) -> dict:
        lanes = {
            "family": {"owner_agent": "Pepper", "lane": "household-execution"},
            "workshop": {"owner_agent": "Rocket", "lane": "fabrication-and-vendors"},
            "memory": {"owner_agent": "Vision", "lane": "memory-governance"},
            "content": {"owner_agent": "Veronica", "lane": "content-operations"},
            "growth": {"owner_agent": "Black Panther", "lane": "wealth-and-growth"},
            "approvals": {"owner_agent": "Nick Fury", "lane": "decision-command"},
        }
        return lanes.get(domain, {"owner_agent": "JARVIS", "lane": "general-operations"})

    def _suggested_packet_for_item(self, item: dict | None) -> str:
        item = dict(item or {})
        domain = str(item.get("domain", "")).strip().lower()
        suggested = str(item.get("suggested_packet", "")).strip().lower()
        if suggested:
            return suggested
        if domain == "growth":
            return self._growth_packet_for_lane(str(item.get("growth_lane_id", "")).strip())
        return "tasks"

    def _notification_policy_for_item(self, item: dict, *, actor_name: str = "Chris", device_id: str = "") -> dict:
        domain = str(item.get("domain", "")).strip().lower()
        status = str(item.get("status", "")).strip().lower()
        needs_revisit = bool(item.get("needs_revisit"))
        tuning = self._recommendation_tuning_profile(actor_name, domain=domain, device_id=device_id)
        if domain == "content":
            policy = {
                "severity": "low",
                "priority_class": "quiet",
                "delivery_mode": "queue-only",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 72,
                "summary": "Content packaging is quiet background work unless it reaches a publish decision.",
            }
        elif domain == "memory":
            policy = {
                "severity": "low",
                "priority_class": "quiet",
                "delivery_mode": "queue-only",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 72,
                "summary": "Memory governance stays in the assistant queue until you deliberately review it.",
            }
        elif domain == "growth":
            due_now = bool(item.get("growth_review_due"))
            high_pressure = bool(item.get("growth_high_pressure"))
            summary = str(item.get("growth_signal_summary", "")).strip() or "Growth work should surface when leverage-bearing review loops are due or stale."
            policy = {
                "severity": "high" if high_pressure else ("normal" if due_now or needs_revisit else "low"),
                "priority_class": "interrupt-worthy" if high_pressure else ("normal" if due_now or needs_revisit else "quiet"),
                "delivery_mode": "browser-eligible" if high_pressure or due_now or needs_revisit else "queue-only",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 24 if due_now else 48,
                "summary": summary,
            }
        elif domain == "approvals":
            policy = {
                "severity": "high" if status in {"pending", "pending-approval"} else "normal",
                "priority_class": "interrupt-worthy" if status in {"pending", "pending-approval"} else "normal",
                "delivery_mode": "browser-eligible",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 24,
                "summary": "Approvals can alert you during active hours, but quiet hours still suppress interruptions.",
            }
        elif domain in {"family", "workshop"} and needs_revisit:
            policy = {
                "severity": "normal",
                "priority_class": "normal",
                "delivery_mode": "browser-eligible",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 36,
                "summary": "Aged family and workshop follow-up can interrupt during active hours, then fall back to the inbox overnight.",
            }
        else:
            policy = {
                "severity": "normal",
                "priority_class": "normal",
                "delivery_mode": "queue-only",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 48,
                "summary": "This follow-up will stay in the assistant queue until JARVIS has a better moment to surface it.",
            }
        if tuning.get("queue_bias", 0) >= 2 and domain not in {"approvals"}:
            policy["delivery_mode"] = "queue-only"
            if str(policy.get("priority_class", "normal")).strip().lower() == "normal":
                policy["priority_class"] = "quiet"
        stale_after_hours = int(policy.get("stale_after_hours", 48) or 48)
        cooldown_delta = int(tuning.get("cooldown_delta_minutes", 0) or 0)
        if cooldown_delta >= 45:
            stale_after_hours += 12
        elif cooldown_delta <= -20:
            stale_after_hours = max(12, stale_after_hours - 12)
        policy["stale_after_hours"] = max(12, min(96, stale_after_hours))
        profile_bits = []
        if int(tuning.get("domain_profile", {}).get("sample_size", 0) or 0) > 0:
            profile_bits.append(f"domain sample {int(tuning['domain_profile']['sample_size'])}")
        if device_id.strip() and int(tuning.get("device_profile", {}).get("sample_size", 0) or 0) > 0:
            profile_bits.append(f"device sample {int(tuning['device_profile']['sample_size'])}")
        policy["tuning"] = tuning
        if profile_bits:
            policy["summary"] = f"{str(policy.get('summary', '')).strip()} Learned tuning: {'; '.join(profile_bits)}."
        return policy

    def _surfacing_cooldown_minutes(self, *, status: str, domain: str, cadence_phase: str, browser_interrupt: bool, actor_name: str = "Chris", device_id: str = "") -> int:
        normalized_status = str(status or "").strip().lower()
        normalized_domain = str(domain or "").strip().lower()
        normalized_phase = str(cadence_phase or "").strip().lower()
        if normalized_status == "ignored":
            base = 240
        elif normalized_status == "opened":
            base = 120
        elif normalized_status == "surfaced":
            base = 60 if browser_interrupt else 90
        elif normalized_status == "unseen":
            base = 20 if browser_interrupt else 45
        elif normalized_domain == "growth":
            base = 120
        elif normalized_phase in {"evening", "night"}:
            base = 120
        else:
            base = 45
        tuning = self._recommendation_tuning_profile(actor_name, domain=normalized_domain, device_id=device_id)
        return max(15, min(360, base + int(tuning.get("cooldown_delta_minutes", 0) or 0)))

    def _compose_why_this_surfaced_now(
        self,
        item: dict,
        *,
        policy: dict,
        cadence_phase: str,
        world_state: dict | None = None,
        growth_state: dict | None = None,
        quiet_hours_active: bool = False,
        browser_interrupt: bool = False,
    ) -> str:
        domain = str(item.get("domain", "general")).strip().lower() or "general"
        parts: list[str] = []
        proactive_reason = str(item.get("proactive_reason", "")).strip()
        if proactive_reason:
            parts.append(proactive_reason)
        phase_label = {
            "morning": "Morning operating time rewards timely follow-through.",
            "midday": "Midday is a good window to correct drift before the day fragments.",
            "pre-transition": "The pre-transition window is better for clearing handoff risk now than later.",
            "evening": "Evening pressure is best handled by collapsing open loops instead of letting them roll over.",
            "night": "Night watch should stay quiet unless the system needs to preserve tomorrow.",
        }.get(str(cadence_phase or "").strip().lower(), "")
        if phase_label:
            parts.append(phase_label)
        world_pressure = str((world_state or {}).get("pressure", "steady")).strip().lower()
        if world_pressure in {"changed", "shifting"}:
            parts.append(f"The world model is {world_pressure}, so this lane has more timing sensitivity than usual.")
        growth_pressure = str(((growth_state or {}).get("summary") or {}).get("pressure", "quiet")).strip().lower()
        if domain == "growth" and growth_pressure in {"warming", "active"}:
            parts.append(f"Growth pressure is {growth_pressure}, so leverage work deserves a fresh look.")
        if quiet_hours_active and not browser_interrupt:
            parts.append("Quiet hours are active, so JARVIS queued this instead of interrupting.")
        elif browser_interrupt:
            parts.append("This crossed the current interrupt threshold for an active-hours nudge.")
        summary = str(policy.get("summary", "")).strip()
        if summary:
            parts.append(summary)
        merged: list[str] = []
        seen: set[str] = set()
        for part in parts:
            normalized = part.strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(normalized)
        return " ".join(merged[:4]).strip()

    def _surfacing_plan_for_item(
        self,
        item: dict,
        *,
        actor_name: str = "Chris",
        device_id: str = "",
        cadence_phase: str,
        world_state: dict | None = None,
        growth_state: dict | None = None,
        quiet_hours_active: bool | None = None,
    ) -> dict:
        policy = dict(self._notification_policy_for_item(item, actor_name=actor_name, device_id=device_id) or {})
        quiet_hours_active = self._quiet_hours_active() if quiet_hours_active is None else bool(quiet_hours_active)
        urgency = self._urgency_score(item)
        world_boost = self._world_state_priority_boost(item, world_state)
        domain = str(item.get("domain", "")).strip().lower()
        base_delivery_mode = str(policy.get("delivery_mode", "queue-only")).strip().lower() or "queue-only"
        base_priority = str(policy.get("priority_class", "normal")).strip().lower() or "normal"
        tuning = dict(policy.get("tuning") or {})
        score = urgency + int(world_boost.get("score", 0) or 0)
        if str(cadence_phase).strip().lower() in {"morning", "pre-transition"} and domain in {"family", "approvals"}:
            score += 1
        growth_pressure = str(((growth_state or {}).get("summary") or {}).get("pressure", "quiet")).strip().lower()
        if domain == "growth" and growth_pressure in {"warming", "active"}:
            score += 1
        if domain == "growth" and bool(item.get("growth_review_due")):
            score += 2
        if domain == "growth" and bool(item.get("growth_high_pressure")):
            score += 1
        interrupt_threshold = 8
        if domain == "approvals":
            interrupt_threshold = 7
        elif domain == "growth":
            interrupt_threshold = 7 if bool(item.get("growth_high_pressure")) else (8 if bool(item.get("growth_review_due")) or growth_pressure == "active" else 9)
        elif str(cadence_phase).strip().lower() in {"evening", "night"}:
            interrupt_threshold = 9
        interrupt_threshold += int(tuning.get("interrupt_threshold_delta", 0) or 0)
        interrupt_threshold = max(5, min(12, interrupt_threshold))
        browser_interrupt = (
            base_delivery_mode == "browser-eligible"
            and not quiet_hours_active
            and score >= interrupt_threshold
        )
        if quiet_hours_active and bool(policy.get("interrupt_during_quiet_hours")) and score >= interrupt_threshold + 1:
            browser_interrupt = True
        delivery_mode = "browser-eligible" if browser_interrupt else "queue-only"
        priority_class = base_priority
        if browser_interrupt and base_priority == "normal":
            priority_class = "interrupt-worthy"
        why_this_surfaced_now = self._compose_why_this_surfaced_now(
            item,
            policy=policy,
            cadence_phase=cadence_phase,
            world_state=world_state,
            growth_state=growth_state,
            quiet_hours_active=quiet_hours_active,
            browser_interrupt=browser_interrupt,
        )
        return {
            **policy,
            "urgency_score": score,
            "browser_interrupt": browser_interrupt,
            "delivery_mode": delivery_mode,
            "priority_class": priority_class,
            "why_this_surfaced_now": why_this_surfaced_now,
            "interrupt_threshold": interrupt_threshold,
            "tuning_summary": {
                "interrupt_threshold_delta": int(tuning.get("interrupt_threshold_delta", 0) or 0),
                "cooldown_delta_minutes": int(tuning.get("cooldown_delta_minutes", 0) or 0),
                "queue_bias": int(tuning.get("queue_bias", 0) or 0),
                "actor_sample": int((tuning.get("actor_profile") or {}).get("sample_size", 0) or 0),
                "domain_sample": int((tuning.get("domain_profile") or {}).get("sample_size", 0) or 0),
                "device_sample": int((tuning.get("device_profile") or {}).get("sample_size", 0) or 0),
            },
        }

    def _should_emit_surface_notification(
        self,
        actor_name: str,
        *,
        surface_key: str,
        packet: str,
        plan: dict,
        title: str,
        detail: str,
        domain: str,
        item_id: str,
    ) -> tuple[bool, dict[str, Any]]:
        existing = self.assistant_core_store.latest_notification(actor_name, surface_key, include_terminal=True) or {}
        if not existing:
            return True, {"reason": "new-surface"}
        status = str(existing.get("status", "unseen")).strip().lower() or "unseen"
        if status in {"acted", "expired"}:
            return True, {"reason": "terminal-refresh"}
        last_event_at = self.assistant_core_store.notification_last_event_at(existing)
        cadence_phase = str((self.assistant_core_store.sweep_record(actor_name) or {}).get("cadence_phase", "")).strip().lower()
        cooldown_minutes = self._surfacing_cooldown_minutes(
            status=status,
            domain=domain,
            cadence_phase=cadence_phase,
            browser_interrupt=bool(plan.get("browser_interrupt")),
            actor_name=actor_name,
        )
        now = datetime.now(timezone.utc)
        material_change = any(
            [
                str(existing.get("title", "")).strip() != title.strip(),
                str(existing.get("detail", "")).strip() != detail.strip(),
                str(existing.get("priority_class", "")).strip().lower() != str(plan.get("priority_class", "")).strip().lower(),
                str(existing.get("delivery_mode", "")).strip().lower() != str(plan.get("delivery_mode", "")).strip().lower(),
                str(existing.get("why_this_surfaced", "")).strip() != str(plan.get("why_this_surfaced_now", "")).strip(),
                str(existing.get("packet", "")).strip() != packet.strip(),
                str(existing.get("item_id", "")).strip() != item_id.strip(),
            ]
        )
        if status == "ignored" and not material_change and last_event_at is not None and last_event_at >= now - timedelta(minutes=cooldown_minutes):
            return False, {"reason": "recently-ignored", "cooldown_minutes": cooldown_minutes}
        if status in {"unseen", "surfaced", "opened"} and not material_change and last_event_at is not None and last_event_at >= now - timedelta(minutes=cooldown_minutes):
            return False, {"reason": f"recently-{status}", "cooldown_minutes": cooldown_minutes}
        return True, {
            "reason": "material-change" if material_change else "cooldown-expired",
            "previous_status": status,
            "cooldown_minutes": cooldown_minutes,
        }

    def _open_loop_key(self, domain: str, item_id: str) -> str:
        return f"{domain.strip().lower()}::{item_id.strip()}"

    def _open_loop_visible_to_actor(self, viewer: UserProfile, *, domain: str, item_actor: str) -> bool:
        actor_label = item_actor.strip().lower()
        if not actor_label:
            return True
        if actor_label == viewer.display_name.strip().lower() or actor_label == viewer.user_id.strip().lower():
            return True
        if domain == "family" and viewer.permissions == "adult":
            return True
        return False

    def _default_revisit_hours(self, domain: str, status: str) -> int:
        normalized_status = str(status or "").strip().lower()
        if domain == "approvals":
            return 6 if normalized_status in {"pending", "pending-approval"} else 24
        if domain == "family":
            return 4 if normalized_status in {"pending", "pending-approval"} else 12
        if domain == "workshop":
            return 12 if normalized_status in {"pending", "pending-approval"} else 24
        if domain == "memory":
            return 24
        if domain == "content":
            return 12 if normalized_status in {"queued", "scripted"} else 24
        if domain == "growth":
            return 18 if normalized_status in {"queued", "staged", "warming"} else 24
        return 24

    def _auto_execution_policy(self, domain: str, status: str, item: dict | None = None) -> dict:
        normalized_domain = domain.strip().lower()
        normalized_status = status.strip().lower()
        item = item or {}
        if normalized_domain == "content" and normalized_status in {"queued", "scripted"}:
            return {
                "allowed": True,
                "action": "export",
                "action_class": "package",
                "preferred_phases": ["morning", "midday", "pre-transition", "evening", "night"],
                "allowed_during_quiet_hours": True,
                "summary": "Content can be packaged automatically, but publishing still requires explicit approval.",
            }
        if normalized_domain == "growth" and normalized_status in {"warming", "staged"}:
            lane_id = str(item.get("item_id", "")).strip().lower()
            if lane_id == "pipeline":
                return {
                    "allowed": True,
                    "action": "refresh-brief",
                    "action_class": "refresh-brief",
                    "preferred_phases": ["midday", "pre-transition", "evening", "night"],
                    "allowed_during_quiet_hours": True,
                    "summary": "Pipeline pressure can safely refresh a Catalyst brief in the background without sending anything externally.",
                }
            if lane_id in {"financial", "marketing"}:
                return {
                    "allowed": True,
                    "action": "prepare-summary",
                    "action_class": "prepare-summary",
                    "preferred_phases": ["morning", "midday", "evening", "night"],
                    "allowed_during_quiet_hours": True,
                    "summary": "Growth summaries can be prepared automatically so the next review starts with a cleaner brief.",
                }
        if normalized_domain in {"family", "workshop"} and normalized_status == "staged":
            return {
                "allowed": True,
                "action": "defer-tomorrow-am",
                "action_class": "defer",
                "preferred_phases": ["evening", "night"],
                "allowed_during_quiet_hours": True,
                "summary": "Staged work can be quietly re-timed into tomorrow morning when the current window is no longer the right one.",
            }
        return {
            "allowed": False,
            "action": "",
            "action_class": "",
            "preferred_phases": [],
            "allowed_during_quiet_hours": False,
            "summary": "This lane still stops for human review or consent before execution.",
        }

    def _auto_execution_ready(self, item: dict, *, cadence_phase: str, quiet_hours_active: bool) -> bool:
        policy = dict(item.get("auto_execution") or {})
        if not policy.get("allowed"):
            return False
        preferred_phases = [str(phase).strip().lower() for phase in list(policy.get("preferred_phases", []))]
        if preferred_phases and str(cadence_phase or "").strip().lower() not in preferred_phases:
            return False
        if quiet_hours_active and not bool(policy.get("allowed_during_quiet_hours")):
            return False
        return True

    def _next_tomorrow_morning(self, hour: int = 8) -> str:
        now = datetime.now(timezone.utc)
        target = (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
        return target.isoformat()

    def _compute_next_review_at(self, timestamp: str, domain: str, status: str) -> str:
        parsed = self._parse_timestamp(timestamp)
        if parsed is None:
            return ""
        hours = self._default_revisit_hours(domain, status)
        return (parsed.astimezone(timezone.utc) + timedelta(hours=hours)).isoformat()

    def _available_actions(self, domain: str, status: str) -> list[dict]:
        normalized_status = str(status or "").strip().lower()
        actions: list[dict] = []
        if domain == "approvals" and normalized_status in {"pending", "pending-approval"}:
            actions.extend(
                [
                    {"id": "approve", "label": "Approve"},
                    {"id": "reject", "label": "Reject"},
                ]
            )
        elif domain == "family":
            if normalized_status in {"pending", "pending-approval"}:
                actions.extend([{"id": "approve", "label": "Approve"}, {"id": "reject", "label": "Reject"}])
            else:
                actions.extend([{"id": "done", "label": "Mark Sent"}, {"id": "archive", "label": "Archive"}])
        elif domain == "workshop":
            if normalized_status in {"pending", "pending-approval"}:
                actions.extend([{"id": "approve", "label": "Approve"}, {"id": "reject", "label": "Reject"}])
            else:
                actions.extend([{"id": "done", "label": "Mark Complete"}, {"id": "archive", "label": "Archive"}])
        elif domain == "memory" and normalized_status == "pending":
            actions.extend([{"id": "approve", "label": "Approve"}, {"id": "reject", "label": "Reject"}])
        elif domain == "content":
            if normalized_status in {"queued", "scripted"}:
                actions.extend([{"id": "export", "label": "Export"}, {"id": "publish", "label": "Push Live"}])
            elif normalized_status == "exported":
                actions.extend([{"id": "publish", "label": "Push Live"}])
            actions.append({"id": "archive", "label": "Archive"})
        elif domain == "growth":
            actions.extend([{"id": "prepare-summary", "label": "Prepare Summary"}, {"id": "refresh-brief", "label": "Refresh Brief"}])
        actions.append({"id": "defer-4h", "label": "Later Today"})
        actions.append({"id": "defer-tomorrow-am", "label": "Tomorrow Morning"})
        actions.append({"id": "defer-1d", "label": "Snooze 1 Day"})
        return actions

    def _urgency_score(self, item: dict) -> int:
        score = 0
        if item.get("needs_revisit"):
            score += 4
        if str(item.get("status", "")).lower() in {"pending", "pending-approval"}:
            score += 3
        if str(item.get("age_bucket", "")) == "aged":
            score += 3
        elif str(item.get("age_bucket", "")) == "stale":
            score += 2
        if str(item.get("domain", "")) in {"approvals", "family"}:
            score += 1
        return score

    def _world_state_priority_boost(self, item: dict, world_state: dict | None = None) -> dict:
        world_state = world_state or {}
        pressure = str(world_state.get("pressure", "steady")).strip().lower()
        delta = dict(world_state.get("delta", {})) if isinstance(world_state.get("delta", {}), dict) else {}
        count_delta = dict(delta.get("count_delta", {})) if isinstance(delta.get("count_delta", {}), dict) else {}
        domain = str(item.get("domain", "")).strip().lower()
        score = 0
        reasons: list[str] = []
        if pressure == "shifting":
            score += 1
            reasons.append("The world model is shifting, so JARVIS should bias toward live coordination.")
        if domain in {"family", "approvals"} and int(count_delta.get("events", 0) or 0) > 0:
            score += 2
            reasons.append("Calendar pressure changed, which makes family and approval coordination more time-sensitive.")
        if domain in {"family", "approvals"} and int(count_delta.get("notifications", 0) or 0) > 0:
            score += 1
            reasons.append("Attention pressure increased, so family and approval work deserves a stronger nudge.")
        if domain == "workshop" and int(count_delta.get("tasks", 0) or 0) > 0:
            score += 1
            reasons.append("The workshop queue changed, so fabrication follow-up is slightly more urgent.")
        if domain == "growth" and (int(count_delta.get("growth_signals", 0) or 0) > 0 or int(count_delta.get("growth_lanes", 0) or 0) > 0):
            score += 2
            reasons.append("Growth signals shifted, so leverage-bearing work deserves a stronger nudge.")
        blocked_work = list(world_state.get("blocked_work", [])) if isinstance(world_state.get("blocked_work", []), list) else []
        conflicts = list(world_state.get("conflicts", [])) if isinstance(world_state.get("conflicts", []), list) else []
        if blocked_work and domain in {str(item.get("domain", "")).strip().lower() for item in blocked_work}:
            score += 2
            reasons.append("This lane is now explicitly blocked, so JARVIS should bias toward clearing the bottleneck.")
        if conflicts:
            for item in conflicts:
                conflict_type = str(item.get("type", "")).strip().lower()
                conflict_domains = {str(value).strip().lower() for value in list(item.get("domains", []))}
                if domain in conflict_domains:
                    score += 1
                    reasons.append(str(item.get("summary", "")).strip() or "This lane is entangled in a live conflict.")
                    break
                if conflict_type == "attention" and domain in {"approvals", "family"}:
                    score += 1
                    reasons.append("Attention conflict is building around decisions and coordination work.")
                    break
        return {"score": score, "reasons": reasons}

    def _follow_up_state(self, timestamp: str, status: str, domain: str) -> dict:
        bucket = self._age_bucket(timestamp)
        normalized_status = str(status or "").strip().lower()
        next_review_at = self._compute_next_review_at(timestamp, domain, status)
        due_for_surface = False
        parsed_next_review = self._parse_timestamp(next_review_at)
        if parsed_next_review is not None:
            due_for_surface = parsed_next_review.astimezone(timezone.utc) <= datetime.now(timezone.utc)
        needs_revisit = normalized_status in {"pending", "pending-approval", "queued", "scripted", "staged", "exported"} and (
            bucket in {"stale", "aged"} or due_for_surface
        )
        if normalized_status in {"pending", "pending-approval"}:
            next_action = "bring back for approval"
        elif normalized_status in {"queued", "scripted", "exported"}:
            next_action = "bring back for review"
        elif domain == "growth" and normalized_status in {"warming", "staged"}:
            next_action = "review the next leverage move"
        elif normalized_status == "staged":
            next_action = "confirm whether to execute"
        else:
            next_action = "watch quietly"
        proactive_reason = ""
        if needs_revisit:
            proactive_reason = f"{domain.title()} work has been waiting long enough that JARVIS should resurface it."
        elif normalized_status in {"pending", "pending-approval"}:
            proactive_reason = f"{domain.title()} work is blocked on an approval decision."
        elif normalized_status in {"queued", "scripted", "staged"}:
            proactive_reason = f"{domain.title()} work is staged and ready for the next step."
        elif domain == "growth" and normalized_status in {"warming"}:
            proactive_reason = "Growth pressure is building, so JARVIS should put the next leverage move back in front of you."
        return {
            "age_bucket": bucket,
            "needs_revisit": needs_revisit,
            "next_action": next_action,
            "proactive_reason": proactive_reason,
            "next_review_at": next_review_at,
            "due_for_surface": due_for_surface,
        }

    def _assistant_surface(self, open_loops: dict) -> dict:
        summary = dict(open_loops.get("summary", {}))
        proactive = list(open_loops.get("proactive_surface", []))
        chips: list[list[str]] = []
        if summary.get("waiting_on_you", 0):
            chips.append(["Tasks", f"{summary.get('waiting_on_you', 0)} waiting on you"])
        if summary.get("needs_revisit", 0):
            chips.append(["Revisit", f"{summary.get('needs_revisit', 0)} aged item(s) should come back now"])
        if proactive:
            top = proactive[0]
            chips.append(["Next", f"{top.get('owner_agent', 'JARVIS')}: {top.get('title', 'Open loop')}"])
        briefing_lines = []
        for item in proactive[:3]:
            line = f"{item.get('owner_agent', 'JARVIS')} should {item.get('next_action', 'follow up')} on {item.get('title', 'this item')}."
            briefing_lines.append(line)
        top_item = proactive[0] if proactive else None
        auto_open = bool(top_item and self._urgency_score(top_item) >= 7)
        packet = self._suggested_packet_for_item(top_item) if top_item else ""
        if top_item:
            top_item = dict(top_item)
            top_item["why_this_surfaced_now"] = str(top_item.get("proactive_reason", "")).strip() or "JARVIS judged that this item deserves attention."
            top_item["suggested_packet"] = packet
        return {
            "chips": chips[:3],
            "briefing_lines": briefing_lines,
            "auto_open_packet": packet if auto_open else "",
            "surface_key": f"{top_item.get('domain','')}::{top_item.get('item_id','')}::{top_item.get('status','')}" if top_item else "",
            "top_item": top_item,
        }

    def assistant_core_tick(self, actor_name: str = "Chris", *, include_today_board: bool = True) -> dict:
        actor = self.get_actor(actor_name)
        open_loops = self.unified_open_loops(actor.display_name, limit=18)
        today_board = self.today_board(actor.display_name) if include_today_board else {}
        world_state = self.world_state_snapshot(actor.display_name, open_loops=open_loops, persist=True)
        cognitive = self.cognitive_snapshot(actor.display_name, include_graph=False, open_loops=open_loops)
        deliberation = dict(cognitive.get("deliberation") or {})
        decision = str(deliberation.get("decision", "hold")).strip().lower()
        summary = dict(open_loops.get("summary", {}))
        surface_key = str(open_loops.get("surface_key", ""))
        suggested_packet = str(open_loops.get("auto_open_packet", ""))
        top_item = dict(open_loops.get("top_item") or {})
        cadence_phase = str((cognitive.get("cadence") or {}).get("phase", "")).strip().lower()
        surfacing_plan = (
            self._surfacing_plan_for_item(
                top_item,
                actor_name=actor.display_name,
                cadence_phase=cadence_phase,
                world_state=world_state,
                growth_state=dict(cognitive.get("growth_state") or {}),
            )
            if top_item
            else {}
        )
        if top_item and surfacing_plan:
            top_item["why_this_surfaced_now"] = str(surfacing_plan.get("why_this_surfaced_now", "")).strip()
        previous = self.assistant_core_store.sweep_record(actor.display_name) or {}
        previous_key = str(previous.get("surface_key", ""))
        previous_updated_at = self._parse_timestamp(str(previous.get("updated_at", "")))
        should_surface = bool(surface_key and suggested_packet and surface_key != previous_key)
        if not should_surface and surface_key and suggested_packet and previous_updated_at is not None:
            should_surface = previous_updated_at <= datetime.now(timezone.utc) - timedelta(minutes=20)
        if decision not in {"notify", "act"}:
            suggested_packet = ""
            should_surface = False
        active_loop = next(
            (
                item for item in list((cognitive.get("cadence") or {}).get("loops", []))
                if str(item.get("state", "")).strip() == "active"
            ),
            {},
        )
        sweep = self.assistant_core_store.save_sweep(
            actor.display_name,
            surface_key=surface_key,
            total_open_loops=int(summary.get("total", 0)),
            waiting_on_you=int(summary.get("waiting_on_you", 0)),
            needs_revisit=int(summary.get("needs_revisit", 0)),
            suggested_packet=suggested_packet,
            cadence_phase=str((cognitive.get("cadence") or {}).get("phase", "")),
            active_loop=str(active_loop.get("label", "")),
        )
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "assistant_surface": {
                "signal_chips": list(open_loops.get("surface_chips", [])),
                "briefing_lines": list(open_loops.get("briefing_lines", [])),
                "auto_open_packet": suggested_packet if should_surface else "",
                "surface_key": surface_key,
                "top_item": top_item,
                "surfacing_plan": surfacing_plan,
            },
            "open_loops": open_loops,
            "today_board": today_board,
            "cognitive": cognitive,
            "world_state": world_state,
            "summary": summary,
            "sweep": sweep,
            "should_surface": should_surface,
            "notifications": self.assistant_notifications(actor.display_name, limit=6),
        }

    def assistant_notifications(
        self,
        actor_name: str = "Chris",
        *,
        limit: int = 12,
        unread_only: bool = False,
        visible_keys: set[str] | None = None,
    ) -> dict:
        actor = self.get_actor(actor_name)
        self.assistant_core_store.expire_notifications(actor.display_name)
        if visible_keys is None:
            visible_keys = {
                self._open_loop_key(str(item.get("domain", "")), str(item.get("item_id", "")))
                for item in self.unified_open_loops(actor.display_name, limit=200).get("items", [])
            }
        raw_items = self.assistant_core_store.list_notifications(actor.display_name, unread_only=unread_only, limit=200)
        items = [
            item
            for item in raw_items
            if str(item.get("packet", "")).strip() == "review"
            or self._open_loop_key(str(item.get("domain", "")), str(item.get("item_id", ""))) in visible_keys
        ][:limit]
        raw_unread = self.assistant_core_store.list_notifications(actor.display_name, unread_only=True, limit=200)
        unread = [
            item
            for item in raw_unread
            if str(item.get("packet", "")).strip() == "review"
            or self._open_loop_key(str(item.get("domain", "")), str(item.get("item_id", ""))) in visible_keys
        ]
        status_counts: dict[str, int] = {}
        priority_counts: dict[str, int] = {}
        for item in items:
            status_key = str(item.get("status", "opened")).strip().lower() or "opened"
            priority_key = str(item.get("priority_class", "normal")).strip().lower() or "normal"
            item["why_this_surfaced_now"] = str(item.get("why_this_surfaced_now", "")).strip() or str(item.get("why_this_surfaced", "")).strip() or str(item.get("delivery_policy_summary", "")).strip()
            item["interrupt_eligible"] = str(item.get("delivery_mode", "queue-only")).strip().lower() == "browser-eligible"
            status_counts[status_key] = int(status_counts.get(status_key, 0) or 0) + 1
            priority_counts[priority_key] = int(priority_counts.get(priority_key, 0) or 0) + 1
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total": len(items),
                "unread": len(unread),
                "by_status": status_counts,
                "by_priority": priority_counts,
            },
            "items": items,
        }

    def assistant_browser_alerts(self, actor_name: str = "Chris", *, device_id: str = "", limit: int = 3) -> dict:
        notifications = self.assistant_notifications(actor_name, unread_only=True, limit=50)
        quiet_hours_active = self._quiet_hours_active()
        items: list[dict] = []
        for item in notifications.get("items", []):
            delivery_mode = str(item.get("delivery_mode", "browser-eligible")).strip().lower()
            if delivery_mode != "browser-eligible":
                continue
            if str(item.get("status", "unseen")).strip().lower() == "opened":
                continue
            if quiet_hours_active and not bool(item.get("interrupt_during_quiet_hours")):
                continue
            delivered_at = self._parse_timestamp(str(item.get("browser_delivered_at", "")).strip())
            updated_at = self._parse_timestamp(str(item.get("updated_at", "")).strip())
            surfaced_at = self._parse_timestamp(str(item.get("surfaced_at", "")).strip())
            if surfaced_at is not None and surfaced_at >= datetime.now(timezone.utc) - timedelta(minutes=45):
                continue
            if delivered_at and (updated_at is None or updated_at <= delivered_at):
                continue
            item["why_this_surfaced_now"] = str(item.get("why_this_surfaced_now", "")).strip() or str(item.get("why_this_surfaced", "")).strip() or str(item.get("delivery_policy_summary", "")).strip()
            item["interrupt_eligible"] = True
            items.append(item)
            if len(items) >= limit:
                break
        return {
            "actor": actor_name,
            "device_id": device_id.strip(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total": len(items),
                "quiet_hours_active": quiet_hours_active,
            },
            "items": items,
        }

    def mark_assistant_notification(self, actor_name: str, notification_id: str, status: str, *, device_id: str = "") -> dict:
        actor = self.get_actor(actor_name)
        record = self.assistant_core_store.mark_notification(notification_id, status=status)
        if record is None:
            raise KeyError("Assistant notification not found.")
        normalized_status = str(record.get("status", status)).strip().lower() or str(status).strip().lower() or "opened"
        self.assistant_core_store.record_outcome(
            actor.display_name,
            source="notification",
            initiator="user",
            status=normalized_status,
            domain=str(record.get("domain", "")).strip(),
            item_id=str(record.get("item_id", "")).strip(),
            notification_id=str(record.get("notification_id", "")).strip(),
            surface_key=str(record.get("surface_key", "")).strip(),
            detail=str(record.get("detail", "")).strip() or str(record.get("title", "")).strip(),
            device_id=device_id.strip(),
            timing_quality=self._notification_timing_quality(record, normalized_status),
        )
        self._invalidate_snapshot_cache(actor.display_name)
        return {
            "ok": True,
            "actor": actor.display_name,
            "record": record,
            "notifications": self.assistant_notifications(actor.display_name, limit=12),
        }

    def mark_assistant_notification_delivered(self, actor_name: str, notification_id: str, *, device_id: str = "") -> dict:
        actor = self.get_actor(actor_name)
        record = self.assistant_core_store.mark_notification_delivered(notification_id, device_id=device_id)
        if record is None:
            raise KeyError("Assistant notification not found.")
        self.assistant_core_store.record_outcome(
            actor.display_name,
            source="notification",
            initiator="system",
            status="surfaced",
            domain=str(record.get("domain", "")).strip(),
            item_id=str(record.get("item_id", "")).strip(),
            notification_id=str(record.get("notification_id", "")).strip(),
            surface_key=str(record.get("surface_key", "")).strip(),
            detail=str(record.get("detail", "")).strip() or str(record.get("title", "")).strip(),
            device_id=device_id.strip(),
            timing_quality=self._notification_timing_quality(record, "surfaced"),
        )
        self._invalidate_snapshot_cache(actor.display_name)
        return {
            "ok": True,
            "actor": actor.display_name,
            "record": record,
            "alerts": self.assistant_browser_alerts(actor.display_name, device_id=device_id, limit=6),
        }

    def notification_state_label(self, status: str) -> str:
        normalized = str(status or "").strip().lower()
        labels = {
            "unseen": "Unseen",
            "surfaced": "Surfaced",
            "opened": "Opened",
            "acted": "Acted",
            "ignored": "Ignored",
            "expired": "Expired",
        }
        return labels.get(normalized, normalized.title() if normalized else "Opened")

    def background_autonomy_run(self, actors: list[str] | None = None) -> dict:
        actor_names = actors or [profile.display_name for profile in self.household.users.values()]
        runs: list[dict] = []
        notifications: list[dict] = []
        executed_actions: list[dict] = []
        for actor_name in actor_names:
            self._invalidate_snapshot_cache(actor_name)
            previous_sweep = self.assistant_core_store.sweep_record(actor_name) or {}
            tick = self.assistant_core_tick(actor_name, include_today_board=False)
            open_loop_items = list((tick.get("open_loops") or {}).get("items", []))
            deliberation = dict((tick.get("cognitive") or {}).get("deliberation") or {})
            cadence = dict((tick.get("cognitive") or {}).get("cadence") or {})
            decision = str(deliberation.get("decision", "hold")).strip().lower()
            top_item = dict(deliberation.get("top_item") or {})
            surfacing_plan = dict((tick.get("assistant_surface") or {}).get("surfacing_plan") or {})
            actor_executed = False
            if decision == "act" and top_item:
                policy = dict(top_item.get("auto_execution") or {})
                action_id = str(policy.get("action", "")).strip()
                if policy.get("allowed") and action_id:
                    domain = str(top_item.get("domain", "")).strip()
                    item_id = str(top_item.get("item_id", "")).strip()
                    why_now = str((surfacing_plan or {}).get("why_this_surfaced_now", "")).strip() or str(top_item.get("proactive_reason", "")).strip()
                    surface_key = str((tick.get("assistant_surface") or {}).get("surface_key", "")).strip()
                    try:
                        result = self.apply_open_loop_action(
                            actor_name,
                            domain=domain,
                            item_id=item_id,
                            action=action_id,
                            note="assistant-autonomy",
                        )
                        succeeded = self._assistant_action_succeeded(result)
                        result_summary = self._assistant_action_result_summary(result)
                        self.audit_log.log_assistant_action(
                            actor=actor_name,
                            domain=domain,
                            item_id=item_id,
                            action=action_id,
                            action_class=str(policy.get("action_class", "")).strip(),
                            detail=str(policy.get("summary", "Assistant autonomy executed a safe action.")).strip(),
                            mode="automatic",
                            policy_basis=str(policy.get("summary", "")).strip(),
                            confidence=self._assistant_action_confidence(policy),
                            decision=decision,
                            cadence_phase=str(cadence.get("phase", "")).strip(),
                            quiet_hours_active=self._quiet_hours_active(),
                            why_now=why_now,
                            surface_key=surface_key,
                            result_summary=result_summary,
                            succeeded=succeeded,
                            caused_friction=not succeeded,
                            friction_reason="" if succeeded else result_summary,
                        )
                        self.assistant_core_store.record_outcome(
                            actor_name,
                            source="assistant-action",
                            initiator="assistant",
                            status="succeeded" if succeeded else "failed",
                            domain=domain,
                            item_id=item_id,
                            action=action_id,
                            action_class=str(policy.get("action_class", "")).strip(),
                            surface_key=surface_key,
                            detail=result_summary,
                            succeeded=succeeded,
                            caused_friction=not succeeded,
                            friction_reason="" if succeeded else result_summary,
                        )
                        actor_executed = succeeded
                        executed_actions.append(
                            {
                                "actor": actor_name,
                                "domain": domain,
                                "item_id": item_id,
                                "action": action_id,
                                "result": result,
                            }
                        )
                    except Exception as exc:
                        failure_summary = str(exc).strip() or "Assistant autonomy action failed."
                        self.audit_log.log_assistant_action(
                            actor=actor_name,
                            domain=domain,
                            item_id=item_id,
                            action=action_id,
                            action_class=str(policy.get("action_class", "")).strip(),
                            detail=str(policy.get("summary", "Assistant autonomy attempted a safe action.")).strip(),
                            mode="automatic",
                            policy_basis=str(policy.get("summary", "")).strip(),
                            confidence=self._assistant_action_confidence(policy),
                            decision=decision,
                            cadence_phase=str(cadence.get("phase", "")).strip(),
                            quiet_hours_active=self._quiet_hours_active(),
                            why_now=why_now,
                            surface_key=surface_key,
                            result_summary=failure_summary,
                            succeeded=False,
                            caused_friction=True,
                            friction_reason=failure_summary,
                        )
                        self.assistant_core_store.record_outcome(
                            actor_name,
                            source="assistant-action",
                            initiator="assistant",
                            status="failed",
                            domain=domain,
                            item_id=item_id,
                            action=action_id,
                            action_class=str(policy.get("action_class", "")).strip(),
                            surface_key=surface_key,
                            detail=failure_summary,
                            succeeded=False,
                            caused_friction=True,
                            friction_reason=failure_summary,
                        )
            if actor_executed:
                tick = self.assistant_core_tick(actor_name, include_today_board=False)
                deliberation = dict((tick.get("cognitive") or {}).get("deliberation") or {})
                cadence = dict((tick.get("cognitive") or {}).get("cadence") or {})
                decision = str(deliberation.get("decision", "hold")).strip().lower()
            top_item = tick.get("assistant_surface", {}).get("top_item") or {}
            surfacing_plan = dict(tick.get("assistant_surface", {}).get("surfacing_plan") or {})
            packet = str(tick.get("assistant_surface", {}).get("auto_open_packet", "")).strip()
            surface_key = str(tick.get("assistant_surface", {}).get("surface_key", "")).strip()
            cadence_record: dict[str, Any] = {}
            if decision in {"queue", "notify"} and tick.get("should_surface") and surface_key and packet:
                notification_policy = surfacing_plan or self._notification_policy_for_item(top_item, actor_name=actor_name)
                delivery_mode = "queue-only" if decision == "queue" else str(notification_policy.get("delivery_mode", "queue-only"))
                title = str(top_item.get("title", "Assistant follow-up")).strip() or "Assistant follow-up"
                detail = str((tick.get("assistant_surface", {}).get("briefing_lines") or ["JARVIS resurfaced a task."])[0]).strip()
                if str(top_item.get("domain", "")).strip().lower() == "growth":
                    detail = str(top_item.get("growth_signal_summary", "")).strip() or str(top_item.get("growth_recommended_next_move", "")).strip() or detail
                should_emit, emit_meta = self._should_emit_surface_notification(
                    actor_name,
                    surface_key=surface_key,
                    packet=packet,
                    plan=notification_policy,
                    title=title,
                    detail=detail,
                    domain=str(top_item.get("domain", "")).strip(),
                    item_id=str(top_item.get("item_id", "")).strip(),
                )
                if should_emit:
                    note = self.assistant_core_store.push_notification(
                        actor_name,
                        surface_key=surface_key,
                        packet=packet,
                        title=title,
                        detail=detail,
                        domain=str(top_item.get("domain", "")).strip(),
                        item_id=str(top_item.get("item_id", "")).strip(),
                        severity=str(notification_policy.get("severity", "normal")),
                        priority_class=str(notification_policy.get("priority_class", "normal")),
                        delivery_mode=delivery_mode,
                        interrupt_during_quiet_hours=bool(notification_policy.get("interrupt_during_quiet_hours")),
                        delivery_policy_summary=str(notification_policy.get("summary", "")),
                        why_this_surfaced=str(notification_policy.get("why_this_surfaced_now", "")).strip() or str(top_item.get("proactive_reason", "")).strip() or str(notification_policy.get("summary", "")),
                        stale_after_hours=int(notification_policy.get("stale_after_hours", 48) or 48),
                    )
                    notifications.append(note)
            current_phase = str(cadence.get("phase", "")).strip().lower()
            previous_phase = str(previous_sweep.get("cadence_phase", "")).strip().lower()
            if current_phase in {"morning", "midday", "pre-transition", "evening", "night"}:
                review = self.cadence_review(actor_name)
                cadence_record = self.assistant_core_store.save_cadence_record(
                    actor_name,
                    phase=current_phase,
                    loop_id=str((review.get("active_loop") or review.get("phase") or "cadence-review")).strip().lower().replace(" ", "-"),
                    loop_label=str(review.get("active_loop", review.get("title", "Cadence Review"))),
                    title=str(review.get("title", "Cadence Review")),
                    digest=str(review.get("digest", "")),
                    outcome_summary=str(review.get("outcome_summary", "")),
                    completion_criteria=list(review.get("completion_criteria", [])),
                    recommended_next_move=str(review.get("recommended_next_move", "")),
                    waiting_on_you=int(((tick.get("open_loops") or {}).get("summary") or {}).get("waiting_on_you", 0) or 0),
                    needs_revisit=int(((tick.get("open_loops") or {}).get("summary") or {}).get("needs_revisit", 0) or 0),
                )
                phase_changed = bool(current_phase and previous_phase and current_phase != previous_phase)
                if self._should_emit_cadence_notification(
                    actor_name,
                    phase=current_phase,
                    digest=str(review.get("digest", "")),
                    current_phase_changed=phase_changed,
                ):
                    detail_parts = [
                        str(review.get("digest", "")).strip(),
                        str(review.get("outcome_summary", "")).strip(),
                    ]
                    review_note = self.assistant_core_store.push_notification(
                        actor_name,
                        surface_key=f"cadence-review::{current_phase}",
                        packet="review",
                        title=str(review.get("title", "Cadence Review")).strip() or "Cadence Review",
                        detail=" ".join(part for part in detail_parts if part).strip() or "JARVIS prepared the next review loop.",
                        domain="growth",
                        item_id=f"cadence-{current_phase}",
                        severity="normal",
                        priority_class="normal" if current_phase in {"evening", "night"} else "interrupt-worthy",
                        delivery_mode="browser-eligible" if current_phase in {"morning", "midday", "pre-transition"} else "queue-only",
                        interrupt_during_quiet_hours=False,
                        delivery_policy_summary="Cadence reviews surface when the day shifts into a new operating loop and stay quiet when the same loop is already well-covered.",
                        why_this_surfaced=str(review.get("digest", "")).strip() or "The day shifted into a new operating loop.",
                        stale_after_hours=24 if current_phase in {"morning", "midday", "pre-transition"} else 36,
                    )
                    notifications.append(review_note)
            runs.append(
                {
                    "actor": actor_name,
                    "cadence_phase": str(cadence.get("phase", "")),
                    "deliberation_mode": str(deliberation.get("mode", "")),
                    "decision": decision,
                    "should_surface": bool(tick.get("should_surface")),
                    "summary": tick.get("summary", {}),
                    "top_item": top_item,
                    "surfacing_plan": surfacing_plan,
                    "cadence_record": cadence_record if current_phase in {"morning", "midday", "pre-transition", "evening", "night"} else {},
                }
            )
            self._invalidate_snapshot_cache(actor_name)
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "runs": runs,
            "notifications_created": notifications,
            "executed_actions": executed_actions,
        }

    def today_board(
        self,
        actor_name: str = "Chris",
        *,
        open_loops: dict | None = None,
        cognition: dict | None = None,
    ) -> dict:
        def builder() -> dict:
            actor = self.get_actor(actor_name)
            board_open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
            visible_keys = {
                self._open_loop_key(str(item.get("domain", "")), str(item.get("item_id", "")))
                for item in list(board_open_loops.get("items", []))
            }
            calendar = self._actor_calendar_events(actor, limit=6)
            first_light = self.first_light_store.latest_packet(actor.user_id) or {}
            quiet_hours_active = self._quiet_hours_active()
            board_cognition = cognition or self.cognitive_snapshot(
                actor.display_name,
                include_graph=False,
                open_loops=board_open_loops,
            )
            growth = board_cognition.get("growth_state") or {}
            growth_guidance = self._growth_loop_guidance(
                actor,
                growth_state=growth,
                cadence=dict(board_cognition.get("cadence") or {}),
            )
            top_items = list(board_open_loops.get("items", []))[:5]
            summary = dict(board_open_loops.get("summary", {}))
            priorities = []
            for item in top_items[:3]:
                priorities.append(
                    {
                        "title": str(item.get("title", "Open loop")),
                        "owner_agent": str(item.get("owner_agent", "JARVIS")),
                        "next_action": str(item.get("next_action", "follow up")),
                        "status": str(item.get("status", "open")),
                    }
                )
            carry = []
            if summary.get("waiting_on_you", 0):
                carry.append(f"{summary.get('waiting_on_you', 0)} item(s) are waiting on a decision or review from you.")
            if summary.get("needs_revisit", 0):
                carry.append(f"{summary.get('needs_revisit', 0)} item(s) have aged enough that JARVIS should bring them back today.")
            growth_summary = dict(growth.get("summary", {})) if isinstance(growth, dict) else {}
            if str(growth_summary.get("pressure", "quiet")).strip().lower() in {"active", "warming"}:
                carry.append(
                    f"Growth pressure is {str(growth_summary.get('pressure', 'quiet'))}, with {int(growth_summary.get('tracked_signal_count', 0) or 0)} signal(s) worth keeping in view."
                )
            if not carry:
                carry.append("The open-loop pressure is light right now; JARVIS can keep most follow-up quiet.")
            autonomy = [
                "JARVIS can stage, defer, surface, and reorganize work inside family, workshop, memory, and content lanes.",
                "Approvals, publishing, and external vendor movement still stop for explicit consent.",
            ]
            if quiet_hours_active:
                autonomy.append("Quiet hours are active right now, so browser alerts are suppressed unless a lane is explicitly allowed to interrupt overnight.")
            else:
                autonomy.append("Active hours are open, so eligible assistant items may escalate into browser alerts on trusted devices.")
            payload = {
                "actor": actor.display_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "calendar": calendar,
                "priorities": priorities,
                "carry": carry,
                "autonomy": autonomy,
                "notification_policy": {
                    "quiet_hours_active": quiet_hours_active,
                    "quiet_window": {
                        "start": getattr(self.household, "quiet_start", "22:00"),
                        "end": getattr(self.household, "quiet_end", "06:00"),
                    },
                },
                "first_light": {
                    "opening": str(first_light.get("opening", "")),
                    "watch_line": str(first_light.get("watch_line", "")),
                    "formation_cue": str(first_light.get("formation_cue", "")),
                },
                "open_loops": {
                    "summary": summary,
                    "top_item": board_open_loops.get("top_item"),
                },
                "growth": growth,
                "growth_guidance": growth_guidance,
                "assistant_notifications": self.assistant_notifications(actor.display_name, limit=5, unread_only=True, visible_keys=visible_keys),
                "cognition": board_cognition,
            }
            if self._is_degraded_payload(board_cognition):
                payload["degraded"] = {
                    "active": True,
                    "reason": "Today Board is carrying a stale cognitive snapshot.",
                    "detail": str((board_cognition.get("degraded") or {}).get("detail", "")),
                    "source": "nested-cognitive-snapshot",
                }
            return payload

        if open_loops is not None or cognition is not None:
            return builder()
        return self._cached_surface("today_board", actor_name, builder)

    def cadence_review(
        self,
        actor_name: str = "Chris",
        *,
        open_loops: dict | None = None,
        cognition: dict | None = None,
    ) -> dict:
        def builder() -> dict:
            actor = self.get_actor(actor_name)
            review_open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
            review_cognition = cognition or self.cognitive_snapshot(
                actor.display_name,
                include_graph=False,
                open_loops=review_open_loops,
            )
            cadence = dict(review_cognition.get("cadence") or {})
            growth = dict(review_cognition.get("growth_state") or {})
            growth_guidance = self._growth_loop_guidance(
                actor,
                growth_state=growth,
                cadence=cadence,
            )
            phase = str(cadence.get("phase", "watch")).strip().lower()
            active_loop = next((item for item in list(cadence.get("loops", [])) if str(item.get("state", "")).strip() == "active"), None) or {}
            loop_label = str(active_loop.get("label", "Autonomy Sweep")).strip() or "Autonomy Sweep"
            if phase == "midday":
                title = "Midday Drift Check"
            elif phase == "pre-transition":
                title = "Handoff Prep"
            elif phase == "evening":
                title = "Evening Collapse"
            elif phase == "morning":
                title = "Morning Operating Review"
            elif phase == "night":
                title = "Night Watch"
            else:
                title = "Cadence Review"
            notifications = self.assistant_notifications(actor.display_name, limit=5, unread_only=True)
            top_growth_focus = list(growth_guidance.get("focus", []))[:3]
            top_items = list(review_open_loops.get("items", []))[:5]
            domain_counts = dict(review_open_loops.get("summary", {}).get("by_domain", {}))
            waiting = int(review_open_loops.get("summary", {}).get("waiting_on_you", 0) or 0)
            revisit = int(review_open_loops.get("summary", {}).get("needs_revisit", 0) or 0)
            growth_pressure = str((growth.get("summary") or {}).get("pressure", "quiet")).strip().lower()
            top_task = top_items[0] if top_items else {}
            recommended_action: dict[str, str] = {}
            dominant_domain = ""
            if domain_counts:
                dominant_domain = max(
                    sorted(domain_counts),
                    key=lambda key: int(domain_counts.get(key, 0) or 0),
                )
            if top_task:
                safe_actions = [
                    action
                    for action in list(top_task.get("available_actions", []))
                    if str(action.get("id", "")).strip().lower() not in {"defer-4h", "defer-tomorrow-am", "defer-1d"}
                ]
                if safe_actions:
                    chosen = dict(safe_actions[0])
                    recommended_action = {
                        "domain": str(top_task.get("domain", "")).strip(),
                        "item_id": str(top_task.get("item_id", "")).strip(),
                        "action_id": str(chosen.get("id", "")).strip(),
                        "label": str(chosen.get("label", "Act")).strip() or "Act",
                        "title": str(top_task.get("title", "Open loop")).strip() or "Open loop",
                    }
            recommended_next_move = (
                str(top_task.get("next_action", "")).strip()
                if top_task
                else (top_growth_focus[0] if top_growth_focus else "Keep monitoring for the next credible move.")
            )
            digest = "No strong review signal is asking for attention right now."
            if phase == "midday":
                if dominant_domain == "family" and top_task:
                    digest = f"Midday drift check: family coordination is starting to drift - {str(top_task.get('title', 'the next family item')).strip()}"
                elif dominant_domain == "approvals" and waiting:
                    digest = f"Midday drift check: approvals are bottlenecking around {str(top_task.get('title', 'the next approval')).strip()}."
                elif dominant_domain == "workshop" and top_task:
                    digest = f"Midday drift check: workshop backlog is building around {str(top_task.get('title', 'the next fabrication item')).strip()}"
                elif growth_pressure in {"active", "warming"} and top_growth_focus:
                    digest = f"Midday drift check: keep one leverage move alive - {top_growth_focus[0]}"
                elif revisit:
                    digest = f"Midday drift check: {revisit} item(s) are aging and should not slip into the afternoon."
                else:
                    digest = "Midday drift check: the day is holding together; protect the next meaningful block."
            elif phase == "pre-transition":
                if dominant_domain == "family" and top_task:
                    digest = f"Handoff prep: family transition pressure is rising - clear or defer {str(top_task.get('title', 'the next family item')).strip()}."
                elif top_task:
                    digest = f"Handoff prep: clear or defer {str(top_task.get('title', 'the next task')).strip()} before the transition."
                else:
                    digest = "Handoff prep: preserve one clear next step before the day turns relational."
            elif phase == "evening":
                if dominant_domain == "approvals" and waiting:
                    digest = f"Evening collapse: approval drag is still centered on {str(top_task.get('title', 'the next approval')).strip()}."
                elif dominant_domain == "workshop" and top_task:
                    digest = f"Evening collapse: workshop backlog should be closed or deferred around {str(top_task.get('title', 'the next fabrication item')).strip()}."
                elif dominant_domain == "family" and top_task:
                    digest = f"Evening collapse: family follow-up is still open around {str(top_task.get('title', 'the next family item')).strip()}."
                elif growth_pressure in {"active", "warming"} and top_growth_focus:
                    digest = f"Evening leverage review: close the loop on {top_growth_focus[0]}"
                else:
                    digest = "Evening collapse: shrink loose ends and leave tomorrow with a cleaner runway."
            elif phase == "morning":
                if growth_pressure in {"active", "warming"} and top_growth_focus:
                    digest = f"Morning operating review: pick one leverage move early - {top_growth_focus[0]}"
                else:
                    digest = "Morning operating review: protect structure before the day fragments."
            elif phase == "night":
                digest = "Night watch: let the system curate, not agitate."
            completion_criteria = self._cadence_completion_criteria(
                phase,
                open_loops=review_open_loops,
                growth_guidance=growth_guidance,
                assistant_inbox=notifications,
                top_task=top_task,
            )
            outcome_summary = self._cadence_outcome_summary(
                phase,
                open_loops=review_open_loops,
                growth_guidance=growth_guidance,
                assistant_inbox=notifications,
            )
            history = self._recent_cadence_history(actor.display_name, limit=5)
            world_state = dict(review_cognition.get("world_state") or {})
            blocked_work = list(world_state.get("blocked_work", [])) if isinstance(world_state.get("blocked_work", []), list) else []
            conflicts = list(world_state.get("conflicts", [])) if isinstance(world_state.get("conflicts", []), list) else []
            hidden_load = list(world_state.get("hidden_load", [])) if isinstance(world_state.get("hidden_load", []), list) else []
            likely_next = list(world_state.get("likely_next", [])) if isinstance(world_state.get("likely_next", []), list) else []
            payload = {
                "actor": actor.display_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "title": title,
                "phase": phase,
                "active_loop": loop_label,
                "summary": str(cadence.get("rationale", "")).strip() or "JARVIS is reviewing the current phase of the day.",
                "digest": digest,
                "why_this_surfaced": digest,
                "outcome_summary": outcome_summary,
                "completion_criteria": completion_criteria,
                "recommended_next_move": recommended_next_move,
                "recommended_action": recommended_action,
                "dominant_domain": dominant_domain,
                "history": history,
                "sections": [
                    {
                        "id": "loop",
                        "title": "Current Loop",
                        "summary": f"{loop_label} · {str(cadence.get('phase', 'watch'))}",
                        "details": [digest, outcome_summary, str(active_loop.get("purpose", cadence.get("rationale", ""))).strip()],
                    },
                    {
                        "id": "criteria",
                        "title": "Completion Criteria",
                        "summary": outcome_summary,
                        "details": completion_criteria,
                    },
                    {
                        "id": "growth",
                        "title": "Growth Review",
                        "summary": f"{growth_guidance.get('label', 'Growth Watch')} · {growth_guidance.get('pressure', 'quiet')}",
                        "details": top_growth_focus or ["No strong growth move is staged right now."],
                    },
                    {
                        "id": "world-friction",
                        "title": "World Friction",
                        "summary": f"{len(blocked_work)} blocked · {len(conflicts)} conflict · {len(hidden_load)} hidden-load signal(s)",
                        "details": (
                            [
                                *(f"Blocked: {str(item.get('title', 'Blocked work')).strip()} · {str(item.get('reason', '')).strip()}" for item in blocked_work[:2]),
                                *(f"Conflict: {str(item.get('summary', '')).strip()}" for item in conflicts[:2]),
                                *(f"Hidden load: {str(item.get('summary', '')).strip()}" for item in hidden_load[:2]),
                                *(f"Likely next: {str(item.get('title', '')).strip()} · {str(item.get('reason', '')).strip()}" for item in likely_next[:2]),
                            ]
                            or ["The world model is not surfacing a strong bottleneck or conflict right now."]
                        ),
                    },
                    {
                        "id": "tasks",
                        "title": "Priority Tasks",
                        "summary": f"{int(review_open_loops.get('summary', {}).get('waiting_on_you', 0) or 0)} waiting · {int(review_open_loops.get('summary', {}).get('needs_revisit', 0) or 0)} revisit",
                        "details": (
                            [f"Recommended next move: {recommended_next_move}"]
                            + [
                                f"{str(item.get('owner_agent', 'JARVIS')).strip()}: {str(item.get('title', 'Open loop')).strip()} · {str(item.get('next_action', 'follow up')).strip()}"
                                for item in top_items[:4]
                            ]
                        ) or [f"Recommended next move: {recommended_next_move}", "No open-loop pressure is asking for attention right now."],
                    },
                    {
                        "id": "inbox",
                        "title": "Assistant Inbox",
                        "summary": f"{int((notifications.get('summary') or {}).get('unread', 0) or 0)} unread assistant item(s)",
                        "details": [
                            " · ".join(
                                part
                                for part in [
                                    str(item.get("title", "")).strip(),
                                    str(item.get("detail", "")).strip(),
                                ]
                                if part
                            )
                            for item in list(notifications.get("items", []))[:4]
                        ] or ["No unread assistant nudges are waiting right now."],
                    },
                    {
                        "id": "history",
                        "title": "Loop History",
                        "summary": f"{len(history)} recent loop record(s)",
                        "details": [
                            " · ".join(
                                part
                                for part in [
                                    str(item.get("title", "")).strip(),
                                    str(item.get("digest", "")).strip(),
                                ]
                                if part
                            )
                            for item in history[:5]
                        ] or ["No cadence history is recorded yet."],
                    },
                ],
            }
            if self._is_degraded_payload(review_cognition):
                payload["degraded"] = {
                    "active": True,
                    "reason": "Cadence Review is carrying a stale cognitive snapshot.",
                    "detail": str((review_cognition.get("degraded") or {}).get("detail", "")),
                    "source": "nested-cognitive-snapshot",
                }
            return payload

        if open_loops is not None or cognition is not None:
            return builder()
        return self._cached_surface("cadence_review", actor_name, builder)

    def cognitive_cadence_snapshot(self, actor_name: str = "Chris", *, open_loops: dict | None = None) -> dict:
        actor = self.get_actor(actor_name)
        open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
        assistant_inbox = self.assistant_notifications(actor.display_name, limit=6, unread_only=True)
        now_local = self._local_now()
        hour = now_local.hour
        upcoming_events = self._actor_calendar_events(actor, limit=4)
        first_upcoming = upcoming_events[0] if upcoming_events else {}
        phase = "watch"
        rationale = "The day is quiet enough for JARVIS to keep a light watch."
        suggested_loop = "autonomy-sweep"
        if hour < 6:
            phase = "night"
            rationale = "Quiet hours are active, so JARVIS should bias toward suppression and overnight maintenance."
            suggested_loop = "learning-curation"
        elif hour < 11:
            phase = "morning"
            rationale = "This is the morning operating window, so JARVIS should protect the day's early structure."
            suggested_loop = "first-light"
        elif hour < 15:
            phase = "midday"
            rationale = "This is the drift-check window, so JARVIS should look for aging commitments and schedule slippage."
            suggested_loop = "drift-check"
        elif hour < 20:
            phase = "pre-transition"
            rationale = "This is a transition-heavy part of the day, so JARVIS should prioritize handoffs and friction reduction."
            suggested_loop = "handoff-prep"
        else:
            phase = "evening"
            rationale = "This is the evening collapse window, so JARVIS should reduce open-loop pressure before night."
            suggested_loop = "open-loop-collapse"
        if upcoming_events:
            start_text = str(first_upcoming.get("start", "")).strip()
            rationale = f"{rationale} Next visible calendar pressure: {str(first_upcoming.get('summary', 'upcoming event')).strip() or 'upcoming event'} at {start_text or 'soon'}."
        growth_guidance = self._growth_loop_guidance(actor, cadence={"phase": phase})
        loop_states = [
            {
                "id": "first-light",
                "label": "First Light",
                "state": "active" if phase == "morning" else "quiet",
                "purpose": "Interpret the day and stage the morning.",
                "completion_criteria": self._cadence_completion_criteria(
                    "morning",
                    open_loops=open_loops,
                    growth_guidance=growth_guidance,
                    assistant_inbox=assistant_inbox,
                    top_task=dict(open_loops.get("top_item") or {}),
                ),
            },
            {
                "id": "drift-check",
                "label": "Drift Check",
                "state": "active" if phase == "midday" else ("staged" if phase in {"morning", "pre-transition"} else "quiet"),
                "purpose": "Catch schedule slippage and resurfaced commitments.",
                "completion_criteria": self._cadence_completion_criteria(
                    "midday",
                    open_loops=open_loops,
                    growth_guidance=growth_guidance,
                    assistant_inbox=assistant_inbox,
                    top_task=dict(open_loops.get("top_item") or {}),
                ),
            },
            {
                "id": "handoff-prep",
                "label": "Handoff Prep",
                "state": "active" if phase == "pre-transition" else ("staged" if phase == "midday" else "quiet"),
                "purpose": "Reduce friction before family and location transitions.",
                "completion_criteria": self._cadence_completion_criteria(
                    "pre-transition",
                    open_loops=open_loops,
                    growth_guidance=growth_guidance,
                    assistant_inbox=assistant_inbox,
                    top_task=dict(open_loops.get("top_item") or {}),
                ),
            },
            {
                "id": "open-loop-collapse",
                "label": "Open-Loop Collapse",
                "state": "active" if phase == "evening" else "quiet",
                "purpose": "Shrink loose ends before night.",
                "completion_criteria": self._cadence_completion_criteria(
                    "evening",
                    open_loops=open_loops,
                    growth_guidance=growth_guidance,
                    assistant_inbox=assistant_inbox,
                    top_task=dict(open_loops.get("top_item") or {}),
                ),
            },
            {
                "id": "learning-curation",
                "label": "Learning Curation",
                "state": "active" if phase == "night" else "quiet",
                "purpose": "Curate memory and adaptation after the day settles.",
                "completion_criteria": self._cadence_completion_criteria(
                    "night",
                    open_loops=open_loops,
                    growth_guidance=growth_guidance,
                    assistant_inbox=assistant_inbox,
                    top_task=dict(open_loops.get("top_item") or {}),
                ),
            },
        ]
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "hour_local": hour,
            "suggested_loop": suggested_loop,
            "rationale": rationale,
            "calendar_pressure_count": len(upcoming_events),
            "open_loop_pressure": dict(open_loops.get('summary', {})),
            "loops": loop_states,
        }

    def internal_council_snapshot(self, actor_name: str = "Chris", *, open_loops: dict | None = None) -> dict:
        actor = self.get_actor(actor_name)
        open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
        deliberation = self.deliberation_snapshot(actor.display_name, open_loops=open_loops)
        top_item = dict(deliberation.get("top_item") or {})
        title = str(top_item.get("title", "No urgent item")).strip() or "No urgent item"
        decision = str(deliberation.get("decision", "hold")).strip().lower()
        trace = dict(deliberation.get("council_trace") or {})
        members = list(trace.get("members", [])) if isinstance(trace.get("members", []), list) else []
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "top_item_title": title,
            "consensus": decision,
            "tally": dict(trace.get("tally") or {}),
            "winning_vote": str(trace.get("winning_vote", decision)).strip() or decision,
            "members": [
                {
                    "role": str(item.get("role", "council")).strip() or "council",
                    "vote": str(item.get("vote", "queue")).strip() or "queue",
                    "weight": int(item.get("weight", 1) or 1),
                    "recommendation": str(item.get("reason", "")).strip(),
                }
                for item in members
            ],
        }

    def _world_graph_schema(self) -> dict[str, Any]:
        return {
            "version": "2026-05-11",
            "entity_types": [
                {"id": "person", "label": "Person", "description": "A household member or actor JARVIS coordinates around."},
                {"id": "room", "label": "Room", "description": "A physical room or place within the world model."},
                {"id": "device", "label": "Device", "description": "A registered or trusted device session."},
                {"id": "event", "label": "Event", "description": "A scheduled event or time-bound commitment."},
                {"id": "task", "label": "Task", "description": "An open loop, staged item, or task-shaped commitment."},
                {"id": "approval", "label": "Approval", "description": "A direct decision gate waiting on a person."},
                {"id": "notification", "label": "Notification", "description": "An assistant attention object or inbox item."},
                {"id": "growth-lane", "label": "Growth Lane", "description": "A top-level growth lane such as finance, pipeline, or marketing."},
                {"id": "growth-signal", "label": "Growth Signal", "description": "A leverage-bearing signal inside the growth model."},
                {"id": "lead", "label": "Lead", "description": "A pipeline opportunity or revenue-shaped target."},
                {"id": "account", "label": "Account", "description": "A connected digital account surface."},
                {"id": "risk", "label": "Risk", "description": "A warning, threshold breach, stall, or decaying pressure signal."},
                {"id": "routine", "label": "Routine", "description": "A recurring cadence loop or review routine."},
                {"id": "project", "label": "Project", "description": "A durable initiative tracked across steps."},
                {"id": "asset", "label": "Asset", "description": "A content, campaign, or operational asset that can compound."},
                {"id": "habit", "label": "Habit", "description": "A recurring human pattern or formation cue."},
            ],
            "edge_types": [
                {"id": "owns", "label": "Owns", "description": "A person owns or is primarily responsible for a device or asset."},
                {"id": "located-in", "label": "Located In", "description": "A device or entity is associated with a room or place."},
                {"id": "attends-or-carries", "label": "Attends Or Carries", "description": "A person is attached to an event or commitment."},
                {"id": "carries", "label": "Carries", "description": "A person currently carries a task or pressure item."},
                {"id": "must-decide", "label": "Must Decide", "description": "A person is the decision-maker for an approval."},
                {"id": "needs-attention", "label": "Needs Attention", "description": "A notification is active for a person right now."},
                {"id": "uses-account", "label": "Uses Account", "description": "A person operates through a connected account surface."},
                {"id": "tracks", "label": "Tracks", "description": "A person or lane tracks a signal, lead, or asset."},
                {"id": "compounds", "label": "Compounds", "description": "A person intentionally compounds a growth lane."},
                {"id": "belongs-to-lane", "label": "Belongs To Lane", "description": "An entity is part of a broader lane."},
                {"id": "at-risk-from", "label": "At Risk From", "description": "An entity is under pressure from a risk signal."},
                {"id": "drives", "label": "Drives", "description": "A signal or routine is driving another entity's urgency."},
                {"id": "scheduled-by", "label": "Scheduled By", "description": "A routine is scheduled for a person."},
                {"id": "supports", "label": "Supports", "description": "A project, asset, or routine supports another entity or lane."},
            ],
        }

    def _world_graph_node(
        self,
        entity_type: str,
        entity_id: str,
        label: str,
        *,
        confidence: str = "medium",
        truth_status: str = "observed",
        **attributes: Any,
    ) -> dict[str, Any]:
        normalized_truth = str(truth_status or "observed").strip().lower() or "observed"
        payload = {
            "id": f"{entity_type}:{entity_id}",
            "type": entity_type,
            "entity_type": entity_type,
            "label": str(label).strip(),
            "confidence": str(confidence or "medium").strip().lower() or "medium",
            "truth_status": normalized_truth,
            "observed": normalized_truth == "observed",
            "inferred": normalized_truth == "inferred",
        }
        payload.update(attributes)
        return payload

    def _world_graph_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        *,
        confidence: str = "medium",
        truth_status: str = "observed",
        **attributes: Any,
    ) -> dict[str, Any]:
        normalized_truth = str(truth_status or "observed").strip().lower() or "observed"
        payload = {
            "source": source,
            "target": target,
            "type": edge_type,
            "edge_type": edge_type,
            "confidence": str(confidence or "medium").strip().lower() or "medium",
            "truth_status": normalized_truth,
            "observed": normalized_truth == "observed",
            "inferred": normalized_truth == "inferred",
        }
        payload.update(attributes)
        return payload

    def world_graph_snapshot(self, actor_name: str = "Chris", *, open_loops: dict | None = None, use_cache: bool = True) -> dict:
        def builder() -> dict:
            actor = self.get_actor(actor_name)
            identity = self.identity_overview()
            actor_open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
            visible_keys = {
                self._open_loop_key(str(item.get("domain", "")), str(item.get("item_id", "")))
                for item in list(actor_open_loops.get("items", []))
            }
            calendar = self._actor_calendar_events(actor, limit=8)
            accounts = self._actor_accounts(actor)
            approvals = [item for item in self.list_pending_approvals() if str(item.get("actor", "")).strip().lower() in {actor.display_name.lower(), actor.user_id.lower()}][:8]
            notifications = self.assistant_notifications(actor.display_name, limit=8, unread_only=True, visible_keys=visible_keys)
            growth_state = self.growth_state_snapshot(actor.display_name)
            finance_state = self.finance_state_snapshot(actor.display_name)
            pipeline_state = self.pipeline_state_snapshot(actor.display_name)
            marketing_state = self.marketing_state_snapshot(actor.display_name)
            vision_state = self.vision_state_snapshot(actor.display_name)
            cadence = self.cognitive_cadence_snapshot(actor.display_name, open_loops=actor_open_loops)
            schema = self._world_graph_schema()
            people = [
            {
                "id": profile.user_id,
                "label": profile.display_name,
                "role": profile.role,
                "permissions": profile.permissions,
            }
            for profile in self.household.users.values()
            ]
            rooms = [
            {
                "id": room.room_id,
                "mode_bias": room.mode_bias,
            }
            for room in self.household.rooms.values()
            ]
            devices = [
            {
                "device_id": str(item.get("device_id", "")),
                "label": str(item.get("label", "")),
                "owner_user_id": str(item.get("owner_user_id", "")),
                "room": str(item.get("room", "")),
                "shared": bool(item.get("shared", False)),
            }
            for item in identity.get("devices", [])
            ]
            nodes: list[dict] = []
            edges: list[dict] = []
            growth_lane_signals = {
            str(item.get("lane_id", "")).strip().lower(): item
            for item in [
                self._growth_lane_operating_signal(
                    actor.display_name,
                    str(lane.get("id", "")).strip(),
                    growth_state=growth_state,
                    finance_state=finance_state,
                    pipeline_state=pipeline_state,
                    marketing_state=marketing_state,
                )
                for lane in list(growth_state.get("lanes", []))
                if str(lane.get("id", "")).strip()
            ]
            }
            for person in people:
                nodes.append(
                    self._world_graph_node(
                        "person",
                        str(person["id"]),
                        str(person["label"]),
                        confidence="high",
                        truth_status="observed",
                        role=person["role"],
                        permissions=person["permissions"],
                    )
                )
            for room in rooms:
                nodes.append(
                    self._world_graph_node(
                        "room",
                        str(room["id"]),
                        str(room["id"]),
                        confidence="high",
                        truth_status="observed",
                        mode_bias=room["mode_bias"],
                    )
                )
            for device in devices:
                nodes.append(
                    self._world_graph_node(
                        "device",
                        str(device["device_id"]),
                        str(device["label"]),
                        confidence="high",
                        truth_status="observed",
                        device_id=device["device_id"],
                        owner_user_id=device["owner_user_id"],
                        room=device["room"],
                        shared=device["shared"],
                    )
                )
                if device["owner_user_id"]:
                    edges.append(
                        self._world_graph_edge(
                            f"person:{device['owner_user_id']}",
                            f"device:{device['device_id']}",
                            "owns",
                            confidence="high",
                            truth_status="observed",
                        )
                    )
                if device["room"]:
                    edges.append(
                        self._world_graph_edge(
                            f"device:{device['device_id']}",
                            f"room:{device['room']}",
                            "located-in",
                            confidence="high",
                            truth_status="observed",
                        )
                    )
            for item in accounts:
                account = dict(item.get("account") or {})
                account_label = str(account.get("email", "")).strip() or str(account.get("name", "")).strip()
                if not account_label:
                    continue
                account_id = account_label.lower().replace("@", "_at_")
                nodes.append(
                    self._world_graph_node(
                        "account",
                        account_id,
                        account_label,
                        confidence="high",
                        truth_status="observed",
                        provider=str(account.get("provider", "")).strip() or "google",
                        unread_emails=int((item.get("counts") or {}).get("unread_emails", 0) or 0),
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        f"person:{actor.user_id}",
                        f"account:{account_id}",
                        "uses-account",
                        confidence="high",
                        truth_status="observed",
                    )
                )
            for event in calendar:
                event_id = str(event.get("id", "")) or str(uuid.uuid4())
                nodes.append(
                    self._world_graph_node(
                        "event",
                        event_id,
                        str(event.get("summary", "(Untitled event)")),
                        confidence="high" if str(event.get("source", "")).strip().lower() == "google" else "medium",
                        truth_status="observed",
                        start=str(event.get("start", "")),
                        source=str(event.get("source", "")),
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        f"person:{actor.user_id}",
                        f"event:{event_id}",
                        "attends-or-carries",
                        confidence="high",
                        truth_status="observed",
                    )
                )
            for observation in list(vision_state.get("recent_observations") or [])[:8]:
                observation_id = str(observation.get("observation_id", "")).strip() or str(uuid.uuid4())
                mode = str(observation.get("mode", "")).strip() or "describe"
                zone = str(observation.get("zone", "")).strip()
                label = str(observation.get("summary", "")).strip() or f"Visual observation ({mode})"
                nodes.append(
                    self._world_graph_node(
                        "event",
                        f"vision-{observation_id}",
                        label,
                        confidence=str(observation.get("confidence", "medium")).strip() or "medium",
                        truth_status="observed",
                        modality="vision",
                        mode=mode,
                        camera_label=str(observation.get("camera_label", "")).strip(),
                        capture_id=str(observation.get("capture_id", "")).strip(),
                        zone=zone,
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        f"person:{actor.user_id}",
                        f"event:vision-{observation_id}",
                        "tracks",
                        confidence=str(observation.get("confidence", "medium")).strip() or "medium",
                        truth_status="observed",
                    )
                )
                if zone:
                    edges.append(
                        self._world_graph_edge(
                            f"event:vision-{observation_id}",
                            f"room:{zone}",
                            "located-in",
                            confidence=str(observation.get("confidence", "medium")).strip() or "medium",
                            truth_status="observed",
                        )
                    )
                observed_object = str(observation.get("observed_object", "")).strip()
                if observed_object:
                    asset_id = observed_object.lower().replace(" ", "-")
                    nodes.append(
                        self._world_graph_node(
                            "asset",
                            f"vision-{asset_id}",
                            observed_object,
                            confidence=str(observation.get("confidence", "medium")).strip() or "medium",
                            truth_status="observed",
                            source="vision",
                        )
                    )
                    edges.append(
                        self._world_graph_edge(
                            f"event:vision-{observation_id}",
                            f"asset:vision-{asset_id}",
                            "supports",
                            confidence=str(observation.get("confidence", "medium")).strip() or "medium",
                            truth_status="observed",
                        )
                    )
            for item in list(actor_open_loops.get("items", []))[:20]:
                item_key = self._open_loop_key(str(item.get("domain", "")), str(item.get("item_id", "")))
                nodes.append(
                    self._world_graph_node(
                        "task",
                        item_key,
                        str(item.get("title", "Open loop")),
                        confidence="high" if str(item.get("domain", "")).strip().lower() in {"approvals", "family", "workshop"} else "medium",
                        truth_status="observed",
                        domain=str(item.get("domain", "")),
                        status=str(item.get("status", "")),
                        owner_agent=str(item.get("owner_agent", "")),
                        next_action=str(item.get("next_action", "")),
                    )
                )
                item_actor = str(item.get("actor", "")).strip().lower()
                if item_actor in self.household.users:
                    edges.append(
                        self._world_graph_edge(
                            f"person:{item_actor}",
                            f"task:{item_key}",
                            "carries",
                            confidence="high",
                            truth_status="observed",
                        )
                    )
                elif item_actor == actor.display_name.lower():
                    edges.append(
                        self._world_graph_edge(
                            f"person:{actor.user_id}",
                            f"task:{item_key}",
                            "carries",
                            confidence="medium",
                            truth_status="inferred",
                        )
                    )
                if str(item.get("domain", "")).strip().lower() == "growth":
                    lane_id = str(item.get("growth_lane_id", "")).strip().lower()
                    if lane_id:
                        edges.append(
                            self._world_graph_edge(
                                f"task:{item_key}",
                                f"growth-lane:{lane_id}",
                                "belongs-to-lane",
                                confidence="high",
                                truth_status="observed",
                                packet=self._growth_packet_for_lane(lane_id),
                            )
                        )
            for item in approvals:
                approval_id = str(item.get("request_id", ""))
                nodes.append(
                    self._world_graph_node(
                        "approval",
                        approval_id,
                        str(item.get("request", "Approval required")),
                        confidence="high",
                        truth_status="observed",
                        status=str(item.get("status", "pending")),
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        f"person:{actor.user_id}",
                        f"approval:{approval_id}",
                        "must-decide",
                        confidence="high",
                        truth_status="observed",
                    )
                )
            for item in notifications.get("items", []):
                note_id = str(item.get("notification_id", ""))
                nodes.append(
                    self._world_graph_node(
                        "notification",
                        note_id,
                        str(item.get("title", "Assistant follow-up")),
                        confidence="high",
                        truth_status="observed",
                        domain=str(item.get("domain", "")),
                        delivery_mode=str(item.get("delivery_mode", "")),
                        packet=str(item.get("packet", "")),
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        f"person:{actor.user_id}",
                        f"notification:{note_id}",
                        "needs-attention",
                        confidence="high",
                        truth_status="observed",
                    )
                )
            for lane in growth_state.get("lanes", []):
                lane_id = str(lane.get("id", "")).strip()
                if not lane_id:
                    continue
                nodes.append(
                    self._world_graph_node(
                        "growth-lane",
                        lane_id,
                        str(lane.get("label", "Growth lane")),
                        confidence=str(lane.get("confidence", "low")),
                        truth_status="inferred",
                        pressure=str(lane.get("pressure", "steady")),
                        summary=str(lane.get("summary", "")),
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        f"person:{actor.user_id}",
                        f"growth-lane:{lane_id}",
                        "compounds",
                        confidence="medium",
                        truth_status="inferred",
                    )
                )
            for index, signal in enumerate(growth_state.get("top_signals", [])[:6], start=1):
                signal_id = f"{actor.user_id}:{index}"
                nodes.append(
                    self._world_graph_node(
                        "growth-signal",
                        signal_id,
                        str(signal),
                        confidence="medium",
                        truth_status="inferred",
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        f"person:{actor.user_id}",
                        f"growth-signal:{signal_id}",
                        "tracks",
                        confidence="medium",
                        truth_status="inferred",
                    )
                )
            for item in list(((pipeline_state.get("state") or {}).get("opportunities") or []))[:8]:
                lead_id = str(item.get("opportunity_id", "")).strip() or str(uuid.uuid4())
                nodes.append(
                    self._world_graph_node(
                        "lead",
                        lead_id,
                        str(item.get("title", "Opportunity")),
                        confidence="medium",
                        truth_status="inferred",
                        stage=str(item.get("stage", "open")),
                        deal_value=item.get("deal_value"),
                        last_activity_at=str(item.get("last_activity_at", "")),
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        "growth-lane:pipeline",
                        f"lead:{lead_id}",
                        "tracks",
                        confidence="medium",
                        truth_status="inferred",
                    )
                )
            for item in list((marketing_state.get("campaigns") or []))[:8]:
                asset_id = str(item.get("campaign_id", "")).strip() or str(uuid.uuid4())
                nodes.append(
                    self._world_graph_node(
                        "asset",
                        asset_id,
                        str(item.get("title", "Campaign")),
                        confidence="medium",
                        truth_status="inferred",
                        status=str(item.get("status", "planned")),
                        offer_link=str(item.get("offer_link", "")),
                        age_days=item.get("age_days"),
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        "growth-lane:marketing",
                        f"asset:{asset_id}",
                        "supports",
                        confidence="medium",
                        truth_status="inferred",
                    )
                )
            for loop in list((cadence.get("loops") or []))[:6]:
                loop_id = str(loop.get("id", "")).strip() or str(uuid.uuid4())
                nodes.append(
                    self._world_graph_node(
                        "routine",
                        loop_id,
                        str(loop.get("label", "Cadence Loop")),
                        confidence="high",
                        truth_status="observed",
                        phase=str(cadence.get("phase", "")),
                        state=str(loop.get("state", "")),
                        purpose=str(loop.get("purpose", "")),
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        f"person:{actor.user_id}",
                        f"routine:{loop_id}",
                        "scheduled-by",
                        confidence="high",
                        truth_status="observed",
                    )
                )
            risks: list[dict[str, Any]] = []
            low_cash_warning = dict((finance_state.get("thresholds") or {}).get("low_cash_warning") or {})
            if str(low_cash_warning.get("status", "")).strip().lower() == "warning":
                risks.append(
                    {
                        "id": "finance-low-cash",
                        "label": str(low_cash_warning.get("summary", "")).strip() or "Finance runway warning",
                        "target": "growth-lane:financial",
                        "truth_status": "inferred",
                        "confidence": "medium",
                    }
                )
            for stalled in list(pipeline_state.get("stalled_opportunities") or [])[:4]:
                lead_id = str(stalled.get("opportunity_id", "")).strip()
                title = str(stalled.get("title", "Stalled opportunity")).strip()
                risks.append(
                    {
                        "id": f"pipeline-stalled-{lead_id or title.lower().replace(' ', '-')}",
                        "label": f"{title} is stale in the pipeline.",
                        "target": f"lead:{lead_id}" if lead_id else "growth-lane:pipeline",
                        "truth_status": "inferred",
                        "confidence": "medium",
                    }
                )
            for campaign in list(marketing_state.get("stale_campaigns") or [])[:4]:
                campaign_id = str(campaign.get("campaign_id", "")).strip()
                title = str(campaign.get("title", "Campaign")).strip()
                risks.append(
                    {
                        "id": f"marketing-stale-{campaign_id or title.lower().replace(' ', '-')}",
                        "label": f"{title} is losing momentum and should be refreshed.",
                        "target": f"asset:{campaign_id}" if campaign_id else "growth-lane:marketing",
                        "truth_status": "inferred",
                        "confidence": "medium",
                    }
                )
            for risk in risks:
                nodes.append(
                    self._world_graph_node(
                        "risk",
                        str(risk["id"]),
                        str(risk["label"]),
                        confidence=str(risk.get("confidence", "medium")),
                        truth_status=str(risk.get("truth_status", "inferred")),
                    )
                )
                edges.append(
                    self._world_graph_edge(
                        str(risk["target"]),
                        f"risk:{risk['id']}",
                        "at-risk-from",
                        confidence=str(risk.get("confidence", "medium")),
                        truth_status=str(risk.get("truth_status", "inferred")),
                    )
                )
            entity_counts = {item["id"]: 0 for item in schema["entity_types"]}
            for node in nodes:
                key = str(node.get("entity_type", "")).strip()
                if key:
                    entity_counts[key] = int(entity_counts.get(key, 0) or 0) + 1
            edge_counts = {item["id"]: 0 for item in schema["edge_types"]}
            for edge in edges:
                key = str(edge.get("edge_type", "")).strip()
                if key:
                    edge_counts[key] = int(edge_counts.get(key, 0) or 0) + 1
            return {
                "actor": actor.display_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "schema": schema,
                "summary": {
                    "people": len([node for node in nodes if node.get("entity_type") == "person"]),
                    "rooms": len([node for node in nodes if node.get("entity_type") == "room"]),
                    "devices": len([node for node in nodes if node.get("entity_type") == "device"]),
                    "events": len([node for node in nodes if node.get("entity_type") == "event"]),
                    "tasks": len([node for node in nodes if node.get("entity_type") == "task"]),
                    "approvals": len([node for node in nodes if node.get("entity_type") == "approval"]),
                    "notifications": len([node for node in nodes if node.get("entity_type") == "notification"]),
                    "growth_lanes": len([node for node in nodes if node.get("entity_type") == "growth-lane"]),
                    "growth_signals": len([node for node in nodes if node.get("entity_type") == "growth-signal"]),
                    "accounts": len([node for node in nodes if node.get("entity_type") == "account"]),
                    "leads": len([node for node in nodes if node.get("entity_type") == "lead"]),
                    "assets": len([node for node in nodes if node.get("entity_type") == "asset"]),
                    "routines": len([node for node in nodes if node.get("entity_type") == "routine"]),
                    "risks": len([node for node in nodes if node.get("entity_type") == "risk"]),
                    "entity_counts": entity_counts,
                    "edge_counts": edge_counts,
                    "edges": len(edges),
                },
                "nodes": nodes,
                "edges": edges,
            }

        if not use_cache:
            return builder()
        return self._cached_surface("world_graph", actor_name, builder)

    def _world_state_reasoning(self, actor: UserProfile, *, open_loops: dict | None = None, world_events: list[dict] | None = None) -> dict:
        working_open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
        items = list(working_open_loops.get("items", []))
        summary = dict(working_open_loops.get("summary", {}))
        unread_notifications = self.assistant_notifications(actor.display_name, limit=6, unread_only=True)
        unread_count = int((unread_notifications.get("summary") or {}).get("unread", 0) or 0)
        world_events = list(world_events or [])
        calendar = self._actor_calendar_events(actor, limit=8)
        by_domain = dict(summary.get("by_domain", {}))

        blocked_work: list[dict[str, Any]] = []
        seen_blocked: set[str] = set()
        for item in items:
            status = str(item.get("status", "")).strip().lower()
            if status not in {"pending", "pending-approval"}:
                continue
            item_key = f"{str(item.get('domain', '')).strip().lower()}::{str(item.get('item_id', '')).strip()}"
            if item_key in seen_blocked:
                continue
            seen_blocked.add(item_key)
            blocked_work.append(
                {
                    "domain": str(item.get("domain", "")).strip().lower() or "general",
                    "title": str(item.get("title", "Blocked work")).strip() or "Blocked work",
                    "reason": str(item.get("next_action", "")).strip() or "Waiting on an approval or decision before it can move.",
                    "severity": "high" if status == "pending-approval" else "medium",
                    "owner_agent": str(item.get("owner_agent", "JARVIS")).strip() or "JARVIS",
                }
            )
            if len(blocked_work) >= 6:
                break

        hidden_load: list[dict[str, Any]] = []
        hidden_deferred = int(summary.get("hidden_deferred", 0) or 0)
        revisit_count = int(summary.get("needs_revisit", 0) or 0)
        waiting_count = int(summary.get("waiting_on_you", 0) or 0)
        if hidden_deferred:
            hidden_load.append(
                {
                    "type": "deferred",
                    "severity": "medium" if hidden_deferred < 4 else "high",
                    "summary": f"{hidden_deferred} deferred item(s) are still carrying pressure behind the visible queue.",
                }
            )
        if unread_count >= 3:
            hidden_load.append(
                {
                    "type": "assistant-inbox",
                    "severity": "medium" if unread_count < 6 else "high",
                    "summary": f"{unread_count} unread assistant item(s) are competing for attention outside the visible top tasks.",
                }
            )
        if revisit_count >= 4 and int(summary.get("total", 0) or 0) <= 8:
            hidden_load.append(
                {
                    "type": "aging-work",
                    "severity": "medium",
                    "summary": f"{revisit_count} aging item(s) are creating more drag than the visible queue size suggests.",
                }
            )
        if waiting_count >= 3 and unread_count >= 2:
            hidden_load.append(
                {
                    "type": "decision-fatigue",
                    "severity": "high",
                    "summary": "Decisions are stacking in both the open-loop queue and the assistant inbox.",
                }
            )

        pressure_clusters: list[dict[str, Any]] = []
        for domain, count in sorted(by_domain.items(), key=lambda entry: (-int(entry[1] or 0), entry[0])):
            domain_items = [item for item in items if str(item.get("domain", "")).strip().lower() == str(domain).strip().lower()]
            aging = sum(1 for item in domain_items if bool(item.get("needs_revisit")))
            blocked = sum(1 for item in domain_items if str(item.get("status", "")).strip().lower() in {"pending", "pending-approval"})
            strength = "high" if blocked or int(count or 0) >= 4 else ("medium" if aging or int(count or 0) >= 2 else "low")
            if int(count or 0) <= 0:
                continue
            pressure_clusters.append(
                {
                    "domain": str(domain).strip().lower(),
                    "count": int(count or 0),
                    "aging": aging,
                    "blocked": blocked,
                    "strength": strength,
                    "summary": f"{str(domain).title()} is carrying {int(count or 0)} visible item(s), with {aging} aging and {blocked} blocked.",
                }
            )
        pressure_clusters = pressure_clusters[:5]

        conflicts: list[dict[str, Any]] = []
        parsed_events = []
        for event in calendar:
            parsed_start = self._parse_timestamp(str(event.get("start", "")).strip())
            if parsed_start is None:
                continue
            parsed_events.append((parsed_start.astimezone(timezone.utc), event))
        parsed_events.sort(key=lambda item: item[0])
        for left, right in zip(parsed_events, parsed_events[1:]):
            delta_minutes = (right[0] - left[0]).total_seconds() / 60
            if delta_minutes <= 90:
                conflicts.append(
                    {
                        "type": "schedule",
                        "severity": "medium",
                        "summary": f"Calendar pressure is compressed between {str(left[1].get('summary', 'an event')).strip()} and {str(right[1].get('summary', 'the next event')).strip()}.",
                        "domains": ["calendar", "family"] if by_domain.get("family") else ["calendar"],
                    }
                )
                break
        if waiting_count >= 3 and unread_count >= 2:
            conflicts.append(
                {
                    "type": "attention",
                    "severity": "high",
                    "summary": "Attention is split between queued decisions and fresh assistant nudges.",
                    "domains": ["approvals", "assistant-inbox"],
                }
            )
        family_due = any(
            str(item.get("domain", "")).strip().lower() == "family" and bool(item.get("needs_revisit"))
            for item in items
        )
        growth_due = any(
            str(item.get("domain", "")).strip().lower() == "growth"
            and (bool(item.get("growth_review_due")) or bool(item.get("needs_revisit")))
            for item in items
        )
        if family_due and growth_due:
            conflicts.append(
                {
                    "type": "growth-vs-family",
                    "severity": "medium",
                    "summary": "Family coordination and growth work both want the same attention window.",
                    "domains": ["family", "growth"],
                }
            )
        finance_pressure = any(
            str(item.get("domain", "")).strip().lower() == "growth"
            and str(item.get("growth_lane_id", "")).strip().lower() == "financial"
            and bool(item.get("growth_review_due") or item.get("needs_revisit"))
            for item in items
        )
        workshop_pressure = any(str(item.get("domain", "")).strip().lower() == "workshop" for item in items)
        if finance_pressure and workshop_pressure:
            conflicts.append(
                {
                    "type": "resource",
                    "severity": "medium",
                    "summary": "Workshop work is competing with financial review pressure for the same operational budget.",
                    "domains": ["workshop", "growth"],
                }
            )
        if not conflicts and world_events:
            high_event = next((item for item in world_events if str(item.get("significance", "")).strip().lower() == "high"), None)
            if high_event:
                conflicts.append(
                    {
                        "type": "state-shift",
                        "severity": "medium",
                        "summary": str(high_event.get("detail", "")).strip() or "A high-significance world event shifted the operating picture.",
                        "domains": [str(high_event.get("scope", "world")).strip().lower()],
                    }
                )

        likely_next: list[dict[str, Any]] = []
        top_item = dict(working_open_loops.get("top_item") or {})
        if top_item:
            likely_next.append(
                {
                    "title": str(top_item.get("title", "Open loop")).strip() or "Open loop",
                    "domain": str(top_item.get("domain", "")).strip().lower() or "general",
                    "confidence": "high" if bool(top_item.get("needs_revisit")) else "medium",
                    "reason": str(top_item.get("next_action", "")).strip() or "This is the strongest visible item in the current queue.",
                }
            )
        for conflict in conflicts[:2]:
            likely_next.append(
                {
                    "title": str(conflict.get("summary", "Resolve conflict")).strip(),
                    "domain": ",".join(list(conflict.get("domains", []))[:2]) or "world",
                    "confidence": "medium",
                    "reason": f"Conflict signal: {str(conflict.get('type', 'world')).strip()}",
                }
            )
        for cluster in pressure_clusters[:2]:
            cluster_domain = str(cluster.get("domain", "")).strip().lower()
            if any(str(item.get("domain", "")).strip().lower() == cluster_domain for item in likely_next):
                continue
            likely_next.append(
                {
                    "title": f"Stabilize {cluster_domain.title()} pressure",
                    "domain": cluster_domain,
                    "confidence": "medium" if str(cluster.get("strength", "low")) != "low" else "low",
                    "reason": str(cluster.get("summary", "")).strip(),
                }
            )
        seen_next: set[str] = set()
        deduped_likely_next: list[dict[str, Any]] = []
        for item in likely_next:
            signature = f"{str(item.get('domain', '')).strip().lower()}::{str(item.get('title', '')).strip().lower()}"
            if signature in seen_next:
                continue
            seen_next.add(signature)
            deduped_likely_next.append(item)
            if len(deduped_likely_next) >= 4:
                break

        return {
            "blocked_work": blocked_work,
            "hidden_load": hidden_load,
            "pressure_clusters": pressure_clusters,
            "conflicts": conflicts[:4],
            "likely_next": deduped_likely_next,
        }

    def world_state_snapshot(self, actor_name: str = "Chris", *, open_loops: dict | None = None, persist: bool = False) -> dict:
        actor = self.get_actor(actor_name)
        graph = self.world_graph_snapshot(actor.display_name, open_loops=open_loops)
        if persist:
            record = self.assistant_core_store.save_world_graph(actor.display_name, graph)
        else:
            record = self.assistant_core_store.world_graph_record(actor.display_name) or {}
        current_summary = dict(graph.get("summary", {}))
        stored_summary = dict(record.get("summary", {})) if isinstance(record.get("summary", {}), dict) else current_summary
        delta = dict(record.get("delta", {})) if isinstance(record.get("delta", {}), dict) else {}
        count_delta = dict(delta.get("count_delta", {})) if isinstance(delta.get("count_delta", {}), dict) else {}
        world_events = self.assistant_core_store.list_world_events(actor.display_name, limit=8)
        volatility = sum(abs(int(value)) for value in count_delta.values())
        pressure = "steady"
        if volatility >= 5:
            pressure = "shifting"
        elif volatility >= 1:
            pressure = "changed"
        event_summary = {
            "recent_count": len(world_events),
            "high_significance": sum(1 for item in world_events if str(item.get("significance", "")).strip().lower() == "high"),
            "deduped_repeats": sum(max(int(item.get("occurrence_count", 1) or 1) - 1, 0) for item in world_events),
            "categories": {},
        }
        for item in world_events:
            category = str(item.get("category", "general")).strip().lower() or "general"
            event_summary["categories"][category] = int(event_summary["categories"].get(category, 0) or 0) + 1
        reasoning = self._world_state_reasoning(
            actor,
            open_loops=open_loops,
            world_events=world_events,
        )
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": current_summary or stored_summary,
            "pressure": pressure,
            "delta": {
                "count_delta": count_delta,
                "added_labels": list(delta.get("added_labels", []))[:6],
                "removed_labels": list(delta.get("removed_labels", []))[:6],
            },
            "event_summary": event_summary,
            "events": world_events,
            "blocked_work": reasoning.get("blocked_work", []),
            "hidden_load": reasoning.get("hidden_load", []),
            "pressure_clusters": reasoning.get("pressure_clusters", []),
            "conflicts": reasoning.get("conflicts", []),
            "likely_next": reasoning.get("likely_next", []),
            "history": self.assistant_core_store.world_graph_history(actor.display_name, limit=6),
        }

    def growth_state_snapshot(self, actor_name: str = "Chris") -> dict:
        actor = self.get_actor(actor_name)
        actor_keys = {actor.display_name.strip().lower(), actor.user_id.strip().lower()}

        def _matches_actor(record: dict[str, Any]) -> bool:
            value = str(record.get("actor", "")).strip().lower()
            return not value or value in actor_keys

        def _unique(values: list[str], limit: int = 6) -> list[str]:
            return _merge_unique([], values, limit=limit)

        content_snapshot = self.content_ops.snapshot()
        content_queue = [item for item in content_snapshot.get("queue", []) if _matches_actor(item)]
        active_content = [item for item in content_queue if str(item.get("status", "")).strip().lower() not in {"archived", "live"}]
        queued_count = sum(1 for item in active_content if str(item.get("status", "")).strip().lower() == "queued")
        scripted_count = sum(1 for item in active_content if str(item.get("status", "")).strip().lower() == "scripted")
        exported_count = sum(1 for item in content_queue if str(item.get("status", "")).strip().lower() == "exported")
        live_count = sum(1 for item in content_queue if str(item.get("status", "")).strip().lower() == "live")
        latest_content = active_content[0] if active_content else (content_queue[0] if content_queue else {})

        wealth_summary = self.wealth_support.summary(limit=8)
        wealth_runs = [item for item in wealth_summary.get("recent_runs", []) if _matches_actor(item)]
        opportunity_theses = _unique(list(wealth_summary.get("opportunity_theses", [])), limit=5)
        experiments = _unique(list(wealth_summary.get("experiments_in_flight", [])), limit=4)
        roi_lessons = _unique(list(wealth_summary.get("roi_lessons", [])), limit=4)
        latest_wealth = wealth_runs[0] if wealth_runs else {}
        finance_state = self.finance_state_snapshot(actor.display_name, wealth_summary=wealth_summary)
        finance_scorecard = dict(finance_state.get("scorecard") or {})
        marketing_state = self.marketing_state_snapshot(actor.display_name, content_snapshot=content_snapshot)
        marketing_scorecard = dict(marketing_state.get("scorecard") or {})
        pipeline_state = self.pipeline_state_snapshot(actor.display_name)
        pipeline_scorecard = dict(pipeline_state.get("scorecard") or {})

        catalyst_store = self.catalyst_support.store
        catalyst_signals = [item for item in catalyst_store.list_signals(limit=16) if _matches_actor(item)]
        project_briefs = [item for item in catalyst_store.list_records(catalyst_store.project_briefs_path, limit=10) if _matches_actor(item)]
        implementation_plans = [item for item in catalyst_store.list_records(catalyst_store.implementation_plans_path, limit=10) if _matches_actor(item)]
        briefings = [item for item in catalyst_store.list_records(catalyst_store.briefing_path, limit=8) if _matches_actor(item)]
        recommended_focus: list[str] = []
        for item in briefings[:3]:
            recommended_focus.extend(item.get("recommended_focus", []) or [])
        signal_titles = _unique([str(item.get("title", "")) for item in catalyst_signals], limit=4)

        pipeline_pressure_score = len(catalyst_signals[:4]) + len(project_briefs[:2]) + len(implementation_plans[:2])
        if pipeline_pressure_score >= 5:
            pipeline_pressure = "active"
        elif pipeline_pressure_score >= 2:
            pipeline_pressure = "warming"
        else:
            pipeline_pressure = "quiet"

        if wealth_runs or experiments or opportunity_theses:
            financial_pressure = "active" if experiments or len(opportunity_theses) >= 3 else "warming"
        else:
            financial_pressure = "quiet"

        if queued_count or scripted_count:
            marketing_pressure = "active"
        elif exported_count or live_count:
            marketing_pressure = "warming"
        else:
            marketing_pressure = "quiet"

        schema = growth_schema_snapshot()
        lane_pressure_rank = {"active": 3, "warming": 2, "quiet": 1}

        domain_snapshots = [
            GrowthDomainSnapshot(
                id="finance",
                label="Finance",
                description="Cash posture, runway, revenue-adjacent progress, and ROI lessons.",
                pressure=financial_pressure,
                confidence=str(finance_scorecard.get("confidence", "medium" if wealth_runs else "low")),
                summary=str(finance_scorecard.get("summary", "")).strip() or f"{len(wealth_runs)} recent workflow(s) · {len(opportunity_theses)} thesis(es) · {len(roi_lessons)} ROI lesson(s)",
                latest=str((finance_state.get("weekly_review") or {}).get("summary", "")).strip() or str(latest_wealth.get("request", "")).strip() or "No recent financial workflow is staged.",
                latest_timestamp=str((finance_state.get("weekly_review") or {}).get("last_reviewed_at", "")).strip() or str(latest_wealth.get("timestamp", "")).strip(),
                live=False,
                source_adapter_id="revenue",
                source_count=len(wealth_runs),
                metrics={
                    "recent_runs": len(wealth_runs),
                    "opportunity_theses": len(opportunity_theses),
                    "roi_lessons": len(roi_lessons),
                    "runway_months": (finance_state.get("derived") or {}).get("runway_months"),
                    "passive_income_progress_ratio": (finance_state.get("derived") or {}).get("passive_income_progress_ratio"),
                    "low_cash_status": ((finance_state.get("thresholds") or {}).get("low_cash_warning") or {}).get("status", "unknown"),
                },
                signals=_unique(opportunity_theses[:3] + roi_lessons[:2], limit=5),
                next_moves=_unique(experiments[:2], limit=3),
                truth_note="Finance telemetry mixes local finance-state planning data with inferred wealth workflows until live account connectors are wired.",
            ),
            GrowthDomainSnapshot(
                id="pipeline",
                label="Pipeline",
                description="Sales pipeline movement, project briefs, and implementation readiness.",
                pressure=pipeline_pressure,
                confidence=str(pipeline_scorecard.get("confidence", "medium" if catalyst_signals else "low")),
                summary=str(pipeline_scorecard.get("summary", "")).strip() or f"{len(catalyst_signals)} signal(s) · {len(project_briefs)} brief(s) · {len(implementation_plans)} implementation plan(s)",
                latest=(
                    str((pipeline_state.get("daily_followup_loop") or {}).get("summary", "")).strip()
                    or (signal_titles[0] if signal_titles else "No explicit CRM or revenue feed is connected yet.")
                ),
                latest_timestamp=str((pipeline_state.get("daily_followup_loop") or {}).get("last_reviewed_at", "")).strip() or str((catalyst_signals[0] if catalyst_signals else {}).get("timestamp", "")).strip(),
                live=False,
                source_adapter_id="pipeline",
                source_count=len(catalyst_signals) + len(project_briefs) + len(implementation_plans),
                metrics={
                    "signals": len(catalyst_signals),
                    "project_briefs": len(project_briefs),
                    "implementation_plans": len(implementation_plans),
                    "active_opportunities": len(pipeline_state.get("opportunities") or []),
                    "stalled_opportunities": len(pipeline_state.get("stalled_opportunities") or []),
                    "daily_followup_due": bool((pipeline_state.get("daily_followup_loop") or {}).get("due")),
                    "weekly_review_due": bool((pipeline_state.get("weekly_review") or {}).get("due")),
                },
                signals=_unique(signal_titles + [str(item.get("title", "")) for item in (pipeline_state.get("stalled_opportunities") or [])] + _unique(recommended_focus, limit=2), limit=5),
                next_moves=_unique(list(pipeline_state.get("recommended_actions") or [])[:3], limit=3),
                truth_note="Pipeline telemetry is currently inferred from Catalyst artifacts instead of a live CRM connector.",
            ),
            GrowthDomainSnapshot(
                id="marketing",
                label="Marketing",
                description="Audience-facing momentum, campaign readiness, and market-facing visibility.",
                pressure=marketing_pressure,
                confidence=str(marketing_scorecard.get("confidence", "medium" if content_queue else "low")),
                summary=str(marketing_scorecard.get("summary", "")).strip() or f"{queued_count} queued campaign asset(s) · {exported_count} exported · {live_count} live",
                latest=str((marketing_state.get("weekly_review") or {}).get("summary", "")).strip() or str(latest_content.get("title", "")).strip() or "No market-facing asset is staged.",
                latest_timestamp=str((marketing_state.get("weekly_review") or {}).get("last_reviewed_at", "")).strip() or str(latest_content.get("updated_at", "") or latest_content.get("created_at", "")).strip(),
                live=False,
                source_adapter_id="audience-growth",
                source_count=len(active_content),
                metrics={
                    "queued_assets": queued_count,
                    "exported_assets": exported_count,
                    "live_assets": live_count,
                    "audience_signals": len(marketing_state.get("audience_signals") or []),
                    "campaigns": len(((marketing_state.get("state") or {}).get("campaigns") or [])),
                    "leverage_score": (marketing_state.get("scorecard") or {}).get("score"),
                },
                signals=_unique([str(latest_content.get("title", "")).strip()] + list(marketing_state.get("audience_signals") or [])[:3] + _unique(recommended_focus, limit=2), limit=5),
                next_moves=_unique(list(marketing_state.get("recommended_actions") or [])[:3], limit=4),
                truth_note="Marketing telemetry is still inferred from local content throughput until audience-growth connectors are wired.",
            ),
            GrowthDomainSnapshot(
                id="content",
                label="Content",
                description="Operational content production state from queued through live.",
                pressure=marketing_pressure,
                confidence="medium" if content_queue else "low",
                summary=f"{queued_count} queued · {scripted_count} scripted · {exported_count} exported · {live_count} live",
                latest=str(latest_content.get("title", "")).strip() or "No active content package is staged.",
                latest_timestamp=str(latest_content.get("updated_at", "") or latest_content.get("created_at", "")).strip(),
                live=bool(content_queue),
                source_adapter_id="content-output",
                source_count=len(content_queue),
                metrics={
                    "queued_assets": queued_count,
                    "scripted_assets": scripted_count,
                    "exported_assets": exported_count,
                    "live_assets": live_count,
                },
                signals=_unique([str(item.get("title", "")).strip() for item in active_content[:4]], limit=4),
                next_moves=_unique([str(item.get("title", "")).strip() for item in active_content[:3]], limit=3),
                truth_note="Content output is live inside JARVIS from local content operations, even though external performance telemetry is still limited.",
            ),
            GrowthDomainSnapshot(
                id="experiments",
                label="Experiments",
                description="Leverage-building experiments, tests in flight, and recent findings.",
                pressure="active" if experiments else ("warming" if wealth_runs else "quiet"),
                confidence="medium" if experiments else ("low" if not wealth_runs else "medium"),
                summary=f"{len(experiments)} experiment(s) in flight · {len(roi_lessons)} lesson(s) captured",
                latest=experiments[0] if experiments else "No active leverage experiment is staged.",
                latest_timestamp=str(latest_wealth.get("timestamp", "")).strip(),
                live=False,
                source_adapter_id="experiments",
                source_count=len(experiments),
                metrics={
                    "experiments_in_flight": len(experiments),
                    "recent_runs": len(wealth_runs),
                    "roi_lessons": len(roi_lessons),
                },
                signals=_unique(experiments[:3] + roi_lessons[:2], limit=5),
                next_moves=_unique(experiments[:3], limit=3),
                truth_note="Experiment telemetry is currently inferred from local wealth workflow memory rather than a dedicated experimentation system.",
            ),
            GrowthDomainSnapshot(
                id="offers",
                label="Offers",
                description="Offer hypotheses, opportunity theses, and packaged next moves worth testing.",
                pressure="active" if len(opportunity_theses) >= 3 else ("warming" if opportunity_theses or recommended_focus else "quiet"),
                confidence="medium" if opportunity_theses or recommended_focus else "low",
                summary=f"{len(opportunity_theses)} opportunity thesis(es) · {len(recommended_focus[:4])} recommended focus item(s)",
                latest=opportunity_theses[0] if opportunity_theses else (_unique(recommended_focus, limit=1)[0] if _unique(recommended_focus, limit=1) else "No explicit offer hypothesis is staged yet."),
                latest_timestamp=str(latest_wealth.get("timestamp", "")).strip() or str((briefings[0] if briefings else {}).get("timestamp", "")).strip(),
                live=False,
                source_adapter_id="offers",
                source_count=len(opportunity_theses) + len(recommended_focus[:4]),
                metrics={
                    "tracked_offers": len(opportunity_theses),
                    "recommended_focus": len(recommended_focus[:4]),
                    "project_briefs": len(project_briefs),
                },
                signals=_unique(opportunity_theses[:3] + _unique(recommended_focus, limit=3), limit=5),
                next_moves=_unique(_unique(recommended_focus, limit=3) + experiments[:2], limit=4),
                truth_note="Offer telemetry is currently inferred from opportunity theses and Catalyst focus recommendations.",
            ),
        ]

        domain_map = {item.id: item for item in domain_snapshots}

        def _lane_pressure(domain_ids: list[str]) -> str:
            pressures = [domain_map[domain_id].pressure for domain_id in domain_ids if domain_id in domain_map]
            if not pressures:
                return "quiet"
            return max(pressures, key=lambda pressure: lane_pressure_rank.get(pressure, 0))

        def _lane_confidence(domain_ids: list[str]) -> str:
            confidence_rank = {"low": 1, "medium": 2, "high": 3}
            confidences = [domain_map[domain_id].confidence for domain_id in domain_ids if domain_id in domain_map]
            if not confidences:
                return "low"
            return max(confidences, key=lambda value: confidence_rank.get(value, 0))

        lane_snapshots = [
            GrowthLaneSnapshot(
                id="financial",
                label="Financial Independence",
                pressure=_lane_pressure(["finance", "experiments", "offers"]),
                confidence=_lane_confidence(["finance", "experiments", "offers"]),
                summary=f"{len(opportunity_theses)} thesis(es) tracked · {len(experiments)} experiment(s) in flight",
                latest=domain_map["finance"].latest or domain_map["offers"].latest,
                latest_timestamp=domain_map["finance"].latest_timestamp or domain_map["offers"].latest_timestamp,
                domain_ids=["finance", "experiments", "offers"],
            ),
            GrowthLaneSnapshot(
                id="marketing",
                label="Content and Marketing Engine",
                pressure=_lane_pressure(["content", "marketing"]),
                confidence=_lane_confidence(["content", "marketing"]),
                summary=str((marketing_state.get("scorecard") or {}).get("summary", "")).strip() or f"{queued_count} queued · {scripted_count} scripted · {exported_count} exported · {live_count} live",
                latest=domain_map["content"].latest or domain_map["marketing"].latest,
                latest_timestamp=domain_map["content"].latest_timestamp or domain_map["marketing"].latest_timestamp,
                domain_ids=["content", "marketing"],
            ),
            GrowthLaneSnapshot(
                id="pipeline",
                label="Sales and Pipeline Posture",
                pressure=_lane_pressure(["pipeline", "offers"]),
                confidence=_lane_confidence(["pipeline", "offers"]),
                summary=str((pipeline_state.get("scorecard") or {}).get("summary", "")).strip() or f"{len(catalyst_signals)} signal(s) · {len(project_briefs)} project brief(s) · {len(implementation_plans)} implementation plan(s)",
                latest=domain_map["pipeline"].latest or domain_map["offers"].latest,
                latest_timestamp=domain_map["pipeline"].latest_timestamp or domain_map["offers"].latest_timestamp,
                domain_ids=["pipeline", "offers"],
            ),
        ]

        adapter_snapshots = [
            GrowthAdapterSnapshot(
                id="revenue",
                label="Revenue Adapter",
                source_kind="wealth-workflows",
                domain_ids=["finance"],
                status="inferred" if wealth_runs else "planned",
                live=False,
                record_count=len(wealth_runs),
                latest_timestamp=str(latest_wealth.get("timestamp", "")).strip(),
                note="Currently inferred from local wealth workflows until live financial telemetry is wired.",
            ),
            GrowthAdapterSnapshot(
                id="pipeline",
                label="Pipeline Adapter",
                source_kind="catalyst",
                domain_ids=["pipeline"],
                status="inferred" if catalyst_signals or project_briefs or implementation_plans else "planned",
                live=False,
                record_count=len(catalyst_signals) + len(project_briefs) + len(implementation_plans),
                latest_timestamp=str((catalyst_signals[0] if catalyst_signals else {}).get("timestamp", "")).strip(),
                note="Currently inferred from local Catalyst records instead of a CRM connector.",
            ),
            GrowthAdapterSnapshot(
                id="content-output",
                label="Content Output Adapter",
                source_kind="content-ops",
                domain_ids=["content", "marketing"],
                status="live-local" if content_queue else "planned",
                live=bool(content_queue),
                record_count=len(content_queue),
                latest_timestamp=str(latest_content.get("updated_at", "") or latest_content.get("created_at", "")).strip(),
                note="Local content operations are live inside JARVIS even though external performance telemetry is still limited.",
            ),
            GrowthAdapterSnapshot(
                id="audience-growth",
                label="Audience Growth Adapter",
                source_kind="audience-telemetry",
                domain_ids=["marketing"],
                status="planned",
                live=False,
                record_count=0,
                latest_timestamp="",
                note="No live audience-growth or ad-platform telemetry is wired yet.",
            ),
            GrowthAdapterSnapshot(
                id="experiments",
                label="Experiments Adapter",
                source_kind="wealth-workflows",
                domain_ids=["experiments"],
                status="inferred" if experiments else "planned",
                live=False,
                record_count=len(experiments),
                latest_timestamp=str(latest_wealth.get("timestamp", "")).strip(),
                note="Experiments are currently inferred from local wealth workflows and recommendation traces.",
            ),
            GrowthAdapterSnapshot(
                id="offers",
                label="Offers Adapter",
                source_kind="wealth-plus-catalyst",
                domain_ids=["offers"],
                status="inferred" if opportunity_theses or recommended_focus else "planned",
                live=False,
                record_count=len(opportunity_theses) + len(recommended_focus[:4]),
                latest_timestamp=str(latest_wealth.get("timestamp", "")).strip() or str((briefings[0] if briefings else {}).get("timestamp", "")).strip(),
                note="Offers are currently inferred from opportunity theses and Catalyst focus recommendations.",
            ),
            GrowthAdapterSnapshot(
                id="opportunity-theses",
                label="Opportunity Thesis Adapter",
                source_kind="wealth-workflows",
                domain_ids=["finance", "offers"],
                status="inferred" if opportunity_theses else "planned",
                live=False,
                record_count=len(opportunity_theses),
                latest_timestamp=str(latest_wealth.get("timestamp", "")).strip(),
                note="Opportunity theses are currently harvested from local wealth workflow memory.",
            ),
        ]

        top_signals = _unique(
            [signal for domain in domain_snapshots for signal in domain.signals],
            limit=8,
        )
        next_moves = _unique(
            [move for domain in domain_snapshots for move in domain.next_moves],
            limit=5,
        )
        overall_pressure = max(
            ({"pressure": lane.pressure} for lane in lane_snapshots),
            key=lambda item: lane_pressure_rank.get(str(item.get("pressure", "quiet")), 0),
        ).get("pressure", "quiet")

        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": schema.get("version", ""),
            "schema": schema,
            "summary": {
                "pressure": overall_pressure,
                "active_lane_count": sum(1 for lane in lane_snapshots if lane.pressure == "active"),
                "tracked_signal_count": len(top_signals),
                "tracked_domain_count": len(domain_snapshots),
                "live_adapter_count": sum(1 for adapter in adapter_snapshots if adapter.live),
                "configured_adapter_count": len(adapter_snapshots),
            },
            "domains": [item.to_dict() for item in domain_snapshots],
            "lanes": [item.to_dict() for item in lane_snapshots],
            "adapters": [item.to_dict() for item in adapter_snapshots],
            "top_signals": top_signals,
            "next_moves": next_moves,
            "truth": {
                "financial_live": any(item.id == "revenue" and item.live for item in adapter_snapshots),
                "sales_live": any(item.id == "pipeline" and item.live for item in adapter_snapshots),
                "marketing_live": any(item.id in {"content-output", "audience-growth"} and item.live for item in adapter_snapshots),
                "notes": [
                    "Growth telemetry now uses a canonical schema for finance, pipeline, marketing, content, experiments, and offers.",
                    "Live external finance, CRM, and audience connectors are still pending even though local telemetry sources are already mapped.",
                ],
            },
            "sources": {
                "wealth_runs": len(wealth_runs),
                "content_queue_items": len(content_queue),
                "catalyst_signals": len(catalyst_signals),
                "project_briefs": len(project_briefs),
                "implementation_plans": len(implementation_plans),
                "domain_count": len(domain_snapshots),
                "adapter_count": len(adapter_snapshots),
            },
            "latest_titles": {
                "wealth": str(latest_wealth.get("request", "")).strip(),
                "content": str(latest_content.get("title", "")).strip(),
                "pipeline": signal_titles[0] if signal_titles else "",
                "offers": domain_map["offers"].latest,
                "finance": domain_map["finance"].latest,
            },
            "latest_timestamps": {
                "wealth": str(latest_wealth.get("timestamp", "")).strip(),
                "content": str(latest_content.get("updated_at", "") or latest_content.get("created_at", "")).strip(),
                "pipeline": str((catalyst_signals[0] if catalyst_signals else {}).get("timestamp", "")).strip(),
                "offers": domain_map["offers"].latest_timestamp,
                "finance": domain_map["finance"].latest_timestamp,
            },
            "opportunity_theses": opportunity_theses,
            "experiments_in_flight": experiments,
            "roi_lessons": roi_lessons,
        }

    def growth_schema(self) -> dict:
        return growth_schema_snapshot()

    def finance_state_snapshot(self, actor_name: str = "Chris", *, wealth_summary: dict | None = None) -> dict:
        actor = self.get_actor(actor_name)
        wealth_summary = wealth_summary or self.wealth_support.summary(limit=8)
        state = dict(self.wealth_support.finance_state() or {})
        reviews = list(self.wealth_support.recent_finance_reviews(limit=8))
        recent_runs = list(wealth_summary.get("recent_runs", []))
        opportunity_theses = [str(item).strip() for item in list(wealth_summary.get("opportunity_theses", [])) if str(item).strip()]
        experiments = [str(item).strip() for item in list(wealth_summary.get("experiments_in_flight", [])) if str(item).strip()]
        roi_lessons = [str(item).strip() for item in list(wealth_summary.get("roi_lessons", [])) if str(item).strip()]

        cash_state = dict(state.get("cash") or {})
        goals = dict(state.get("goals") or {})
        thresholds = dict(state.get("thresholds") or {})
        spend_events = [item for item in list(state.get("spend_events", [])) if isinstance(item, dict)]

        def _num(value: Any) -> float | None:
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        available_cash = _num(cash_state.get("available"))
        reserve_target = _num(cash_state.get("reserve_target"))
        monthly_revenue = _num(cash_state.get("monthly_revenue"))
        monthly_burn = _num(cash_state.get("monthly_burn"))
        obligations_due = _num(cash_state.get("obligations_due_30d"))
        fi_target = _num(goals.get("financial_independence_target"))
        fi_current = _num(goals.get("current_financial_independence_value"))
        passive_target = _num(goals.get("passive_income_target_monthly"))
        passive_current = _num(goals.get("current_passive_income_monthly"))
        asset_target = _num(goals.get("compounding_asset_target"))
        asset_current = _num(goals.get("compounding_assets_live"))
        low_cash_threshold = _num(thresholds.get("low_cash_runway_months")) or 3.0
        unusual_spend_threshold = _num(thresholds.get("unusual_spend_amount")) or 1000.0
        goal_progress_min_ratio = _num(thresholds.get("goal_progress_min_ratio")) or 0.25

        runway_months = None
        if available_cash is not None and monthly_burn and monthly_burn > 0:
            runway_months = round(available_cash / monthly_burn, 2)
        reserve_gap = None
        if available_cash is not None and reserve_target is not None:
            reserve_gap = round(available_cash - reserve_target, 2)

        passive_income_progress_ratio = None
        if passive_target and passive_target > 0 and passive_current is not None:
            passive_income_progress_ratio = round(passive_current / passive_target, 4)
        fi_progress_ratio = None
        if fi_target and fi_target > 0 and fi_current is not None:
            fi_progress_ratio = round(fi_current / fi_target, 4)
        compounding_asset_progress_ratio = None
        if asset_target and asset_target > 0 and asset_current is not None:
            compounding_asset_progress_ratio = round(asset_current / asset_target, 4)

        now = datetime.now(timezone.utc)
        recent_unusual_spend = []
        for event in spend_events:
            amount = _num(event.get("amount"))
            if amount is None or amount < unusual_spend_threshold:
                continue
            event_time = self._parse_timestamp(str(event.get("timestamp", "")).strip())
            if event_time is None or event_time < now - timedelta(days=30):
                continue
            recent_unusual_spend.append(
                {
                    "timestamp": event_time.astimezone(timezone.utc).isoformat(),
                    "label": str(event.get("label", "Spend event")).strip() or "Spend event",
                    "amount": amount,
                }
            )

        def _status(score: int | None, *, unknown: bool = False) -> str:
            if unknown:
                return "unknown"
            if score is None:
                return "unknown"
            if score >= 80:
                return "healthy"
            if score >= 55:
                return "warming"
            return "warning"

        low_cash_status = "unknown"
        low_cash_summary = "Cash posture is not quantified yet."
        if runway_months is not None:
            if runway_months < low_cash_threshold:
                low_cash_status = "warning"
                low_cash_summary = f"Runway is about {runway_months:.1f} month(s), under the {low_cash_threshold:.1f}-month threshold."
            elif runway_months < low_cash_threshold + 1:
                low_cash_status = "warming"
                low_cash_summary = f"Runway is about {runway_months:.1f} month(s), close to the {low_cash_threshold:.1f}-month warning line."
            else:
                low_cash_status = "healthy"
                low_cash_summary = f"Runway is about {runway_months:.1f} month(s), above the {low_cash_threshold:.1f}-month threshold."

        unusual_spend_status = "warning" if recent_unusual_spend else ("unknown" if not spend_events else "healthy")
        unusual_spend_summary = (
            f"{len(recent_unusual_spend)} unusual spend event(s) crossed ${unusual_spend_threshold:,.0f} in the last 30 days."
            if recent_unusual_spend
            else ("No spend telemetry is wired yet." if not spend_events else "No unusual spend crossed the configured threshold recently.")
        )

        goal_progress_status = "unknown"
        goal_progress_summary = "Goal progress is not quantified yet."
        progress_candidates = [value for value in [passive_income_progress_ratio, fi_progress_ratio, compounding_asset_progress_ratio] if value is not None]
        if progress_candidates:
            best_progress = max(progress_candidates)
            if best_progress < goal_progress_min_ratio:
                goal_progress_status = "warning"
            elif best_progress < 0.6:
                goal_progress_status = "warming"
            else:
                goal_progress_status = "healthy"
            goal_progress_summary = f"Best quantified progress is {best_progress * 100:.0f}% against a configured target."

        score_components = [
            {
                "id": "cash-posture",
                "label": "Cash posture",
                "status": low_cash_status,
                "score": 85 if low_cash_status == "healthy" else 60 if low_cash_status == "warming" else 35 if low_cash_status == "warning" else None,
                "summary": low_cash_summary,
            },
            {
                "id": "goal-progress",
                "label": "Goal progress",
                "status": goal_progress_status,
                "score": 85 if goal_progress_status == "healthy" else 60 if goal_progress_status == "warming" else 35 if goal_progress_status == "warning" else None,
                "summary": goal_progress_summary,
            },
            {
                "id": "leverage-engine",
                "label": "Leverage engine",
                "status": "healthy" if experiments else ("warming" if opportunity_theses else "warning"),
                "score": 80 if experiments else 60 if opportunity_theses else 35,
                "summary": f"{len(opportunity_theses)} thesis(es), {len(experiments)} experiment(s), and {len(roi_lessons)} lesson(s) are currently tracked.",
            },
            {
                "id": "obligation-coverage",
                "label": "Obligation coverage",
                "status": "unknown" if available_cash is None or obligations_due is None else ("healthy" if available_cash >= obligations_due else "warning"),
                "score": None if available_cash is None or obligations_due is None else (80 if available_cash >= obligations_due else 30),
                "summary": (
                    "Obligations are not quantified yet."
                    if available_cash is None or obligations_due is None
                    else (f"Available cash covers the next 30-day obligations (${obligations_due:,.0f})." if available_cash >= obligations_due else f"Available cash does not fully cover the next 30-day obligations (${obligations_due:,.0f}).")
                ),
            },
        ]

        known_scores = [int(item["score"]) for item in score_components if item.get("score") is not None]
        overall_score = round(sum(known_scores) / len(known_scores)) if known_scores else 0
        if overall_score >= 80:
            overall_band = "tracking"
        elif overall_score >= 55:
            overall_band = "building"
        elif known_scores:
            overall_band = "at-risk"
        else:
            overall_band = "unscored"

        weekly_history = [
            {
                "completed_at": str(item.get("completed_at", "")).strip(),
                "summary": str(item.get("summary", "")).strip(),
                "score": item.get("score"),
                "band": str(item.get("band", "")).strip(),
                "note": str(item.get("note", "")).strip(),
            }
            for item in reviews
        ]
        last_reviewed_at = weekly_history[0]["completed_at"] if weekly_history else ""
        last_review_dt = self._parse_timestamp(last_reviewed_at)
        next_review_at = ((last_review_dt or now) + timedelta(days=7)).astimezone(timezone.utc).isoformat()
        weekly_due = last_review_dt is None or last_review_dt <= now - timedelta(days=7)
        weekly_summary = (
            "Weekly money review is due now."
            if weekly_due
            else f"Weekly money review was completed recently and comes due again around {next_review_at[:10]}."
        )

        return {
            "actor": actor.display_name,
            "generated_at": now.isoformat(),
            "state": {
                "cash": cash_state,
                "goals": goals,
                "thresholds": thresholds,
                "spend_events": spend_events,
                "notes": list(state.get("notes", [])),
            },
            "derived": {
                "runway_months": runway_months,
                "reserve_gap": reserve_gap,
                "passive_income_progress_ratio": passive_income_progress_ratio,
                "financial_independence_progress_ratio": fi_progress_ratio,
                "compounding_asset_progress_ratio": compounding_asset_progress_ratio,
            },
            "thresholds": {
                "low_cash_warning": {
                    "status": low_cash_status,
                    "summary": low_cash_summary,
                    "threshold_months": low_cash_threshold,
                    "runway_months": runway_months,
                },
                "unusual_spend": {
                    "status": unusual_spend_status,
                    "summary": unusual_spend_summary,
                    "threshold_amount": unusual_spend_threshold,
                    "events": recent_unusual_spend,
                },
                "goal_progress": {
                    "status": goal_progress_status,
                    "summary": goal_progress_summary,
                    "minimum_ratio": goal_progress_min_ratio,
                    "passive_income_ratio": passive_income_progress_ratio,
                    "financial_independence_ratio": fi_progress_ratio,
                    "compounding_asset_ratio": compounding_asset_progress_ratio,
                },
            },
            "scorecard": {
                "score": overall_score,
                "band": overall_band,
                "confidence": "medium" if known_scores else "low",
                "summary": (
                    "The finance lane is building, but it still needs more live numbers to become a strong operating model."
                    if overall_band == "building"
                    else "The finance lane has enough signal to support weekly review."
                    if overall_band == "tracking"
                    else "Finance state still needs more real numbers before JARVIS can score it confidently."
                    if overall_band == "unscored"
                    else "The finance lane is under pressure and should be reviewed before the next week rolls forward."
                ),
                "components": score_components,
            },
            "wealth_context": {
                "recent_runs": len(recent_runs),
                "opportunity_theses": opportunity_theses[:6],
                "experiments_in_flight": experiments[:6],
                "roi_lessons": roi_lessons[:6],
            },
            "weekly_review": {
                "label": "Weekly Money Review",
                "cadence": "weekly",
                "due": weekly_due,
                "summary": weekly_summary,
                "last_reviewed_at": last_reviewed_at,
                "next_review_at": next_review_at,
                "history_count": len(weekly_history),
            },
            "history": weekly_history[:6],
            "truth": {
                "financial_live": False,
                "notes": [
                    "Finance state currently mixes local planning values with inferred wealth workflow signals.",
                    "Live institutions and account telemetry are not connected yet.",
                ],
            },
        }

    def finance_review(self, actor_name: str = "Chris") -> dict:
        def builder() -> dict:
            finance_state = self.finance_state_snapshot(actor_name)
            growth = self.growth_state_snapshot(actor_name)
            scorecard = dict(finance_state.get("scorecard") or {})
            thresholds = dict(finance_state.get("thresholds") or {})
            weekly_review = dict(finance_state.get("weekly_review") or {})
            wealth_context = dict(finance_state.get("wealth_context") or {})
            top_moves = _merge_unique(
                list(wealth_context.get("experiments_in_flight", []))[:2],
                list(growth.get("next_moves", []))[:3],
                limit=4,
            )
            summary = str(scorecard.get("summary", "")).strip() or "Finance review is standing by."
            return {
                "actor": actor_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "title": "Finance Review",
                "summary": summary,
                "scorecard": scorecard,
                "weekly_review": weekly_review,
                "thresholds": thresholds,
                "state": finance_state.get("state") or {},
                "derived": finance_state.get("derived") or {},
                "history": finance_state.get("history") or [],
                "recommended_next_move": top_moves[0] if top_moves else "Capture real cash, burn, and target values so JARVIS can score the lane more honestly.",
                "sections": [
                    {
                        "id": "scorecard",
                        "title": "Financial Independence Scorecard",
                        "summary": f"Score {int(scorecard.get('score', 0) or 0)} · {str(scorecard.get('band', 'unscored')).strip()}",
                        "details": [
                            f"{str(item.get('label', 'Metric')).strip()}: {str(item.get('status', 'unknown')).strip()} · {str(item.get('summary', '')).strip()}"
                            for item in list(scorecard.get("components", []))
                        ] or ["No finance scorecard metrics are available yet."],
                    },
                    {
                        "id": "weekly-loop",
                        "title": "Weekly Money Review",
                        "summary": str(weekly_review.get("summary", "")).strip(),
                        "details": [
                            f"Due now: {'yes' if weekly_review.get('due') else 'no'}",
                            f"Last reviewed: {str(weekly_review.get('last_reviewed_at', '')).strip() or 'Not recorded yet.'}",
                            f"Next review: {str(weekly_review.get('next_review_at', '')).strip() or 'Not scheduled yet.'}",
                        ],
                    },
                    {
                        "id": "thresholds",
                        "title": "Threshold Watch",
                        "summary": "Low cash, unusual spend, and goal progress thresholds are tracked here.",
                        "details": [
                            f"Low cash warning: {str((thresholds.get('low_cash_warning') or {}).get('status', 'unknown')).strip()} · {str((thresholds.get('low_cash_warning') or {}).get('summary', '')).strip()}",
                            f"Unusual spend: {str((thresholds.get('unusual_spend') or {}).get('status', 'unknown')).strip()} · {str((thresholds.get('unusual_spend') or {}).get('summary', '')).strip()}",
                            f"Goal progress: {str((thresholds.get('goal_progress') or {}).get('status', 'unknown')).strip()} · {str((thresholds.get('goal_progress') or {}).get('summary', '')).strip()}",
                        ],
                    },
                    {
                        "id": "finance-state",
                        "title": "Finance State",
                        "summary": "Cash posture, burn, obligations, and target values.",
                        "details": [
                            f"Available cash: {str(((finance_state.get('state') or {}).get('cash') or {}).get('available', 'unknown'))}",
                            f"Monthly burn: {str(((finance_state.get('state') or {}).get('cash') or {}).get('monthly_burn', 'unknown'))}",
                            f"Monthly revenue: {str(((finance_state.get('state') or {}).get('cash') or {}).get('monthly_revenue', 'unknown'))}",
                            f"Obligations due in 30d: {str(((finance_state.get('state') or {}).get('cash') or {}).get('obligations_due_30d', 'unknown'))}",
                        ],
                    },
                    {
                        "id": "next-moves",
                        "title": "Next Moves",
                        "summary": "What JARVIS thinks is worth moving next.",
                        "details": top_moves or ["Capture real cash, burn, and target values so the finance lane can become more truthful."],
                    },
                ],
            }

        return self._cached_surface("finance_review", actor_name, builder)

    def complete_finance_review(self, actor_name: str = "Chris", note: str = "") -> dict:
        finance_state = self.finance_state_snapshot(actor_name)
        scorecard = dict(finance_state.get("scorecard") or {})
        review = self.wealth_support.complete_finance_review(
            actor_name,
            {
                "summary": str((finance_state.get("weekly_review") or {}).get("summary", "")).strip() or "Weekly money review completed.",
                "score": scorecard.get("score"),
                "band": str(scorecard.get("band", "")).strip(),
                "note": note,
            },
        )
        self._invalidate_snapshot_cache(actor_name, surfaces=("finance_review", "finance_state", "dashboard", "today_board", "cognitive"))
        return {
            "ok": True,
            "review": review,
            "weekly_review": self.finance_state_snapshot(actor_name).get("weekly_review", {}),
        }

    def marketing_state_snapshot(self, actor_name: str = "Chris", *, content_snapshot: dict | None = None) -> dict:
        actor = self.get_actor(actor_name)
        actor_keys = {actor.display_name.strip().lower(), actor.user_id.strip().lower()}

        def _matches_actor(record: dict[str, Any]) -> bool:
            value = str(record.get("actor", "")).strip().lower()
            return not value or value in actor_keys

        content_snapshot = content_snapshot or self.content_ops.snapshot()
        queue = [item for item in list(content_snapshot.get("queue", [])) if _matches_actor(item)]
        state = dict(self.content_ops.marketing_state() or {})
        reviews = list(self.content_ops.recent_marketing_reviews(limit=12))
        thresholds = dict(state.get("thresholds") or {})
        campaigns = [item for item in list(state.get("campaigns", [])) if isinstance(item, dict)]
        offer_links = [item for item in list(state.get("offer_links", [])) if isinstance(item, dict)]
        audience_signals = [str(item).strip() for item in list(state.get("audience_signals", [])) if str(item).strip()]

        queued = [item for item in queue if str(item.get("status", "")).strip().lower() == "queued"]
        scripted = [item for item in queue if str(item.get("status", "")).strip().lower() == "scripted"]
        exported = [item for item in queue if str(item.get("status", "")).strip().lower() == "exported"]
        live = [item for item in queue if str(item.get("status", "")).strip().lower() == "live"]
        latest = queue[0] if queue else {}
        minimum_live_assets = int(thresholds.get("minimum_live_assets") or 1)
        minimum_exported_assets = int(thresholds.get("minimum_exported_assets") or 2)
        stale_campaign_after_days = int(thresholds.get("stale_campaign_after_days") or 10)
        minimum_leverage_score = int(thresholds.get("minimum_leverage_score") or 55)
        now = datetime.now(timezone.utc)

        campaign_statuses: list[dict[str, Any]] = []
        stale_campaigns: list[dict[str, Any]] = []
        for item in campaigns:
            updated_at = str(item.get("updated_at", "")).strip() or str(item.get("last_activity_at", "")).strip()
            updated_dt = self._parse_timestamp(updated_at)
            age_days = (now - updated_dt).days if updated_dt else None
            stale = bool(age_days is not None and age_days >= stale_campaign_after_days)
            snapshot = {
                "campaign_id": str(item.get("campaign_id", "")).strip() or str(uuid.uuid4()),
                "title": str(item.get("title", "")).strip() or "Campaign",
                "status": str(item.get("status", "planned")).strip() or "planned",
                "offer_link": str(item.get("offer_link", "")).strip(),
                "updated_at": updated_at,
                "age_days": age_days,
                "stale": stale,
                "notes": [str(note).strip() for note in list(item.get("notes", [])) if str(note).strip()][:4],
            }
            campaign_statuses.append(snapshot)
            if stale:
                stale_campaigns.append(snapshot)

        score_components = [
            {
                "id": "distribution-readiness",
                "label": "Distribution readiness",
                "status": "healthy" if len(exported) >= minimum_exported_assets else ("warming" if exported or scripted else "warning"),
                "score": 85 if len(exported) >= minimum_exported_assets else 60 if exported or scripted else 30,
                "summary": f"{len(exported)} exported asset(s) and {len(scripted)} scripted asset(s) are ready for distribution.",
            },
            {
                "id": "live-presence",
                "label": "Live presence",
                "status": "healthy" if len(live) >= minimum_live_assets else ("warming" if exported else "warning"),
                "score": 80 if len(live) >= minimum_live_assets else 55 if exported else 25,
                "summary": f"{len(live)} live asset(s) are currently visible in the lane.",
            },
            {
                "id": "campaign-freshness",
                "label": "Campaign freshness",
                "status": "healthy" if not stale_campaigns and campaign_statuses else ("warming" if len(stale_campaigns) <= 1 else "warning"),
                "score": 80 if not stale_campaigns and campaign_statuses else 55 if len(stale_campaigns) <= 1 else 25,
                "summary": "Campaigns are fresh enough to keep momentum." if campaign_statuses and not stale_campaigns else (f"{len(stale_campaigns)} campaign(s) need attention before momentum decays." if stale_campaigns else "No campaign cadence is explicitly tracked yet."),
            },
            {
                "id": "offer-linkage",
                "label": "Offer linkage",
                "status": "healthy" if offer_links else ("warming" if campaign_statuses else "warning"),
                "score": 80 if offer_links else 55 if campaign_statuses else 30,
                "summary": f"{len(offer_links)} campaign-to-offer link(s) are explicitly tracked.",
            },
        ]

        known_scores = [int(item["score"]) for item in score_components if item.get("score") is not None]
        overall_score = round(sum(known_scores) / len(known_scores)) if known_scores else 0
        if overall_score >= 80:
            overall_band = "tracking"
        elif overall_score >= minimum_leverage_score:
            overall_band = "building"
        elif known_scores:
            overall_band = "at-risk"
        else:
            overall_band = "unscored"

        history = [
            {
                "completed_at": str(item.get("completed_at", "")).strip(),
                "review_type": str(item.get("review_type", "weekly")).strip() or "weekly",
                "summary": str(item.get("summary", "")).strip(),
                "score": item.get("score"),
                "band": str(item.get("band", "")).strip(),
                "note": str(item.get("note", "")).strip(),
            }
            for item in reviews
        ]
        weekly_history = [item for item in history if item.get("review_type") == "weekly"]
        last_weekly_at = weekly_history[0]["completed_at"] if weekly_history else ""
        last_weekly_dt = self._parse_timestamp(last_weekly_at)
        weekly_due = last_weekly_dt is None or last_weekly_dt <= now - timedelta(days=7)
        next_weekly_at = ((last_weekly_dt or now) + timedelta(days=7)).astimezone(timezone.utc).isoformat()

        recommended_actions = _merge_unique(
            [f"Refresh campaign {item.get('title', 'momentum')}." for item in stale_campaigns[:2]],
            [f"Export {str(item.get('title', '')).strip()}." for item in queued[:2] if str(item.get("title", "")).strip()],
            limit=5,
        )
        if not recommended_actions:
            recommended_actions = _merge_unique(
                [f"Link {str(item.get('title', '')).strip()} to a concrete offer." for item in campaign_statuses[:2] if str(item.get("title", "")).strip()],
                [f"Move {str(item.get('title', '')).strip()} live." for item in exported[:2] if str(item.get("title", "")).strip()],
                limit=5,
            )
        if not recommended_actions:
            recommended_actions = ["Stage one campaign and one offer link so the marketing lane can start learning from real momentum."]

        performance_summary = {
            "queued_assets": len(queued),
            "scripted_assets": len(scripted),
            "exported_assets": len(exported),
            "live_assets": len(live),
            "campaigns": len(campaign_statuses),
            "stale_campaigns": len(stale_campaigns),
            "offer_links": len(offer_links),
            "audience_signals": len(audience_signals),
        }

        return {
            "actor": actor.display_name,
            "generated_at": now.isoformat(),
            "state": {
                "campaigns": campaign_statuses[:10],
                "offer_links": offer_links[:10],
                "audience_signals": audience_signals[:10],
                "thresholds": thresholds,
                "notes": list(state.get("notes", [])),
            },
            "scorecard": {
                "score": overall_score,
                "band": overall_band,
                "confidence": "medium" if known_scores else "low",
                "summary": (
                    "Marketing has enough operational shape to support weekly review."
                    if overall_band == "tracking"
                    else "Marketing is building, but it still needs steadier campaign freshness and clearer offer linkage."
                    if overall_band == "building"
                    else "Marketing momentum is fragile and should be tightened before it drifts further."
                    if overall_band == "at-risk"
                    else "Marketing still needs more explicit campaign structure before JARVIS can score it confidently."
                ),
                "components": score_components,
            },
            "performance": performance_summary,
            "weekly_review": {
                "label": "Weekly Marketing Review",
                "cadence": "weekly",
                "due": weekly_due,
                "summary": "Weekly marketing review is due now." if weekly_due else f"Weekly marketing review was completed recently and comes due again around {next_weekly_at[:10]}.",
                "last_reviewed_at": last_weekly_at,
                "next_review_at": next_weekly_at,
                "history_count": len(weekly_history),
            },
            "stale_campaigns": stale_campaigns[:6],
            "campaigns": campaign_statuses[:10],
            "offer_links": offer_links[:10],
            "audience_signals": audience_signals[:10],
            "history": history[:8],
            "recommended_actions": recommended_actions,
            "truth": {
                "marketing_live": False,
                "notes": [
                    "Marketing state currently combines local content throughput with a local campaign operating model.",
                    "No live audience-growth or ad-platform connector is wired yet.",
                ],
            },
        }

    def marketing_review(self, actor_name: str = "Chris") -> dict:
        def builder() -> dict:
            marketing_state = self.marketing_state_snapshot(actor_name)
            scorecard = dict(marketing_state.get("scorecard") or {})
            weekly_review = dict(marketing_state.get("weekly_review") or {})
            performance = dict(marketing_state.get("performance") or {})
            stale_campaigns = list(marketing_state.get("stale_campaigns") or [])
            recommended_actions = list(marketing_state.get("recommended_actions") or [])
            summary = str(scorecard.get("summary", "")).strip() or "Marketing review is standing by."
            return {
                "actor": actor_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "title": "Marketing Review",
                "summary": summary,
                "scorecard": scorecard,
                "weekly_review": weekly_review,
                "performance": performance,
                "state": marketing_state.get("state") or {},
                "history": marketing_state.get("history") or [],
                "stale_campaigns": stale_campaigns,
                "recommended_next_move": recommended_actions[0] if recommended_actions else "Stage one campaign and link it to a concrete offer.",
                "sections": [
                    {
                        "id": "scorecard",
                        "title": "Content and Marketing Scorecard",
                        "summary": f"Score {int(scorecard.get('score', 0) or 0)} · {str(scorecard.get('band', 'unscored')).strip()}",
                        "details": [
                            f"{str(item.get('label', 'Metric')).strip()}: {str(item.get('status', 'unknown')).strip()} · {str(item.get('summary', '')).strip()}"
                            for item in list(scorecard.get("components", []))
                        ] or ["No marketing scorecard metrics are available yet."],
                    },
                    {
                        "id": "weekly-loop",
                        "title": "Weekly Marketing Review",
                        "summary": str(weekly_review.get("summary", "")).strip(),
                        "details": [
                            f"Due now: {'yes' if weekly_review.get('due') else 'no'}",
                            f"Last reviewed: {str(weekly_review.get('last_reviewed_at', '')).strip() or 'Not recorded yet.'}",
                            f"Next review: {str(weekly_review.get('next_review_at', '')).strip() or 'Not scheduled yet.'}",
                        ],
                    },
                    {
                        "id": "campaign-health",
                        "title": "Campaign Health",
                        "summary": "Campaign freshness and offer linkage shape whether content compounds or drifts.",
                        "details": [
                            f"Stale campaigns: {len(stale_campaigns)}",
                            f"Offer links: {len(marketing_state.get('offer_links') or [])}",
                            f"Audience signals: {len(marketing_state.get('audience_signals') or [])}",
                        ] + [
                            f"{str(item.get('title', 'Campaign')).strip()} · {str(item.get('status', 'planned')).strip()} · {str(item.get('age_days', '?'))} day(s) old"
                            for item in stale_campaigns[:4]
                        ],
                    },
                    {
                        "id": "performance",
                        "title": "Performance Summary",
                        "summary": "Current throughput across queued, scripted, exported, and live assets.",
                        "details": [
                            f"Queued assets: {int(performance.get('queued_assets', 0) or 0)}",
                            f"Scripted assets: {int(performance.get('scripted_assets', 0) or 0)}",
                            f"Exported assets: {int(performance.get('exported_assets', 0) or 0)}",
                            f"Live assets: {int(performance.get('live_assets', 0) or 0)}",
                            f"Campaigns tracked: {int(performance.get('campaigns', 0) or 0)}",
                        ],
                    },
                    {
                        "id": "next-moves",
                        "title": "Next Moves",
                        "summary": "What JARVIS thinks is worth moving next to strengthen the marketing engine.",
                        "details": recommended_actions or ["Stage one campaign and link it to a concrete offer."],
                    },
                ],
            }

        return self._cached_surface("marketing_review", actor_name, builder)

    def complete_marketing_review(self, actor_name: str = "Chris", note: str = "") -> dict:
        marketing_state = self.marketing_state_snapshot(actor_name)
        scorecard = dict(marketing_state.get("scorecard") or {})
        review = self.content_ops.complete_marketing_review(
            actor_name,
            {
                "review_type": "weekly",
                "summary": str((marketing_state.get("weekly_review") or {}).get("summary", "")).strip() or "Weekly marketing review completed.",
                "score": scorecard.get("score"),
                "band": str(scorecard.get("band", "")).strip(),
                "note": note,
            },
        )
        self._invalidate_snapshot_cache(actor_name, surfaces=("marketing_review", "marketing_state", "dashboard", "today_board", "cognitive"))
        return {
            "ok": True,
            "review": review,
            "weekly_review": self.marketing_state_snapshot(actor_name).get("weekly_review", {}),
        }

    def pipeline_state_snapshot(self, actor_name: str = "Chris") -> dict:
        actor = self.get_actor(actor_name)
        actor_keys = {actor.display_name.strip().lower(), actor.user_id.strip().lower()}

        def _matches_actor(record: dict[str, Any]) -> bool:
            value = str(record.get("actor", "")).strip().lower()
            return not value or value in actor_keys

        state = dict(self.catalyst_support.pipeline_state() or {})
        reviews = list(self.catalyst_support.recent_pipeline_reviews(limit=12))
        catalyst_store = self.catalyst_support.store
        catalyst_signals = [item for item in catalyst_store.list_signals(limit=18) if _matches_actor(item)]
        project_briefs = [item for item in catalyst_store.list_records(catalyst_store.project_briefs_path, limit=12) if _matches_actor(item)]
        implementation_plans = [item for item in catalyst_store.list_records(catalyst_store.implementation_plans_path, limit=12) if _matches_actor(item)]
        briefings = [item for item in catalyst_store.list_records(catalyst_store.briefing_path, limit=8) if _matches_actor(item)]
        manual_opportunities = [item for item in list(state.get("opportunities", [])) if isinstance(item, dict)]

        crm = dict(state.get("crm") or {})
        thresholds = dict(state.get("thresholds") or {})
        stalled_after_days = int(thresholds.get("stalled_after_days") or 7)
        hot_followup_within_days = int(thresholds.get("hot_followup_within_days") or 2)
        minimum_active_opportunities = int(thresholds.get("minimum_active_opportunities") or 3)
        now = datetime.now(timezone.utc)

        def _record_title(record: dict[str, Any]) -> str:
            return (
                str(record.get("project_name", "")).strip()
                or str(record.get("title", "")).strip()
                or str(record.get("subject", "")).strip()
            )

        opportunities_by_key: dict[str, dict[str, Any]] = {}

        def _ensure_opportunity(title: str, *, stage: str, source: str, timestamp: str) -> dict[str, Any]:
            key = title.strip().lower()
            if not key:
                return {}
            current = opportunities_by_key.get(key)
            stage_rank = {
                "lead": 1,
                "signal-captured": 2,
                "project-brief": 3,
                "implementation-ready": 4,
                "proposal": 5,
                "negotiation": 6,
                "won": 7,
                "lost": 7,
            }
            if current is None:
                current = {
                    "opportunity_id": str(uuid.uuid4()),
                    "title": title,
                    "stage": stage,
                    "source": source,
                    "status": "open",
                    "value_estimate": None,
                    "owner": actor.display_name,
                    "last_activity_at": timestamp,
                    "next_followup_at": "",
                    "notes": [],
                    "signals": [],
                    "next_actions": [],
                }
                opportunities_by_key[key] = current
                return current
            if stage_rank.get(stage, 0) >= stage_rank.get(str(current.get("stage", "")).strip(), 0):
                current["stage"] = stage
                current["source"] = source
            if timestamp and (not current.get("last_activity_at") or str(timestamp) > str(current.get("last_activity_at"))):
                current["last_activity_at"] = timestamp
            return current

        for item in catalyst_signals:
            title = _record_title(item)
            entry = _ensure_opportunity(title, stage="signal-captured", source="catalyst-signal", timestamp=str(item.get("timestamp", "")).strip())
            if not entry:
                continue
            entry.setdefault("signals", []).append(str(item.get("title", "")).strip())
            if str(item.get("content", "")).strip():
                entry.setdefault("notes", []).append(str(item.get("content", "")).strip()[:180])

        for item in project_briefs:
            title = _record_title(item)
            entry = _ensure_opportunity(title, stage="project-brief", source="project-brief", timestamp=str(item.get("timestamp", "")).strip())
            if not entry:
                continue
            entry.setdefault("signals", []).append(str(item.get("problem", "")).strip())
            entry.setdefault("next_actions", []).extend(list(item.get("first_release", []))[:3])
            entry.setdefault("notes", []).extend(list(item.get("risks", []))[:2])

        for item in implementation_plans:
            title = _record_title(item)
            entry = _ensure_opportunity(title, stage="implementation-ready", source="implementation-plan", timestamp=str(item.get("timestamp", "")).strip())
            if not entry:
                continue
            entry.setdefault("next_actions", []).extend(list(item.get("next_actions", []))[:4])
            entry.setdefault("notes", []).extend(list(item.get("dependencies", []))[:2])

        for item in manual_opportunities:
            title = str(item.get("title", "")).strip()
            entry = _ensure_opportunity(
                title,
                stage=str(item.get("stage", "lead")).strip() or "lead",
                source=str(item.get("source", "manual")).strip() or "manual",
                timestamp=str(item.get("last_activity_at", "")).strip() or str(item.get("updated_at", "")).strip(),
            )
            if not entry:
                continue
            for key in ("status", "value_estimate", "owner", "next_followup_at"):
                if item.get(key) not in (None, ""):
                    entry[key] = item.get(key)
            entry["opportunity_id"] = str(item.get("opportunity_id", "")).strip() or str(entry.get("opportunity_id", "")).strip() or str(uuid.uuid4())
            entry.setdefault("notes", []).extend([str(note).strip() for note in list(item.get("notes", [])) if str(note).strip()][:4])
            entry.setdefault("next_actions", []).extend([str(step).strip() for step in list(item.get("next_actions", [])) if str(step).strip()][:4])

        opportunities: list[dict[str, Any]] = []
        stalled: list[dict[str, Any]] = []
        followup_due: list[dict[str, Any]] = []
        stage_counts: dict[str, int] = {}

        for entry in opportunities_by_key.values():
            last_activity_at = str(entry.get("last_activity_at", "")).strip()
            last_dt = self._parse_timestamp(last_activity_at)
            age_days = (now - last_dt).days if last_dt else None
            next_followup_at = str(entry.get("next_followup_at", "")).strip()
            next_followup_dt = self._parse_timestamp(next_followup_at)
            if not next_followup_dt and last_dt:
                next_followup_dt = last_dt + timedelta(days=hot_followup_within_days)
                next_followup_at = next_followup_dt.astimezone(timezone.utc).isoformat()
                entry["next_followup_at"] = next_followup_at
            is_stalled = bool(age_days is not None and age_days >= stalled_after_days)
            if next_followup_dt and next_followup_dt <= now:
                is_stalled = True
            if next_followup_dt and next_followup_dt <= now + timedelta(days=hot_followup_within_days):
                followup_due.append(entry)
            entry["age_days"] = age_days
            entry["stalled"] = is_stalled
            entry["next_actions"] = _merge_unique([], [str(item).strip() for item in entry.get("next_actions", []) if str(item).strip()], limit=5)
            entry["notes"] = _merge_unique([], [str(item).strip() for item in entry.get("notes", []) if str(item).strip()], limit=5)
            entry["signals"] = _merge_unique([], [str(item).strip() for item in entry.get("signals", []) if str(item).strip()], limit=4)
            opportunities.append(entry)
            stage = str(entry.get("stage", "lead")).strip() or "lead"
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            if is_stalled:
                stalled.append(entry)

        opportunities.sort(
            key=lambda item: (
                0 if item.get("stalled") else 1,
                self._parse_timestamp(str(item.get("next_followup_at", "")).strip()) or datetime.max.replace(tzinfo=timezone.utc),
            )
        )
        stalled.sort(key=lambda item: item.get("age_days") or 0, reverse=True)
        followup_due = _merge_unique(
            [],
            [str(item.get("title", "")).strip() for item in followup_due if str(item.get("title", "")).strip()],
            limit=6,
        )

        active_opportunities = [item for item in opportunities if str(item.get("status", "open")).strip().lower() not in {"won", "lost", "archived"}]
        followup_target = int(crm.get("weekly_followup_target") or 5)
        avg_deal_value = crm.get("average_deal_value")
        stalled_count = len(stalled)
        active_count = len(active_opportunities)
        plan_count = len(implementation_plans)
        brief_count = len(project_briefs)
        signal_count = len(catalyst_signals)

        score_components = [
            {
                "id": "pipeline-coverage",
                "label": "Pipeline coverage",
                "status": "healthy" if active_count >= minimum_active_opportunities else ("warming" if active_count else "warning"),
                "score": 85 if active_count >= minimum_active_opportunities else 60 if active_count else 30,
                "summary": f"{active_count} active opportunity(ies) are currently tracked against a target of {minimum_active_opportunities}.",
            },
            {
                "id": "followup-discipline",
                "label": "Follow-up discipline",
                "status": "healthy" if stalled_count == 0 and active_count else ("warming" if stalled_count <= 1 else "warning"),
                "score": 85 if stalled_count == 0 and active_count else 60 if stalled_count <= 1 else 25,
                "summary": "No opportunity appears stale right now." if stalled_count == 0 else f"{stalled_count} opportunity(ies) need follow-up before they cool off further.",
            },
            {
                "id": "execution-readiness",
                "label": "Execution readiness",
                "status": "healthy" if plan_count else ("warming" if brief_count else "warning"),
                "score": 85 if plan_count else 60 if brief_count else 35,
                "summary": f"{plan_count} implementation plan(s) and {brief_count} project brief(s) are staged for execution.",
            },
            {
                "id": "signal-flow",
                "label": "Signal flow",
                "status": "healthy" if signal_count >= followup_target else ("warming" if signal_count else "warning"),
                "score": 80 if signal_count >= followup_target else 55 if signal_count else 30,
                "summary": f"{signal_count} Catalyst signal(s) are feeding the lane right now.",
            },
        ]

        known_scores = [int(item["score"]) for item in score_components if item.get("score") is not None]
        overall_score = round(sum(known_scores) / len(known_scores)) if known_scores else 0
        if overall_score >= 80:
            overall_band = "tracking"
        elif overall_score >= 55:
            overall_band = "building"
        elif known_scores:
            overall_band = "at-risk"
        else:
            overall_band = "unscored"

        history = [
            {
                "completed_at": str(item.get("completed_at", "")).strip(),
                "review_type": str(item.get("review_type", "weekly")).strip() or "weekly",
                "summary": str(item.get("summary", "")).strip(),
                "score": item.get("score"),
                "band": str(item.get("band", "")).strip(),
                "note": str(item.get("note", "")).strip(),
            }
            for item in reviews
        ]
        daily_history = [item for item in history if item.get("review_type") == "daily"]
        weekly_history = [item for item in history if item.get("review_type") == "weekly"]
        last_daily_at = daily_history[0]["completed_at"] if daily_history else ""
        last_weekly_at = weekly_history[0]["completed_at"] if weekly_history else ""
        last_daily_dt = self._parse_timestamp(last_daily_at)
        last_weekly_dt = self._parse_timestamp(last_weekly_at)
        daily_due = last_daily_dt is None or last_daily_dt.date() < now.date() or stalled_count > 0
        weekly_due = last_weekly_dt is None or last_weekly_dt <= now - timedelta(days=7)
        next_daily_at = datetime.combine((now + timedelta(days=1)).date(), datetime.min.time(), tzinfo=timezone.utc).isoformat()
        next_weekly_at = ((last_weekly_dt or now) + timedelta(days=7)).astimezone(timezone.utc).isoformat()

        recommended_actions = _merge_unique(
            [f"Follow up on {item.get('title', 'the stalled opportunity')}." for item in stalled[:3]],
            [f"Promote {str(item.get('project_name', '')).strip()} into an implementation plan." for item in project_briefs[:2] if str(item.get("project_name", "")).strip()],
            limit=5,
        )
        if not recommended_actions and active_opportunities:
            recommended_actions = _merge_unique([], [f"Refresh the next step for {item.get('title', 'the active opportunity')}." for item in active_opportunities[:3]], limit=4)
        if not recommended_actions:
            recommended_actions = ["Capture at least one live opportunity so the pipeline lane can start learning from real movement."]

        return {
            "actor": actor.display_name,
            "generated_at": now.isoformat(),
            "state": {
                "crm": crm,
                "thresholds": thresholds,
                "opportunities": opportunities[:12],
                "notes": list(state.get("notes", [])),
            },
            "scorecard": {
                "score": overall_score,
                "band": overall_band,
                "confidence": "medium" if known_scores else "low",
                "summary": (
                    "Pipeline has enough shape to support daily and weekly revenue reviews."
                    if overall_band == "tracking"
                    else "Pipeline is building, but it still needs steadier follow-up and more live opportunities."
                    if overall_band == "building"
                    else "Pipeline is under pressure and should not be left unattended."
                    if overall_band == "at-risk"
                    else "Pipeline still needs more explicit opportunity data before JARVIS can score it confidently."
                ),
                "components": score_components,
            },
            "derived": {
                "active_opportunities": active_count,
                "stalled_opportunities": stalled_count,
                "followups_due_now": len(followup_due),
                "project_briefs": brief_count,
                "implementation_plans": plan_count,
                "signals": signal_count,
                "average_deal_value": avg_deal_value,
                "stage_counts": stage_counts,
            },
            "stalled_opportunities": stalled[:6],
            "daily_followup_loop": {
                "label": "Daily Pipeline Follow-up",
                "cadence": "daily",
                "due": daily_due,
                "summary": (
                    f"{stalled_count} opportunity(ies) are stale enough to deserve follow-up now."
                    if stalled_count
                    else "Daily pipeline follow-up is quiet right now."
                ),
                "last_reviewed_at": last_daily_at,
                "next_review_at": next_daily_at,
                "history_count": len(daily_history),
            },
            "weekly_review": {
                "label": "Weekly Pipeline Review",
                "cadence": "weekly",
                "due": weekly_due,
                "summary": (
                    "Weekly pipeline review is due now."
                    if weekly_due
                    else f"Weekly pipeline review was completed recently and comes due again around {next_weekly_at[:10]}."
                ),
                "last_reviewed_at": last_weekly_at,
                "next_review_at": next_weekly_at,
                "history_count": len(weekly_history),
            },
            "history": history[:8],
            "followup_titles": followup_due,
            "recommended_actions": recommended_actions,
            "truth": {
                "sales_live": False,
                "notes": [
                    "Pipeline state currently mixes manual opportunity notes with Catalyst-derived signals, briefs, and plans.",
                    "No live CRM connector is wired yet.",
                ],
            },
        }

    def pipeline_review(self, actor_name: str = "Chris") -> dict:
        def builder() -> dict:
            pipeline_state = self.pipeline_state_snapshot(actor_name)
            scorecard = dict(pipeline_state.get("scorecard") or {})
            daily_followup_loop = dict(pipeline_state.get("daily_followup_loop") or {})
            weekly_review = dict(pipeline_state.get("weekly_review") or {})
            stalled = list(pipeline_state.get("stalled_opportunities") or [])
            opportunities = list(((pipeline_state.get("state") or {}).get("opportunities") or []))
            recommended_actions = list(pipeline_state.get("recommended_actions") or [])
            derived = dict(pipeline_state.get("derived") or {})
            summary = str(scorecard.get("summary", "")).strip() or "Pipeline review is standing by."
            return {
                "actor": actor_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "title": "Pipeline Review",
                "summary": summary,
                "scorecard": scorecard,
                "daily_followup_loop": daily_followup_loop,
                "weekly_review": weekly_review,
                "state": pipeline_state.get("state") or {},
                "derived": derived,
                "history": pipeline_state.get("history") or [],
                "stalled_opportunities": stalled,
                "recommended_next_move": recommended_actions[0] if recommended_actions else "Stage one live opportunity so the pipeline lane has something real to work with.",
                "sections": [
                    {
                        "id": "scorecard",
                        "title": "Sales and Pipeline Scorecard",
                        "summary": f"Score {int(scorecard.get('score', 0) or 0)} · {str(scorecard.get('band', 'unscored')).strip()}",
                        "details": [
                            f"{str(item.get('label', 'Metric')).strip()}: {str(item.get('status', 'unknown')).strip()} · {str(item.get('summary', '')).strip()}"
                            for item in list(scorecard.get("components", []))
                        ] or ["No pipeline scorecard metrics are available yet."],
                    },
                    {
                        "id": "review-loops",
                        "title": "Daily and Weekly Reviews",
                        "summary": "JARVIS tracks both short-horizon follow-up and broader weekly pipeline health.",
                        "details": [
                            f"Daily follow-up due: {'yes' if daily_followup_loop.get('due') else 'no'} · {str(daily_followup_loop.get('summary', '')).strip()}",
                            f"Weekly review due: {'yes' if weekly_review.get('due') else 'no'} · {str(weekly_review.get('summary', '')).strip()}",
                            f"Last daily review: {str(daily_followup_loop.get('last_reviewed_at', '')).strip() or 'Not recorded yet.'}",
                            f"Last weekly review: {str(weekly_review.get('last_reviewed_at', '')).strip() or 'Not recorded yet.'}",
                        ],
                    },
                    {
                        "id": "stalled-opportunities",
                        "title": "Stalled Opportunities",
                        "summary": "These opportunities are the ones most likely to decay if left unattended.",
                        "details": [
                            f"{str(item.get('title', 'Opportunity')).strip()} · {str(item.get('stage', 'open')).strip()} · {str(item.get('age_days', '?'))} day(s) since activity"
                            for item in stalled[:6]
                        ] or ["No stalled opportunities are currently detected."],
                    },
                    {
                        "id": "stage-map",
                        "title": "Stage Map",
                        "summary": "Pipeline stage coverage and current active opportunity mix.",
                        "details": [
                            f"Active opportunities: {int(derived.get('active_opportunities', 0) or 0)}",
                            f"Signals: {int(derived.get('signals', 0) or 0)}",
                            f"Project briefs: {int(derived.get('project_briefs', 0) or 0)}",
                            f"Implementation plans: {int(derived.get('implementation_plans', 0) or 0)}",
                        ]
                        + [
                            f"{stage}: {count}"
                            for stage, count in dict(derived.get("stage_counts") or {}).items()
                        ],
                    },
                    {
                        "id": "next-moves",
                        "title": "Next Moves",
                        "summary": "What JARVIS thinks is worth doing to move revenue posture forward.",
                        "details": recommended_actions or ["Stage one live opportunity so the pipeline lane can become more truthful."],
                    },
                ],
            }

        return self._cached_surface("pipeline_review", actor_name, builder)

    def complete_pipeline_review(self, actor_name: str = "Chris", review_type: str = "weekly", note: str = "") -> dict:
        pipeline_state = self.pipeline_state_snapshot(actor_name)
        scorecard = dict(pipeline_state.get("scorecard") or {})
        summary_source = pipeline_state.get("weekly_review") if review_type == "weekly" else pipeline_state.get("daily_followup_loop")
        review = self.catalyst_support.complete_pipeline_review(
            actor_name,
            {
                "review_type": review_type,
                "summary": str((summary_source or {}).get("summary", "")).strip() or "Pipeline review completed.",
                "score": scorecard.get("score"),
                "band": str(scorecard.get("band", "")).strip(),
                "note": note,
            },
        )
        self._invalidate_snapshot_cache(actor_name, surfaces=("pipeline_review", "pipeline_state", "dashboard", "today_board", "cognitive", "cadence_review"))
        refreshed = self.pipeline_state_snapshot(actor_name)
        return {
            "ok": True,
            "review": review,
            "daily_followup_loop": refreshed.get("daily_followup_loop", {}),
            "weekly_review": refreshed.get("weekly_review", {}),
        }

    def _self_model_domain_constraints(self) -> list[dict[str, Any]]:
        return [
            {
                "domain": "approvals",
                "allowed": ["surface", "queue", "notify", "mark acted after approval"],
                "requires_approval": ["approve", "reject", "final decision"],
                "should_not_do": ["self-approve another person's decision without explicit consent"],
            },
            {
                "domain": "family",
                "allowed": ["stage drafts", "defer", "prepare coordination artifacts"],
                "requires_approval": ["send outward messages", "commit household changes externally"],
                "should_not_do": ["send family communication on its own"],
            },
            {
                "domain": "workshop",
                "allowed": ["stage vendor prep", "defer", "refresh fabrication briefs"],
                "requires_approval": ["submit to vendor", "purchase", "manufacturing commitment"],
                "should_not_do": ["move a fabrication job to an external vendor automatically"],
            },
            {
                "domain": "memory",
                "allowed": ["propose memory changes", "queue review"],
                "requires_approval": ["approve memory writes", "promote uncertain profile facts"],
                "should_not_do": ["promote contested personal memory as truth"],
            },
            {
                "domain": "content",
                "allowed": ["package", "export", "defer", "queue review"],
                "requires_approval": ["publish", "post live", "external send"],
                "should_not_do": ["publish or broadcast content on its own"],
            },
            {
                "domain": "growth",
                "allowed": ["prepare summary", "refresh brief", "defer", "surface next moves"],
                "requires_approval": ["revenue-affecting commitments", "payments", "external commitments"],
                "should_not_do": ["move money or make external financial commitments automatically"],
            },
        ]

    def _self_model_recent_failed_actions(self) -> list[dict[str, Any]]:
        attempts = self.audit_log.list_recent(limit=30, entry_type="assistant-action")
        failures: list[dict[str, Any]] = []
        for item in attempts:
            if item.get("succeeded") is not False:
                continue
            failures.append(
                {
                    "timestamp": str(item.get("timestamp", "")).strip(),
                    "domain": str(item.get("domain", "")).strip() or "general",
                    "action": str(item.get("action", "")).strip() or "unknown",
                    "action_class": str(item.get("action_class", "")).strip() or "uncategorized",
                    "result_summary": str(item.get("result_summary", "")).strip() or str(item.get("detail", "")).strip() or "Action failed.",
                    "policy_basis": str(item.get("policy_basis", "")).strip(),
                }
            )
            if len(failures) >= 6:
                break
        return failures

    def self_model_snapshot(self, actor_name: str = "Chris") -> dict:
        actor = self.get_actor(actor_name)
        integration_status = self.status()
        growth = self.growth_state_snapshot(actor.display_name)
        ready_tools = [item["name"] for item in integration_status if item.get("ok")]
        blocked_tools = [item["name"] for item in integration_status if not item.get("ok")]
        tool_readiness = [
            {
                "name": str(item.get("name", "")).strip(),
                "state": str(item.get("state", "unknown")).strip() or "unknown",
                "ready": bool(item.get("ok")),
                "detail": str(item.get("detail", "")).strip(),
            }
            for item in integration_status
        ]
        google_connected = any(item.get("name") == "google-workspace" and item.get("ok") for item in integration_status)
        home_connected = any(item.get("name") == "home-assistant" and item.get("ok") for item in integration_status)
        local_brain_ready = any(item.get("name") == "local-brain" and item.get("ok") for item in integration_status)
        tracked_growth_signals = int((growth.get("summary") or {}).get("tracked_signal_count", 0) or 0)
        growth_domains = {str(item.get("id", "")).strip().lower() for item in list(growth.get("domains", []))}
        domain_confidence = {
            "identity": "high" if self.identity_overview().get("members") else "medium",
            "calendar": "high" if google_connected and self._actor_calendar_events(actor, limit=1) else ("medium" if self._actor_calendar_events(actor, limit=1) else "low"),
            "family": "high" if google_connected else "medium",
            "workshop": "medium",
            "memory": "medium",
            "content": "high" if "content" in growth_domains else "medium",
            "growth": "medium" if tracked_growth_signals else "low",
            "finance": "medium" if "finance" in growth_domains else "low",
            "pipeline": "medium" if "pipeline" in growth_domains else "low",
            "marketing": "medium" if "marketing" in growth_domains else "low",
            "home": "high" if home_connected else "low",
            "weather": "low",
        }
        recent_failed_actions = self._self_model_recent_failed_actions()
        known_failure_modes = [
            {
                "id": "outbound-mobile-missing",
                "severity": "medium",
                "summary": "Phone and iPad delivery still stop at browser-alert posture.",
            },
            {
                "id": "live-growth-connectors-missing",
                "severity": "medium",
                "summary": "Finance, CRM, and ad-platform telemetry are still partly inferred rather than live-connected.",
            },
        ]
        if not google_connected:
            known_failure_modes.append(
                {
                    "id": "google-workspace-disconnected",
                    "severity": "high",
                    "summary": "Google Workspace is disconnected, so calendar and email awareness can degrade.",
                }
            )
        if not home_connected:
            known_failure_modes.append(
                {
                    "id": "home-assistant-disconnected",
                    "severity": "medium",
                    "summary": "Home Assistant is unavailable, so live home state and actions are blocked.",
                }
            )
        if not local_brain_ready:
            known_failure_modes.append(
                {
                    "id": "local-brain-not-ready",
                    "severity": "medium",
                    "summary": "The local brain is not fully ready, which weakens local synthesis and fallback reasoning.",
                }
            )
        for item in recent_failed_actions[:3]:
            known_failure_modes.append(
                {
                    "id": f"recent-failure-{str(item.get('action', 'action')).strip().lower()}",
                    "severity": "medium",
                    "summary": str(item.get("result_summary", "Recent assistant action failed.")).strip(),
                }
            )
        uncertainty_model = [
            {
                "area": "weather",
                "level": "high",
                "reason": "Weather remains staged instead of being sourced from a live feed.",
            },
            {
                "area": "mobile-delivery",
                "level": "high",
                "reason": "Phone and iPad outbound delivery are not connected beyond browser alerts.",
            },
            {
                "area": "growth-telemetry",
                "level": "medium",
                "reason": "Financial, CRM, and ad-platform signals are partly inferred until live connectors land.",
            },
            {
                "area": "home-state",
                "level": "low" if home_connected else "high",
                "reason": "Home-state confidence depends on the Home Assistant connection.",
            },
        ]
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tools": {
                "ready": ready_tools,
                "blocked": blocked_tools,
                "readiness": tool_readiness,
            },
            "capabilities": [
                "stage work",
                "defer and revisit",
                "package content",
                "prepare meeting and family coordination artifacts",
                "surface assistant notifications",
                "inspect local vision/model forge workflows",
                "track growth pressure across wealth, pipeline, and content",
            ],
            "constraints": [
                "external send/publish/vendor movement still require explicit approval",
                "browser alerts respect quiet hours unless a policy explicitly allows interruption",
                "home assistant remains unavailable until the integration is connected",
                "financial, sales, and marketing signals are inference-based until live connectors are wired",
            ],
            "confidence": {
                "identity": domain_confidence["identity"],
                "calendar": domain_confidence["calendar"],
                "assistant_autonomy": "high",
                "weather": domain_confidence["weather"],
                "growth": domain_confidence["growth"],
            },
            "domain_confidence": domain_confidence,
            "action_constraints": self._self_model_domain_constraints(),
            "known_failure_modes": known_failure_modes[:8],
            "recent_failed_actions": recent_failed_actions,
            "uncertainties": [
                "weather remains staged rather than live",
                "phone/iPad outbound delivery is not yet connected beyond browser alerts",
                "financial institutions, CRM, and ad-platform telemetry are not connected yet",
            ],
            "uncertainty_model": uncertainty_model,
        }

    def goal_stack_snapshot(self, actor_name: str = "Chris", *, open_loops: dict | None = None) -> dict:
        actor = self.get_actor(actor_name)
        open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
        first_light = self.first_light_store.latest_packet(actor.user_id) or {}
        growth = self.growth_state_snapshot(actor.display_name)
        immediate = [str(item.get("title", "")) for item in list(open_loops.get("items", []))[:3] if str(item.get("title", "")).strip()]
        if growth.get("next_moves"):
            immediate = _merge_unique(immediate, list(growth.get("next_moves", [])), limit=4)
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "immediate": immediate,
            "daily": list(first_light.get("first_20_minutes", []))[:4] or ["Protect the most important block and clear real blockers."],
            "weekly": [
                "reduce family friction across recurring transitions",
                "close or defer stale approvals instead of letting them accumulate",
                "move one leverage-bearing project forward",
                "advance one revenue-bearing experiment or growth asset",
            ],
            "strategic": [
                "grow leverage while reducing chaos",
                "improve personal accuracy for each family member",
                "increase trust without increasing noise",
                "build repeatable income engines and compounding assets",
            ],
            "maintenance": [
                "keep services healthy and truthful",
                "keep open loops current and governed",
                "keep growth signals honest about what is live versus inferred",
            ],
            "identity_formation": [
                "protect attention",
                "prefer steady coordination over reactive scramble",
            ],
        }

    def _deliberation_scores(
        self,
        top_item: dict,
        *,
        world_state: dict,
        cadence: dict,
        growth_state: dict,
        notification_policy: dict,
        quiet_hours_active: bool,
        world_boost: dict,
    ) -> dict[str, int]:
        domain = str(top_item.get("domain", "")).strip().lower()
        age_bucket = str(top_item.get("age_bucket", "")).strip().lower()
        cadence_phase = str(cadence.get("phase", "watch")).strip().lower()
        growth_pressure = str((growth_state.get("summary") or {}).get("pressure", "quiet")).strip().lower()
        blocked_work = list(world_state.get("blocked_work", [])) if isinstance(world_state.get("blocked_work", []), list) else []
        conflicts = list(world_state.get("conflicts", [])) if isinstance(world_state.get("conflicts", []), list) else []
        likely_next = list(world_state.get("likely_next", [])) if isinstance(world_state.get("likely_next", []), list) else []

        risk_score = 1
        if str(top_item.get("status", "")).strip().lower() in {"pending", "pending-approval"}:
            risk_score += 2
        if domain in {"approvals", "family", "growth"}:
            risk_score += 1
        if bool(top_item.get("auto_execution", {}).get("allowed")):
            risk_score -= 1
        if quiet_hours_active:
            risk_score += 1
        if conflicts:
            risk_score += 1
        risk_score = max(1, min(risk_score, 5))

        interruption_score = 1
        if bool(top_item.get("needs_revisit")):
            interruption_score += 2
        if cadence_phase in {"morning", "pre-transition"} and domain in {"family", "approvals"}:
            interruption_score += 2
        if growth_pressure in {"active", "warming"} and domain == "growth":
            interruption_score += 1
        interruption_score += min(int(world_boost.get("score", 0) or 0), 2)
        if blocked_work and domain in {str(item.get("domain", "")).strip().lower() for item in blocked_work}:
            interruption_score += 1
        if quiet_hours_active and not bool(notification_policy.get("interrupt_during_quiet_hours")):
            interruption_score -= 2
        interruption_score = max(0, min(interruption_score, 5))

        smallest_helpful_move_score = 1
        if str(top_item.get("next_action", "")).strip():
            smallest_helpful_move_score += 2
        if age_bucket in {"aged", "stale"}:
            smallest_helpful_move_score += 1
        if bool(top_item.get("auto_execution", {}).get("allowed")):
            smallest_helpful_move_score += 1
        if likely_next and str(likely_next[0].get("domain", "")).strip().lower() == domain:
            smallest_helpful_move_score += 1
        smallest_helpful_move_score = max(1, min(smallest_helpful_move_score, 5))

        return {
            "risk": risk_score,
            "interruption": interruption_score,
            "smallest_helpful_move": smallest_helpful_move_score,
        }

    def _deliberation_mode_candidates(
        self,
        *,
        top_item: dict,
        world_state: dict,
        quiet_hours_active: bool,
        decision: str,
        scores: dict[str, int],
    ) -> list[dict[str, Any]]:
        domain = str(top_item.get("domain", "")).strip().lower()
        blocked_work = list(world_state.get("blocked_work", [])) if isinstance(world_state.get("blocked_work", []), list) else []
        conflicts = list(world_state.get("conflicts", [])) if isinstance(world_state.get("conflicts", []), list) else []
        candidates = [
            {
                "mode": "routing",
                "score": 2 + (1 if domain in {"family", "approvals"} else 0),
                "reason": "Route the next move to the right lane and packet.",
            },
            {
                "mode": "planning",
                "score": 2 + (1 if bool(top_item.get("needs_revisit")) else 0),
                "reason": "Sequence the next move without committing too much too early.",
            },
            {
                "mode": "simulation",
                "score": 2 + (1 if conflicts else 0) + (1 if scores.get("risk", 0) >= 3 else 0),
                "reason": "Test alternatives before escalating or interrupting.",
            },
            {
                "mode": "critique",
                "score": 1 + (1 if blocked_work else 0) + (1 if scores.get("risk", 0) >= 4 else 0),
                "reason": "Look for the failure mode before acting.",
            },
            {
                "mode": "execution",
                "score": 1 + (2 if decision == "act" else 0) + (1 if bool(top_item.get("auto_execution", {}).get("allowed")) else 0),
                "reason": "The path is bounded enough to execute directly.",
            },
            {
                "mode": "watch",
                "score": 1 + (2 if quiet_hours_active else 0) + (1 if decision == "hold" else 0),
                "reason": "Stay quiet and keep the state under observation.",
            },
        ]
        candidates.sort(key=lambda item: (-int(item.get("score", 0) or 0), str(item.get("mode", ""))))
        return candidates

    def _internal_council_trace(
        self,
        *,
        top_item: dict,
        decision: str,
        notification_policy: dict,
        quiet_hours_active: bool,
        scores: dict[str, int],
        world_state: dict,
    ) -> dict[str, Any]:
        title = str(top_item.get("title", "No urgent item")).strip() or "No urgent item"
        next_action = str(top_item.get("next_action", "keep monitoring")).strip() or "keep monitoring"
        domain = str(top_item.get("domain", "")).strip().lower() or "general"
        blocked_domains = {str(item.get("domain", "")).strip().lower() for item in list(world_state.get("blocked_work", [])) if isinstance(item, dict)}
        members = [
            {
                "role": "planner",
                "vote": "act" if bool(top_item.get("auto_execution", {}).get("allowed")) else ("notify" if bool(top_item.get("needs_revisit")) else "queue"),
                "weight": 3,
                "reason": f"Sequence around {title.lower()} by aiming for '{next_action}'.",
            },
            {
                "role": "critic",
                "vote": "hold" if scores.get("risk", 0) >= 4 else "queue",
                "weight": 2,
                "reason": "Challenge risky or noisy moves before they spill out.",
            },
            {
                "role": "executor",
                "vote": "act" if decision == "act" else ("notify" if decision == "notify" else "queue"),
                "weight": 3,
                "reason": "Translate the chosen move into the smallest concrete next step.",
            },
            {
                "role": "historian",
                "vote": "notify" if domain in blocked_domains else "queue",
                "weight": 1,
                "reason": "Bias toward patterns that previously unblocked stale work.",
            },
            {
                "role": "safety_governor",
                "vote": "hold" if quiet_hours_active and not bool(notification_policy.get("interrupt_during_quiet_hours")) else decision,
                "weight": 4,
                "reason": str(notification_policy.get("summary", "Stay inside approval boundaries and avoid noisy escalation.")),
            },
            {
                "role": "strategist",
                "vote": "notify" if domain == "growth" and scores.get("interruption", 0) >= 3 else ("act" if decision == "act" else "queue"),
                "weight": 2,
                "reason": "Prefer the move that reduces friction while preserving leverage.",
            },
        ]
        tally: dict[str, int] = {}
        for item in members:
            vote = str(item.get("vote", "queue")).strip().lower() or "queue"
            tally[vote] = int(tally.get(vote, 0) or 0) + int(item.get("weight", 1) or 1)
        ordered = sorted(tally.items(), key=lambda entry: (-int(entry[1]), entry[0]))
        return {
            "consensus": decision,
            "tally": tally,
            "members": members,
            "winning_vote": ordered[0][0] if ordered else decision,
        }

    def deliberation_snapshot(self, actor_name: str = "Chris", *, open_loops: dict | None = None) -> dict:
        actor = self.get_actor(actor_name)
        open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
        world_state = self.world_state_snapshot(actor.display_name, open_loops=open_loops, persist=False)
        cadence = self.cognitive_cadence_snapshot(actor.display_name, open_loops=open_loops)
        growth_state = self.growth_state_snapshot(actor.display_name)
        top_item = dict(open_loops.get("top_item") or {})
        if not top_item:
            return {
                "actor": actor.display_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "mode": "watch",
                "decision": "hold",
                "reasoning": [
                    "No urgent open-loop item is strong enough to justify an intervention right now."
                ],
                "simulation": {
                    "smallest_helpful_move": "Keep monitoring and wait for the next meaningful signal.",
                    "risk_if_act_now": "Could create unnecessary noise.",
                    "risk_if_hold": "Low.",
                },
        }
        notification_policy = self._notification_policy_for_item(top_item, actor_name=actor.display_name)
        quiet_hours_active = self._quiet_hours_active()
        cadence_phase = str(cadence.get("phase", "watch")).strip().lower()
        world_boost = self._world_state_priority_boost(top_item, world_state)
        growth_pressure = str((growth_state.get("summary") or {}).get("pressure", "quiet")).strip().lower()
        growth_guidance = self._growth_loop_guidance(
            actor,
            growth_state=growth_state,
            cadence=cadence,
        )
        blocked_work = list(world_state.get("blocked_work", [])) if isinstance(world_state.get("blocked_work", []), list) else []
        conflicts = list(world_state.get("conflicts", [])) if isinstance(world_state.get("conflicts", []), list) else []
        likely_next = list(world_state.get("likely_next", [])) if isinstance(world_state.get("likely_next", []), list) else []
        decision = "queue"
        mode = "careful-planning"
        if self._auto_execution_ready(top_item, cadence_phase=cadence_phase, quiet_hours_active=quiet_hours_active):
            decision = "act"
            mode = "action"
        elif quiet_hours_active and not bool(notification_policy.get("interrupt_during_quiet_hours")):
            decision = "hold"
            mode = "watch"
        elif cadence_phase in {"morning", "pre-transition"} and str(top_item.get("domain", "")).strip().lower() in {"family", "approvals"}:
            decision = "notify"
            mode = "simulation"
        elif str(top_item.get("domain", "")).strip().lower() == "growth" and growth_pressure in {"active", "warming"}:
            decision = "queue" if quiet_hours_active else "notify"
            mode = "simulation"
        elif world_boost.get("score", 0) >= 2 and bool(top_item.get("needs_revisit")):
            decision = "notify"
            mode = "simulation"
        elif bool(top_item.get("needs_revisit")):
            decision = "notify"
            mode = "simulation"
        scores = self._deliberation_scores(
            top_item,
            world_state=world_state,
            cadence=cadence,
            growth_state=growth_state,
            notification_policy=notification_policy,
            quiet_hours_active=quiet_hours_active,
            world_boost=world_boost,
        )
        mode_candidates = self._deliberation_mode_candidates(
            top_item=top_item,
            world_state=world_state,
            quiet_hours_active=quiet_hours_active,
            decision=decision,
            scores=scores,
        )
        if mode_candidates:
            mode = str(mode_candidates[0].get("mode", mode)).strip() or mode
        council_trace = self._internal_council_trace(
            top_item=top_item,
            decision=decision,
            notification_policy=notification_policy,
            quiet_hours_active=quiet_hours_active,
            scores=scores,
            world_state=world_state,
        )
        smallest_helpful_move = str(top_item.get("next_action", "follow up")).strip() or "follow up"
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "decision": decision,
            "top_item": top_item,
            "reasoning": [
                f"Top pressure is in the {str(top_item.get('domain', 'general'))} lane.",
                f"Cadence phase is {cadence_phase or 'watch'}, which points JARVIS toward {str(cadence.get('suggested_loop', 'autonomy-sweep'))}.",
                f"Growth pressure is {growth_pressure}, so leverage-bearing work should {'stay quiet' if growth_pressure == 'quiet' else 'stay on the board'} when it matters.",
                f"Current growth review posture: {growth_guidance.get('label', 'Growth Watch')} - {growth_guidance.get('summary', '')}",
                *list(world_boost.get("reasons", []))[:2],
                *( [f"Blocked work is now visible around {blocked_work[0].get('title', 'the current bottleneck')}." ] if blocked_work else [] ),
                *( [f"Conflict watch: {conflicts[0].get('summary', '')}"] if conflicts else [] ),
                *( [f"Most likely next: {likely_next[0].get('title', '')}"] if likely_next else [] ),
                str(notification_policy.get("summary", "JARVIS is balancing queueing, surfacing, and interruption policy.")),
                "Quiet-hour policy suppresses alerts unless explicitly permitted." if quiet_hours_active else "Active-hour policy allows eligible resurfacing to interrupt on trusted devices.",
            ],
            "scores": scores,
            "mode_candidates": mode_candidates,
            "decision_record": {
                "decision": decision,
                "mode": mode,
                "smallest_helpful_move": smallest_helpful_move,
                "risk_level": "high" if scores.get("risk", 0) >= 4 else ("medium" if scores.get("risk", 0) >= 2 else "low"),
                "interruption_level": "high" if scores.get("interruption", 0) >= 4 else ("medium" if scores.get("interruption", 0) >= 2 else "low"),
                "why": [
                    *(list(world_boost.get("reasons", []))[:2]),
                    str(notification_policy.get("summary", "JARVIS is balancing queueing, surfacing, and interruption policy.")),
                ],
            },
            "simulation": {
                "smallest_helpful_move": smallest_helpful_move,
                "risk_if_act_now": "Noise or premature interruption." if decision != "act" else "Low, because this path is explicitly policy-approved.",
                "risk_if_hold": "Important follow-up may go stale." if bool(top_item.get("needs_revisit")) else "Low.",
                "smallest_helpful_move_score": scores.get("smallest_helpful_move", 1),
                "risk_score": scores.get("risk", 1),
                "interruption_score": scores.get("interruption", 0),
            },
            "council_trace": council_trace,
        }

    def cognitive_snapshot(self, actor_name: str = "Chris", *, include_graph: bool = True, open_loops: dict | None = None) -> dict:
        if open_loops is None and not include_graph:
            return self._cached_surface(
                "cognitive",
                actor_name,
                lambda: self.cognitive_snapshot(actor_name, include_graph=include_graph, open_loops=self.unified_open_loops(actor_name, limit=18)),
                include_graph=str(bool(include_graph)).lower(),
            )
        actor = self.get_actor(actor_name)
        open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
        payload = {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "self_model": self.self_model_snapshot(actor.display_name),
            "world_state": self.world_state_snapshot(actor.display_name, open_loops=open_loops, persist=False),
            "growth_state": self.growth_state_snapshot(actor.display_name),
            "goal_stack": self.goal_stack_snapshot(actor.display_name, open_loops=open_loops),
            "cadence": self.cognitive_cadence_snapshot(actor.display_name, open_loops=open_loops),
            "deliberation": self.deliberation_snapshot(actor.display_name, open_loops=open_loops),
            "internal_council": self.internal_council_snapshot(actor.display_name, open_loops=open_loops),
            "notification_policy": {
                "quiet_hours_active": self._quiet_hours_active(),
                "quiet_window": {
                    "start": getattr(self.household, "quiet_start", "22:00"),
                    "end": getattr(self.household, "quiet_end", "06:00"),
                },
            },
        }
        if include_graph:
            payload["world_graph"] = self.world_graph_snapshot(actor.display_name, open_loops=open_loops)
        return payload

    def world_state_view(self, actor_name: str = "Chris") -> dict:
        return self._cached_surface(
            "world_state",
            actor_name,
            lambda: self.world_state_snapshot(actor_name, persist=False),
        )

    def unified_open_loops(self, actor_name: str = "Chris", limit: int = 30) -> dict:
        actor = self.get_actor(actor_name)
        items: list[dict] = []
        hidden_deferred = 0

        def maybe_include(item: dict) -> None:
            nonlocal hidden_deferred
            domain = str(item.get("domain", "")).strip().lower()
            item_id = str(item.get("item_id", "")).strip()
            item_actor = str(item.get("actor", "")).strip()
            if not self._open_loop_visible_to_actor(actor, domain=domain, item_actor=item_actor):
                return
            deferred = self.assistant_core_store.deferred_record(self._open_loop_key(domain, item_id))
            if deferred:
                until = str(deferred.get("until", "")).strip()
                parsed_until = self._parse_timestamp(until)
                if parsed_until and parsed_until.astimezone(timezone.utc) > datetime.now(timezone.utc):
                    hidden_deferred += 1
                    return
                self.assistant_core_store.clear_deferred(self._open_loop_key(domain, item_id))
            item["available_actions"] = self._available_actions(domain, str(item.get("status", "")))
            items.append(item)

        for item in self.list_pending_approvals():
            task_lane = self._task_lane_for_domain("approvals")
            threshold = self._approval_threshold_for_domain("approvals")
            timestamp = str(item.get("timestamp", "")) or str(item.get("created_at", ""))
            follow_up = self._follow_up_state(timestamp, str(item.get("status", "pending")), "approvals")
            maybe_include(
                {
                    "item_id": str(item.get("request_id", "")),
                    "domain": "approvals",
                    "kind": "approval-request",
                    "title": str(item.get("request", "Approval required")).strip(),
                    "summary": str(item.get("rationale", "")).strip(),
                    "status": str(item.get("status", "pending")).strip(),
                    "actor": str(item.get("actor", "")).strip(),
                    "timestamp": timestamp,
                    "task_lane": task_lane["lane"],
                    "owner_agent": task_lane["owner_agent"],
                    "approval_threshold": threshold,
                    "auto_execution": self._auto_execution_policy("approvals", str(item.get("status", "pending")), item),
                    **follow_up,
                }
            )

        for item in self.family_support.list_drafts(limit=limit):
            status = str(item.get("status", "staged")).strip()
            if status.lower() in {"sent", "archived"}:
                continue
            timestamp = str(item.get("timestamp", ""))
            task_lane = self._task_lane_for_domain("family")
            threshold = self._approval_threshold_for_domain("family")
            follow_up = self._follow_up_state(timestamp, status, "family")
            maybe_include(
                {
                    "item_id": str(item.get("draft_id", "")),
                    "domain": "family",
                    "kind": "message-draft",
                    "title": f"{item.get('audience', 'Message draft')} · {item.get('purpose', 'draft')}",
                    "summary": str(item.get("context", "")).strip(),
                    "status": status,
                    "actor": str(item.get("actor", "")).strip(),
                    "timestamp": timestamp,
                    "task_lane": task_lane["lane"],
                    "owner_agent": task_lane["owner_agent"],
                    "approval_threshold": threshold,
                    "auto_execution": self._auto_execution_policy("family", status, item),
                    "approval_request_id": str(item.get("approval_request_id", "")).strip(),
                    **follow_up,
                }
            )

        for item in self.list_vendor_preps(limit=limit):
            status = str(item.get("status", "staged")).strip()
            if status.lower() in {"submitted", "completed", "live"}:
                continue
            timestamp = str(item.get("timestamp", ""))
            task_lane = self._task_lane_for_domain("workshop")
            threshold = self._approval_threshold_for_domain("workshop")
            follow_up = self._follow_up_state(timestamp, status, "workshop")
            maybe_include(
                {
                    "item_id": str(item.get("prep_id", "")),
                    "domain": "workshop",
                    "kind": "vendor-prep",
                    "title": f"{item.get('part_name', 'Vendor prep')} · {item.get('vendor_target', 'vendor')}",
                    "summary": str(item.get("process", "")).strip(),
                    "status": status,
                    "actor": str(item.get("actor", "")).strip(),
                    "timestamp": timestamp,
                    "task_lane": task_lane["lane"],
                    "owner_agent": task_lane["owner_agent"],
                    "approval_threshold": threshold,
                    "auto_execution": self._auto_execution_policy("workshop", status, item),
                    "approval_request_id": str(item.get("approval_request_id", "")).strip(),
                    **follow_up,
                }
            )

        for item in self.memory_support.proposals(status="pending")[:limit]:
            timestamp = str(item.get("created_at", ""))
            task_lane = self._task_lane_for_domain("memory")
            threshold = self._approval_threshold_for_domain("memory")
            follow_up = self._follow_up_state(timestamp, str(item.get("status", "pending")), "memory")
            maybe_include(
                {
                    "item_id": str(item.get("proposal_id", "")),
                    "domain": "memory",
                    "kind": "memory-proposal",
                    "title": str(item.get("title", "Memory proposal")).strip(),
                    "summary": str(item.get("rationale", "")).strip(),
                    "status": str(item.get("status", "pending")).strip(),
                    "actor": str(item.get("actor", "")).strip(),
                    "timestamp": timestamp,
                    "task_lane": task_lane["lane"],
                    "owner_agent": task_lane["owner_agent"],
                    "approval_threshold": threshold,
                    "auto_execution": self._auto_execution_policy("memory", str(item.get("status", "pending")), item),
                    **follow_up,
                }
            )

        content_queue = self.content_ops.snapshot().get("queue", [])
        for item in content_queue[:limit]:
            status = str(item.get("status", "queued")).strip()
            if status.lower() == "live":
                continue
            timestamp = str(item.get("created_at", "")) or str(item.get("updated_at", ""))
            task_lane = self._task_lane_for_domain("content")
            threshold = self._approval_threshold_for_domain("content")
            follow_up = self._follow_up_state(timestamp, status, "content")
            maybe_include(
                {
                    "item_id": str(item.get("queue_id", "")),
                    "domain": "content",
                    "kind": "content-queue",
                    "title": str(item.get("title", "Queued content")).strip() or "Queued content",
                    "summary": str(item.get("hook", "") or item.get("angle", "")).strip(),
                    "status": status,
                    "actor": str(item.get("actor", "")).strip(),
                    "timestamp": timestamp,
                    "task_lane": task_lane["lane"],
                    "owner_agent": task_lane["owner_agent"],
                    "approval_threshold": threshold,
                    "auto_execution": self._auto_execution_policy("content", status, item),
                    **follow_up,
                }
            )

        growth_state = self.growth_state_snapshot(actor.display_name)
        finance_state = self.finance_state_snapshot(actor.display_name)
        pipeline_state = self.pipeline_state_snapshot(actor.display_name)
        marketing_state = self.marketing_state_snapshot(actor.display_name)
        lane_titles = {str(item.get("title", "")).strip().lower() for item in items}
        for lane in growth_state.get("lanes", []):
            pressure = str(lane.get("pressure", "quiet")).strip().lower()
            latest = str(lane.get("latest", "")).strip()
            if pressure == "quiet" and not latest:
                continue
            timestamp = str((growth_state.get("latest_timestamps") or {}).get(str(lane.get("id", "")), "")).strip() or str(growth_state.get("generated_at", "")).strip()
            status = "warming" if pressure in {"warming", "active"} else "staged"
            lane_signal = self._growth_lane_operating_signal(
                actor.display_name,
                str(lane.get("id", "")).strip(),
                growth_state=growth_state,
                finance_state=finance_state,
                pipeline_state=pipeline_state,
                marketing_state=marketing_state,
            )
            follow_up = self._follow_up_state(timestamp, status, "growth")
            if lane_signal.get("due_now"):
                follow_up["needs_revisit"] = True
                follow_up["due_for_surface"] = True
            if str(lane_signal.get("next_action", "")).strip():
                follow_up["next_action"] = str(lane_signal.get("next_action", "")).strip()
            if str(lane_signal.get("why_now", "")).strip():
                follow_up["proactive_reason"] = str(lane_signal.get("why_now", "")).strip()
            title = str(lane_signal.get("title", "")).strip() or latest or str(lane.get("label", "Growth lane")).strip()
            if title.lower() in lane_titles:
                continue
            lane_titles.add(title.lower())
            task_lane = self._task_lane_for_domain("growth")
            threshold = self._approval_threshold_for_domain("growth")
            maybe_include(
                {
                    "item_id": str(lane.get("id", "")) or str(uuid.uuid4()),
                    "domain": "growth",
                    "kind": "growth-lane",
                    "title": title,
                    "summary": str(lane_signal.get("summary", "")).strip() or str(lane.get("summary", "")).strip(),
                    "status": status,
                    "actor": actor.display_name,
                    "timestamp": timestamp,
                    "task_lane": task_lane["lane"],
                    "owner_agent": task_lane["owner_agent"],
                    "approval_threshold": threshold,
                    "suggested_packet": str(lane_signal.get("packet", "")).strip(),
                    "growth_lane_id": str(lane_signal.get("lane_id", "")).strip(),
                    "growth_review_due": bool(lane_signal.get("due_now")),
                    "growth_high_pressure": bool(lane_signal.get("high_pressure")),
                    "growth_signal_summary": str(lane_signal.get("summary", "")).strip(),
                    "growth_recommended_next_move": str(lane_signal.get("recommended_next_move", "")).strip(),
                    "auto_execution": self._auto_execution_policy("growth", status, lane),
                    **follow_up,
                }
            )

        bucket_rank = {"aged": 0, "stale": 1, "today": 2, "fresh": 3, "unknown": 4}
        items.sort(
            key=lambda item: (
                0 if item.get("needs_revisit") else 1,
                0 if str(item.get("status", "")).lower() in {"pending", "pending-approval"} else 1,
                bucket_rank.get(str(item.get("age_bucket", "unknown")), 4),
                str(item.get("timestamp", "")),
            )
        )
        counts: dict[str, int] = {}
        staged = 0
        waiting = 0
        revisit = 0
        for item in items:
            domain = str(item.get("domain", "general"))
            counts[domain] = counts.get(domain, 0) + 1
            if str(item.get("status", "")).lower() in {"queued", "scripted", "staged"}:
                staged += 1
            if str(item.get("status", "")).lower() in {"pending", "pending-approval"}:
                waiting += 1
            if item.get("needs_revisit"):
                revisit += 1
        proactive = [item for item in items if item.get("proactive_reason")][:6]
        surface = self._assistant_surface({"summary": {"waiting_on_you": waiting, "needs_revisit": revisit}, "proactive_surface": proactive})
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total": len(items[:limit]),
                "staged": staged,
                "waiting_on_you": waiting,
                "needs_revisit": revisit,
                "hidden_deferred": hidden_deferred,
                "by_domain": counts,
            },
            "task_lanes": [
                {"domain": domain, **self._task_lane_for_domain(domain), "approval_threshold": self._approval_threshold_for_domain(domain)}
                for domain in ["approvals", "family", "workshop", "memory", "content", "growth"]
            ],
            "items": items[:limit],
            "proactive_surface": proactive,
            "surface_chips": surface["chips"],
            "briefing_lines": surface["briefing_lines"],
            "auto_open_packet": surface["auto_open_packet"],
            "surface_key": surface["surface_key"],
            "top_item": surface["top_item"],
        }

    def explainability_snapshot(self, actor_name: str = "Chris") -> dict:
        activity = self.audit_log.list_recent(limit=12, entry_type="plan")
        assistant_actions = self.audit_log.list_recent(limit=12, entry_type="assistant-action")
        actor = self.get_actor(actor_name)
        assistant_outcomes = self.assistant_core_store.outcome_history(actor.display_name, limit=16)
        tuning_summary = self.recommendation_tuning_snapshot(actor.display_name)
        approvals = self.approval_history()
        status_items = self.status()
        blocked_integrations = [item for item in status_items if not item["ok"]]
        module_counts: dict[str, int] = {}
        for item in activity:
            module = item.get("module", "unknown")
            module_counts[module] = module_counts.get(module, 0) + 1
        action_summary = {
            "total": len(assistant_actions),
            "automatic": sum(1 for item in assistant_actions if str(item.get("mode", "")).strip().lower() == "automatic"),
            "successful": sum(1 for item in assistant_actions if item.get("succeeded") is True),
            "failed": sum(1 for item in assistant_actions if item.get("succeeded") is False),
            "friction": sum(1 for item in assistant_actions if item.get("caused_friction") is True),
            "by_domain": {},
            "by_action_class": {},
        }
        normalized_assistant_actions: list[dict] = []
        for item in assistant_actions:
            domain = str(item.get("domain", "general")).strip().lower() or "general"
            action_class = str(item.get("action_class", "uncategorized")).strip().lower() or "uncategorized"
            action_summary["by_domain"][domain] = int(action_summary["by_domain"].get(domain, 0) or 0) + 1
            action_summary["by_action_class"][action_class] = int(action_summary["by_action_class"].get(action_class, 0) or 0) + 1
            normalized_assistant_actions.append(
                {
                    "actor": str(item.get("actor", "")).strip(),
                    "domain": str(item.get("domain", "")).strip(),
                    "item_id": str(item.get("item_id", "")).strip(),
                    "action": str(item.get("action", "")).strip(),
                    "action_class": str(item.get("action_class", "")).strip() or "uncategorized",
                    "mode": str(item.get("mode", "")).strip() or "automatic",
                    "policy_basis": str(item.get("policy_basis", "")).strip() or str(item.get("detail", "")).strip(),
                    "confidence": str(item.get("confidence", "")).strip() or "medium",
                    "decision": str(item.get("decision", "")).strip(),
                    "cadence_phase": str(item.get("cadence_phase", "")).strip(),
                    "quiet_hours_active": bool(item.get("quiet_hours_active", False)),
                    "why_now": str(item.get("why_now", "")).strip(),
                    "result_summary": str(item.get("result_summary", "")).strip() or "Action completed.",
                    "succeeded": bool(item.get("succeeded", False)),
                    "caused_friction": bool(item.get("caused_friction", False)),
                    "friction_reason": str(item.get("friction_reason", "")).strip(),
                    "surface_key": str(item.get("surface_key", "")).strip(),
                    "timestamp": str(item.get("timestamp", "")).strip(),
                }
            )
        latest_reasons = [
            {
                "actor": item.get("actor", ""),
                "request": item.get("request", ""),
                "module": item.get("module", ""),
                "action_class": item.get("action_class", ""),
                "needs_approval": item.get("needs_approval", False),
                "second_factor_required": item.get("second_factor_required", False),
                "rationale": item.get("rationale", ""),
                "timestamp": item.get("timestamp", ""),
            }
            for item in activity[:8]
        ]
        return {
            "blocked_integrations": blocked_integrations,
            "approval_history": approvals[-12:],
            "module_counts": module_counts,
            "latest_reasons": latest_reasons,
            "assistant_action_summary": action_summary,
            "assistant_actions": normalized_assistant_actions,
            "assistant_outcome_summary": self.assistant_core_store.outcome_summary(actor.display_name, limit=200),
            "assistant_outcomes": assistant_outcomes,
            "assistant_tuning_summary": tuning_summary,
        }

    def recommendation_tuning_snapshot(self, actor_name: str = "Chris", *, device_id: str = "") -> dict:
        domains = ["approvals", "family", "workshop", "growth", "content", "memory"]
        actor_profile = self._recommendation_tuning_profile(actor_name, device_id=device_id)
        domain_profiles = {
            domain: self._recommendation_tuning_profile(actor_name, domain=domain, device_id=device_id)
            for domain in domains
        }
        strongest_queue_bias = sorted(
            (
                {
                    "domain": domain,
                    "queue_bias": int(profile.get("queue_bias", 0) or 0),
                    "sample_size": int((profile.get("domain_profile") or {}).get("sample_size", 0) or 0),
                }
                for domain, profile in domain_profiles.items()
            ),
            key=lambda item: (-int(item.get("queue_bias", 0) or 0), -int(item.get("sample_size", 0) or 0), item.get("domain", "")),
        )[:3]
        return {
            "actor": actor_name,
            "device_id": device_id.strip(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "actor_profile": actor_profile,
            "domains": domain_profiles,
            "summary": {
                "interrupt_threshold_delta": int(actor_profile.get("interrupt_threshold_delta", 0) or 0),
                "cooldown_delta_minutes": int(actor_profile.get("cooldown_delta_minutes", 0) or 0),
                "queue_bias": int(actor_profile.get("queue_bias", 0) or 0),
                "sample_size": int((actor_profile.get("actor_profile") or {}).get("sample_size", 0) or 0),
            },
            "strongest_queue_bias": strongest_queue_bias,
        }

    def update_approval(self, request_id: str, status: str) -> dict | None:
        return self.approval_store.update_status(request_id, status)

    def _default_defer_until(self, action: str) -> str:
        if action == "defer-tomorrow-am":
            return self._next_tomorrow_morning()
        hours = 24 if action == "defer-1d" else 4
        return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()

    def _growth_lane_snapshot(self, actor_name: str, lane_id: str) -> dict:
        growth_state = self.growth_state_snapshot(actor_name)
        lane_key = lane_id.strip().lower()
        lane = next(
            (item for item in list(growth_state.get("lanes", [])) if str(item.get("id", "")).strip().lower() == lane_key),
            {},
        )
        return {
            "growth_state": growth_state,
            "lane": lane,
        }

    def _prepare_growth_summary(self, actor_name: str, lane_id: str) -> dict:
        lane_state = self._growth_lane_snapshot(actor_name, lane_id)
        growth_state = lane_state["growth_state"]
        lane = dict(lane_state["lane"] or {})
        label = str(lane.get("label", "Growth lane")).strip() or "Growth lane"
        context = (
            f"Prepare a concise review summary for {label}. "
            f"Current pressure: {lane.get('pressure', 'quiet')}. "
            f"Lane summary: {lane.get('summary', '')}. "
            f"Top signals: {' | '.join(list(growth_state.get('top_signals', []))[:4])}."
        )
        record = self.catalyst_support.briefing_generation(actor_name, context)
        return {
            "ok": True,
            "workflow": "prepare-summary",
            "lane_id": lane_id,
            "lane_label": label,
            "record": record,
        }

    def _refresh_growth_brief(self, actor_name: str, lane_id: str) -> dict:
        lane_state = self._growth_lane_snapshot(actor_name, lane_id)
        growth_state = lane_state["growth_state"]
        lane = dict(lane_state["lane"] or {})
        label = str(lane.get("label", "Growth lane")).strip() or "Growth lane"
        context = (
            f"Refresh the operating brief for {label}. "
            f"Current pressure: {lane.get('pressure', 'quiet')}. "
            f"Lane summary: {lane.get('summary', '')}. "
            f"Next moves: {' | '.join(list(growth_state.get('next_moves', []))[:3])}."
        )
        record = self.catalyst_support.proactive_surfacing(actor_name, horizon="today", context=context)
        return {
            "ok": True,
            "workflow": "refresh-brief",
            "lane_id": lane_id,
            "lane_label": label,
            "record": record,
        }

    def apply_open_loop_action(
        self,
        actor_name: str,
        *,
        domain: str,
        item_id: str,
        action: str,
        until: str = "",
        note: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        domain = domain.strip().lower()
        action = action.strip().lower()
        item_key = self._open_loop_key(domain, item_id)
        result: dict[str, object] = {"ok": True, "actor": actor.display_name, "domain": domain, "item_id": item_id, "action": action}

        if action in {"defer", "defer-1d", "defer-4h", "defer-tomorrow-am"}:
            record = self.assistant_core_store.set_deferred(
                item_key,
                until=until.strip() or self._default_defer_until(action),
                actor=actor.display_name,
                reason=note,
            )
            result["deferred"] = record
        elif action == "surface-now":
            self.assistant_core_store.clear_deferred(item_key)
            result["cleared"] = True
        elif domain == "approvals":
            mapped = {"approve": "approved", "reject": "rejected"}.get(action)
            if not mapped:
                raise ValueError("Unsupported approval action.")
            updated = self.update_approval(item_id, mapped)
            if updated is None:
                raise KeyError("Approval request not found.")
            linked_draft = next(
                (item for item in self.list_message_drafts(limit=200) if str(item.get("approval_request_id", "")).strip() == item_id),
                None,
            )
            if linked_draft:
                self.update_message_draft(str(linked_draft.get("draft_id", "")), "staged" if mapped == "approved" else "archived")
            linked_prep = next(
                (item for item in self.list_vendor_preps(limit=200) if str(item.get("approval_request_id", "")).strip() == item_id),
                None,
            )
            if linked_prep:
                self.update_vendor_prep_status(str(linked_prep.get("prep_id", "")), "staged" if mapped == "approved" else "archived")
            result["record"] = updated
        elif domain == "family":
            draft = next((item for item in self.list_message_drafts(limit=200) if str(item.get("draft_id", "")) == item_id), None)
            if not draft:
                raise KeyError("Message draft not found.")
            if action == "approve":
                approval_id = str(draft.get("approval_request_id", "")).strip()
                if approval_id:
                    self.update_approval(approval_id, "approved")
                updated = self.update_message_draft(item_id, "staged")
            elif action == "reject":
                approval_id = str(draft.get("approval_request_id", "")).strip()
                if approval_id:
                    self.update_approval(approval_id, "rejected")
                updated = self.update_message_draft(item_id, "archived")
            elif action == "done":
                updated = self.update_message_draft(item_id, "sent")
            elif action == "archive":
                updated = self.update_message_draft(item_id, "archived")
            else:
                raise ValueError("Unsupported family action.")
            result["record"] = updated
        elif domain == "workshop":
            prep = next((item for item in self.list_vendor_preps(limit=200) if str(item.get("prep_id", "")) == item_id), None)
            if not prep:
                raise KeyError("Vendor prep not found.")
            if action == "approve":
                approval_id = str(prep.get("approval_request_id", "")).strip()
                if approval_id:
                    self.update_approval(approval_id, "approved")
                updated = self.update_vendor_prep_status(item_id, "staged")
            elif action == "reject":
                approval_id = str(prep.get("approval_request_id", "")).strip()
                if approval_id:
                    self.update_approval(approval_id, "rejected")
                updated = self.update_vendor_prep_status(item_id, "archived")
            elif action == "done":
                updated = self.update_vendor_prep_status(item_id, "completed")
            elif action == "archive":
                updated = self.update_vendor_prep_status(item_id, "archived")
            else:
                raise ValueError("Unsupported workshop action.")
            result["record"] = updated
        elif domain == "memory":
            if action == "approve":
                result["record"] = self.resolve_memory_proposal(item_id, "approved")
            elif action == "reject":
                result["record"] = self.resolve_memory_proposal(item_id, "rejected")
            else:
                raise ValueError("Unsupported memory action.")
        elif domain == "content":
            if action == "export":
                result["record"] = self.veronica_export(item_id)
            elif action == "publish":
                result["record"] = self.veronica_push_live(item_id)
            elif action == "archive":
                updated = self.content_ops.store.update_queue_item(item_id, status="archived", archived_at=datetime.now(timezone.utc).isoformat())
                result["record"] = {"ok": bool(updated), "record": updated}
            else:
                raise ValueError("Unsupported content action.")
        elif domain == "growth":
            if action == "prepare-summary":
                result["record"] = self._prepare_growth_summary(actor.display_name, item_id)
            elif action == "refresh-brief":
                result["record"] = self._refresh_growth_brief(actor.display_name, item_id)
            else:
                raise ValueError("Unsupported growth action.")
        else:
            raise ValueError("Unsupported task domain.")

        outcome_status = "acted"
        if action.startswith("defer-") or action == "defer":
            outcome_status = "deferred"
        elif action == "reject":
            outcome_status = "rejected"
        if note.strip() != "assistant-autonomy":
            self.assistant_core_store.record_outcome(
                actor.display_name,
                source="task-action",
                initiator="user",
                status=outcome_status,
                domain=domain,
                item_id=item_id,
                action=action,
                detail=self._assistant_action_result_summary(result),
            )

        if action in {"approve", "reject", "done", "archive", "export", "publish", "prepare-summary", "refresh-brief"} or action.startswith("defer-"):
            self.assistant_core_store.mark_notifications_for_item(actor.display_name, domain=domain, item_id=item_id, status="acted")

        self._invalidate_snapshot_cache(actor.display_name)
        result["open_loops"] = self.unified_open_loops(actor.display_name, limit=18)
        return result

    def respond(self, actor_name: str, room: str, request: str) -> OpenAIResult:
        plan = self.plan_request(actor_name, room, request)
        actor = self.get_actor(actor_name)
        if not plan.allowed:
            result = OpenAIResult(
                provider="policy",
                model="policy",
                output_text=self.tutoring_support.denial_response(actor, request, plan.rationale),
            )
            self.audit_log.log_response(
                plan,
                provider=result.provider,
                model=result.model,
                active_nodes=self._active_nodes_for(plan, result.provider),
                output_text=result.output_text,
            )
            return result
        result = run_response_graph(self, plan)
        self.audit_log.log_response(
            plan,
            provider=result.provider,
            model=result.model,
            active_nodes=self._active_nodes_for(plan, result.provider),
            output_text=result.output_text,
        )
        return result

    def brain_graph_snapshot(self) -> dict:
        second_brain = self.openai_client.second_brain_status()
        recent = self.audit_log.list_recent(limit=1, entry_type="response")
        latest = recent[0] if recent else {}
        active_nodes = latest.get("active_nodes", []) if isinstance(latest, dict) else []
        return {
            "active_provider": latest.get("provider", "standby") if isinstance(latest, dict) else "standby",
            "active_model": latest.get("model", "") if isinstance(latest, dict) else "",
            "last_module": latest.get("module", "") if isinstance(latest, dict) else "",
            "last_timestamp": latest.get("timestamp", "") if isinstance(latest, dict) else "",
            "active_nodes": active_nodes,
            "secondary_brain": second_brain,
            "nodes": [
                {"id": "router", "label": "Router", "status": "ready"},
                {"id": "primary-brain", "label": "Primary", "status": "ready" if self.config.openai_api_key else "offline"},
                {
                    "id": "second-brain",
                    "label": "Second",
                    "status": "ready" if second_brain.get("model_available") else ("configured" if second_brain.get("healthy") or second_brain.get("enabled") else "disabled"),
                },
                {"id": "memory-core", "label": "Memory", "status": "ready"},
                {"id": "catalyst-personal", "label": "Catalyst", "status": "ready"},
                {"id": "household-associate", "label": "Ambient", "status": "ready"},
                {"id": "family-logistics", "label": "Family", "status": "ready"},
                {"id": "executive-work", "label": "Work", "status": "ready"},
                {"id": "faith-and-formation", "label": "Chronicle", "status": "ready"},
                {"id": "workshop-copilot", "label": "Workshop", "status": "ready"},
            ],
        }

    def agent_registry_snapshot(self) -> dict:
        return {
            "agents": [
                {
                    "agent_id": agent.agent_id,
                    "label": agent.label,
                    "purpose": agent.purpose,
                    "cadence_minutes": agent.cadence_minutes,
                    "triggers": list(agent.triggers),
                    "dependencies": list(agent.dependencies),
                    "memory_scope": list(agent.memory_scope),
                    "owns": list(agent.owns),
                    "quiet_hours_behavior": agent.quiet_hours_behavior,
                }
                for agent in self.agent_registry.list()
            ]
        }

    def background_agent_status(
        self,
        *,
        recent_activity: list[dict] | None = None,
        integration_status: list[dict] | None = None,
    ) -> dict:
        active_mode = self.family_support.active_mode().mode
        activity = recent_activity if recent_activity is not None else self.recent_activity(limit=20)
        status_items = integration_status if integration_status is not None else self.status()
        return self.background_cycle(
            active_mode=active_mode,
            recent_activity=activity,
            integration_status=status_items,
        )["scheduler"]

    def memory_curator_snapshot(self, *, recent_activity: list[dict] | None = None) -> dict:
        activity = recent_activity if recent_activity is not None else self.recent_activity(limit=20)
        status_items = self.status()
        active_mode = self.family_support.active_mode().mode
        return self.background_cycle(
            active_mode=active_mode,
            recent_activity=activity,
            integration_status=status_items,
        )["memory_curator"]

    def background_cycle(
        self,
        *,
        active_mode: str | None = None,
        recent_activity: list[dict] | None = None,
        integration_status: list[dict] | None = None,
    ) -> dict:
        resolved_mode = active_mode or self.family_support.active_mode().mode
        activity = recent_activity if recent_activity is not None else self.recent_activity(limit=20)
        status_items = integration_status if integration_status is not None else self.status()
        return run_background_cycle_graph(
            self,
            active_mode=resolved_mode,
            recent_activity=activity,
            integration_status=status_items,
        )

    def life_agent_snapshot(self) -> dict:
        agents = [agent.to_dict() for agent in self.life_agent_store.load()]
        tiers = {
            "orchestrator": [agent for agent in agents if agent["tier"] == "orchestrator"],
            "strategic": [agent for agent in agents if agent["tier"] == "strategic"],
            "execution": [agent for agent in agents if agent["tier"] == "execution"],
        }
        validation = {
            "valid_count": sum(1 for agent in agents if not agent.get("validation_errors")),
            "invalid_count": sum(1 for agent in agents if agent.get("validation_errors")),
        }
        return {
            "agents": agents,
            "tiers": tiers,
            "schema": self.life_agent_store.schema_snapshot(),
            "validation": validation,
        }

    def save_life_agent(self, payload: dict) -> dict:
        agent = self.life_agent_store.upsert(payload)
        return {"ok": True, "agent": agent.to_dict(), "snapshot": self.life_agent_snapshot()}

    def delete_life_agent(self, agent_id: str) -> dict:
        deleted = self.life_agent_store.delete(agent_id)
        return {"ok": deleted, "snapshot": self.life_agent_snapshot()}

    def life_party_mode(self, actor_name: str, room: str, prompt: str, selected_agent_ids: list[str]) -> dict:
        actor = self.get_actor(actor_name)
        agents = {agent.agent_id: agent for agent in self.life_agent_store.load() if agent.enabled}
        selected = [agents[agent_id] for agent_id in selected_agent_ids if agent_id in agents]
        if not selected:
            selected = list(agents.values())[:4]
        party_result = run_party_mode_graph(self, actor.display_name, room, prompt, selected)
        return {
            "ok": True,
            "actor": actor.display_name,
            "room": room,
            "request": prompt,
            "participants": party_result["participants"],
            "retrieved_context": party_result["retrieved_context"],
            "synthesis": party_result["synthesis"],
        }

    def wealth_leverage_workflow(self, actor_name: str, room: str, prompt: str) -> dict:
        actor = self.get_actor(actor_name)
        agents = {agent.agent_id: agent for agent in self.life_agent_store.load() if agent.enabled}
        preferred_ids = ["black-panther", "shuri", "rocket"]
        selected = [agents[agent_id] for agent_id in preferred_ids if agent_id in agents]
        if not selected:
            selected = [agent for agent in agents.values() if agent.domain in {"finance", "executive", "workshop"}][:3]
        workflow_prompt = (
            prompt.strip()
            or "Help me identify the strongest next path toward financial independence through passive income, leverage, and ROI-aware experimentation."
        )
        result = run_wealth_leverage_graph(self, actor.display_name, room, workflow_prompt, selected)
        memory_record = self.wealth_support.record_workflow(
            {
                "request": workflow_prompt,
                "workflow": "wealth-and-leverage",
                "agents": [agent.agent_id for agent in selected],
                "focus_areas": result["focus_areas"],
                "participants": result["participants"],
                "synthesis": result["synthesis"],
            }
        )
        return {
            "ok": True,
            "actor": actor.display_name,
            "room": room,
            "request": workflow_prompt,
            "workflow": "wealth-and-leverage",
            "agents": [agent.agent_id for agent in selected],
            "focus_areas": result["focus_areas"],
            "participants": result["participants"],
            "retrieved_context": result["retrieved_context"],
            "synthesis": result["synthesis"],
            "memory_record": memory_record,
        }

    def _active_nodes_for(self, plan: RequestPlan, provider: str) -> list[str]:
        provider_node = {
            "openai": "primary-brain",
            "ollama": "second-brain",
            "policy": "primary-brain",
            "fallback": "primary-brain",
        }.get(provider, "primary-brain")
        return ["router", provider_node, "memory-core", plan.module]

    def meeting_brief(self, actor_name: str, context: str) -> str:
        actor = self.get_actor(actor_name)
        likely = self.likely_meetings(limit=3)
        meeting_lines = [
            f"{item.get('summary', '(Untitled event)')} · {item.get('start', 'No start time')} · {item.get('source_label', item.get('source', 'calendar'))}"
            for item in likely
        ]
        enriched_context = context.strip()
        if meeting_lines:
            addon = "Likely upcoming meetings from merged calendar:\n- " + "\n- ".join(meeting_lines)
            enriched_context = f"{enriched_context}\n\n{addon}".strip()
        return self.executive_support.meeting_brief(actor.display_name, enriched_context)

    def meeting_followup(self, actor_name: str, transcript: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.meeting_followup(actor.display_name, transcript)

    def decision_framework(self, actor_name: str, context: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.decision_framework(actor.display_name, context)

    def research_summary(self, actor_name: str, topic: str, notes: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.research_summary(actor.display_name, topic, notes)

    def confidentiality_review(self, text: str) -> dict:
        return self.executive_support.confidentiality_review(text)

    def manuscript_review(self, actor_name: str, excerpt: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.manuscript_review(actor.display_name, excerpt)

    def iron_clad_editor(self, actor_name: str, excerpt: str) -> str:
        actor = self.get_actor(actor_name)
        return self.executive_support.iron_clad_editor(actor.display_name, excerpt)

    def venture_brief(self, actor_name: str, topic: str, notes: str) -> str:
        actor = self.get_actor(actor_name)
        wealth_context = self.wealth_support.summary(limit=6)
        enriched_notes = (
            f"{notes}\n\nWealth and leverage continuity:\n{json.dumps(wealth_context, indent=2)}"
            if wealth_context.get("recent_runs")
            else notes
        )
        return self.executive_support.venture_brief(actor.display_name, topic, enriched_notes)

    def devotional_pause(self, actor_name: str, theme: str, mode: str = "scripture") -> str:
        actor = self.get_actor(actor_name)
        return self.chronicle_support.devotional_pause(actor.display_name, theme, mode)

    def family_devotional_prep(self, actor_name: str, theme: str, context: str = "") -> str:
        actor = self.get_actor(actor_name)
        return self.chronicle_support.family_devotional_prep(actor.display_name, theme, context)

    def chronicle_capture(self, actor_name: str, theme: str, note: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.chronicle_support.chronicle_capture(actor.display_name, theme, note)

    def chronicle_timeline(self, limit: int = 10) -> list[dict]:
        return self.chronicle_support.prayer_timeline(limit=limit)

    def chronicle_theme_summary(self, limit: int = 25) -> dict:
        return self.chronicle_support.prayer_theme_summary(limit=limit)

    def catalyst_overview(self) -> dict:
        overview = self.catalyst_support.overview()
        accounts = self.list_personal_accounts()
        google_accounts = [item for item in accounts if item["provider"] == "google"]
        family_calendar = self.family_calendar.summary()
        google_summary = {
            "accounts": [
                self.google_account_snapshot(item["account_id"])
                for item in google_accounts
            ],
            "count": len(google_accounts),
        }
        connectors: list[dict] = []
        seen_ids: set[str] = set()
        for item in overview.get("connectors", []):
            connector = dict(item)
            seen_ids.add(str(connector.get("id", "")))
            if connector.get("id") == "gmail":
                connector["status"] = "connected" if any(entry["status"].get("gmail_ready") for entry in google_summary["accounts"]) else "disconnected"
                connector["notes"] = (
                    "Personal Gmail is connected."
                    if connector["status"] == "connected"
                    else "No Gmail account is currently connected."
                )
            elif connector.get("id") == "google_calendar":
                connector["status"] = "connected" if any(entry["status"].get("calendar_ready") for entry in google_summary["accounts"]) else "disconnected"
                connector["notes"] = (
                    "Personal Google Calendar is connected."
                    if connector["status"] == "connected"
                    else "No Google calendar account is currently connected."
                )
            elif connector.get("id") in {"manual", "local_memory", "docs"}:
                connector["status"] = "local"
            connectors.append(connector)
        if "family_calendar" not in seen_ids:
            connectors.append(
                {
                    "id": "family_calendar",
                    "label": family_calendar.get("calendar", {}).get("label", "Family Shared Calendar"),
                    "status": "connected" if family_calendar.get("configured") and not family_calendar.get("error") else "disconnected",
                    "notes": family_calendar.get("detail", "Family shared calendar feed is not configured yet."),
                }
            )
        else:
            for connector in connectors:
                if connector.get("id") == "family_calendar":
                    connector["status"] = "connected" if family_calendar.get("configured") and not family_calendar.get("error") else "disconnected"
                    connector["notes"] = family_calendar.get("detail", "Family shared calendar feed is not configured yet.")
        overview["connectors"] = connectors
        overview["google_workspace"] = google_summary
        overview["family_calendar"] = family_calendar
        overview["personal_accounts"] = accounts
        return overview

    def google_workspace_status(self) -> dict:
        return {
            "default": self.google_workspace.status().to_dict(),
            "accounts": [self.google_account_snapshot(item["account_id"]) for item in self.list_personal_accounts() if item["provider"] == "google"],
        }

    def google_workspace_summary(self) -> dict:
        return {
            "client_secret": self.google_workspace.client_secret_summary(),
            "accounts": [self.google_account_snapshot(item["account_id"]) for item in self.list_personal_accounts() if item["provider"] == "google"],
        }

    def family_calendar_summary(self) -> dict:
        return self.family_calendar.summary()

    def google_connect_url(self, account_id: str, base_url: str) -> dict:
        account = self.account_registry.get(account_id)
        if not account:
            return {"ok": False, "detail": "Account not found."}
        if account.provider != "google":
            return {"ok": False, "detail": f"{account.provider.title()} login is not wired yet."}
        return self.google_workspace.build_connect_url(account, base_url)

    def google_handle_callback(self, base_url: str, code: str, state: str) -> dict:
        result = self.google_workspace.handle_callback(base_url, code, state)
        account_id = str(result.get("account_id", "")).strip()
        if result.get("ok") and account_id:
            self.account_registry.update_status(account_id, "connected", "Google login complete.")
        return result

    def google_disconnect(self) -> dict:
        return self.google_workspace.disconnect()

    def google_save_client_secret(self, raw_json: str) -> dict:
        return self.google_workspace.save_client_secret_json(raw_json)

    def google_disconnect_account(self, account_id: str) -> dict:
        account = self.account_registry.get(account_id)
        if not account:
            return {"ok": False, "message": "Account not found."}
        if account.provider != "google":
            return {"ok": False, "message": f"{account.provider.title()} disconnect is not wired yet."}
        result = self.google_workspace.disconnect(account)
        self.account_registry.update_status(account_id, "planned", "Disconnected from Google.")
        result["account"] = account.to_dict()
        return result

    def list_personal_accounts(self) -> list[dict]:
        return [item.to_dict() for item in self.account_registry.list_accounts()]

    def account_registry_snapshot(self) -> dict:
        snapshot = self.account_registry.describe()
        accounts = []
        for item in snapshot["accounts"]:
            enriched = dict(item)
            if enriched.get("provider") == "google":
                enriched["connection"] = self.google_account_snapshot(enriched["account_id"])["status"]
            accounts.append(enriched)
        snapshot["accounts"] = accounts
        return snapshot

    def save_personal_account(self, payload: dict) -> dict:
        account = self.account_registry.save_account(payload)
        self._invalidate_snapshot_cache()
        return {
            "message": f"Saved account '{account.label}'.",
            "account": account.to_dict(),
            "registry": self.account_registry_snapshot(),
        }

    def google_account_snapshot(self, account_id: str) -> dict:
        account = self.account_registry.get(account_id)
        if not account:
            return {"account_id": account_id, "status": self.google_workspace.status().to_dict(), "emails": [], "calendar_events": []}
        summary = self.google_workspace.summary(account)
        profile_email = str(summary.get("profile_email", "")).strip()
        if profile_email and account.login_hint != profile_email:
            updated = self.account_registry.update_login_hint(account.account_id, profile_email)
            if updated:
                account = updated
        summary["account"] = account.to_dict()
        return summary

    def merged_calendar_events(self, limit: int = 20) -> list[dict]:
        events: list[dict] = []
        google = self.google_workspace_summary()
        for entry in google.get("accounts", []):
            account = entry.get("account", {})
            label = account.get("owner_display_name") or account.get("label") or "Google Calendar"
            for item in entry.get("calendar_events", []):
                events.append(
                    {
                        **item,
                        "source": "google",
                        "source_label": label,
                    }
                )
        family = self.family_calendar_summary()
        family_label = family.get("calendar", {}).get("label", "Family Shared Calendar")
        for item in family.get("events", []):
            events.append(
                {
                    **item,
                    "source": family.get("calendar", {}).get("source", "family"),
                    "source_label": family_label,
                }
            )
        events.sort(key=lambda item: str(item.get("start", "")))
        return events[:limit]

    def merged_calendar_brief(self, limit: int = 5) -> str:
        events = self.merged_calendar_events(limit=limit)
        if not events:
            return "No upcoming calendar pressure in the next 30 days."
        return "; ".join(
            f"{item.get('summary', '(Untitled event)')} on {item.get('start', 'unknown time')}"
            for item in events[:limit]
        )

    def likely_meetings(self, limit: int = 6) -> list[dict]:
        candidates = []
        meeting_keywords = (
            "meeting",
            "call",
            "sync",
            "review",
            "brief",
            "agenda",
            "interview",
            "session",
            "consult",
            "prep",
            "strategy",
            "standup",
            "1:1",
            "check-in",
            "planning",
            "office hours",
            "discovery",
        )
        non_meeting_keywords = (
            "hair",
            "movie",
            "birthday",
            "anniversary",
            "senior sunday",
            "national day",
            "camp",
            "campout",
            "soccer",
            "baseball",
            "basketball",
            "observation",
            "dentist",
            "doctor",
            "appointment",
            "pickup",
            "dropoff",
            "drop-off",
            "travel",
            "flight",
            "church",
            "worship",
            "stag",
            "party",
            "dinner",
            "lunch",
            "breakfast",
            "graduation",
            "concert",
        )
        for item in self.merged_calendar_events(limit=30):
            summary = str(item.get("summary", ""))
            lowered = summary.lower()
            if item.get("all_day"):
                continue
            source = str(item.get("source", "")).lower()
            source_label = str(item.get("source_label", "")).lower()
            if any(token in lowered for token in non_meeting_keywords):
                continue
            has_meeting_signal = any(token in lowered for token in meeting_keywords)
            google_bias = source == "google" and not any(token in source_label for token in ("family", "cozi"))
            if not has_meeting_signal and not google_bias:
                continue
            candidates.append(item)
        return candidates[:limit]

    def catalyst_capture_signal(
        self,
        actor_name: str,
        source: str,
        title: str,
        content: str,
        *,
        sender: str = "",
        tags: list[str] | None = None,
    ) -> dict:
        actor = self.get_actor(actor_name)
        record = self.catalyst_support.capture_signal(
            actor.display_name,
            source,
            title,
            content,
            sender=sender,
            tags=tags,
        )
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("pipeline_review", "pipeline_state", "dashboard", "today_board", "cognitive", "cadence_review"))
        return record

    def catalyst_email_triage(self, actor_name: str, subject: str, body: str, sender: str) -> dict:
        actor = self.get_actor(actor_name)
        result = self.catalyst_support.email_triage(actor.display_name, subject, body, sender)
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("pipeline_review", "pipeline_state", "dashboard", "today_board", "cognitive", "cadence_review"))
        return result

    def catalyst_meeting_prep(
        self,
        actor_name: str,
        meeting_title: str,
        open_commitments: list[str],
        recent_signals: list[str],
    ) -> dict:
        actor = self.get_actor(actor_name)
        chosen_title = meeting_title.strip()
        signals = list(recent_signals)
        if not chosen_title:
            likely = self.likely_meetings(limit=1)
            if likely:
                item = likely[0]
                chosen_title = str(item.get("summary", "")).strip() or "Upcoming meeting"
                signals.append(
                    f"Detected from merged calendar: {chosen_title} · {item.get('start', 'No start time')} · {item.get('source_label', item.get('source', 'calendar'))}"
                )
        return self.catalyst_support.meeting_prep(actor.display_name, chosen_title or "Upcoming meeting", open_commitments, signals)

    def catalyst_meeting_extraction(self, actor_name: str, transcript: str, context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        result = self.catalyst_support.meeting_extraction(actor.display_name, transcript, context)
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("pipeline_review", "pipeline_state", "dashboard", "today_board", "cognitive", "cadence_review"))
        return result

    def catalyst_briefing(self, actor_name: str, user_context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        context = user_context.strip()
        calendar_context = self.merged_calendar_brief(limit=5)
        if calendar_context:
            context = f"{context}\nMerged calendar: {calendar_context}".strip()
        briefing = self.catalyst_support.briefing_generation(actor.display_name, context)
        briefing["strategic_brief"] = self.daily_strategic_brief(actor.display_name)
        briefing["systems_note"] = self.cross_domain_synthesis_brief(actor.display_name, "today's family, work, and calendar load")
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("pipeline_review", "pipeline_state", "dashboard", "today_board", "cognitive", "cadence_review"))
        return briefing

    def herald_workspace_snapshot(self) -> dict:
        overview = self.catalyst_overview()
        latest_runs = overview.get("latest_runs", {})
        return {
            "likely_meetings": self.likely_meetings(limit=8),
            "merged_calendar": self.merged_calendar_events(limit=12),
            "participant_suggestions": ["Chris", "Rebekah", "External Guest", "Client", "Advisor", "Partner"],
            "context_options": ["New Discussion", "Follow-up", "Decision Call", "Client Meet", "Trade", "Capital", "Healthcare", "Green Infra", "Technologies", "Labs"],
            "latest_meeting_prep": latest_runs.get("meeting_prep", {}),
            "latest_meeting_extraction": latest_runs.get("meeting_extraction", {}),
            "latest_briefing": latest_runs.get("briefing", {}),
        }

    def herald_prepare_meeting(
        self,
        actor_name: str,
        event_id: str = "",
        context: str = "",
        *,
        participants: list[str] | None = None,
        contexts: list[str] | None = None,
        objective: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        selected_event = None
        if event_id:
            for item in self.merged_calendar_events(limit=40):
                if str(item.get("id", "")) == event_id:
                    selected_event = item
                    break
        if not selected_event:
            likely = self.likely_meetings(limit=1)
            selected_event = likely[0] if likely else None
        meeting_title = str(selected_event.get("summary", "")).strip() if selected_event else ""
        signals: list[str] = []
        if selected_event:
            signals.append(
                f"Merged calendar signal: {meeting_title} · {selected_event.get('start', 'No start time')} · {selected_event.get('source_label', selected_event.get('source', 'calendar'))}"
            )
        clean_participants = [entry.strip() for entry in (participants or []) if entry.strip()]
        clean_contexts = [entry.strip() for entry in (contexts or []) if entry.strip()]
        if clean_participants:
            signals.append("Participants: " + ", ".join(clean_participants))
        if clean_contexts:
            signals.append("Context lanes: " + ", ".join(clean_contexts))
        if objective.strip():
            signals.append("Objective: " + objective.strip())
        if context.strip():
            signals.append(context.strip())
        result = self.catalyst_support.meeting_prep(actor.display_name, meeting_title or "Upcoming meeting", clean_contexts, signals)
        result["participants"] = clean_participants
        result["contexts"] = clean_contexts
        result["objective"] = objective.strip()
        return result

    def veronica_workspace_snapshot(self) -> dict:
        return self.content_ops.snapshot()

    def veronica_generate_options(
        self,
        actor_name: str,
        topic: str,
        *,
        channel: str = "YouTube",
        context: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        result = self.content_ops.generate_options(actor.display_name, topic, channel=channel, context=context)
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("marketing_review", "marketing_state", "dashboard", "today_board", "cognitive"))
        return result

    def veronica_approve_option(self, actor_name: str, option_id: str) -> dict:
        actor = self.get_actor(actor_name)
        result = self.content_ops.approve_option(actor.display_name, option_id)
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("marketing_review", "marketing_state", "dashboard", "today_board", "cognitive"))
        return result

    def veronica_push_live(self, queue_id: str) -> dict:
        record = self.content_ops.push_live(queue_id)
        if not record:
            return {"ok": False, "message": "Queue item not found."}
        actor_name = str(record.get("actor", "Chris")).strip() or "Chris"
        self._invalidate_snapshot_cache(actor_name, surfaces=("marketing_review", "marketing_state", "dashboard", "today_board", "cognitive"))
        return {"ok": True, "record": record}

    def veronica_export(self, queue_id: str) -> dict:
        try:
            record = self.content_ops.export_queue_item(queue_id)
        except ValueError as exc:
            return {"ok": False, "message": str(exc)}
        actor_name = str(record.get("actor", "Chris")).strip() or "Chris"
        self._invalidate_snapshot_cache(actor_name, surfaces=("marketing_review", "marketing_state", "dashboard", "today_board", "cognitive"))
        return {"ok": True, "record": record}

    def ultron_workspace_snapshot(self) -> dict:
        return {
            "status": self.status(),
            "privacy_state": self.privacy_state(),
            "security_incidents": self.list_security_incidents(limit=12),
            "anomalies": self.anomaly_watch(),
            "approvals": self.list_pending_approvals(),
            "openviking": self.openviking_status(),
            "brain_graph": self.brain_graph_snapshot(),
        }

    def nick_fury_workspace_snapshot(self, actor_name: str = "Chris") -> dict:
        actor = self.get_actor(actor_name)
        return {
            "actor": actor.display_name,
            "brief": self.daily_strategic_brief(actor.display_name),
            "systems_note": self.cross_domain_synthesis_brief(actor.display_name, "whole operating picture"),
            "calendar": self.merged_calendar_events(limit=8),
            "approvals": self.list_pending_approvals()[:8],
            "wealth_summary": self.wealth_support.summary(limit=6),
            "recent_activity": self.recent_activity(limit=8),
            "active_mode": self.active_mode(),
        }

    def daily_strategic_brief(self, actor_name: str) -> str:
        actor = self.get_actor(actor_name)
        approvals = self.list_pending_approvals()
        prompt = (
            f"You are Nick Fury, Strategic Briefing Director inside Chris's JARVIS mesh. "
            "Return 3 concise sentences: what matters now, what can wait, and the clean next move."
        )
        context = json.dumps(
            {
                "actor": actor.display_name,
                "active_mode": self.active_mode(),
                "calendar": self.merged_calendar_events(limit=6),
                "pending_approvals": approvals[:6],
                "recent_activity": self.recent_activity(limit=6),
                "wealth_summary": self.wealth_support.summary(limit=6),
            },
            indent=2,
        )
        return self.openai_client.prompt_text(prompt, context, max_output_tokens=220).strip()

    def cross_domain_synthesis_brief(self, actor_name: str, topic: str = "") -> str:
        actor = self.get_actor(actor_name)
        prompt = (
            f"You are Vision, Systems Integrator inside Chris's JARVIS mesh. "
            "Return 2-3 concise sentences describing the most important cross-domain interaction or second-order effect."
        )
        context = json.dumps(
            {
                "actor": actor.display_name,
                "topic": topic or "current operating picture",
                "calendar": self.merged_calendar_events(limit=6),
                "active_mode": self.active_mode(),
                "family_focus": self.snapshot.family_focus,
                "recent_activity": self.recent_activity(limit=6),
            },
            indent=2,
        )
        return self.openai_client.prompt_text(prompt, context, max_output_tokens=180).strip()

    def catalyst_draft(
        self,
        actor_name: str,
        intent: str,
        context: str,
        recipient: str,
        tone: str = "professional",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.draft_composition(actor.display_name, intent, context, recipient, tone)

    def catalyst_project_brief(
        self,
        actor_name: str,
        project_name: str,
        problem: str,
        desired_outcome: str,
        constraints: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        result = self.catalyst_support.project_brief(actor.display_name, project_name, problem, desired_outcome, constraints)
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("pipeline_review", "pipeline_state", "dashboard", "today_board", "cognitive", "cadence_review"))
        return result

    def catalyst_implementation_plan(
        self,
        actor_name: str,
        project_name: str,
        brief: str,
        constraints: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        result = self.catalyst_support.implementation_plan(actor.display_name, project_name, brief, constraints)
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("pipeline_review", "pipeline_state", "dashboard", "today_board", "cognitive", "cadence_review"))
        return result

    def catalyst_proactive_surfacing(self, actor_name: str, horizon: str = "today", context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        result = self.catalyst_support.proactive_surfacing(actor.display_name, horizon, context)
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("pipeline_review", "pipeline_state", "dashboard", "today_board", "cognitive", "cadence_review"))
        return result

    def _design_review_path(self) -> Path:
        root = Path("data") / "design-review"
        root.mkdir(parents=True, exist_ok=True)
        return root / "holo-review.json"

    def design_review_state(self) -> dict:
        path = self._design_review_path()
        if not path.exists():
            return {
                "active_page": "shell",
                "page_settings": {"shell": {"enabled": True}},
                "pages": {"shell": {"removed": [], "notes": {}, "overrides": {}}},
            }
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "active_page": "shell",
                "page_settings": {"shell": {"enabled": True}},
                "pages": {"shell": {"removed": [], "notes": {}, "overrides": {}}},
            }
        if "pages" in raw:
            return {
                "active_page": str(raw.get("active_page", "shell") or "shell"),
                "page_settings": dict(raw.get("page_settings", {"shell": {"enabled": True}})),
                "pages": dict(raw.get("pages", {})),
            }
        return {
            "active_page": "shell",
            "page_settings": {"shell": {"enabled": True}},
            "pages": {
                "shell": {
                    "removed": list(raw.get("removed", [])),
                    "notes": dict(raw.get("notes", {})),
                    "overrides": dict(raw.get("overrides", {})),
                }
            },
        }

    def save_design_review_state(self, payload: dict) -> dict:
        if "pages" in payload:
            state = {
                "active_page": str(payload.get("active_page", "shell") or "shell"),
                "page_settings": dict(payload.get("page_settings", {"shell": {"enabled": True}})),
                "pages": dict(payload.get("pages", {})),
            }
        else:
            state = {
                "active_page": "shell",
                "page_settings": {"shell": {"enabled": True}},
                "pages": {
                    "shell": {
                        "removed": list(payload.get("removed", [])),
                        "notes": dict(payload.get("notes", {})),
                        "overrides": dict(payload.get("overrides", {})),
                    }
                },
            }
        path = self._design_review_path()
        path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "message": "Design review state saved.", "state": state, "path": str(path)}

    def dashboard_snapshot(self, actor_name: str = "Chris") -> dict:
        def builder() -> dict:
            actor = self.get_actor(actor_name)
            active_mode = self.family_support.active_mode()
            adult_names = [profile.display_name for profile in self.household.users.values() if profile.permissions == "adult"]
            parent_viewer = "Rebekah" if "Rebekah" in adult_names else (adult_names[0] if adult_names else "Chris")
            recent_activity = self.recent_activity(limit=20)
            integration_status = self.status()
            background_cycle = self.background_cycle(
                active_mode=active_mode.mode,
                recent_activity=recent_activity,
                integration_status=integration_status,
            )
            background_agents = background_cycle["scheduler"]
            memory_curator = background_cycle["memory_curator"]
            open_loops = self.unified_open_loops(actor.display_name, limit=18)
            cognitive = self.cognitive_snapshot(actor.display_name, include_graph=False, open_loops=open_loops)
            today_board = self.today_board(actor.display_name, open_loops=open_loops, cognition=cognitive)
            cadence_review = self.cadence_review(actor.display_name, open_loops=open_loops, cognition=cognitive)
            growth_state = cognitive.get("growth_state") or self.growth_state_snapshot(actor.display_name)

            def card_payload(card) -> dict:
                return {
                    "title": card.title,
                    "status": card.status,
                    "summary": card.summary,
                    "details": list(card.details),
                }

            def event_payload(event) -> dict:
                return {
                    "time": event.time,
                    "owner": event.owner,
                    "title": event.title,
                    "note": event.note,
                }

            payload = {
                "day_label": self.snapshot.day_label,
                "location": self.household.location_label,
                "weather": self.snapshot.weather,
                "house_note": self.snapshot.house_note,
                "truth": {
                    "weather_live": False,
                    "mission_live": False,
                    "home_live": self.home_overview().get("mode") == "live",
                    "watch_live": self.cold_storage_monitor().get("mode") == "live",
                },
                "active_mode": {
                    "mode": active_mode.mode,
                    "status": active_mode.status,
                    "reason": active_mode.reason,
                    "actor": active_mode.actor,
                    "timestamp": active_mode.timestamp,
                },
                "cards": {
                    "body": card_payload(self.snapshot.body),
                    "home": card_payload(self.snapshot.home),
                    "mission": card_payload(self.snapshot.mission),
                },
                "body_home_mission": [
                    card_payload(self.snapshot.body),
                    card_payload(self.snapshot.home),
                    card_payload(self.snapshot.mission),
                ],
                "events": [event_payload(event) for event in self.snapshot.events],
                "family_focus": self.snapshot.family_focus,
                "merged_calendar": self.merged_calendar_events(limit=12),
                "watch_items": self.snapshot.watch_items,
                "mode_brief": self.family_mode_brief(active_mode.mode),
                "departure_checklist": self.family_support.departure_checklist(),
                "departure_runs": self.list_departure_runs(limit=5),
                "message_drafts": self.family_support.list_drafts(limit=5),
                "anomalies": self.family_support.anomaly_watch(
                    self.snapshot.home.details,
                    self.snapshot.watch_items,
                ),
                "meal_plans": self.list_meal_plans(limit=5),
                "vehicle_plans": self.list_vehicle_plans(limit=5),
                "weather_plans": self.list_weather_plans(limit=5),
                "child_boundaries": self.child_boundaries(),
                "tutoring_summaries": self.tutoring_summaries(parent_viewer, limit=6),
                "printer_status": self.printer_status(),
                "workshop_inspections": self.list_workshop_inspections(limit=5),
                "vendor_preps": self.list_vendor_preps(limit=5),
                "cad_packages": self.list_cad_packages(limit=5),
                "print_preps": self.list_print_preps(limit=5),
                "material_recommendations": self.list_material_recommendations(limit=5),
                "safety_checks": self.list_safety_checks(limit=5),
                "inventory_summary": self.inventory_summary(),
                "voice_note_tasks": self.list_voice_note_tasks(limit=5),
                "open_loops": open_loops,
                "today_board": today_board,
                "cadence_review": cadence_review,
                "cognitive": cognitive,
                "growth_state": growth_state,
                "assistant_surface": {
                    "signal_chips": list(open_loops.get("surface_chips", [])),
                    "briefing_lines": list(open_loops.get("briefing_lines", [])),
                    "auto_open_packet": str(open_loops.get("auto_open_packet", "")),
                    "surface_key": str(open_loops.get("surface_key", "")),
                    "top_item": open_loops.get("top_item"),
                },
                "assistant_notifications": self.assistant_notifications(actor.display_name, limit=6),
                "home_overview": self.home_overview(),
                "environment_status": self.environment_status_snapshot(actor.display_name),
                "home_actions": self.list_home_actions(limit=8),
                "climate_status": self.climate_status(),
                "access_overview": self.access_overview(),
                "garage_status": self.garage_status(),
                "leak_monitor": self.leak_monitor(),
                "cold_storage_monitor": self.cold_storage_monitor(),
                "outage_readiness": self.outage_readiness(),
                "perception_overview": self.perception_overview(),
                "memory_overview": self.memory_overview(actor.display_name),
                "catalyst_overview": self.catalyst_overview(),
                "google_workspace": self.google_workspace_summary(),
                "family_calendar": self.family_calendar_summary(),
                "chronicle_timeline": self.chronicle_timeline(limit=5),
                "chronicle_theme_summary": self.chronicle_theme_summary(limit=20),
                "device_boundaries": self.list_device_boundaries(limit=6),
                "security_incidents": self.list_security_incidents(limit=8),
                "weather_advisories": self.list_weather_advisories(limit=5),
                "arrival_events": self.list_arrival_events(limit=5),
                "unlock_assessments": self.list_unlock_assessments(limit=5),
                "overnight_review": self.overnight_review(),
                "explainability": self.explainability_snapshot(),
                "brain_graph": self.brain_graph_snapshot(),
                "background_agents": background_agents,
                "background_cycle": background_cycle,
                "agent_registry": self.agent_registry_snapshot(),
                "memory_curator": memory_curator,
            }
            degraded_inputs = []
            if self._is_degraded_payload(today_board):
                degraded_inputs.append("Today Board")
            if self._is_degraded_payload(cadence_review):
                degraded_inputs.append("Cadence Review")
            if self._is_degraded_payload(cognitive):
                degraded_inputs.append("Cognitive snapshot")
            if degraded_inputs:
                payload["degraded"] = {
                    "active": True,
                    "reason": f"{', '.join(degraded_inputs)} fell back to a last good snapshot.",
                    "detail": "The shell is still usable, but one or more cognitive surfaces are stale.",
                    "source": "nested-surface-fallback",
                }
            return payload

        return self._cached_surface("dashboard", actor_name, builder)

    def home_overview(self) -> dict:
        return self.home_support.home_overview()

    def list_home_actions(self, limit: int = 20) -> list[dict]:
        return self.home_support.store.list_actions(limit=limit)

    def room_scene(self, actor_name: str, room: str, scene_name: str, intent: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.home_support.room_scene(actor.display_name, room, scene_name, intent=intent)

    def climate_status(self) -> list[dict]:
        return self.home_support.climate_status()

    def climate_control(
        self,
        actor_name: str,
        zone: str,
        hvac_mode: str,
        target_temperature: float | None = None,
        context: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.home_support.climate_control(
            actor.display_name,
            zone,
            hvac_mode,
            target_temperature=target_temperature,
            context=context,
        )

    def access_overview(self) -> dict:
        return self.home_support.access_overview()

    def access_control(self, actor_name: str, target: str, desired_state: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.home_support.access_control(actor.display_name, target, desired_state)

    def garage_status(self) -> list[dict]:
        return self.home_support.garage_status()

    def garage_safe_close(self, actor_name: str, target: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.home_support.garage_safe_close(actor.display_name, target)

    def leak_monitor(self) -> dict:
        return self.home_support.leak_monitor()

    def cold_storage_monitor(self) -> dict:
        return self.home_support.cold_storage_monitor()

    def energy_window(self, appliance: str, request_text: str = "") -> dict:
        return self.home_support.energy_window(appliance, request_text=request_text)

    def outage_readiness(self) -> dict:
        return self.home_support.outage_readiness()

    def perception_overview(self) -> dict:
        return self.perception_support.perception_overview()

    def _vision_capture_root(self) -> Path:
        root = Path("data") / "vision" / "captures"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _save_vision_capture_image(self, image_data_url: str) -> tuple[str, Path]:
        if not image_data_url.strip():
            raise ValueError("image_data_url is required")
        header, _, encoded = image_data_url.partition(",")
        if not encoded:
            raise ValueError("Invalid image payload.")
        _ = header
        capture_id = str(uuid.uuid4())
        image_path = self._vision_capture_root() / f"{capture_id}.jpg"
        image_bytes = base64.b64decode(encoded)
        image_path.write_bytes(image_bytes)
        return capture_id, image_path

    def _vision_capture_metadata_path(self, capture_id: str) -> Path:
        return self._vision_capture_root() / f"{capture_id}.json"

    def _save_vision_capture_metadata(self, capture_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        metadata_path = self._vision_capture_metadata_path(capture_id)
        metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def _recent_vision_captures(self, actor_name: str = "", *, limit: int = 8) -> list[dict[str, Any]]:
        actor_key = str(actor_name).strip().lower()
        records: list[dict[str, Any]] = []
        for metadata_path in sorted(self._vision_capture_root().glob("*.json"), reverse=True):
            try:
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if actor_key and str(payload.get("actor", "")).strip().lower() != actor_key:
                continue
            records.append(payload)
            if len(records) >= limit:
                break
        return records

    def save_vision_calibration(self, actor_name: str, camera_label: str, calibration: dict[str, Any]) -> dict:
        actor = self.get_actor(actor_name)
        result = self.perception_support.save_vision_calibration(actor.display_name, camera_label, calibration)
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("vision_state", "dashboard", "today_board", "cognitive", "world_state", "world_graph"))
        return {
            "ok": True,
            "calibration": result,
        }

    def vision_state_snapshot(self, actor_name: str = "Chris") -> dict:
        def builder() -> dict:
            actor = self.get_actor(actor_name)
            perception = self.perception_support.perception_overview()
            calibration = self.perception_support.latest_vision_calibration(actor.display_name) or {}
            observations = [
                item
                for item in list(perception.get("visual_observations") or [])
                if str(item.get("actor", "")).strip().lower() == actor.display_name.lower()
            ]
            captures = self._recent_vision_captures(actor.display_name, limit=8)
            observed_capture_ids = {
                str(item.get("capture_id", "")).strip()
                for item in observations
                if str(item.get("capture_id", "")).strip()
            }
            for capture in captures:
                capture_id = str(capture.get("capture_id", "")).strip()
                if capture_id and capture_id in observed_capture_ids:
                    continue
                analysis = str(capture.get("analysis", "")).strip()
                observations.append(
                    {
                        "observation_id": f"capture-{capture_id or uuid.uuid4()}",
                        "actor": actor.display_name,
                        "camera_label": str(capture.get("camera_label", "")).strip(),
                        "camera_id": "",
                        "zone": "unknown",
                        "mode": str(capture.get("mode", "describe")).strip() or "describe",
                        "observation_type": "capture-backfill",
                        "summary": analysis.splitlines()[0].strip() if analysis else "Saved vision capture.",
                        "detail": analysis,
                        "confidence": "low",
                        "capture_id": capture_id,
                        "image_path": str(capture.get("image_path", "")).strip(),
                        "observed_object": "",
                        "measurement": dict(capture.get("measurement") or {}),
                        "evidence": {"source": "capture-backfill"},
                        "timestamp": str(capture.get("created_at", "")).strip(),
                    }
                )
            observations.sort(
                key=lambda item: self._parse_timestamp(str(item.get("timestamp", ""))) or datetime.fromtimestamp(0, timezone.utc),
                reverse=True,
            )
            evidence_items: list[dict[str, Any]] = []
            for item in observations[:8]:
                evidence_items.append(
                    {
                        "type": "observation",
                        "timestamp": str(item.get("timestamp", "")).strip(),
                        "summary": str(item.get("summary", "")).strip(),
                        "detail": str(item.get("detail", "")).strip(),
                        "mode": str(item.get("mode", "")).strip(),
                        "confidence": str(item.get("confidence", "medium")).strip() or "medium",
                        "capture_id": str(item.get("capture_id", "")).strip(),
                        "camera_label": str(item.get("camera_label", "")).strip(),
                        "zone": str(item.get("zone", "")).strip(),
                    }
                )
            score = 0
            if calibration:
                score += 3
            if observations:
                score += 3
            if captures:
                score += 2
            return {
                "actor": actor.display_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "calibration": calibration,
                "recent_observations": observations[:8],
                "recent_captures": captures[:8],
                "evidence_items": evidence_items[:8],
                "summary": {
                    "observation_count": len(observations),
                    "capture_count": len(captures),
                    "has_calibration": bool(calibration),
                    "confidence": self._confidence_label(score),
                },
            }

        return self._cached_surface("vision_state", actor_name, builder)

    def _host_battery_snapshot(self) -> dict[str, Any]:
        raw = self._run_local_probe(["pmset", "-g", "batt"], timeout=3)
        if not raw:
            return {
                "available": False,
                "state": "unknown",
                "percent": None,
                "power_source": "unknown",
                "detail": "Battery telemetry unavailable on this host.",
            }
        percent = None
        state = "unknown"
        power_source = "unknown"
        detail = raw.splitlines()[-1].strip() if raw.splitlines() else raw
        first_line = raw.splitlines()[0].strip().lower() if raw.splitlines() else ""
        if "ac power" in first_line:
            power_source = "ac"
        elif "battery power" in first_line:
            power_source = "battery"
        import re
        match = re.search(r"(\d+)%", raw)
        if match:
            percent = int(match.group(1))
        lowered = raw.lower()
        if "charging" in lowered:
            state = "charging"
        elif "discharging" in lowered:
            state = "discharging"
        elif "charged" in lowered:
            state = "charged"
        return {
            "available": True,
            "state": state,
            "percent": percent,
            "power_source": power_source,
            "detail": detail,
        }

    def _host_network_snapshot(self) -> dict[str, Any]:
        route_raw = self._run_local_probe(["route", "-n", "get", "default"], timeout=3)
        scutil_raw = self._run_local_probe(["scutil", "--nwi"], timeout=3)
        interface = ""
        gateway = ""
        for line in route_raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("interface:"):
                interface = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("gateway:"):
                gateway = stripped.split(":", 1)[1].strip()
        reachable = "reachable" if scutil_raw else "unknown"
        if "network information" in scutil_raw.lower() or "network interfaces" in scutil_raw.lower():
            reachable = "up"
        return {
            "available": bool(route_raw or scutil_raw),
            "interface": interface or "unknown",
            "gateway": gateway or "unknown",
            "reachability": reachable,
            "detail": (route_raw.splitlines()[0].strip() if route_raw.splitlines() else "") or "Network probe unavailable.",
        }

    def _host_system_snapshot(self) -> dict[str, Any]:
        uptime_raw = self._run_local_probe(["uptime"], timeout=3)
        disk_raw = self._run_local_probe(["df", "-h", "/"], timeout=3)
        disk_line = disk_raw.splitlines()[-1].strip() if len(disk_raw.splitlines()) >= 2 else ""
        return {
            "available": bool(uptime_raw or disk_line),
            "uptime": uptime_raw,
            "disk_root": disk_line,
            "runtime_role": self.service_role,
            "runtime_pid": self.process_id,
            "runtime_started_at": self.process_started_at,
        }

    def _device_environment_summary(self) -> dict[str, Any]:
        devices = self.connected_devices_snapshot()
        fresh = 0
        today = 0
        stale = 0
        aged = 0
        for item in devices.get("devices", []):
            bucket = self._age_bucket(str(item.get("last_seen_at", "")))
            if bucket == "fresh":
                fresh += 1
            elif bucket == "today":
                today += 1
            elif bucket == "stale":
                stale += 1
            elif bucket == "aged":
                aged += 1
        return {
            "summary": dict(devices.get("summary") or {}),
            "fresh": fresh,
            "today": today,
            "stale": stale,
            "aged": aged,
            "always_available": len([item for item in devices.get("devices", []) if bool(item.get("always_available"))]),
            "recent_devices": [
                {
                    "device_id": str(item.get("device_id", "")).strip(),
                    "label": str(item.get("label", "")).strip(),
                    "room": str(item.get("room", "")).strip(),
                    "age_bucket": self._age_bucket(str(item.get("last_seen_at", ""))),
                    "owner_confidence": dict(item.get("owner_confidence") or {}),
                }
                for item in list(devices.get("devices", []))[:6]
            ],
        }

    def _environment_escalation_snapshot(self) -> dict[str, Any]:
        perception = self.perception_overview()
        anomalies = list(perception.get("anomalies") or [])
        leak = self.leak_monitor()
        cold_storage = self.cold_storage_monitor()
        now = datetime.now(timezone.utc)
        signatures: dict[str, dict[str, Any]] = {}
        suppressed_repeats = 0

        def severity_weight(value: str) -> int:
            return {
                "critical": 4,
                "elevated": 3,
                "alert": 3,
                "watch": 2,
                "warning": 2,
                "stable": 1,
                "clear": 0,
            }.get(str(value or "").strip().lower(), 1)

        def consider(record: dict[str, Any], *, source_type: str) -> None:
            nonlocal suppressed_repeats
            signature = str(record.get("signature", "")).strip() or (
                f"{source_type}:{str(record.get('category', '')).strip().lower()}:{str(record.get('source', '')).strip().lower()}:{str(record.get('name', '')).strip().lower()}"
            )
            timestamp = self._parse_timestamp(str(record.get("timestamp", "")).strip()) or now
            existing = signatures.get(signature)
            if existing is None:
                signatures[signature] = {**record, "source_type": source_type, "signature": signature, "timestamp": timestamp.isoformat(), "repeat_count": 1}
                return
            suppressed_repeats += 1
            existing["repeat_count"] = int(existing.get("repeat_count", 1) or 1) + 1
            existing_time = self._parse_timestamp(str(existing.get("timestamp", "")).strip()) or now
            if severity_weight(str(record.get("severity", ""))) > severity_weight(str(existing.get("severity", ""))) or timestamp > existing_time:
                signatures[signature] = {**record, "source_type": source_type, "signature": signature, "timestamp": timestamp.isoformat(), "repeat_count": existing["repeat_count"]}

        for item in anomalies:
            consider(
                {
                    "title": str(item.get("source", "Anomaly")).strip() or "Anomaly",
                    "summary": str(item.get("recommendation", "")).strip() or str(item.get("detail", "")).strip() or "Environmental anomaly detected.",
                    "category": str(item.get("category", "environment")).strip() or "environment",
                    "source": str(item.get("source", "")).strip(),
                    "severity": str(item.get("severity", "watch")).strip() or "watch",
                    "timestamp": str(item.get("timestamp", "")).strip(),
                },
                source_type="perception",
            )
        for item in list(leak.get("active_sensors") or []):
            consider(
                {
                    "title": str(item.get("name", "Leak sensor")).strip(),
                    "summary": "Active leak sensor needs immediate confirmation.",
                    "category": "leak",
                    "source": str(item.get("entityId", "")).strip(),
                    "severity": "critical",
                    "timestamp": now.isoformat(),
                },
                source_type="home",
            )
        for item in list(cold_storage.get("active_sensors") or []):
            consider(
                {
                    "title": str(item.get("name", "Cold storage")).strip(),
                    "summary": str(item.get("recommended_action", "")).strip() or "Cold-storage variance needs review.",
                    "category": "cold-storage",
                    "source": str(item.get("entityId", "")).strip(),
                    "severity": str(item.get("severity", "watch")).strip() or "watch",
                    "timestamp": str(item.get("last_checked", "")).strip() or now.isoformat(),
                },
                source_type="home",
            )

        escalation_candidates = []
        cooldown_minutes = 45
        for item in signatures.values():
            severity = str(item.get("severity", "watch")).strip().lower()
            timestamp = self._parse_timestamp(str(item.get("timestamp", "")).strip()) or now
            age_minutes = max(0, int((now - timestamp.astimezone(timezone.utc)).total_seconds() // 60))
            if severity not in {"critical", "elevated", "alert", "warning", "watch"}:
                continue
            cooldown_active = age_minutes < cooldown_minutes and int(item.get("repeat_count", 1) or 1) > 1
            escalation_candidates.append(
                {
                    "title": str(item.get("title", "Environment signal")).strip() or "Environment signal",
                    "summary": str(item.get("summary", "")).strip(),
                    "category": str(item.get("category", "environment")).strip() or "environment",
                    "source": str(item.get("source", "")).strip(),
                    "severity": severity,
                    "timestamp": timestamp.isoformat(),
                    "age_minutes": age_minutes,
                    "repeat_count": int(item.get("repeat_count", 1) or 1),
                    "cooldown_active": cooldown_active,
                    "should_escalate": not cooldown_active and severity in {"critical", "elevated", "alert"},
                }
            )
        escalation_candidates.sort(key=lambda item: (severity_weight(str(item.get("severity", ""))), -int(item.get("age_minutes", 0) or 0)), reverse=True)
        return {
            "cooldown_minutes": cooldown_minutes,
            "suppressed_repeats": suppressed_repeats,
            "escalation_candidates": escalation_candidates[:8],
        }

    def environment_status_snapshot(self, actor_name: str = "Chris") -> dict:
        def builder() -> dict:
            actor = self.get_actor(actor_name)
            home = self.home_overview()
            leak = self.leak_monitor()
            cold = self.cold_storage_monitor()
            outage = self.outage_readiness()
            perception = self.perception_overview()
            climate = self.climate_status()
            garage = self.garage_status()
            devices = self._device_environment_summary()
            battery = self._host_battery_snapshot()
            network = self._host_network_snapshot()
            system = self._host_system_snapshot()
            runtime_service = self.runtime_service_status()
            escalation = self._environment_escalation_snapshot()
            adapters = [
                {
                    "id": "home-assistant",
                    "label": "Home Assistant",
                    "available": bool(home.get("mode") == "live"),
                    "mode": str(home.get("mode", "profile-backed")),
                    "detail": "Physical home entities and automations." if home.get("mode") == "live" else "Using staged home profile.",
                },
                {
                    "id": "device-registry",
                    "label": "Connected Devices",
                    "available": True,
                    "mode": "registry-backed",
                    "detail": f"{int((devices.get('summary') or {}).get('total', 0) or 0)} known device session(s).",
                },
                {
                    "id": "perception",
                    "label": "Perception",
                    "available": True,
                    "mode": "event-backed",
                    "detail": f"{len(list(perception.get('anomalies') or []))} recent anomaly event(s).",
                },
                {
                    "id": "runtime",
                    "label": "Runtime Service",
                    "available": True,
                    "mode": "live",
                    "detail": str(((runtime_service.get("service_runtime") or {}).get("role", "runtime"))),
                },
            ]
            alert_count = len([item for item in escalation.get("escalation_candidates", []) if bool(item.get("should_escalate"))])
            watch_count = len([item for item in escalation.get("escalation_candidates", []) if str(item.get("severity", "")).strip().lower() in {"watch", "warning"}])
            live_adapter_count = len([item for item in adapters if bool(item.get("available")) and str(item.get("mode", "")).strip().lower() == "live"])
            overall_status = "steady"
            if alert_count or leak.get("status") == "alert" or cold.get("status") == "alert":
                overall_status = "alert"
            elif watch_count or cold.get("status") == "watch":
                overall_status = "watch"
            summary_lines = [
                f"Environment is {overall_status}.",
                f"Host battery is {battery.get('state', 'unknown')} at {battery.get('percent', '--')}%.",
                f"Network reachability is {network.get('reachability', 'unknown')} via {network.get('interface', 'unknown')}.",
                f"{int((devices.get('summary') or {}).get('total', 0) or 0)} device session(s) are known, with {int(devices.get('fresh', 0) or 0)} fresh.",
                f"Suppressed {int(escalation.get('suppressed_repeats', 0) or 0)} repeated anomaly signal(s) inside the cooldown window.",
            ]
            return {
                "actor": actor.display_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": overall_status,
                "summary": summary_lines,
                "status_summary": {
                    "status": overall_status,
                    "active_alert_count": alert_count,
                    "watch_count": watch_count,
                    "live_adapter_count": live_adapter_count,
                    "known_device_sessions": int((devices.get("summary") or {}).get("total", 0) or 0),
                    "fresh_device_sessions": int(devices.get("fresh", 0) or 0),
                },
                "adapters": adapters,
                "host_signals": {
                    "battery": battery,
                    "network": network,
                    "system": system,
                },
                "device_status": devices,
                "physical_systems": {
                    "home": home,
                    "climate": climate,
                    "garage": garage,
                    "leak": leak,
                    "cold_storage": cold,
                    "outage": outage,
                },
                "recent_anomalies": list(perception.get("anomalies") or [])[:8],
                "anomaly_escalation": escalation,
            }

        return self._cached_surface("environment_status", actor_name, builder)

    def microphone_ingress(
        self,
        microphone: str,
        transcript: str,
        wake_word_detected: bool = False,
        actor_hint: str = "",
    ) -> dict:
        return self.perception_support.far_field_microphone_ingress(
            microphone,
            transcript,
            wake_word_detected=wake_word_detected,
            actor_hint=actor_hint,
        )

    def presence_update(self, sensor: str, room: str, occupied: bool, detail: str = "") -> dict:
        result = self.perception_support.presence_sensor_update(sensor, room, occupied, detail=detail)
        self._invalidate_snapshot_cache(
            surfaces=("dashboard", "today_board", "cadence_review", "cognitive", "world_state", "world_graph")
        )
        return result

    def phone_presence_update(
        self,
        actor_name: str,
        device: str,
        state: str,
        zone: str = "",
        detail: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        result = self.perception_support.phone_presence_update(
            actor.display_name,
            device,
            state,
            zone=zone,
            detail=detail,
        )
        self._invalidate_snapshot_cache(
            actor.display_name,
            surfaces=("dashboard", "today_board", "cadence_review", "cognitive", "world_state", "world_graph"),
        )
        return result

    def camera_event(
        self,
        camera: str,
        event_type: str,
        detail: str,
        detected_object: str = "",
        confidence: str = "medium",
    ) -> dict:
        result = self.perception_support.camera_event(
            camera,
            event_type,
            detail,
            detected_object=detected_object,
            confidence=confidence,
        )
        self._invalidate_snapshot_cache(surfaces=("vision_state", "dashboard", "today_board", "cognitive", "world_state", "world_graph"))
        return result

    def analyze_camera_frame(
        self,
        actor_name: str,
        prompt: str,
        image_data_url: str,
        camera_label: str = "Desk Camera",
        mode: str = "describe",
        compare_to_capture_id: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        requested_mode = (mode or "describe").strip().lower()
        detail_prompt = prompt.strip() or "Describe what is visible and call out the most important objects or activity."
        capture_id, image_path = self._save_vision_capture_image(image_data_url)

        compare_payload: dict | None = None
        image_inputs = [image_data_url]
        if requested_mode == "compare" and not compare_to_capture_id.strip():
            raise ValueError("Compare mode needs a previous frame. Capture one frame first.")
        if compare_to_capture_id.strip():
            prior_metadata = self._vision_capture_metadata_path(compare_to_capture_id.strip())
            if prior_metadata.exists():
                compare_payload = json.loads(prior_metadata.read_text(encoding="utf-8"))
                prior_image_path = Path(str(compare_payload.get("image_path", "")))
                if prior_image_path.exists():
                    prior_bytes = prior_image_path.read_bytes()
                    prior_data_url = "data:image/jpeg;base64," + base64.b64encode(prior_bytes).decode("ascii")
                    image_inputs.append(prior_data_url)
        if requested_mode == "compare" and len(image_inputs) < 2:
            raise ValueError("The previous frame could not be found for comparison. Capture a new baseline first.")

        mode_instruction = {
            "describe": "Describe the visible scene clearly and practically.",
            "text": "Focus on reading visible text exactly where possible. If text is unclear, say so instead of guessing.",
            "compare": "Compare the current image to the earlier reference image and call out meaningful differences.",
        }.get(requested_mode, "Describe the visible scene clearly and practically.")

        analysis_prompt = (
            f"You are JARVIS analyzing a user-invoked camera snapshot from {camera_label}. "
            "Do not claim continuous monitoring. "
            "Answer only from the provided captured frame or frames. "
            "Be concrete, practical, and brief. "
            f"{mode_instruction} "
            f"User request: {detail_prompt}"
        )
        if requested_mode == "compare" and len(image_inputs) > 1:
            analysis_prompt += " The first image is the current capture. The second image is the previous capture for comparison."
        analysis = self.openai_client.analyze_images(analysis_prompt, image_inputs)
        payload = {
            "capture_id": capture_id,
            "actor": actor.display_name,
            "camera_label": camera_label,
            "prompt": detail_prompt,
            "mode": requested_mode,
            "compare_to_capture_id": compare_to_capture_id.strip() or None,
            "image_path": str(image_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis,
        }
        if compare_payload:
            payload["compare_reference"] = {
                "capture_id": compare_payload.get("capture_id"),
                "created_at": compare_payload.get("created_at"),
                "camera_label": compare_payload.get("camera_label"),
            }
        self._save_vision_capture_metadata(capture_id, payload)
        camera_context = self.perception_support.camera_profile(camera_label)
        self.perception_support.record_visual_observation(
            actor.display_name,
            camera_label,
            requested_mode,
            analysis.splitlines()[0].strip() if analysis.strip() else "Visual analysis captured.",
            detail=analysis,
            confidence="medium",
            capture_id=capture_id,
            image_path=str(image_path),
            observation_type="analysis",
            zone=str(camera_context.get("zone", "unknown")).strip() or "unknown",
            evidence={
                "prompt": detail_prompt,
                "compare_to_capture_id": compare_to_capture_id.strip() or "",
            },
        )
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("vision_state", "dashboard", "today_board", "cognitive", "world_state", "world_graph"))
        return payload

    def measure_camera_frame(
        self,
        actor_name: str,
        image_data_url: str,
        camera_label: str,
        calibration: dict[str, Any],
        measurement: dict[str, Any],
        *,
        object_label: str = "",
        detail: str = "",
        selection: dict[str, Any] | None = None,
    ) -> dict:
        actor = self.get_actor(actor_name)
        capture_id, image_path = self._save_vision_capture_image(image_data_url)
        calibration_record = self.perception_support.save_vision_calibration(actor.display_name, camera_label, calibration)
        measurement_payload = dict(measurement or {})
        selection_payload = dict(selection or {})
        unit = str(measurement_payload.get("unit", calibration_record.get("unit", "cm"))).strip() or "cm"
        summary_bits = []
        if object_label.strip():
            summary_bits.append(object_label.strip())
        width = measurement_payload.get("width")
        height = measurement_payload.get("height")
        if width is not None and height is not None:
            try:
                summary_bits.append(f"{float(width):.2f} x {float(height):.2f} {unit}")
            except (TypeError, ValueError):
                pass
        summary = "Measured visual span"
        if summary_bits:
            summary = "Measured " + " - ".join(summary_bits)
        payload = {
            "capture_id": capture_id,
            "actor": actor.display_name,
            "camera_label": camera_label,
            "mode": "measure",
            "image_path": str(image_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "measurement": measurement_payload,
            "calibration": calibration_record,
            "selection": selection_payload,
            "detail": detail,
        }
        self._save_vision_capture_metadata(capture_id, payload)
        camera_context = self.perception_support.camera_profile(camera_label)
        observation = self.perception_support.record_visual_observation(
            actor.display_name,
            camera_label,
            "measure",
            summary,
            detail=detail or summary,
            confidence="medium" if calibration_record.get("pixels_per_unit") else "low",
            capture_id=capture_id,
            image_path=str(image_path),
            observation_type="measurement",
            zone=str(camera_context.get("zone", "unknown")).strip() or "unknown",
            observed_object=object_label,
            measurement=measurement_payload,
            evidence={
                "selection": selection_payload,
                "calibration_reference": {
                    "reference_length": calibration_record.get("reference_length"),
                    "reference_pixels": calibration_record.get("reference_pixels"),
                    "unit": calibration_record.get("unit"),
                },
            },
        )
        self._invalidate_snapshot_cache(actor.display_name, surfaces=("vision_state", "dashboard", "today_board", "cognitive", "world_state", "world_graph"))
        return {
            "ok": True,
            "capture": payload,
            "observation": observation,
        }

    def package_rule(
        self,
        zone: str,
        preferred_drop: str,
        rain_sensitive: bool,
        note: str = "",
    ) -> dict:
        return self.perception_support.update_package_rule(zone, preferred_drop, rain_sensitive, note=note)

    def object_recognition(
        self,
        source: str,
        room: str,
        observed_object: str,
        detail: str = "",
        confidence: str = "medium",
    ) -> dict:
        result = self.perception_support.object_recognition(
            source,
            room,
            observed_object,
            detail=detail,
            confidence=confidence,
        )
        self._invalidate_snapshot_cache(surfaces=("vision_state", "dashboard", "today_board", "cognitive", "world_state", "world_graph"))
        return result

    def environmental_anomaly(
        self,
        category: str,
        source: str,
        reading: str,
        baseline: str,
        severity: str = "watch",
        detail: str = "",
    ) -> dict:
        return self.perception_support.environmental_anomaly(
            category,
            source,
            reading,
            baseline,
            severity=severity,
            detail=detail,
        )

    def privacy_state(self) -> dict:
        return self.perception_support.privacy_state()

    def update_privacy_state(
        self,
        kind: str,
        target: str,
        enabled: bool | None = None,
        muted: bool | None = None,
    ) -> dict:
        return self.perception_support.update_privacy_state(kind, target, enabled=enabled, muted=muted)

    def memory_overview(self, viewer_name: str) -> dict:
        viewer = self.get_actor(viewer_name)
        overview = self.memory_support.overview(viewer)
        overview["openviking"] = self.openviking_support.status()
        return overview

    def remember(
        self,
        actor_name: str,
        memory_type: str,
        scope: str,
        summary: str,
        detail: str,
        owner: str = "",
        project: str = "",
        tags: list[str] | None = None,
        sensitivity: str = "normal",
        subject_user_id: str = "",
        access_policy: str = "",
        source_type: str = "user-stated",
        confidence: str = "confirmed",
    ) -> dict:
        actor = self.get_actor(actor_name)
        result = self.memory_support.remember(
            actor,
            memory_type,
            scope,
            summary,
            detail,
            owner=owner,
            project=project,
            tags=tags,
            sensitivity=sensitivity,
            subject_user_id=subject_user_id,
            access_policy=access_policy,
            source_type=source_type,
            confidence=confidence,
        )
        entry = result.get("entry")
        if result.get("stored") and isinstance(entry, dict):
            result["openviking_sync"] = self.openviking_support.sync_memory_entry(
                {
                    **entry,
                    "payload": self.memory_support.cipher.decrypt_json(entry["encrypted_payload"]),
                }
            )
        return result

    def review_memory(
        self,
        viewer_name: str,
        memory_type: str = "",
        owner: str = "",
        project: str = "",
    ) -> list[dict]:
        viewer = self.get_actor(viewer_name)
        return self.memory_support.review(viewer, memory_type=memory_type, owner=owner, project=project)

    def forget_memory(self, viewer_name: str, entry_id: str) -> dict:
        viewer = self.get_actor(viewer_name)
        return self.memory_support.forget(viewer, entry_id)

    def export_memory(
        self,
        viewer_name: str,
        memory_type: str = "",
        owner: str = "",
        project: str = "",
    ) -> dict:
        viewer = self.get_actor(viewer_name)
        return self.memory_support.export(viewer, memory_type=memory_type, owner=owner, project=project)

    def memory_profile_snapshot(self, viewer_name: str, subject_user_id: str = "") -> dict:
        viewer = self.get_actor(viewer_name)
        return {
            "viewer": viewer.display_name,
            "subject_user_id": subject_user_id.strip().lower(),
            "facts": self.memory_support.profile_facts(viewer, subject_user_id=subject_user_id),
        }

    def learning_review_snapshot(self, viewer_name: str, subject_user_id: str = "") -> dict:
        viewer, subject = self._personalization_subject(viewer_name, subject_user_id)
        persona = self.build_persona_snapshot(subject.display_name, refresh=False)
        facts = self.memory_support.profile_facts(viewer, subject_user_id=subject.user_id)[:12]
        proposals = [
            item for item in self.memory_support.proposals(status="pending")
            if str(item.get("subject_user_id", "")).strip().lower() == subject.user_id
            or (not str(item.get("subject_user_id", "")).strip() and str(item.get("owner", "")).strip() == subject.display_name)
        ][:12]
        first_light_history = [
            item for item in self.first_light_store.load().get("history", [])
            if str(item.get("user_id", "")).strip().lower() == subject.user_id
        ][-5:]
        member = self.identity_registry.member(subject.user_id)
        personalization = self._personalization_snapshot(
            subject,
            member=member,
            profile_facts=facts,
            first_light_history=first_light_history,
        )
        return {
            "viewer": viewer.display_name,
            "subject_user_id": subject.user_id,
            "subject_display_name": subject.display_name,
            "child_safe_boundary": viewer.permissions != "adult",
            "profile": {
                "preferred_tone": getattr(member, "preferred_tone", ""),
                "briefing_style": getattr(member, "briefing_style", ""),
                "anticipation_style": getattr(member, "anticipation_style", ""),
                "preferred_voice": getattr(member, "preferred_voice", ""),
                "primary_rooms": list(getattr(member, "primary_rooms", []) or []),
                "morning_room": getattr(member, "morning_room", ""),
            },
            "persona_snapshot": persona,
            "personalization": personalization,
            "profile_facts": facts,
            "pending_proposals": proposals,
            "first_light_history": first_light_history,
            "governance": {
                "can_review_all": viewer.permissions == "adult",
                "can_retire_facts": True,
                "can_approve_proposals": viewer.permissions == "adult",
                "can_manage_personalization": viewer.permissions == "adult",
            },
        }

    def memory_proposals(self, status: str = "") -> list[dict]:
        return self.memory_support.proposals(status=status)

    def resolve_memory_proposal(self, proposal_id: str, decision: str) -> dict:
        result = self.memory_support.resolve_proposal(proposal_id, decision)
        entry = result.get("entry")
        if decision == "approved" and isinstance(entry, dict):
            result["openviking_sync"] = self.openviking_support.sync_memory_entry(
                {
                    **entry,
                    "payload": self.memory_support.cipher.decrypt_json(entry["encrypted_payload"]),
                }
            )
        return result

    def update_profile_fact_status(self, viewer_name: str, fact_id: str, status: str) -> dict:
        viewer = self.get_actor(viewer_name)
        updated = self.memory_support.update_profile_fact_status(viewer, fact_id, status)
        return {"ok": True, "fact": updated}

    def openviking_status(self) -> dict:
        return self.openviking_support.status()

    def sync_memory_to_openviking(self) -> dict:
        return self.openviking_support.sync_memory_entries(
            self.memory_support.approved_entries_for_context()
        )

    def run_memory_curation(self) -> dict:
        return self.memory_support.nightly_curation()

    def active_mode(self) -> dict:
        state = self.family_support.active_mode()
        return {
            "mode": state.mode,
            "status": state.status,
            "reason": state.reason,
            "actor": state.actor,
            "timestamp": state.timestamp,
        }

    def transition_mode(self, actor_name: str, mode: str, reason: str) -> dict:
        actor = self.get_actor(actor_name)
        state = self.family_support.transition_mode(actor.display_name, mode, reason)
        return {
            "mode": state.mode,
            "status": state.status,
            "reason": state.reason,
            "actor": state.actor,
            "timestamp": state.timestamp,
        }

    def family_mode_brief(self, mode: str = "") -> dict:
        active_mode = mode or self.family_support.active_mode().mode
        return self.family_support.mode_brief(
            active_mode,
            weather=self.snapshot.weather,
            home_details=self.snapshot.home.details,
            watch_items=self.snapshot.watch_items,
            event_titles=[event.title for event in self.snapshot.events],
        )

    def family_plan(self, actor_name: str, request: str) -> str:
        actor = self.get_actor(actor_name)
        active_mode = self.family_support.active_mode().mode
        merged_context = self.merged_calendar_brief(limit=5)
        enriched_request = request if not merged_context else f"{request}\n\nMerged calendar context: {merged_context}"
        return self.family_support.family_plan(actor.display_name, enriched_request, active_mode)

    def rebekah_command_center(self, request: str) -> str:
        active_mode = self.family_support.active_mode().mode
        return self.family_support.rebekah_command_center(request, active_mode)

    def troop_plan(self, actor_name: str, request: str) -> str:
        actor = self.get_actor(actor_name)
        return self.family_support.troop_plan(actor.display_name, request)

    def grocery_support(self, actor_name: str, request: str) -> str:
        actor = self.get_actor(actor_name)
        return self.family_support.grocery_support(actor.display_name, request)

    def departure_plan(self, actor_name: str, context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        garage_items = self.garage_status()
        garage_note = ""
        if garage_items:
            first = garage_items[0]
            garage_note = f"{first.get('name', 'Garage')} is {first.get('state', 'unknown')}."
        calendar_context = self.merged_calendar_brief(limit=4)
        enriched_context = context if not calendar_context else f"{context}\nMerged calendar: {calendar_context}".strip()
        return self.family_support.departure_orchestration(
            actor.display_name,
            enriched_context,
            self.snapshot.weather,
            garage_state=garage_note,
            family_focus=self.snapshot.family_focus,
        )

    def list_departure_runs(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_departure_runs(limit=limit)

    def meal_plan(self, actor_name: str, request: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.family_support.meal_plan(actor.display_name, request)

    def list_meal_plans(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_meal_plans(limit=limit)

    def vehicle_plan(self, actor_name: str, request: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.family_support.vehicle_assignment(actor.display_name, request, self.snapshot.weather)

    def list_vehicle_plans(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_vehicle_plans(limit=limit)

    def weather_contingency(self, actor_name: str, request: str) -> dict:
        actor = self.get_actor(actor_name)
        active_mode = self.family_support.active_mode().mode
        return self.family_support.weather_contingency(
            actor.display_name,
            request,
            self.snapshot.weather,
            active_mode,
        )

    def list_weather_plans(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_weather_plans(limit=limit)

    def draft_message(
        self,
        actor_name: str,
        audience: str,
        purpose: str,
        context: str,
        tone: str = "warm",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.family_support.draft_message(actor.display_name, audience, purpose, context, tone)

    def stage_parent_message(
        self,
        actor_name: str,
        audience: str,
        purpose: str,
        context: str,
        tone: str = "warm",
    ) -> dict:
        actor = self.get_actor(actor_name)
        draft = self.family_support.stage_parent_message(actor.display_name, audience, purpose, context, tone)
        approval_request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            actor=actor.display_name,
            room="family",
            request=f"Approve parent message to {audience} about {purpose}",
            action_class="EXECUTE_MEDIUM_RISK",
            second_factor_required=False,
            status="pending",
            rationale="Parent-facing communication must be reviewed before sending.",
        )
        self.approval_store.add(approval_request)
        draft["approval_request_id"] = approval_request.request_id
        return draft

    def list_message_drafts(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_drafts(limit=limit)

    def update_message_draft(self, draft_id: str, status: str) -> dict | None:
        return self.family_support.update_draft_status(draft_id, status)

    def anomaly_watch(self) -> list[dict]:
        return self.family_support.anomaly_watch(
            self.snapshot.home.details,
            self.snapshot.watch_items,
        )

    def package_or_motion_monitor(
        self,
        actor_name: str,
        category: str,
        location: str,
        detail: str,
        severity: str = "watch",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.package_or_motion_monitor(
            actor.display_name,
            category,
            location,
            detail,
            severity=severity,
        )

    def safety_escalation(
        self,
        actor_name: str,
        hazard_type: str,
        source: str,
        detail: str,
        severity: str = "critical",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.safety_escalation(
            actor.display_name,
            hazard_type,
            source,
            detail,
            severity=severity,
        )

    def weather_advisory(self, actor_name: str, context: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.weather_advisory(actor.display_name, context, self.snapshot.weather)

    def child_arrival(self, actor_name: str, location: str, detail: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.child_arrival(actor.display_name, location, detail)

    def unlock_assessment(
        self,
        actor_name: str,
        target: str,
        requested_by_voice: bool = True,
        second_factor_present: bool = False,
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.security_support.unlock_assessment(
            actor.display_name,
            target,
            requested_by_voice,
            second_factor_present,
        )

    def overnight_review(self) -> dict:
        return self.security_support.overnight_review(self.snapshot.watch_items)

    def list_security_incidents(self, limit: int = 20) -> list[dict]:
        return self.security_support.list_incidents(limit=limit)

    def list_weather_advisories(self, limit: int = 20) -> list[dict]:
        return self.security_support.list_weather(limit=limit)

    def list_arrival_events(self, limit: int = 20) -> list[dict]:
        return self.security_support.list_arrivals(limit=limit)

    def list_unlock_assessments(self, limit: int = 20) -> list[dict]:
        return self.security_support.list_unlocks(limit=limit)

    def capture_voice_note(self, actor_name: str, source: str, note: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.family_support.capture_voice_note(actor.display_name, source, note)

    def list_voice_note_tasks(self, limit: int = 20) -> list[dict]:
        return self.family_support.list_voice_note_tasks(limit=limit)

    def update_voice_note_status(self, note_id: str, status: str) -> dict | None:
        return self.family_support.update_voice_note_status(note_id, status)

    def child_boundaries(self, actor_name: str | None = None) -> list[dict]:
        if actor_name:
            actor = self.get_actor(actor_name)
            return self.tutoring_support.child_boundaries(actor)
        children = [profile for profile in self.household.users.values() if profile.permissions == "child"]
        reports: list[dict] = []
        for child in children:
            reports.extend(self.tutoring_support.child_boundaries(child))
        return reports

    def tutor(self, actor_name: str, request: str, subject: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.tutoring_support.tutoring_turn(actor, request, subject=subject)

    def tutoring_summaries(
        self,
        viewer_name: str,
        child_name: str = "",
        limit: int = 10,
    ) -> dict:
        viewer = self.get_actor(viewer_name)
        return self.tutoring_support.parent_summaries(viewer, child_name=child_name, limit=limit)

    def device_boundary_plan(self, actor_name: str, window_label: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.tutoring_support.device_boundary_plan(actor, window_label=window_label)

    def list_device_boundaries(self, child_name: str = "", limit: int = 20) -> list[dict]:
        return self.tutoring_support.list_device_boundaries(child_name=child_name, limit=limit)

    def update_device_boundary_status(self, routine_id: str, status: str) -> dict | None:
        return self.tutoring_support.update_device_boundary_status(routine_id, status)

    def workshop_plan(self, actor_name: str, request: str) -> str:
        actor = self.get_actor(actor_name)
        return self.workshop_support.workshop_plan(actor.display_name, request)

    def printer_status(self) -> list[dict]:
        return self.workshop_support.printer_status()

    def material_recommendation(
        self,
        actor_name: str,
        part_name: str,
        use_case: str,
        requirements: str,
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.material_recommendation(actor.display_name, part_name, use_case, requirements)

    def cad_package(self, actor_name: str, part_name: str, dimensions: str, constraints: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.cad_package(actor.display_name, part_name, dimensions, constraints)

    def cad_package_advanced(
        self,
        actor_name: str,
        part_name: str,
        dimensions: str,
        constraints: str,
        family_hint: str,
        printer_hint: str,
        profile_hint: str,
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.cad_package_advanced(
            actor.display_name,
            part_name,
            dimensions,
            constraints,
            family_hint,
            printer_hint,
            profile_hint,
        )

    def print_prep(
        self,
        actor_name: str,
        part_name: str,
        printer_id: str,
        material: str,
        profile_name: str,
        notes: str,
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.print_prep(
            actor.display_name,
            part_name,
            printer_id,
            material,
            profile_name,
            notes,
        )

    def safety_check(self, actor_name: str, operation: str, context: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.safety_check(actor.display_name, operation, context)

    def inventory_summary(self) -> list[dict]:
        return self.workshop_support.inventory_summary()

    def inspect_part(
        self,
        actor_name: str,
        part_name: str,
        request: str,
        observations: str,
        goals: str,
        image_path: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.workshop_support.inspect_part(
            actor.display_name,
            part_name,
            request,
            observations,
            goals,
            image_path=image_path,
        )

    def list_workshop_inspections(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.store.list_inspections(limit=limit)

    def list_cad_packages(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_cad_packages(limit=limit)

    def get_cad_package(self, package_id: str) -> dict | None:
        return self.workshop_support.store.get_cad_package(package_id)

    def workshop_machine_options(self) -> dict:
        return self.workshop_support.workshop_machine_options()

    def package_artifact_path(self, package_id: str, kind: str) -> tuple[Path, str]:
        return self.workshop_support.package_artifact_path(package_id, kind)

    def slicer_pack_archive(self, package_id: str) -> tuple[Path, str]:
        return self.workshop_support.slicer_pack_archive(package_id)

    def open_package_in_slicer(self, package_id: str, slicer_app: str = "") -> dict[str, str]:
        return self.workshop_support.open_package_in_slicer(package_id, slicer_app)

    def list_print_preps(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_print_preps(limit=limit)

    def list_material_recommendations(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_material_recommendations(limit=limit)

    def list_safety_checks(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_safety_checks(limit=limit)

    def vendor_prep(
        self,
        actor_name: str,
        part_name: str,
        vendor_target: str,
        process: str,
        material: str,
        notes: str,
    ) -> dict:
        actor = self.get_actor(actor_name)
        prep = self.workshop_support.prepare_vendor_prep(
            actor.display_name,
            part_name,
            vendor_target,
            process,
            material,
            notes,
        )
        approval_request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            actor=actor.display_name,
            room="workshop",
            request=f"Approve vendor package for {part_name} to {vendor_target}",
            action_class="EXECUTE_MEDIUM_RISK",
            second_factor_required=False,
            status="pending",
            rationale="External vendor submission requires explicit approval before any quote request is sent.",
        )
        self.approval_store.add(approval_request)
        prep["approval_request_id"] = approval_request.request_id
        prep["status"] = "pending-approval"
        return self.workshop_support.save_vendor_prep(prep)

    def list_vendor_preps(self, limit: int = 10) -> list[dict]:
        return self.workshop_support.list_vendor_preps(limit=limit)

    def update_vendor_prep_status(self, prep_id: str, status: str) -> dict | None:
        return self.workshop_support.update_vendor_prep_status(prep_id, status)

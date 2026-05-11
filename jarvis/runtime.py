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

            enriched_devices.append(
                {
                    **device,
                    "owner_display_name": owner.get("display_name", "") if owner else "",
                    "default_actor_display_name": default_actor.get("display_name", "") if default_actor else "",
                    "last_actor_display_name": last_actor.get("display_name", "") if last_actor else "",
                    "has_fingerprint": bool(str(device.get("fingerprint", "")).strip()),
                    "mapped": mapped,
                    "posture": posture,
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
        if not refresh:
            cached = self.adaptation_store.profile(actor.user_id)
            if cached:
                return cached
        member = self._actor_member(actor)
        latest_first_light = self.first_light_store.latest_packet(actor.user_id) or {}
        profile_facts = self.memory_support.profile_facts(actor, subject_user_id=actor.user_id)[:8]
        perception = self.perception_support.perception_overview()
        actor_presence = str((perception.get("actor_presence") or {}).get(actor.display_name, "unknown"))
        occupied_rooms = [room for room, occupied in (perception.get("room_presence") or {}).items() if occupied][:6]
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
        presence_identity = {
            "primary_rooms": list(getattr(member, "primary_rooms", []) or []),
            "morning_room": getattr(member, "morning_room", "") if member else "",
            "actor_presence": actor_presence,
            "occupied_rooms": occupied_rooms,
        }
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

    def _first_light_deltas(self, actor: UserProfile, current_events: list[dict], unread_count: int) -> list[str]:
        latest = self.first_light_store.latest_packet(actor.user_id)
        world_events = self.assistant_core_store.list_world_events(actor.display_name, limit=3)
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
                newest = world_events[0]
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
            newest = world_events[0]
            added = clean_labels(list(newest.get("added_labels", [])))
            removed = clean_labels(list(newest.get("removed_labels", [])), limit=1)
            if added:
                deltas.append("World model picked up new pressure: " + "; ".join(added))
            elif removed:
                deltas.append("Some pressure fell away: " + "; ".join(removed))
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
        delta_lines = self._first_light_deltas(actor, actor_events, unread_count)
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

    def _parse_timestamp(self, value: str) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

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

    def _notification_policy_for_item(self, item: dict) -> dict:
        domain = str(item.get("domain", "")).strip().lower()
        status = str(item.get("status", "")).strip().lower()
        needs_revisit = bool(item.get("needs_revisit"))
        if domain == "content":
            return {
                "severity": "low",
                "priority_class": "quiet",
                "delivery_mode": "queue-only",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 72,
                "summary": "Content packaging is quiet background work unless it reaches a publish decision.",
            }
        if domain == "memory":
            return {
                "severity": "low",
                "priority_class": "quiet",
                "delivery_mode": "queue-only",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 72,
                "summary": "Memory governance stays in the assistant queue until you deliberately review it.",
            }
        if domain == "growth":
            return {
                "severity": "normal" if needs_revisit else "low",
                "priority_class": "normal" if needs_revisit else "quiet",
                "delivery_mode": "browser-eligible" if needs_revisit else "queue-only",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 48,
                "summary": "Growth work should surface during active hours when leverage-bearing experiments or pipeline follow-up have gone stale.",
            }
        if domain == "approvals":
            return {
                "severity": "high" if status in {"pending", "pending-approval"} else "normal",
                "priority_class": "interrupt-worthy" if status in {"pending", "pending-approval"} else "normal",
                "delivery_mode": "browser-eligible",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 24,
                "summary": "Approvals can alert you during active hours, but quiet hours still suppress interruptions.",
            }
        if domain in {"family", "workshop"} and needs_revisit:
            return {
                "severity": "normal",
                "priority_class": "normal",
                "delivery_mode": "browser-eligible",
                "interrupt_during_quiet_hours": False,
                "stale_after_hours": 36,
                "summary": "Aged family and workshop follow-up can interrupt during active hours, then fall back to the inbox overnight.",
            }
        return {
            "severity": "normal",
            "priority_class": "normal",
            "delivery_mode": "queue-only",
            "interrupt_during_quiet_hours": False,
            "stale_after_hours": 48,
            "summary": "This follow-up will stay in the assistant queue until JARVIS has a better moment to surface it.",
        }

    def _surfacing_cooldown_minutes(self, *, status: str, domain: str, cadence_phase: str, browser_interrupt: bool) -> int:
        normalized_status = str(status or "").strip().lower()
        normalized_domain = str(domain or "").strip().lower()
        normalized_phase = str(cadence_phase or "").strip().lower()
        if normalized_status == "ignored":
            return 240
        if normalized_status == "opened":
            return 120
        if normalized_status == "surfaced":
            return 60 if browser_interrupt else 90
        if normalized_status == "unseen":
            return 20 if browser_interrupt else 45
        if normalized_domain == "growth":
            return 120
        if normalized_phase in {"evening", "night"}:
            return 120
        return 45

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
        cadence_phase: str,
        world_state: dict | None = None,
        growth_state: dict | None = None,
        quiet_hours_active: bool | None = None,
    ) -> dict:
        policy = dict(self._notification_policy_for_item(item) or {})
        quiet_hours_active = self._quiet_hours_active() if quiet_hours_active is None else bool(quiet_hours_active)
        urgency = self._urgency_score(item)
        world_boost = self._world_state_priority_boost(item, world_state)
        domain = str(item.get("domain", "")).strip().lower()
        base_delivery_mode = str(policy.get("delivery_mode", "queue-only")).strip().lower() or "queue-only"
        base_priority = str(policy.get("priority_class", "normal")).strip().lower() or "normal"
        score = urgency + int(world_boost.get("score", 0) or 0)
        if str(cadence_phase).strip().lower() in {"morning", "pre-transition"} and domain in {"family", "approvals"}:
            score += 1
        growth_pressure = str(((growth_state or {}).get("summary") or {}).get("pressure", "quiet")).strip().lower()
        if domain == "growth" and growth_pressure in {"warming", "active"}:
            score += 1
        interrupt_threshold = 8
        if domain == "approvals":
            interrupt_threshold = 7
        elif domain == "growth":
            interrupt_threshold = 8 if growth_pressure == "active" else 9
        elif str(cadence_phase).strip().lower() in {"evening", "night"}:
            interrupt_threshold = 9
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
        if top_item:
            top_item = dict(top_item)
            top_item["why_this_surfaced_now"] = str(top_item.get("proactive_reason", "")).strip() or "JARVIS judged that this item deserves attention."
        return {
            "chips": chips[:3],
            "briefing_lines": briefing_lines,
            "auto_open_packet": "tasks" if auto_open else "",
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

    def mark_assistant_notification(self, actor_name: str, notification_id: str, status: str) -> dict:
        actor = self.get_actor(actor_name)
        record = self.assistant_core_store.mark_notification(notification_id, status=status)
        if record is None:
            raise KeyError("Assistant notification not found.")
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
                    result = self.apply_open_loop_action(
                        actor_name,
                        domain=str(top_item.get("domain", "")),
                        item_id=str(top_item.get("item_id", "")),
                        action=action_id,
                        note="assistant-autonomy",
                    )
                    self.audit_log.log_assistant_action(
                        actor=actor_name,
                        domain=str(top_item.get("domain", "")),
                        item_id=str(top_item.get("item_id", "")),
                        action=action_id,
                        action_class=str(policy.get("action_class", "")).strip(),
                        detail=str(policy.get("summary", "Assistant autonomy executed a safe action.")).strip(),
                        mode="automatic",
                        policy_basis=str(policy.get("summary", "")).strip(),
                        confidence=self._assistant_action_confidence(policy),
                        decision=decision,
                        cadence_phase=str(cadence.get("phase", "")).strip(),
                        quiet_hours_active=self._quiet_hours_active(),
                        why_now=str((surfacing_plan or {}).get("why_this_surfaced_now", "")).strip() or str(top_item.get("proactive_reason", "")).strip(),
                        surface_key=str((tick.get("assistant_surface") or {}).get("surface_key", "")).strip(),
                        result_summary=self._assistant_action_result_summary(result),
                        succeeded=bool(result.get("ok")),
                    )
                    actor_executed = True
                    executed_actions.append(
                        {
                            "actor": actor_name,
                            "domain": str(top_item.get("domain", "")),
                            "item_id": str(top_item.get("item_id", "")),
                            "action": action_id,
                            "result": result,
                        }
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
                notification_policy = surfacing_plan or self._notification_policy_for_item(top_item)
                delivery_mode = "queue-only" if decision == "queue" else str(notification_policy.get("delivery_mode", "queue-only"))
                title = str(top_item.get("title", "Assistant follow-up")).strip() or "Assistant follow-up"
                detail = str((tick.get("assistant_surface", {}).get("briefing_lines") or ["JARVIS resurfaced a task."])[0]).strip()
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

    def today_board(self, actor_name: str = "Chris") -> dict:
        def builder() -> dict:
            actor = self.get_actor(actor_name)
            open_loops = self.unified_open_loops(actor.display_name, limit=18)
            visible_keys = {
                self._open_loop_key(str(item.get("domain", "")), str(item.get("item_id", "")))
                for item in list(open_loops.get("items", []))
            }
            calendar = self._actor_calendar_events(actor, limit=6)
            first_light = self.first_light_store.latest_packet(actor.user_id) or {}
            quiet_hours_active = self._quiet_hours_active()
            cognition = self.cognitive_snapshot(actor.display_name, include_graph=False, open_loops=open_loops)
            growth = cognition.get("growth_state") or {}
            growth_guidance = self._growth_loop_guidance(
                actor,
                growth_state=growth,
                cadence=dict(cognition.get("cadence") or {}),
            )
            top_items = list(open_loops.get("items", []))[:5]
            summary = dict(open_loops.get("summary", {}))
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
                    "top_item": open_loops.get("top_item"),
                },
                "growth": growth,
                "growth_guidance": growth_guidance,
                "assistant_notifications": self.assistant_notifications(actor.display_name, limit=5, unread_only=True, visible_keys=visible_keys),
                "cognition": cognition,
            }
            if self._is_degraded_payload(cognition):
                payload["degraded"] = {
                    "active": True,
                    "reason": "Today Board is carrying a stale cognitive snapshot.",
                    "detail": str((cognition.get("degraded") or {}).get("detail", "")),
                    "source": "nested-cognitive-snapshot",
                }
            return payload

        return self._cached_surface("today_board", actor_name, builder)

    def cadence_review(self, actor_name: str = "Chris") -> dict:
        def builder() -> dict:
            actor = self.get_actor(actor_name)
            open_loops = self.unified_open_loops(actor.display_name, limit=18)
            cognition = self.cognitive_snapshot(actor.display_name, include_graph=False, open_loops=open_loops)
            cadence = dict(cognition.get("cadence") or {})
            growth = dict(cognition.get("growth_state") or {})
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
            top_items = list(open_loops.get("items", []))[:5]
            domain_counts = dict(open_loops.get("summary", {}).get("by_domain", {}))
            waiting = int(open_loops.get("summary", {}).get("waiting_on_you", 0) or 0)
            revisit = int(open_loops.get("summary", {}).get("needs_revisit", 0) or 0)
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
                open_loops=open_loops,
                growth_guidance=growth_guidance,
                assistant_inbox=notifications,
                top_task=top_task,
            )
            outcome_summary = self._cadence_outcome_summary(
                phase,
                open_loops=open_loops,
                growth_guidance=growth_guidance,
                assistant_inbox=notifications,
            )
            history = self._recent_cadence_history(actor.display_name, limit=5)
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
                        "id": "tasks",
                        "title": "Priority Tasks",
                        "summary": f"{int(open_loops.get('summary', {}).get('waiting_on_you', 0) or 0)} waiting · {int(open_loops.get('summary', {}).get('needs_revisit', 0) or 0)} revisit",
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
            if self._is_degraded_payload(cognition):
                payload["degraded"] = {
                    "active": True,
                    "reason": "Cadence Review is carrying a stale cognitive snapshot.",
                    "detail": str((cognition.get("degraded") or {}).get("detail", "")),
                    "source": "nested-cognitive-snapshot",
                }
            return payload

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
        next_action = str(top_item.get("next_action", "keep monitoring")).strip() or "keep monitoring"
        decision = str(deliberation.get("decision", "hold")).strip().lower()
        policy = self._notification_policy_for_item(top_item) if top_item else {}
        recommendations = {
            "planner": f"Sequence the next move around {title.lower()} by aiming for '{next_action}'.",
            "critic": "Avoid interrupting unless the item is truly aging or blocked." if decision != "act" else "The bounded action looks safe, but keep the blast radius small.",
            "executor": "Act on the policy-approved step now." if decision == "act" else f"Keep the next concrete move ready: {next_action}.",
            "safety_governor": str(policy.get("summary", "Stay inside approval boundaries and avoid noisy escalation.")),
            "strategist": "Prefer moves that reduce family friction and keep leverage-bearing work moving.",
        }
        votes = {
            "planner": "act" if decision == "act" else "queue",
            "critic": "hold" if decision == "hold" else "queue",
            "executor": decision if decision in {"act", "notify"} else "queue",
            "safety_governor": "hold" if self._quiet_hours_active() and not bool(policy.get("interrupt_during_quiet_hours")) else decision,
            "strategist": "notify" if decision == "notify" else ("act" if decision == "act" else "queue"),
        }
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "top_item_title": title,
            "consensus": decision,
            "members": [
                {"role": role, "vote": votes.get(role, "queue"), "recommendation": text}
                for role, text in recommendations.items()
            ],
        }

    def world_graph_snapshot(self, actor_name: str = "Chris", *, open_loops: dict | None = None) -> dict:
        actor = self.get_actor(actor_name)
        identity = self.identity_overview()
        open_loops = open_loops or self.unified_open_loops(actor.display_name, limit=18)
        visible_keys = {
            self._open_loop_key(str(item.get("domain", "")), str(item.get("item_id", "")))
            for item in list(open_loops.get("items", []))
        }
        calendar = self._actor_calendar_events(actor, limit=8)
        approvals = [item for item in self.list_pending_approvals() if str(item.get("actor", "")).strip().lower() in {actor.display_name.lower(), actor.user_id.lower()}][:8]
        notifications = self.assistant_notifications(actor.display_name, limit=8, unread_only=True, visible_keys=visible_keys)
        growth_state = self.growth_state_snapshot(actor.display_name)
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
        for person in people:
            nodes.append({"id": f"person:{person['id']}", "type": "person", **person})
        for room in rooms:
            nodes.append({"id": f"room:{room['id']}", "type": "room", **room})
        for device in devices:
            nodes.append({"id": f"device:{device['device_id']}", "type": "device", **device})
            if device["owner_user_id"]:
                edges.append({"source": f"person:{device['owner_user_id']}", "target": f"device:{device['device_id']}", "type": "owns"})
            if device["room"]:
                edges.append({"source": f"device:{device['device_id']}", "target": f"room:{device['room']}", "type": "located-in"})
        for event in calendar:
            event_id = str(event.get("id", "")) or str(uuid.uuid4())
            nodes.append(
                {
                    "id": f"event:{event_id}",
                    "type": "event",
                    "label": str(event.get("summary", "(Untitled event)")),
                    "start": str(event.get("start", "")),
                    "source": str(event.get("source", "")),
                }
            )
            edges.append({"source": f"person:{actor.user_id}", "target": f"event:{event_id}", "type": "attends-or-carries"})
        for item in list(open_loops.get("items", []))[:20]:
            item_key = self._open_loop_key(str(item.get("domain", "")), str(item.get("item_id", "")))
            nodes.append(
                {
                    "id": f"task:{item_key}",
                    "type": "task",
                    "label": str(item.get("title", "Open loop")),
                    "domain": str(item.get("domain", "")),
                    "status": str(item.get("status", "")),
                    "owner_agent": str(item.get("owner_agent", "")),
                    "next_action": str(item.get("next_action", "")),
                }
            )
            item_actor = str(item.get("actor", "")).strip().lower()
            if item_actor in self.household.users:
                edges.append({"source": f"person:{item_actor}", "target": f"task:{item_key}", "type": "carries"})
            elif item_actor == actor.display_name.lower():
                edges.append({"source": f"person:{actor.user_id}", "target": f"task:{item_key}", "type": "carries"})
        for item in approvals:
            approval_id = str(item.get("request_id", ""))
            nodes.append(
                {
                    "id": f"approval:{approval_id}",
                    "type": "approval",
                    "label": str(item.get("request", "Approval required")),
                    "status": str(item.get("status", "pending")),
                }
            )
            edges.append({"source": f"person:{actor.user_id}", "target": f"approval:{approval_id}", "type": "must-decide"})
        for item in notifications.get("items", []):
            note_id = str(item.get("notification_id", ""))
            nodes.append(
                {
                    "id": f"notification:{note_id}",
                    "type": "notification",
                    "label": str(item.get("title", "Assistant follow-up")),
                    "domain": str(item.get("domain", "")),
                    "delivery_mode": str(item.get("delivery_mode", "")),
                }
            )
            edges.append({"source": f"person:{actor.user_id}", "target": f"notification:{note_id}", "type": "needs-attention"})
        for lane in growth_state.get("lanes", []):
            lane_id = str(lane.get("id", "")).strip()
            if not lane_id:
                continue
            nodes.append(
                {
                    "id": f"growth-lane:{lane_id}",
                    "type": "growth-lane",
                    "label": str(lane.get("label", "Growth lane")),
                    "pressure": str(lane.get("pressure", "steady")),
                    "confidence": str(lane.get("confidence", "low")),
                }
            )
            edges.append({"source": f"person:{actor.user_id}", "target": f"growth-lane:{lane_id}", "type": "compounds"})
        for index, signal in enumerate(growth_state.get("top_signals", [])[:6], start=1):
            signal_id = f"{actor.user_id}:{index}"
            nodes.append(
                {
                    "id": f"growth-signal:{signal_id}",
                    "type": "growth-signal",
                    "label": str(signal),
                }
            )
            edges.append({"source": f"person:{actor.user_id}", "target": f"growth-signal:{signal_id}", "type": "tracks"})
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "people": len([node for node in nodes if node.get("type") == "person"]),
                "rooms": len([node for node in nodes if node.get("type") == "room"]),
                "devices": len([node for node in nodes if node.get("type") == "device"]),
                "events": len([node for node in nodes if node.get("type") == "event"]),
                "tasks": len([node for node in nodes if node.get("type") == "task"]),
                "approvals": len([node for node in nodes if node.get("type") == "approval"]),
                "notifications": len([node for node in nodes if node.get("type") == "notification"]),
                "growth_lanes": len([node for node in nodes if node.get("type") == "growth-lane"]),
                "growth_signals": len([node for node in nodes if node.get("type") == "growth-signal"]),
                "edges": len(edges),
            },
            "nodes": nodes,
            "edges": edges,
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
        volatility = sum(abs(int(value)) for value in count_delta.values())
        pressure = "steady"
        if volatility >= 5:
            pressure = "shifting"
        elif volatility >= 1:
            pressure = "changed"
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
                confidence="medium" if wealth_runs else "low",
                summary=f"{len(wealth_runs)} recent workflow(s) · {len(opportunity_theses)} thesis(es) · {len(roi_lessons)} ROI lesson(s)",
                latest=str(latest_wealth.get("request", "")).strip() or "No recent financial workflow is staged.",
                latest_timestamp=str(latest_wealth.get("timestamp", "")).strip(),
                live=False,
                source_adapter_id="revenue",
                source_count=len(wealth_runs),
                metrics={
                    "recent_runs": len(wealth_runs),
                    "opportunity_theses": len(opportunity_theses),
                    "roi_lessons": len(roi_lessons),
                },
                signals=_unique(opportunity_theses[:3] + roi_lessons[:2], limit=5),
                next_moves=_unique(experiments[:2], limit=3),
                truth_note="Finance telemetry is currently inferred from local wealth workflows until live account connectors are wired.",
            ),
            GrowthDomainSnapshot(
                id="pipeline",
                label="Pipeline",
                description="Sales pipeline movement, project briefs, and implementation readiness.",
                pressure=pipeline_pressure,
                confidence="medium" if catalyst_signals else "low",
                summary=f"{len(catalyst_signals)} signal(s) · {len(project_briefs)} brief(s) · {len(implementation_plans)} implementation plan(s)",
                latest=signal_titles[0] if signal_titles else "No explicit CRM or revenue feed is connected yet.",
                latest_timestamp=str((catalyst_signals[0] if catalyst_signals else {}).get("timestamp", "")).strip(),
                live=False,
                source_adapter_id="pipeline",
                source_count=len(catalyst_signals) + len(project_briefs) + len(implementation_plans),
                metrics={
                    "signals": len(catalyst_signals),
                    "project_briefs": len(project_briefs),
                    "implementation_plans": len(implementation_plans),
                },
                signals=_unique(signal_titles + _unique(recommended_focus, limit=2), limit=5),
                next_moves=_unique([str(move) for move in recommended_focus[:3]], limit=3),
                truth_note="Pipeline telemetry is currently inferred from Catalyst artifacts instead of a live CRM connector.",
            ),
            GrowthDomainSnapshot(
                id="marketing",
                label="Marketing",
                description="Audience-facing momentum, campaign readiness, and market-facing visibility.",
                pressure=marketing_pressure,
                confidence="medium" if content_queue else "low",
                summary=f"{queued_count} queued campaign asset(s) · {exported_count} exported · {live_count} live",
                latest=str(latest_content.get("title", "")).strip() or "No market-facing asset is staged.",
                latest_timestamp=str(latest_content.get("updated_at", "") or latest_content.get("created_at", "")).strip(),
                live=False,
                source_adapter_id="audience-growth",
                source_count=len(active_content),
                metrics={
                    "queued_assets": queued_count,
                    "exported_assets": exported_count,
                    "live_assets": live_count,
                    "audience_signals": 0,
                },
                signals=_unique([str(latest_content.get("title", "")).strip()] + _unique(recommended_focus, limit=3), limit=4),
                next_moves=_unique([str(item.get("title", "")).strip() for item in active_content[:2]] + [str(move) for move in recommended_focus[:2]], limit=4),
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
                summary=f"{queued_count} queued · {scripted_count} scripted · {exported_count} exported · {live_count} live",
                latest=domain_map["content"].latest or domain_map["marketing"].latest,
                latest_timestamp=domain_map["content"].latest_timestamp or domain_map["marketing"].latest_timestamp,
                domain_ids=["content", "marketing"],
            ),
            GrowthLaneSnapshot(
                id="pipeline",
                label="Sales and Pipeline Posture",
                pressure=_lane_pressure(["pipeline", "offers"]),
                confidence=_lane_confidence(["pipeline", "offers"]),
                summary=f"{len(catalyst_signals)} signal(s) · {len(project_briefs)} project brief(s) · {len(implementation_plans)} implementation plan(s)",
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

    def self_model_snapshot(self, actor_name: str = "Chris") -> dict:
        actor = self.get_actor(actor_name)
        integration_status = self.status()
        growth = self.growth_state_snapshot(actor.display_name)
        ready_tools = [item["name"] for item in integration_status if item.get("ok")]
        blocked_tools = [item["name"] for item in integration_status if not item.get("ok")]
        return {
            "actor": actor.display_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tools": {
                "ready": ready_tools,
                "blocked": blocked_tools,
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
                "identity": "high" if self.identity_overview().get("members") else "medium",
                "calendar": "medium" if self._actor_calendar_events(actor, limit=1) else "low",
                "assistant_autonomy": "high",
                "weather": "low",
                "growth": "medium" if growth.get("summary", {}).get("tracked_signal_count", 0) else "low",
            },
            "uncertainties": [
                "weather remains staged rather than live",
                "phone/iPad outbound delivery is not yet connected beyond browser alerts",
                "financial institutions, CRM, and ad-platform telemetry are not connected yet",
            ],
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
        notification_policy = self._notification_policy_for_item(top_item)
        quiet_hours_active = self._quiet_hours_active()
        cadence_phase = str(cadence.get("phase", "watch")).strip().lower()
        world_boost = self._world_state_priority_boost(top_item, world_state)
        growth_pressure = str((growth_state.get("summary") or {}).get("pressure", "quiet")).strip().lower()
        growth_guidance = self._growth_loop_guidance(
            actor,
            growth_state=growth_state,
            cadence=cadence,
        )
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
                str(notification_policy.get("summary", "JARVIS is balancing queueing, surfacing, and interruption policy.")),
                "Quiet-hour policy suppresses alerts unless explicitly permitted." if quiet_hours_active else "Active-hour policy allows eligible resurfacing to interrupt on trusted devices.",
            ],
            "simulation": {
                "smallest_helpful_move": str(top_item.get("next_action", "follow up")),
                "risk_if_act_now": "Noise or premature interruption." if decision != "act" else "Low, because this path is explicitly policy-approved.",
                "risk_if_hold": "Important follow-up may go stale." if bool(top_item.get("needs_revisit")) else "Low.",
            },
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
        lane_titles = {str(item.get("title", "")).strip().lower() for item in items}
        for lane in growth_state.get("lanes", []):
            pressure = str(lane.get("pressure", "quiet")).strip().lower()
            latest = str(lane.get("latest", "")).strip()
            if pressure == "quiet" and not latest:
                continue
            timestamp = str((growth_state.get("latest_timestamps") or {}).get(str(lane.get("id", "")), "")).strip() or str(growth_state.get("generated_at", "")).strip()
            status = "warming" if pressure in {"warming", "active"} else "staged"
            follow_up = self._follow_up_state(timestamp, status, "growth")
            title = latest or str(lane.get("label", "Growth lane")).strip()
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
                    "summary": str(lane.get("summary", "")).strip(),
                    "status": status,
                    "actor": actor.display_name,
                    "timestamp": timestamp,
                    "task_lane": task_lane["lane"],
                    "owner_agent": task_lane["owner_agent"],
                    "approval_threshold": threshold,
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

    def explainability_snapshot(self) -> dict:
        activity = self.audit_log.list_recent(limit=12, entry_type="plan")
        assistant_actions = self.audit_log.list_recent(limit=12, entry_type="assistant-action")
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
        return self.catalyst_support.capture_signal(
            actor.display_name,
            source,
            title,
            content,
            sender=sender,
            tags=tags,
        )

    def catalyst_email_triage(self, actor_name: str, subject: str, body: str, sender: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.email_triage(actor.display_name, subject, body, sender)

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
        return self.catalyst_support.meeting_extraction(actor.display_name, transcript, context)

    def catalyst_briefing(self, actor_name: str, user_context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        context = user_context.strip()
        calendar_context = self.merged_calendar_brief(limit=5)
        if calendar_context:
            context = f"{context}\nMerged calendar: {calendar_context}".strip()
        briefing = self.catalyst_support.briefing_generation(actor.display_name, context)
        briefing["strategic_brief"] = self.daily_strategic_brief(actor.display_name)
        briefing["systems_note"] = self.cross_domain_synthesis_brief(actor.display_name, "today's family, work, and calendar load")
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
        return self.content_ops.generate_options(actor.display_name, topic, channel=channel, context=context)

    def veronica_approve_option(self, actor_name: str, option_id: str) -> dict:
        actor = self.get_actor(actor_name)
        return self.content_ops.approve_option(actor.display_name, option_id)

    def veronica_push_live(self, queue_id: str) -> dict:
        record = self.content_ops.push_live(queue_id)
        if not record:
            return {"ok": False, "message": "Queue item not found."}
        return {"ok": True, "record": record}

    def veronica_export(self, queue_id: str) -> dict:
        try:
            record = self.content_ops.export_queue_item(queue_id)
        except ValueError as exc:
            return {"ok": False, "message": str(exc)}
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
        return self.catalyst_support.project_brief(actor.display_name, project_name, problem, desired_outcome, constraints)

    def catalyst_implementation_plan(
        self,
        actor_name: str,
        project_name: str,
        brief: str,
        constraints: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.implementation_plan(actor.display_name, project_name, brief, constraints)

    def catalyst_proactive_surfacing(self, actor_name: str, horizon: str = "today", context: str = "") -> dict:
        actor = self.get_actor(actor_name)
        return self.catalyst_support.proactive_surfacing(actor.display_name, horizon, context)

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
            today_board = self.today_board(actor.display_name)
            cadence_review = self.cadence_review(actor.display_name)
            cognitive = self.cognitive_snapshot(actor.display_name, include_graph=False, open_loops=open_loops)
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
        return self.perception_support.presence_sensor_update(sensor, room, occupied, detail=detail)

    def phone_presence_update(
        self,
        actor_name: str,
        device: str,
        state: str,
        zone: str = "",
        detail: str = "",
    ) -> dict:
        actor = self.get_actor(actor_name)
        return self.perception_support.phone_presence_update(
            actor.display_name,
            device,
            state,
            zone=zone,
            detail=detail,
        )

    def camera_event(
        self,
        camera: str,
        event_type: str,
        detail: str,
        detected_object: str = "",
        confidence: str = "medium",
    ) -> dict:
        return self.perception_support.camera_event(
            camera,
            event_type,
            detail,
            detected_object=detected_object,
            confidence=confidence,
        )

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
        if not image_data_url.strip():
            raise ValueError("image_data_url is required")
        requested_mode = (mode or "describe").strip().lower()
        detail_prompt = prompt.strip() or "Describe what is visible and call out the most important objects or activity."
        capture_id = str(uuid.uuid4())
        capture_root = Path("data") / "vision" / "captures"
        capture_root.mkdir(parents=True, exist_ok=True)
        image_path = capture_root / f"{capture_id}.jpg"
        metadata_path = capture_root / f"{capture_id}.json"

        header, _, encoded = image_data_url.partition(",")
        if not encoded:
            raise ValueError("Invalid image payload.")
        image_bytes = base64.b64decode(encoded)
        image_path.write_bytes(image_bytes)

        compare_payload: dict | None = None
        image_inputs = [image_data_url]
        if requested_mode == "compare" and not compare_to_capture_id.strip():
            raise ValueError("Compare mode needs a previous frame. Capture one frame first.")
        if compare_to_capture_id.strip():
            prior_metadata = capture_root / f"{compare_to_capture_id.strip()}.json"
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
        metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

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
        return self.perception_support.object_recognition(
            source,
            room,
            observed_object,
            detail=detail,
            confidence=confidence,
        )

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
        viewer = self.get_actor(viewer_name)
        subject_id = subject_user_id.strip().lower() or viewer.user_id
        subject = self.get_actor(subject_id)
        if viewer.permissions != "adult" and viewer.user_id != subject.user_id:
            raise PermissionError("Child-safe learning review only allows a child to view their own profile.")
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
            "profile_facts": facts,
            "pending_proposals": proposals,
            "first_light_history": first_light_history,
            "governance": {
                "can_review_all": viewer.permissions == "adult",
                "can_retire_facts": True,
                "can_approve_proposals": viewer.permissions == "adult",
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

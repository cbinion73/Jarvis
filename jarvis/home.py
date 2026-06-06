from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

from .config import AppConfig
from .persistence import append_jsonl, atomic_write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HomeStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.overrides_path = self.root / "entity_overrides.json"
        self.actions_path = self.root / "home_actions.json"
        self._log_paths = {
            self.overrides_path: self.root / "entity_overrides_log.jsonl",
            self.actions_path: self.root / "home_actions_log.jsonl",
        }
        self._state_log_paths = {
            self.overrides_path: self.root / "entity_overrides_state_log.jsonl",
            self.actions_path: self.root / "home_actions_state_log.jsonl",
        }

    def _load_json(self, path: Path, default: object) -> object:
        if not path.exists():
            return self._load_json_from_state_log(path, default)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._load_json_from_state_log(path, default)
        if payload == default:
            return self._load_json_from_state_log(path, default)
        return payload

    def _load_json_from_log(self, path: Path, default: object) -> object:
        log_path = self._log_paths[path]
        if not log_path.exists():
            return default
        latest: object = default
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                latest = payload.get("records", default)
        except (OSError, json.JSONDecodeError):
            return default
        if isinstance(default, dict):
            return dict(latest) if isinstance(latest, dict) else default
        if isinstance(default, list):
            return [dict(item) if isinstance(item, dict) else item for item in latest] if isinstance(latest, list) else default
        return latest

    def _load_json_from_state_log(self, path: Path, default: object) -> object:
        log_path = self._state_log_paths[path]
        if not log_path.exists():
            return default
        latest: object = default
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                latest = payload.get("records", default)
        except (OSError, json.JSONDecodeError):
            return default
        if isinstance(default, dict):
            return dict(latest) if isinstance(latest, dict) else default
        if isinstance(default, list):
            return [dict(item) if isinstance(item, dict) else item for item in latest] if isinstance(latest, list) else default
        return latest

    def _save_json(self, path: Path, payload: object) -> None:
        atomic_write_json(path, payload)
        append_jsonl(
            self._log_paths[path],
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )
        append_jsonl(
            self._state_log_paths[path],
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def load_overrides(self) -> dict[str, dict]:
        payload = self._load_json(self.overrides_path, {})
        return payload if isinstance(payload, dict) else {}

    def save_override(
        self,
        entity_id: str,
        state: str | None = None,
        attributes: dict | None = None,
    ) -> dict:
        overrides = self.load_overrides()
        current = dict(overrides.get(entity_id, {}))
        if state is not None:
            current["state"] = state
        if attributes:
            merged = dict(current.get("attributes", {}))
            merged.update(attributes)
            current["attributes"] = merged
        overrides[entity_id] = current
        self._save_json(self.overrides_path, overrides)
        return current

    def list_actions(self, limit: int = 20) -> list[dict]:
        payload = self._load_json(self.actions_path, [])
        records = payload if isinstance(payload, list) else []
        return list(reversed(records[-limit:]))

    def add_action(self, record: dict) -> dict:
        records = self._load_json(self.actions_path, [])
        if not isinstance(records, list):
            records = []
        records.append(record)
        self._save_json(self.actions_path, records)
        return record


class HomeAssistantAdapter:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    @property
    def live(self) -> bool:
        return bool(self.config.home_assistant_url and self.config.home_assistant_token)

    def _request(self, method: str, path: str, payload: dict | None = None) -> object:
        if not self.live:
            raise RuntimeError("Home Assistant credentials are not configured.")
        url = f"{self.config.home_assistant_url.rstrip('/')}{path}"
        body = None
        headers = {
            "Authorization": f"Bearer {self.config.home_assistant_token}",
            "Content-Type": "application/json",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=body, headers=headers, method=method.upper())
        with request.urlopen(req, timeout=8) as response:
            raw = response.read().decode("utf-8").strip()
        if not raw:
            return {}
        return json.loads(raw)

    def fetch_states(self) -> list[dict]:
        payload = self._request("GET", "/api/states")
        return payload if isinstance(payload, list) else []

    def call_service(self, domain: str, service: str, service_data: dict) -> object:
        return self._request("POST", f"/api/services/{domain}/{service}", service_data)


class HomeSupport:
    def __init__(self, config: AppConfig, store: HomeStore) -> None:
        self.config = config
        self.store = store
        self.adapter = HomeAssistantAdapter(config)
        self.profile = config.load_json_profile(
            config.home_profile_path,
            {
                "providerNotes": {},
                "scenes": [],
                "lights": [],
                "switches": [],
                "climate": [],
                "locks": [],
                "doors": [],
                "garage": [],
                "leakSensors": [],
                "coldStorage": [],
                "energyWindows": [],
                "outagePlan": {},
            },
        )

    def _profile_items(self, key: str) -> list[dict]:
        items = self.profile.get(key, [])
        return items if isinstance(items, list) else []

    def _outage_plan(self) -> dict:
        plan = self.profile.get("outagePlan", {})
        return plan if isinstance(plan, dict) else {}

    def _merge_item(self, item: dict) -> dict:
        merged = dict(item)
        merged["attributes"] = dict(item.get("attributes", {}))
        override = self.store.load_overrides().get(item.get("entityId", ""), {})
        if "state" in override:
            merged["state"] = override["state"]
        if "attributes" in override:
            merged["attributes"].update(override["attributes"])
        return merged

    def _items(self, key: str) -> list[dict]:
        return [self._merge_item(item) for item in self._profile_items(key)]

    def _find_item(self, key: str, target: str) -> dict | None:
        lowered = target.strip().lower()
        for item in self._items(key):
            fields = [
                item.get("entityId", ""),
                item.get("name", ""),
                item.get("room", ""),
                item.get("zone", ""),
                item.get("location", ""),
            ]
            if any(lowered == str(field).strip().lower() for field in fields if field):
                return item
        for item in self._items(key):
            fields = [
                item.get("entityId", ""),
                item.get("name", ""),
                item.get("room", ""),
                item.get("zone", ""),
                item.get("location", ""),
            ]
            if any(lowered in str(field).strip().lower() for field in fields if field):
                return item
        return None

    def _log_action(
        self,
        actor: str,
        category: str,
        target: str,
        action: str,
        outcome: str,
        detail: str,
        live_attempted: bool,
    ) -> dict:
        record = {
            "action_id": str(uuid.uuid4()),
            "actor": actor,
            "category": category,
            "target": target,
            "action": action,
            "outcome": outcome,
            "detail": detail,
            "live_attempted": live_attempted,
            "timestamp": _now_iso(),
        }
        return self.store.add_action(record)

    def _call_service(
        self,
        actor: str,
        category: str,
        target: str,
        domain: str,
        service: str,
        service_data: dict,
        fallback_state: str | None = None,
        fallback_attributes: dict | None = None,
    ) -> dict:
        live_attempted = False
        if self.adapter.live:
            try:
                live_attempted = True
                response = self.adapter.call_service(domain, service, service_data)
                if target:
                    self.store.save_override(target, fallback_state, fallback_attributes)
                action = self._log_action(
                    actor,
                    category,
                    target,
                    f"{domain}.{service}",
                    "live",
                    f"Live Home Assistant service call succeeded for {target or service_data.get('entity_id', '')}.",
                    live_attempted,
                )
                return {
                    "mode": "live",
                    "service_response": response,
                    "action": action,
                }
            except Exception as exc:  # pragma: no cover - exercised only with live HA configured
                detail = f"Live Home Assistant call failed, using local simulation instead: {exc}"
                action = self._log_action(actor, category, target, f"{domain}.{service}", "fallback", detail, True)
                if target:
                    self.store.save_override(target, fallback_state, fallback_attributes)
                return {"mode": "fallback", "service_response": {"error": str(exc)}, "action": action}
        if target:
            self.store.save_override(target, fallback_state, fallback_attributes)
        action = self._log_action(
            actor,
            category,
            target,
            f"{domain}.{service}",
            "simulated",
            "No live Home Assistant credentials are configured, so the change was staged locally.",
            live_attempted,
        )
        return {"mode": "simulated", "service_response": {}, "action": action}

    def home_overview(self) -> dict:
        lights = self._items("lights")
        switches = self._items("switches")
        climate = self._items("climate")
        locks = self._items("locks")
        doors = self._items("doors")
        garage = self._items("garage")
        leaks = self._items("leakSensors")
        cold_storage = self._items("coldStorage")
        outage = self._outage_plan()
        active_lights = [item["name"] for item in lights if item.get("state") == "on"]
        active_switches = [item["name"] for item in switches if item.get("state") == "on"]
        open_locks = [item["name"] for item in locks if item.get("state") in {"unlocked", "open"}]
        open_garages = [item["name"] for item in garage if item.get("state") != "closed"]
        active_leaks = [item for item in leaks if item.get("state") not in {"dry", "clear", "off"}]
        active_cold_storage = [item for item in cold_storage if self._cold_storage_severity(item) != "stable"]
        return {
            "mode": "live" if self.adapter.live else "profile-backed",
            "provider_notes": self.profile.get("providerNotes", {}),
            "counts": {
                "lights_on": len(active_lights),
                "outlets_on": len(active_switches),
                "open_locks": len(open_locks),
                "garage_not_closed": len(open_garages),
                "active_leaks": len(active_leaks),
                "cold_storage_variances": len(active_cold_storage),
            },
            "lights": lights,
            "switches": switches,
            "climate": climate,
            "locks": locks,
            "doors": doors,
            "garage": garage,
            "leaks": leaks,
            "cold_storage": self.cold_storage_monitor(),
            "energy_windows": self._profile_items("energyWindows"),
            "outage_plan": outage,
            "summary": [
                f"Lights on: {', '.join(active_lights) if active_lights else 'none'}",
                f"Active outlets: {', '.join(active_switches) if active_switches else 'none'}",
                f"Garage open: {', '.join(open_garages) if open_garages else 'none'}",
                f"Leak watch: {', '.join(item.get('name', 'unknown') for item in active_leaks) if active_leaks else 'clear'}",
                f"Cold storage: {', '.join(item.get('name', 'unknown') for item in active_cold_storage) if active_cold_storage else 'stable'}",
            ],
            "recent_actions": self.store.list_actions(limit=8),
        }

    def room_scene(self, actor: str, room: str, scene_name: str, intent: str = "") -> dict:
        room_lower = room.strip().lower()
        scene_lower = scene_name.strip().lower()
        matching_scene = None
        for scene in self._profile_items("scenes"):
            if scene.get("room", "").strip().lower() != room_lower:
                continue
            tokens = [scene.get("id", ""), scene.get("name", "")]
            if any(scene_lower == str(token).strip().lower() for token in tokens if token):
                matching_scene = scene
                break
        if matching_scene is None:
            for scene in self._profile_items("scenes"):
                if scene.get("room", "").strip().lower() != room_lower:
                    continue
                tokens = [scene.get("id", ""), scene.get("name", "")]
                if any(scene_lower in str(token).strip().lower() for token in tokens if token):
                    matching_scene = scene
                    break
        room_lights = [item for item in self._items("lights") if item.get("room", "").strip().lower() == room_lower]
        room_switches = [item for item in self._items("switches") if item.get("room", "").strip().lower() == room_lower]
        if matching_scene is None and not room_lights and not room_switches:
            raise ValueError(f"No scene or controllable entities found for room '{room}'.")

        desired_state = (matching_scene or {}).get("desiredState", "on")
        brightness = (matching_scene or {}).get("brightnessPercent")
        color_temp = (matching_scene or {}).get("colorTemp")
        affected_entities = list((matching_scene or {}).get("affects", []))
        if not affected_entities:
            affected_entities = [item["entityId"] for item in room_lights + room_switches]

        live_result = {"mode": "simulated", "service_response": {}, "action": None}
        if matching_scene and matching_scene.get("entityId"):
            live_result = self._call_service(
                actor,
                "scene",
                matching_scene["entityId"],
                "scene",
                "turn_on",
                {"entity_id": matching_scene["entityId"]},
            )
        else:
            for entity_id in affected_entities:
                target = self._find_item("lights", entity_id) or self._find_item("switches", entity_id)
                if target is None:
                    continue
                domain = "light" if target in room_lights or entity_id.startswith("light.") else "switch"
                attrs = {}
                if brightness is not None:
                    attrs["brightnessPercent"] = brightness
                if color_temp:
                    attrs["colorTemp"] = color_temp
                self._call_service(
                    actor,
                    "scene",
                    entity_id,
                    domain,
                    "turn_on" if desired_state == "on" else "turn_off",
                    {"entity_id": entity_id},
                    fallback_state=desired_state,
                    fallback_attributes=attrs,
                )

        for entity_id in affected_entities:
            attrs = {}
            if brightness is not None:
                attrs["brightnessPercent"] = brightness
            if color_temp:
                attrs["colorTemp"] = color_temp
            self.store.save_override(entity_id, desired_state, attrs or None)

        return {
            "room": room,
            "scene": matching_scene.get("name", scene_name) if matching_scene else scene_name,
            "intent": intent,
            "desired_state": desired_state,
            "brightness_percent": brightness,
            "color_temp": color_temp,
            "affected_entities": affected_entities,
            "mode": live_result["mode"],
            "note": (matching_scene or {}).get("note", ""),
        }

    def climate_status(self) -> list[dict]:
        return self._items("climate")

    def climate_control(
        self,
        actor: str,
        zone: str,
        hvac_mode: str,
        target_temperature: float | None = None,
        context: str = "",
    ) -> dict:
        item = self._find_item("climate", zone)
        if item is None:
            raise ValueError(f"No climate entity matched '{zone}'.")
        service_payload = {"entity_id": item["entityId"], "hvac_mode": hvac_mode}
        result = self._call_service(
            actor,
            "climate",
            item["entityId"],
            "climate",
            "set_hvac_mode",
            service_payload,
            fallback_state=hvac_mode,
            fallback_attributes={"hvacMode": hvac_mode},
        )
        attrs = {"hvacMode": hvac_mode}
        if target_temperature is not None:
            self._call_service(
                actor,
                "climate",
                item["entityId"],
                "climate",
                "set_temperature",
                {"entity_id": item["entityId"], "temperature": target_temperature},
                fallback_state=hvac_mode,
                fallback_attributes={"targetTemperature": target_temperature, "hvacMode": hvac_mode},
            )
            attrs["targetTemperature"] = target_temperature
        self.store.save_override(item["entityId"], hvac_mode, attrs)
        updated = self._merge_item(item)
        return {
            "zone": item.get("zone", item.get("name", zone)),
            "entity_id": item["entityId"],
            "mode": result["mode"],
            "context": context,
            "climate": updated,
        }

    def access_overview(self) -> dict:
        return {
            "locks": self._items("locks"),
            "doors": self._items("doors"),
        }

    def access_control(self, actor: str, target: str, desired_state: str) -> dict:
        item = self._find_item("locks", target)
        category = "lock"
        domain = "lock"
        service = "lock" if desired_state == "locked" else "unlock"
        if item is None:
            item = self._find_item("doors", target)
            category = "door"
            domain = "cover"
            service = "close_cover" if desired_state in {"closed", "locked"} else "open_cover"
        if item is None:
            raise ValueError(f"No lock or door matched '{target}'.")
        result = self._call_service(
            actor,
            category,
            item["entityId"],
            domain,
            service,
            {"entity_id": item["entityId"]},
            fallback_state=desired_state,
        )
        self.store.save_override(item["entityId"], desired_state)
        updated = self._merge_item(item)
        return {
            "target": item.get("name", target),
            "entity_id": item["entityId"],
            "desired_state": desired_state,
            "mode": result["mode"],
            "entity": updated,
        }

    def garage_status(self) -> list[dict]:
        return self._items("garage")

    def garage_safe_close(self, actor: str, target: str = "") -> dict:
        item = self._find_item("garage", target) if target else None
        if item is None:
            garages = self._items("garage")
            if not garages:
                raise ValueError("No garage entity is configured.")
            item = garages[0]
        attrs = item.get("attributes", {})
        blockers = []
        checks = {
            "interiorDoorClosed": "interior door is still open",
            "vehicleClear": "vehicle path is not clear",
            "dogClear": "dog is still in the garage path",
            "motionClear": "recent motion still needs review",
        }
        for key, label in checks.items():
            if attrs.get(key) is False:
                blockers.append(label)
        safe_to_close = not blockers
        mode = "simulated"
        if safe_to_close:
            result = self._call_service(
                actor,
                "garage",
                item["entityId"],
                "cover",
                "close_cover",
                {"entity_id": item["entityId"]},
                fallback_state="closed",
                fallback_attributes={"lastSafeClose": _now_iso()},
            )
            mode = result["mode"]
            self.store.save_override(item["entityId"], "closed", {"lastSafeClose": _now_iso()})
        else:
            self._log_action(
                actor,
                "garage",
                item["entityId"],
                "safe-close-check",
                "blocked",
                "; ".join(blockers),
                False,
            )
        updated = self._merge_item(item)
        return {
            "target": item.get("name", "garage"),
            "entity_id": item["entityId"],
            "safe_to_close": safe_to_close,
            "blockers": blockers,
            "mode": mode,
            "garage": updated,
        }

    def leak_monitor(self) -> dict:
        leaks = self._items("leakSensors")
        active = [item for item in leaks if item.get("state") not in {"dry", "clear", "off"}]
        return {
            "mode": "live" if self.adapter.live else "profile-backed",
            "status": "alert" if active else "clear",
            "active_count": len(active),
            "active_sensors": active,
            "all_sensors": leaks,
            "recommended_action": (
                "Check the active leak sources immediately and confirm containment."
                if active
                else "No active leak alerts in the staged house profile."
            ),
        }

    def _cold_storage_severity(self, item: dict) -> str:
        attrs = item.get("attributes", {})
        variance = float(attrs.get("varianceDegrees", 0) or 0)
        warn = float(attrs.get("varianceAlertThreshold", 3) or 3)
        critical = float(attrs.get("criticalThreshold", warn + 2) or (warn + 2))
        if abs(variance) >= critical:
            return "critical"
        if abs(variance) >= warn:
            return "elevated"
        return "stable"

    def cold_storage_monitor(self) -> dict:
        sensors = self._items("coldStorage")
        reviewed = []
        elevated = []
        for item in sensors:
            attrs = item.get("attributes", {})
            severity = self._cold_storage_severity(item)
            reviewed_item = {
                "entityId": item.get("entityId", ""),
                "name": item.get("name", ""),
                "location": item.get("location", ""),
                "provider": item.get("provider", ""),
                "state": item.get("state", ""),
                "severity": severity,
                "current_temperature": attrs.get("currentTemperature"),
                "baseline_temperature": attrs.get("baselineTemperature"),
                "variance_degrees": attrs.get("varianceDegrees", 0),
                "safe_range": attrs.get("safeRange", ""),
                "recommended_action": attrs.get("recommendedAction", ""),
                "last_checked": attrs.get("lastChecked", ""),
            }
            reviewed.append(reviewed_item)
            if severity != "stable":
                elevated.append(reviewed_item)
        return {
            "mode": "live" if self.adapter.live else "profile-backed",
            "status": "alert" if any(item["severity"] == "critical" for item in elevated) else ("watch" if elevated else "stable"),
            "active_count": len(elevated),
            "active_sensors": elevated,
            "all_sensors": reviewed,
            "recommended_action": (
                "Inspect airflow, seals, and loading immediately on the affected freezer or fridge."
                if elevated
                else "Cold-storage readings are within the staged variance envelope."
            ),
        }

    def energy_window(self, appliance: str, request_text: str = "") -> dict:
        lowered = appliance.strip().lower()
        choice = None
        for item in self._profile_items("energyWindows"):
            if lowered == str(item.get("appliance", "")).strip().lower():
                choice = item
                break
        if choice is None:
            for item in self._profile_items("energyWindows"):
                if lowered in str(item.get("appliance", "")).strip().lower():
                    choice = item
                    break
        if choice is None:
            raise ValueError(f"No energy window matched '{appliance}'.")
        return {
            "appliance": choice.get("appliance", appliance),
            "preferred_window": choice.get("preferredWindow", ""),
            "fallback_window": choice.get("fallbackWindow", ""),
            "reason": choice.get("reason", ""),
            "request": request_text,
            "recommendation": (
                f"Run {choice.get('appliance', appliance)} during {choice.get('preferredWindow', 'the preferred window')} "
                f"to align with the staged lower-cost period."
            ),
        }

    def outage_readiness(self) -> dict:
        plan = self._outage_plan()
        return {
            "status": "resilient" if plan else "undefined",
            "critical_loads": plan.get("criticalLoads", []),
            "minimum_runtime_minutes": plan.get("minimumRuntimeMinutes", 0),
            "degrade_order": plan.get("degradeOrder", []),
            "manual_fallbacks": plan.get("manualFallbacks", []),
            "network_segments": plan.get("networkSegments", []),
            "remote_access": plan.get("remoteAccess", "VPN only"),
            "mode": "live" if self.adapter.live else "profile-backed",
        }

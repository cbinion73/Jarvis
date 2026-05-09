from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PerceptionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.microphone_events_path = self.root / "microphone_events.json"
        self.presence_events_path = self.root / "presence_events.json"
        self.phone_events_path = self.root / "phone_presence_events.json"
        self.camera_events_path = self.root / "camera_events.json"
        self.object_events_path = self.root / "object_events.json"
        self.anomalies_path = self.root / "environmental_anomalies.json"
        self.package_rules_path = self.root / "package_rules.json"
        self.privacy_state_path = self.root / "privacy_state.json"

    def _load_json(self, path: Path, default: object) -> object:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_json(self, path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def append_record(self, path: Path, record: dict) -> dict:
        payload = self._load_json(path, [])
        records = payload if isinstance(payload, list) else []
        records.append(record)
        self._save_json(path, records)
        return record

    def list_records(self, path: Path, limit: int = 20) -> list[dict]:
        payload = self._load_json(path, [])
        records = payload if isinstance(payload, list) else []
        return list(reversed(records[-limit:]))

    def load_privacy_state(self) -> dict:
        payload = self._load_json(self.privacy_state_path, {})
        return payload if isinstance(payload, dict) else {}

    def save_privacy_state(self, payload: dict) -> dict:
        self._save_json(self.privacy_state_path, payload)
        return payload

    def load_package_rules(self) -> list[dict]:
        payload = self._load_json(self.package_rules_path, [])
        return payload if isinstance(payload, list) else []

    def save_package_rules(self, payload: list[dict]) -> list[dict]:
        self._save_json(self.package_rules_path, payload)
        return payload


class PerceptionSupport:
    def __init__(self, config: AppConfig, store: PerceptionStore) -> None:
        self.config = config
        self.store = store
        self.profile = config.load_json_profile(
            config.perception_profile_path,
            {
                "microphones": [],
                "presenceSensors": [],
                "phonePresence": [],
                "cameras": [],
                "packageRules": [],
                "objectVocabulary": [],
                "anomalyBaselines": [],
                "privacyZones": [],
                "privacyDefaults": {},
            },
        )
        if not self.store.load_package_rules():
            self.store.save_package_rules(self.profile.get("packageRules", []))
        if not self.store.load_privacy_state():
            defaults = self.profile.get("privacyDefaults", {})
            cameras = {}
            microphones = {}
            for item in self.profile.get("cameras", []):
                cameras[item["id"]] = {
                    "enabled": bool(item.get("enabledByDefault", True)),
                    "indicator": item.get("indicator", "led"),
                    "zone": item.get("zone", ""),
                }
            for item in self.profile.get("microphones", []):
                microphones[item["id"]] = {
                    "muted": bool(item.get("mutedByDefault", False)),
                    "indicator": item.get("indicator", "led"),
                    "zone": item.get("room", ""),
                }
            self.store.save_privacy_state(
                {
                    "cameras": cameras,
                    "microphones": microphones,
                    "physicalMuteRequired": bool(defaults.get("physicalMuteRequired", True)),
                    "sensitiveZones": defaults.get("sensitiveZones", []),
                    "lastUpdated": _now_iso(),
                }
            )

    def _profile_items(self, key: str) -> list[dict]:
        items = self.profile.get(key, [])
        return items if isinstance(items, list) else []

    def _find_profile_item(self, key: str, target: str) -> dict | None:
        lowered = target.strip().lower()
        for item in self._profile_items(key):
            for field in ("id", "name", "room", "zone", "deviceName", "actor"):
                value = str(item.get(field, "")).strip().lower()
                if value and lowered == value:
                    return item
        for item in self._profile_items(key):
            for field in ("id", "name", "room", "zone", "deviceName", "actor"):
                value = str(item.get(field, "")).strip().lower()
                if value and lowered in value:
                    return item
        return None

    def far_field_microphone_ingress(
        self,
        microphone: str,
        transcript: str,
        wake_word_detected: bool = False,
        actor_hint: str = "",
    ) -> dict:
        mic = self._find_profile_item("microphones", microphone)
        record = {
            "event_id": str(uuid.uuid4()),
            "microphone": microphone,
            "microphone_id": mic.get("id", microphone) if mic else microphone,
            "room": mic.get("room", "unknown") if mic else "unknown",
            "device_name": mic.get("deviceName", "") if mic else "",
            "actor_hint": actor_hint or (mic.get("defaultSpeaker", "") if mic else ""),
            "transcript": transcript,
            "wake_word_detected": wake_word_detected,
            "ingress_type": "far-field",
            "timestamp": _now_iso(),
        }
        return self.store.append_record(self.store.microphone_events_path, record)

    def presence_sensor_update(self, sensor: str, room: str, occupied: bool, detail: str = "") -> dict:
        profile = self._find_profile_item("presenceSensors", sensor) or self._find_profile_item("presenceSensors", room)
        record = {
            "event_id": str(uuid.uuid4()),
            "sensor": sensor,
            "sensor_id": profile.get("id", sensor) if profile else sensor,
            "room": room or (profile.get("room", "unknown") if profile else "unknown"),
            "occupied": occupied,
            "detail": detail,
            "timestamp": _now_iso(),
        }
        return self.store.append_record(self.store.presence_events_path, record)

    def phone_presence_update(self, actor: str, device: str, state: str, zone: str = "", detail: str = "") -> dict:
        profile = self._find_profile_item("phonePresence", actor) or self._find_profile_item("phonePresence", device)
        record = {
            "event_id": str(uuid.uuid4()),
            "actor": actor,
            "device": device or (profile.get("device", "") if profile else ""),
            "state": state,
            "zone": zone or (profile.get("homeZone", "unknown") if profile else "unknown"),
            "detail": detail,
            "timestamp": _now_iso(),
        }
        return self.store.append_record(self.store.phone_events_path, record)

    def camera_event(
        self,
        camera: str,
        event_type: str,
        detail: str,
        detected_object: str = "",
        confidence: str = "medium",
    ) -> dict:
        profile = self._find_profile_item("cameras", camera)
        camera_id = profile.get("id", camera) if profile else camera
        zone = profile.get("zone", "unknown") if profile else "unknown"
        privacy = self.store.load_privacy_state()
        camera_privacy = privacy.get("cameras", {}).get(camera_id, {})
        record = {
            "event_id": str(uuid.uuid4()),
            "camera": camera,
            "camera_id": camera_id,
            "zone": zone,
            "event_type": event_type,
            "detail": detail,
            "detected_object": detected_object,
            "confidence": confidence,
            "privacy_enabled": camera_privacy.get("enabled", True),
            "timestamp": _now_iso(),
        }
        saved = self.store.append_record(self.store.camera_events_path, record)
        if detected_object:
            self._object_recognition_from_camera(camera_id, zone, detected_object, detail, confidence)
        return saved

    def update_package_rule(
        self,
        zone: str,
        preferred_drop: str,
        rain_sensitive: bool,
        note: str = "",
    ) -> dict:
        rules = self.store.load_package_rules()
        lowered = zone.strip().lower()
        updated = None
        for rule in rules:
            if str(rule.get("zone", "")).strip().lower() == lowered:
                rule["preferredDrop"] = preferred_drop
                rule["rainSensitive"] = rain_sensitive
                rule["note"] = note
                rule["updatedAt"] = _now_iso()
                updated = rule
                break
        if updated is None:
            updated = {
                "zone": zone,
                "preferredDrop": preferred_drop,
                "rainSensitive": rain_sensitive,
                "note": note,
                "updatedAt": _now_iso(),
            }
            rules.append(updated)
        self.store.save_package_rules(rules)
        return updated

    def object_recognition(
        self,
        source: str,
        room: str,
        observed_object: str,
        detail: str = "",
        confidence: str = "medium",
    ) -> dict:
        label = self._normalize_object(observed_object)
        record = {
            "event_id": str(uuid.uuid4()),
            "source": source,
            "room": room,
            "observed_object": observed_object,
            "normalized_label": label,
            "detail": detail,
            "confidence": confidence,
            "recognized_as_workshop_part": room == "workshop" or source.startswith("workshop"),
            "timestamp": _now_iso(),
        }
        return self.store.append_record(self.store.object_events_path, record)

    def _object_recognition_from_camera(
        self,
        camera_id: str,
        zone: str,
        detected_object: str,
        detail: str,
        confidence: str,
    ) -> dict:
        return self.object_recognition(camera_id, "workshop" if "workshop" in zone else zone, detected_object, detail, confidence)

    def environmental_anomaly(
        self,
        category: str,
        source: str,
        reading: str,
        baseline: str,
        severity: str = "watch",
        detail: str = "",
    ) -> dict:
        recommendation = {
            "freezer": "Check seal, airflow, and the last door-open interval.",
            "weather": "Adjust timing plans and backup routes instead of overreacting.",
            "motion": "Compare against expected arrivals before escalating.",
            "network": "Prefer local-first controls until the network settles.",
        }.get(category.lower(), "Review the reading against the household baseline.")
        record = {
            "event_id": str(uuid.uuid4()),
            "category": category,
            "source": source,
            "reading": reading,
            "baseline": baseline,
            "severity": severity,
            "detail": detail,
            "recommendation": recommendation,
            "timestamp": _now_iso(),
        }
        return self.store.append_record(self.store.anomalies_path, record)

    def privacy_state(self) -> dict:
        state = self.store.load_privacy_state()
        state["lastCameraEvents"] = self.store.list_records(self.store.camera_events_path, limit=6)
        state["lastMicrophoneEvents"] = self.store.list_records(self.store.microphone_events_path, limit=6)
        return state

    def update_privacy_state(
        self,
        kind: str,
        target: str,
        enabled: bool | None = None,
        muted: bool | None = None,
    ) -> dict:
        state = self.store.load_privacy_state()
        if kind == "camera":
            cameras = state.setdefault("cameras", {})
            item = dict(cameras.get(target, {}))
            if enabled is not None:
                item["enabled"] = enabled
            cameras[target] = item
        elif kind == "microphone":
            microphones = state.setdefault("microphones", {})
            item = dict(microphones.get(target, {}))
            if muted is not None:
                item["muted"] = muted
            microphones[target] = item
        else:
            raise ValueError("kind must be 'camera' or 'microphone'")
        state["lastUpdated"] = _now_iso()
        return self.store.save_privacy_state(state)

    def perception_overview(self) -> dict:
        presence_events = self.store.list_records(self.store.presence_events_path, limit=50)
        phone_events = self.store.list_records(self.store.phone_events_path, limit=50)
        camera_events = self.store.list_records(self.store.camera_events_path, limit=20)
        object_events = self.store.list_records(self.store.object_events_path, limit=20)
        anomalies = self.store.list_records(self.store.anomalies_path, limit=20)
        mics = self.store.list_records(self.store.microphone_events_path, limit=20)
        room_presence: dict[str, bool] = {}
        for event in reversed(presence_events):
            room_presence[event["room"]] = bool(event["occupied"])
        actor_presence: dict[str, str] = {}
        for event in reversed(phone_events):
            actor_presence[event["actor"]] = event["state"]
        package_rules = self.store.load_package_rules()
        workshop_objects = [item for item in object_events if item.get("room") == "workshop"]
        privacy = self.privacy_state()
        return {
            "microphone_events": mics[:8],
            "presence_events": presence_events[:8],
            "phone_presence": phone_events[:8],
            "camera_events": camera_events[:8],
            "package_rules": package_rules,
            "object_events": object_events[:8],
            "workshop_objects": workshop_objects[:6],
            "anomalies": anomalies[:8],
            "room_presence": room_presence,
            "actor_presence": actor_presence,
            "privacy_state": privacy,
            "summary": [
                f"Occupied rooms: {', '.join([room for room, occupied in room_presence.items() if occupied]) or 'none'}",
                f"Recently heard via microphones: {mics[0]['room'] if mics else 'none'}",
                f"Recent camera zones: {', '.join(dict.fromkeys(item['zone'] for item in camera_events if item.get('zone'))) or 'none'}",
                f"Active anomalies: {len([item for item in anomalies if item.get('severity') in {'elevated', 'critical'}])}",
            ],
        }

    def _normalize_object(self, observed_object: str) -> str:
        lowered = observed_object.strip().lower()
        for item in self._profile_items("objectVocabulary"):
            label = str(item.get("label", "")).strip().lower()
            synonyms = [str(s).strip().lower() for s in item.get("synonyms", [])]
            if lowered == label or lowered in synonyms:
                return item.get("label", observed_object)
        return observed_object

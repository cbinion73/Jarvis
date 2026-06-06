"""
kasa_bridge.py — TP-Link Kasa smart device integration for JARVIS
Uses python-kasa (0.10+) async API via asyncio.run() wrappers for sync service calls.

EC70 Camera notes:
  - Discovered via UDP broadcast on port 9999 (same as other Kasa devices)
  - Controlled via HTTPS on port 10443 using LinkieTransportV2
  - Auth: Basic HTTP auth with email:password (Kasa cloud credentials)
    NOT the default admin:md5(admin) hardcoded in python-kasa
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

logger = logging.getLogger(__name__)

# ── Cache config ────────────────────────────────────────────────────────────
_DEVICE_CACHE_TTL = 30          # seconds — devices list (short: state changes)
_DISCOVERY_CACHE_TTL = 300      # seconds — full discovery scan (expensive)
_SCENES_PATH = Path("data/settings/kasa_scenes.json")
_SCENES_LOG_PATH = _SCENES_PATH.with_name("kasa_scenes_log.jsonl")
_SCENES_STATE_LOG_PATH = _SCENES_PATH.with_name("kasa_scenes_state_log.jsonl")

# ── Stream config ────────────────────────────────────────────────────────────
_STREAM_HLS_DIR = Path("data/camera_hls")
_STREAM_HLS_DIR.mkdir(parents=True, exist_ok=True)

# ── Default scenes ──────────────────────────────────────────────────────────
DEFAULT_SCENES: list[dict] = [
    {
        "id": "all_off",
        "name": "All Off",
        "icon": "🌑",
        "actions": [{"match": "*", "state": False}],
    },
    {
        "id": "all_on",
        "name": "All On",
        "icon": "☀️",
        "actions": [{"match": "*", "state": True}],
    },
    {
        "id": "movie",
        "name": "Movie Mode",
        "icon": "🎬",
        "actions": [{"match": "*", "state": True, "brightness": 20}],
    },
    {
        "id": "bedtime",
        "name": "Bedtime",
        "icon": "🌙",
        "actions": [{"match": "*", "state": True, "brightness": 10, "color_temp": 2700}],
    },
    {
        "id": "morning",
        "name": "Morning",
        "icon": "🌅",
        "actions": [{"match": "*", "state": True, "brightness": 80, "color_temp": 4000}],
    },
]


# ── Room grouping heuristics ─────────────────────────────────────────────────
ROOM_KEYWORDS: dict[str, list[str]] = {
    "Living Room":  ["living", "lounge", "couch", "sofa", "tv", "television"],
    "Family Room":  ["family room", "family"],
    "Bedroom":      ["bed", "master", "sleep"],
    "Office":       ["office", "desk", "study", "work"],
    "Kitchen":      ["kitchen", "counter", "pantry"],
    "Bathroom":     ["bath", "shower", "vanity"],
    "Garage":       ["garage", "shop"],
    "Outdoor":      ["outdoor", "outside", "porch", "patio", "yard", "front", "back"],
    "Kids Room":    ["kids", "child", "nursery", "playroom"],
    "Dining":       ["dining", "eat"],
    "Hallway":      ["hall", "entry", "foyer", "stair"],
}


def _infer_room(alias: str) -> str:
    name_lower = alias.lower()
    for room, keywords in ROOM_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return room
    return "Other"


def _load_scenes() -> list[dict]:
    if _SCENES_PATH.exists():
        try:
            return json.loads(_SCENES_PATH.read_text(encoding="utf-8"))
        except Exception:
            return _load_scenes_from_state_log() or _load_scenes_from_log()
    if not _SCENES_PATH.exists():
        return _load_scenes_from_state_log() or _load_scenes_from_log()
    return DEFAULT_SCENES


def _load_scenes_from_log() -> list[dict]:
    if _SCENES_LOG_PATH.exists():
        try:
            latest: list[dict] = []
            for line in _SCENES_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
            if latest:
                return latest
        except Exception:
            pass
    return DEFAULT_SCENES


def _load_scenes_from_state_log() -> list[dict]:
    if _SCENES_STATE_LOG_PATH.exists():
        try:
            latest: list[dict] = []
            for line in _SCENES_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
            if latest:
                return latest
        except Exception:
            pass
    return []


def _save_scenes(scenes: list[dict]) -> None:
    _SCENES_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(_SCENES_PATH, scenes)
    append_jsonl(
        _SCENES_LOG_PATH,
        {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "records": scenes,
        },
    )
    append_jsonl(
        _SCENES_STATE_LOG_PATH,
        {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "records": scenes,
        },
    )


# ── Bridge class ─────────────────────────────────────────────────────────────
class KasaBridge:
    """Thread-safe wrapper around python-kasa async API."""

    def __init__(self, username: str = "", password: str = "") -> None:
        self.username = username
        self.password = password
        self._lock = threading.Lock()
        self._devices: dict[str, Any] = {}          # ip → kasa Device
        self._device_cache: dict = {}               # serialized payload
        self._device_cache_ts: float = 0.0
        self._discovery_ts: float = 0.0
        self._stream_procs: dict[str, Any] = {}     # camera_id → subprocess.Popen

    # ── Internal async helpers ──────────────────────────────────────────────

    def _run(self, coro):
        """Run a coroutine synchronously (creates a new event loop each call)."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _discover_async(self) -> dict:
        """Full network discovery — expensive, TTL = 5 min.
        Patches python-kasa to handle Camera device type (EC70) without crashing.
        """
        from kasa import Discover, Credentials
        import kasa.discover as _kd
        from kasa.iot.iotplug import IotPlug

        # EC70 cameras respond to discovery but python-kasa 0.10 throws KeyError
        # on DeviceType.Camera. Patch to use IotPlug as a stand-in so the device
        # is included in the results dict — we handle it separately.
        _orig_cls = _kd.Discover._get_device_class
        def _patched_cls(info):
            try:
                return _orig_cls(info)
            except KeyError:
                return IotPlug  # camera stand-in
        _kd.Discover._get_device_class = staticmethod(_patched_cls)

        try:
            kwargs: dict = {"discovery_timeout": 6, "discovery_packets": 3}
            if self.username and self.password:
                kwargs["credentials"] = Credentials(self.username, self.password)
            found = await Discover.discover(**kwargs)
        finally:
            _kd.Discover._get_device_class = staticmethod(_orig_cls)

        # Identify cameras by type from internal _last_update data
        for ip, dev in list(found.items()):
            try:
                lu = dev._last_update or {}
                si = lu.get("system", {}).get("get_sysinfo", {})
                if not si:
                    # Camera responded but sysinfo didn't come through normally
                    # Mark it so _serialize_device can handle it
                    dev._kasa_is_camera = True
                    dev._kasa_camera_ip = ip
            except Exception:
                pass

        return found  # {ip: Device}

    async def _update_device(self, device) -> None:
        if getattr(device, "_kasa_is_camera", False):
            return  # camera has its own update path
        try:
            await device.update()
        except Exception as exc:
            logger.debug("device update failed for %s: %s", getattr(device, "host", "?"), exc)

    async def _query_camera(self, ip: str) -> dict:
        """Query EC70 camera via LinkieTransportV2 + user credentials."""
        from kasa import DeviceConfig, DeviceConnectionParameters, DeviceFamily, DeviceEncryptionType
        from kasa.transports.linkietransport import LinkieTransportV2
        from kasa.protocols.iotprotocol import IotProtocol

        cred_str = f"{self.username}:{self.password}"

        class _AuthedLinkie(LinkieTransportV2):
            @property
            def credentials_hash(self_inner):  # noqa: N805
                return base64.b64encode(cred_str.encode()).decode()

        config = DeviceConfig(
            host=ip,
            connection_type=DeviceConnectionParameters(
                device_family=DeviceFamily.IotIpCamera,
                encryption_type=DeviceEncryptionType.Xor,
                http_port=10443,
            ),
        )
        transport = _AuthedLinkie(config=config)
        protocol = IotProtocol(transport=transport)
        try:
            result = await protocol.query({"system": {"get_sysinfo": {}}})
            return result.get("system", {}).get("get_sysinfo", {}).get("system", {})
        finally:
            await transport.close()

    # ── Discovery ───────────────────────────────────────────────────────────

    def _ensure_discovered(self) -> None:
        now = time.monotonic()
        if now - self._discovery_ts < _DISCOVERY_CACHE_TTL and self._devices:
            return
        logger.info("kasa: running discovery scan…")
        try:
            found = self._run(self._discover_async())
            # Tag cameras: EC70 sysinfo has nested "system" key AND type=IOT.IPCAMERA
            for ip, dev in found.items():
                try:
                    lu = dev._last_update or {}
                    sysinfo = lu.get("system", {}).get("get_sysinfo", {})
                    # Camera has nested structure: {"get_sysinfo": {"system": {...}}}
                    dtype = (
                        sysinfo.get("type")                          # regular device
                        or sysinfo.get("system", {}).get("type")    # camera
                        or sysinfo.get("mic_type", "")
                    )
                    if "ipcamera" in dtype.lower() or "camera" in dtype.lower():
                        dev._kasa_is_camera = True
                        dev._kasa_camera_ip = ip
                    elif not sysinfo:
                        # Empty sysinfo — also likely a camera that replied but data not parsed
                        dev._kasa_is_camera = True
                        dev._kasa_camera_ip = ip
                except Exception:
                    pass
            self._devices = found
            self._discovery_ts = now
            self._device_cache_ts = 0.0  # force status refresh
            cam_count = sum(1 for d in found.values() if getattr(d, "_kasa_is_camera", False))
            logger.info("kasa: discovered %d devices (%d cameras)", len(found), cam_count)
        except Exception as exc:
            logger.warning("kasa: discovery failed: %s", exc)

    # ── Device serialization ────────────────────────────────────────────────

    def _serialize_camera(self, ip: str, si: dict) -> dict:
        """Serialize EC70 camera sysinfo into the standard device dict."""
        alias = si.get("alias", "Camera")
        return {
            "ip": ip,
            "mac": si.get("mac", ""),
            "alias": alias,
            "model": si.get("model", "EC70"),
            "device_type": "camera",
            "is_on": True,   # camera is always "on" if reachable
            "brightness": None,
            "color_temp": None,
            "hue": None,
            "saturation": None,
            "room": _infer_room(alias),
            "reachable": True,
            "sw_ver": si.get("sw_ver", ""),
        }

    def _serialize_device(self, device) -> dict:
        """Extract safe serializable dict from a kasa Device."""
        # Handle camera stand-in
        if getattr(device, "_kasa_is_camera", False):
            ip = str(getattr(device, "host", ""))
            try:
                si = self._run(self._query_camera(ip))
                if si:
                    return self._serialize_camera(ip, si)
            except Exception as exc:
                logger.debug("camera query failed %s: %s", ip, exc)
            return {
                "ip": ip, "alias": "Camera (offline)", "model": "EC70",
                "device_type": "camera", "is_on": False, "room": "Other",
                "reachable": False,
            }

        try:
            alias = getattr(device, "alias", None) or str(getattr(device, "host", "unknown"))
            is_on = False
            brightness = None
            color_temp = None
            hue = None
            saturation = None
            device_type = "switch"

            # Determine device type and capabilities
            try:
                is_on = bool(device.is_on)
            except Exception:
                pass

            # Check for dimmer/bulb capabilities
            if hasattr(device, "modules"):
                mods = device.modules
                if "Brightness" in mods or hasattr(device, "brightness"):
                    device_type = "dimmer"
                    try:
                        brightness = int(device.brightness)
                    except Exception:
                        pass
                if "ColorTemperature" in mods or hasattr(device, "color_temp"):
                    device_type = "bulb"
                    try:
                        color_temp = int(device.color_temp)
                    except Exception:
                        pass
                if "Color" in mods or hasattr(device, "hue"):
                    device_type = "color_bulb"
                    try:
                        hue = int(device.hue)
                        saturation = int(device.saturation)
                    except Exception:
                        pass

            # Fallback type detection
            cls_name = type(device).__name__.lower()
            if device_type == "switch":
                if "bulb" in cls_name:
                    device_type = "bulb"
                elif "strip" in cls_name or "power" in cls_name:
                    device_type = "strip"
                elif "plug" in cls_name:
                    device_type = "plug"

            model = getattr(device, "model", "")
            ip = str(getattr(device, "host", ""))
            mac = ""
            try:
                info = device.sys_info or {}
                mac = info.get("mac", "") or info.get("hw_id", "")
            except Exception:
                pass

            return {
                "ip": ip,
                "mac": mac,
                "alias": alias,
                "model": str(model),
                "device_type": device_type,
                "is_on": is_on,
                "brightness": brightness,
                "color_temp": color_temp,
                "hue": hue,
                "saturation": saturation,
                "room": _infer_room(alias),
                "reachable": True,
            }
        except Exception as exc:
            logger.debug("serialize_device failed: %s", exc)
            return {
                "ip": str(getattr(device, "host", "?")),
                "alias": "Unknown",
                "device_type": "switch",
                "is_on": False,
                "room": "Other",
                "reachable": False,
            }

    # ── Public API ──────────────────────────────────────────────────────────

    def get_devices(self, force_refresh: bool = False) -> dict:
        """Return cached device list with room grouping."""
        with self._lock:
            now = time.monotonic()
            if (
                not force_refresh
                and self._device_cache
                and now - self._device_cache_ts < _DEVICE_CACHE_TTL
            ):
                return self._device_cache

            self._ensure_discovered()
            if not self._devices:
                return {
                    "kasa_available": False,
                    "devices": [],
                    "rooms": {},
                    "total": 0,
                    "on_count": 0,
                    "scenes": _load_scenes(),
                }

            # Update all device states in parallel
            async def _update_all():
                await asyncio.gather(
                    *[self._update_device(d) for d in self._devices.values()],
                    return_exceptions=True,
                )

            self._run(_update_all())

            devices = [self._serialize_device(d) for d in self._devices.values()]
            devices.sort(key=lambda d: (d["room"], d["alias"]))

            rooms: dict[str, list] = {}
            for dev in devices:
                rooms.setdefault(dev["room"], []).append(dev)

            on_count = sum(1 for d in devices if d.get("is_on"))

            payload = {
                "kasa_available": True,
                "devices": devices,
                "rooms": rooms,
                "total": len(devices),
                "on_count": on_count,
                "scenes": _load_scenes(),
            }
            self._device_cache = payload
            self._device_cache_ts = now
            return payload

    def _find_device(self, ip_or_alias: str):
        """Find a device by IP or alias (case-insensitive)."""
        # Try exact IP first
        if ip_or_alias in self._devices:
            return self._devices[ip_or_alias]
        # Try alias match
        target = ip_or_alias.lower()
        for dev in self._devices.values():
            alias = (getattr(dev, "alias", "") or "").lower()
            if alias == target or alias.replace(" ", "_") == target.replace(" ", "_"):
                return dev
        return None

    def toggle_device(self, ip_or_alias: str) -> dict:
        """Toggle device on/off. Returns new state."""
        with self._lock:
            self._ensure_discovered()
            device = self._find_device(ip_or_alias)
            if device is None:
                return {"ok": False, "error": f"Device not found: {ip_or_alias}"}

            async def _toggle():
                await device.update()
                if device.is_on:
                    await device.turn_off()
                else:
                    await device.turn_on()
                await device.update()

            try:
                self._run(_toggle())
                self._device_cache_ts = 0.0  # invalidate
                return {"ok": True, "is_on": bool(device.is_on), "alias": getattr(device, "alias", "")}
            except Exception as exc:
                logger.warning("toggle_device failed %s: %s", ip_or_alias, exc)
                return {"ok": False, "error": str(exc)}

    def set_device(self, ip_or_alias: str, *, state: bool | None = None,
                   brightness: int | None = None, color_temp: int | None = None) -> dict:
        """Set device state, brightness, or color temp."""
        with self._lock:
            self._ensure_discovered()
            device = self._find_device(ip_or_alias)
            if device is None:
                return {"ok": False, "error": f"Device not found: {ip_or_alias}"}

            async def _set():
                await device.update()
                if state is True:
                    await device.turn_on()
                elif state is False:
                    await device.turn_off()
                    return  # No point setting brightness/color if turning off

                if brightness is not None and hasattr(device, "set_brightness"):
                    pct = max(1, min(100, brightness))
                    await device.set_brightness(pct)
                if color_temp is not None and hasattr(device, "set_color_temp"):
                    ct = max(2500, min(6500, color_temp))
                    await device.set_color_temp(ct)
                await device.update()

            try:
                self._run(_set())
                self._device_cache_ts = 0.0
                result = self._serialize_device(device)
                result["ok"] = True
                return result
            except Exception as exc:
                logger.warning("set_device failed %s: %s", ip_or_alias, exc)
                return {"ok": False, "error": str(exc)}

    def run_scene(self, scene_id: str) -> dict:
        """Apply a scene to matching devices."""
        scenes = _load_scenes()
        scene = next((s for s in scenes if s["id"] == scene_id), None)
        if scene is None:
            return {"ok": False, "error": f"Scene not found: {scene_id}"}

        with self._lock:
            self._ensure_discovered()
            if not self._devices:
                return {"ok": False, "error": "No devices discovered"}

            results = []
            for action in scene.get("actions", []):
                match_pattern = action.get("match", "*")
                target_state = action.get("state")
                target_brightness = action.get("brightness")
                target_color_temp = action.get("color_temp")

                for ip, device in self._devices.items():
                    alias = (getattr(device, "alias", "") or "").lower()
                    if match_pattern != "*" and match_pattern.lower() not in alias:
                        continue

                    async def _apply(dev=device):
                        await dev.update()
                        if target_state is False:
                            await dev.turn_off()
                            return
                        await dev.turn_on()
                        if target_brightness is not None and hasattr(dev, "set_brightness"):
                            await dev.set_brightness(max(1, min(100, target_brightness)))
                        if target_color_temp is not None and hasattr(dev, "set_color_temp"):
                            await dev.set_color_temp(max(2500, min(6500, target_color_temp)))

                    try:
                        self._run(_apply())
                        results.append({"ip": ip, "ok": True})
                    except Exception as exc:
                        results.append({"ip": ip, "ok": False, "error": str(exc)})

            self._device_cache_ts = 0.0
            return {"ok": True, "scene": scene["name"], "results": results}

    # ── Camera HLS streaming ────────────────────────────────────────────────

    def get_stream_url(self, ip: str) -> str:
        """Return the raw camera stream URL for a given IP."""
        u = urllib.parse.quote(self.username, safe="")
        p = urllib.parse.quote(self.password, safe="")
        return f"https://{u}:{p}@{ip}:19443/https/stream/mixed?video=h264&audio=g711"

    def start_hls_stream(self, ip: str, camera_id: str) -> dict:
        """Start an ffmpeg HLS transcoder for the camera stream.
        Returns {"ok": True, "hls_url": "/camera_hls/{camera_id}/stream.m3u8"}
        """
        import subprocess
        import time as _time

        out_dir = _STREAM_HLS_DIR / camera_id
        out_dir.mkdir(parents=True, exist_ok=True)
        m3u8 = out_dir / "stream.m3u8"

        # Kill existing process for this camera if any
        self.stop_hls_stream(camera_id)

        stream_url = self.get_stream_url(ip)
        ffmpeg_cmd = [
            "/opt/homebrew/bin/ffmpeg", "-y",
            # +genpts: generate timestamps from wall clock — required because the
            # EC70 multipart stream sends H264 NAL units with no PTS/DTS.
            "-fflags", "+genpts+nobuffer",
            "-flags", "low_delay",
            "-rtbufsize", "5M",
            "-i", stream_url,
            "-c:v", "copy",           # copy H264 — no re-encode needed
            "-an",                    # drop audio for clean HLS
            "-hls_time", "2",
            "-hls_list_size", "5",
            "-hls_flags", "delete_segments+append_list",
            "-hls_segment_filename", str(out_dir / "seg%03d.ts"),
            str(m3u8),
        ]

        try:
            proc = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._stream_procs[camera_id] = proc
            # EC70 stream needs ~4s to buffer before writing first segment
            for _ in range(24):   # up to 12s
                if m3u8.exists():
                    break
                _time.sleep(0.5)

            if m3u8.exists():
                return {"ok": True, "hls_url": f"/camera_hls/{camera_id}/stream.m3u8"}
            else:
                proc.kill()
                del self._stream_procs[camera_id]
                return {"ok": False, "error": "HLS stream did not start in time"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def stop_hls_stream(self, camera_id: str) -> None:
        """Stop the ffmpeg process for a camera stream."""
        proc = self._stream_procs.pop(camera_id, None)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    def stop_all_streams(self) -> None:
        """Stop all active HLS streams."""
        for cid in list(self._stream_procs.keys()):
            self.stop_hls_stream(cid)

    def get_scenes(self) -> list[dict]:
        return _load_scenes()

    def save_scene(self, scene: dict) -> dict:
        scenes = _load_scenes()
        existing = next((i for i, s in enumerate(scenes) if s["id"] == scene["id"]), None)
        if existing is not None:
            scenes[existing] = scene
        else:
            scenes.append(scene)
        _save_scenes(scenes)
        return {"ok": True, "scenes": scenes}

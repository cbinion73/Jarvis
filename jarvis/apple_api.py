"""
JARVIS Apple API — Epic 14
===========================
Provides the REST endpoints consumed by JarvisPhone, JarvisWatch, and JarvisMac.

All responses use a consistent envelope:
  {"ok": bool, "data": {...}, "error": str, "ts": str}

Endpoints
---------
GET  /api/apple/briefing                    Chamber home-screen packet (5 zones)
GET  /api/apple/status                      Quick status for Watch complications
GET  /api/apple/needs                       Approval queue (Needs You zone)
POST /api/apple/speak                       Text command → agent response
GET  /api/apple/health/summary              Health summary for HealthKit display
POST /api/apple/health/log                  Log HealthKit samples from iPhone
GET  /api/apple/home/state                  House state for Home tab
POST /api/apple/home/command                Issue a home command (staged for approval)
GET  /api/apple/notifications/pending       Pending notifications for APNs delivery
POST /api/apple/presence                    Phone reports user presence / location
GET  /api/apple/voice/greeting              Voice greeting for wake
POST /api/apple/approvals/{id}/approve      One-tap approval from Watch / Phone
POST /api/apple/focus                       Focus Filter state from iPhone
POST /api/apple/sound-alert                 On-device sound classification alert
POST /api/apple/vision/scan                 On-device OCR / barcode scan result
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from .nav_bridge import NavBridge, haversine, min_distance_to_route, sample_route_points
from .settings import LOCATION_SETTINGS_PATH

logger = logging.getLogger(__name__)

_NAV_STOP_LABELS = {
    "food": "Food",
    "starbucks": "Starbucks",
    "parks": "Parks",
    "historic": "Historic",
    "family": "Family",
    "gas": "Gas",
}

_US_STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ok(data: Any) -> dict:
    return {"ok": True, "data": data, "error": None, "ts": _ts()}


def _err(message: str, status: int = 400) -> tuple[dict, int]:
    return {"ok": False, "data": None, "error": message, "ts": _ts()}, status


def _nav_bridge() -> NavBridge:
    return NavBridge(
        os.getenv("GOOGLE_MAPS_API_KEY", ""),
        os.getenv("NPS_API_KEY", ""),
    )


def _nav_route_points(route_info: dict[str, Any]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for pair in list(route_info.get("coordinates") or []):
        if isinstance(pair, list) and len(pair) == 2:
            try:
                points.append((float(pair[1]), float(pair[0])))
            except (TypeError, ValueError):
                continue
    return points


def _nav_state_codes(*labels: str) -> list[str]:
    found: list[str] = []
    for label in labels:
        lowered = str(label or "").lower()
        for state_name, code in _US_STATE_CODES.items():
            if state_name in lowered and code not in found:
                found.append(code)
    return found


def _nav_nps_along_route(bridge: NavBridge, route_points: list[tuple[float, float]], states: list[str]) -> list[dict[str, Any]]:
    parks = bridge.search_nps_by_states(states)
    if not parks or not route_points:
        return []

    filtered: list[dict[str, Any]] = []
    for park in parks:
        try:
            plat = float(park.get("latitude") or 0)
            plng = float(park.get("longitude") or 0)
        except (TypeError, ValueError):
            continue
        if plat == 0 and plng == 0:
            continue
        dist = min_distance_to_route(plat, plng, route_points)
        if dist > 25.0:
            continue
        closest_idx = min(
            range(len(route_points)),
            key=lambda i: haversine(plat, plng, route_points[i][0], route_points[i][1]),
        )
        cumulative = 0.0
        for idx in range(1, closest_idx + 1):
            cumulative += haversine(
                route_points[idx - 1][0], route_points[idx - 1][1],
                route_points[idx][0], route_points[idx][1],
            )
        filtered.append(
            {
                "name": str(park.get("fullName") or ""),
                "address": str(park.get("states") or ""),
                "description": str(park.get("description") or ""),
                "url": str(park.get("url") or ""),
                "lat": plat,
                "lng": plng,
                "route_mile_marker": round(cumulative, 1),
                "distance_from_route": round(dist, 1),
                "rating": None,
            }
        )
    filtered.sort(key=lambda item: item.get("route_mile_marker") or 0)
    return filtered


# ---------------------------------------------------------------------------
# HealthSampleStore
# ---------------------------------------------------------------------------

class HealthSampleStore:
    """
    Lightweight append-only store for raw HealthKit samples.
    Samples are written as newline-delimited JSON (JSONL) to
    ~/.jarvis/health/samples.jsonl so they can be replayed or aggregated.
    """

    ROOT = Path.home() / ".jarvis" / "health"

    def _samples_path(self, actor_id: str) -> Path:
        return self.ROOT / actor_id / "samples.jsonl"

    def log_samples(self, actor_id: str, samples: list[dict]) -> int:
        """
        Append raw samples to JSONL.  Returns the number of records logged.
        Each record is enriched with a server-side received_at timestamp.
        """
        if not samples:
            return 0
        path = self._samples_path(actor_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        received_at = _ts()
        with path.open("a", encoding="utf-8") as fh:
            for sample in samples:
                row = dict(sample)
                row["received_at"] = received_at
                fh.write(json.dumps(row, default=str) + "\n")
        return len(samples)

    def _read_samples(self, actor_id: str) -> list[dict]:
        path = self._samples_path(actor_id)
        if not path.exists():
            return []
        rows: list[dict] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return rows

    def get_summary(self, actor_id: str, date: str | None = None) -> dict:
        """
        Aggregate samples for a given date (default today, YYYY-MM-DD).
        Returns a dict with keys:
          steps, heart_rate_avg, sleep_hours, active_calories, stand_hours, hrv, last_sync
        """
        target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        samples = self._read_samples(actor_id)

        steps = 0
        hr_values: list[float] = []
        sleep_hours = 0.0
        active_calories = 0
        stand_hours = 0
        hrv_values: list[float] = []
        last_sync: str | None = None

        for s in samples:
            # Match by date prefix (handles both date-only and datetime strings)
            sample_date = str(s.get("date", ""))[:10]
            if sample_date != target_date:
                continue
            sample_type = str(s.get("type", "")).lower()
            value = float(s.get("value", 0) or 0)
            if sample_type == "steps":
                steps = max(steps, int(value))
            elif sample_type in ("heart_rate", "resting_heart_rate"):
                hr_values.append(value)
            elif sample_type == "sleep":
                sleep_hours = max(sleep_hours, value)
            elif sample_type in ("active_calories", "active_energy"):
                active_calories = max(active_calories, int(value))
            elif sample_type == "stand_hours":
                stand_hours = max(stand_hours, int(value))
            elif sample_type == "hrv":
                hrv_values.append(value)
            received = s.get("received_at")
            if received and (last_sync is None or received > last_sync):
                last_sync = received

        return {
            "steps": steps,
            "heart_rate_avg": int(sum(hr_values) / len(hr_values)) if hr_values else 0,
            "sleep_hours": round(sleep_hours, 1),
            "active_calories": active_calories,
            "stand_hours": stand_hours,
            "hrv": int(sum(hrv_values) / len(hrv_values)) if hrv_values else 0,
            "last_sync": last_sync or "",
        }

    def get_recent(self, actor_id: str, sample_type: str, days: int = 7) -> list[dict]:
        """Recent samples of a given type, newest first, limited to *days* days back."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        samples = self._read_samples(actor_id)
        result = [
            s for s in samples
            if str(s.get("type", "")).lower() == sample_type.lower()
            and str(s.get("date", ""))[:10] >= cutoff
        ]
        # newest first
        result.sort(key=lambda s: str(s.get("date", "")), reverse=True)
        return result


# ---------------------------------------------------------------------------
# Pending-notification store (in-memory, cleared on delivery)
# ---------------------------------------------------------------------------

class _NotificationStore:
    def __init__(self) -> None:
        self._pending: list[dict] = []

    def push(self, title: str, body: str, category: str = "general", badge: int = 0) -> str:
        nid = str(uuid.uuid4())
        self._pending.append({
            "id": nid,
            "title": title,
            "body": body,
            "category": category,
            "badge": badge,
            "created_at": _ts(),
        })
        return nid

    def drain(self) -> list[dict]:
        items = list(self._pending)
        self._pending.clear()
        return items


_notification_store = _NotificationStore()
_health_store = HealthSampleStore()


# ---------------------------------------------------------------------------
# Greeting helpers
# ---------------------------------------------------------------------------

def _time_of_day_greeting() -> tuple[str, str]:
    """Return (greeting, mode) based on local hour."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning, Sir.", "morning"
    elif hour < 17:
        return "Good afternoon, Sir.", "afternoon"
    elif hour < 21:
        return "Good evening, Sir.", "evening"
    return "Good night, Sir.", "night"


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def _register_apple_api(app: FastAPI, runtime: Any) -> None:  # noqa: C901
    """Register all /api/apple/* routes onto *app*."""

    # ------------------------------------------------------------------
    # POST /api/apple/device/register  — store APNs device token
    # ------------------------------------------------------------------
    @app.post("/api/apple/device/register")
    async def apple_device_register(payload: dict):
        """Store an APNs device token for push notification delivery."""
        actor_id = str(payload.get("actor_id") or "chris").strip()
        token    = str(payload.get("token")    or "").strip()
        platform = str(payload.get("platform") or "ios").strip()
        if not token:
            raise HTTPException(status_code=400, detail="token is required")
        try:
            from .apns_sender import register_device_token
            register_device_token(actor_id, token, platform)
        except Exception as exc:
            logger.warning("device_register: %s", exc)
        return _ok({"registered": True})

    # ------------------------------------------------------------------
    # GET /api/apple/briefing
    # ------------------------------------------------------------------
    @app.get("/api/apple/briefing")
    async def apple_briefing(actor: str = "chris"):
        """
        Return the full 5-zone Chamber home-screen packet.
        Tries the BriefingBuilder cache first; falls back to chamber_home_snapshot.
        """
        try:
            from .scheduler import get_briefing_builder
            builder = get_briefing_builder()
        except Exception:
            builder = None

        greeting, mode = _time_of_day_greeting()

        # Attempt live briefing
        packet: dict | None = None
        if builder is not None:
            try:
                import asyncio
                cached = await asyncio.to_thread(builder.get_cached)
                if cached:
                    packet = cached
                else:
                    packet = await asyncio.to_thread(builder.build, actor)
            except Exception as exc:
                logger.warning("apple_briefing: briefing builder failed: %s", exc)

        # Fallback: chamber_home_snapshot
        if packet is None:
            try:
                import asyncio
                packet = await asyncio.to_thread(runtime.chamber_home_snapshot, actor)
            except Exception as exc:
                logger.warning("apple_briefing: chamber_home_snapshot failed: %s", exc)
                packet = {}

        # Normalise into the Apple briefing shape expected by Swift BriefingModels
        raw_briefing  = packet.get("briefing_items")  or packet.get("feed",        [])
        raw_working   = packet.get("working_items")   or packet.get("in_progress", [])
        raw_needs     = packet.get("needs_items")     or packet.get("needs_you",   [])
        raw_drift     = packet.get("drift_items")     or packet.get("drift",       [])

        data = {
            "briefing_items": [
                _normalise_briefing_item(i)
                for i in raw_briefing
                if isinstance(i, dict) and _is_live_apple_item(i, zone="briefing")
            ],
            "working_items":  [
                _normalise_working_item(i)
                for i in raw_working
                if isinstance(i, dict) and _is_live_apple_item(i, zone="working")
            ],
            "needs_items":    [
                _normalise_needs_item(i)
                for i in raw_needs
                if isinstance(i, dict) and _is_live_apple_item(i, zone="needs")
            ],
            "drift_items":    [
                _normalise_drift_item(i)
                for i in raw_drift
                if isinstance(i, dict) and _is_live_apple_item(i, zone="drift")
            ],
            "greeting":       packet.get("greeting") or greeting,
            "mode":           packet.get("mode")     or mode,
            "generated_at":   packet.get("generated_at") or _ts(),
        }
        return _ok(data)

    # ------------------------------------------------------------------
    # GET /api/apple/status  (Watch complication data)
    # ------------------------------------------------------------------
    @app.get("/api/apple/status")
    async def apple_status():
        """Lightweight status payload for Apple Watch complications."""
        try:
            status = runtime.status()
        except Exception:
            status = {}

        if not isinstance(status, dict):
            status = {}

        # Attempt to read pending-approval count
        needs_count = 0
        try:
            from .approvals import get_approval_queue
            queue = get_approval_queue()
            if queue is not None:
                needs_count = len(queue.list_pending())
        except Exception:
            pass

        # Attempt to read current mode from status
        mode = status.get("mode") or status.get("current_mode") or "home"

        # Weather — best-effort from runtime
        weather = ""
        try:
            world = runtime.world_state_view("chris")
            weather = world.get("weather", {}).get("summary") or ""
        except Exception:
            pass

        # Drift flag
        drift = False
        try:
            snap = runtime.chamber_home_snapshot("chris")
            drift = bool(snap.get("drift_items") or snap.get("drift"))
        except Exception:
            pass

        data = {
            "needs_count": needs_count,
            "mode": str(mode),
            "weather": str(weather),
            "drift": drift,
            "ts": _ts(),
        }
        return _ok(data)

    # ------------------------------------------------------------------
    # GET /api/apple/weather
    # ------------------------------------------------------------------
    @app.get("/api/apple/weather")
    async def apple_weather():
        """Compact live Storm weather snapshot for Apple clients."""
        try:
            snapshot = runtime.storm_weather_snapshot(force=False)
        except Exception as exc:
            logger.warning("apple_weather: %s", exc)
            snapshot = {}

        current = snapshot.get("current") if isinstance(snapshot, dict) else {}
        current = current if isinstance(current, dict) else {}
        hourly = snapshot.get("hourly") if isinstance(snapshot, dict) else []
        hourly = hourly if isinstance(hourly, list) else []

        data = {
            "available": bool(snapshot.get("available")) if isinstance(snapshot, dict) else False,
            "live": bool(snapshot.get("live")) if isinstance(snapshot, dict) else False,
            "stale": bool(snapshot.get("stale")) if isinstance(snapshot, dict) else False,
            "location": str(snapshot.get("location") or current.get("location") or ""),
            "summary": str(snapshot.get("summary") or current.get("condition") or ""),
            "source": str(snapshot.get("source") or "weather.gov"),
            "fetched_at": str(snapshot.get("fetched_at") or _ts()),
            "current": {
                "temperature_f": current.get("temperature_f"),
                "feels_like_f": current.get("feels_like_f"),
                "condition": str(current.get("condition") or ""),
                "icon": str(current.get("icon") or ""),
                "wind": str(current.get("wind") or ""),
                "humidity_pct": current.get("humidity_pct"),
                "visibility_miles": current.get("visibility_miles"),
                "pressure_hpa": current.get("pressure_hpa"),
                "visual_key": str(current.get("visual_key") or ""),
                "moon_phase": str(current.get("moon_phase") or ""),
                "moon_phase_label": str(current.get("moon_phase_label") or ""),
                "using_forecast_fallback": bool(current.get("using_forecast_fallback")),
            },
            "hourly": [
                {
                    "time": str(item.get("time") or ""),
                    "temperature_f": item.get("temperature_f"),
                    "rain_pct": item.get("rain_pct"),
                    "forecast": str(item.get("forecast") or ""),
                    "icon": str(item.get("icon") or ""),
                }
                for item in hourly[:8]
                if isinstance(item, dict)
            ],
            "alerts_count": len(snapshot.get("alerts") or []) if isinstance(snapshot, dict) else 0,
        }
        return _ok(data)

    # ------------------------------------------------------------------
    # GET /api/apple/navigation/locations
    # ------------------------------------------------------------------
    @app.get("/api/apple/navigation/locations")
    async def apple_navigation_locations():
        """Saved family locations for Navigation quick actions."""
        payload = {"preferred_location_id": None, "saved_locations": []}
        try:
            if LOCATION_SETTINGS_PATH.exists():
                raw = json.loads(LOCATION_SETTINGS_PATH.read_text(encoding="utf-8"))
                saved = raw.get("saved_locations") if isinstance(raw, dict) else []
                payload = {
                    "preferred_location_id": str((raw or {}).get("preferred_location_id") or "") or None,
                    "saved_locations": [
                        {
                            "id": str(item.get("id") or ""),
                            "label": str(item.get("label") or ""),
                            "address": str(item.get("address") or ""),
                            "geography": str(item.get("geography") or ""),
                            "latitude": item.get("latitude"),
                            "longitude": item.get("longitude"),
                            "source": str(item.get("source") or ""),
                            "notes": str(item.get("notes") or ""),
                        }
                        for item in saved
                        if isinstance(item, dict)
                    ],
                }
        except Exception as exc:
            logger.warning("apple_navigation_locations: %s", exc)
        return _ok(payload)

    # ------------------------------------------------------------------
    # GET /api/apple/navigation/route
    # ------------------------------------------------------------------
    @app.get("/api/apple/navigation/route")
    async def apple_navigation_route(origin: str, destination: str):
        """Route weather summary for the iPhone Navigation tab."""
        origin = str(origin or "").strip()
        destination = str(destination or "").strip()
        if not origin or not destination:
            raise HTTPException(status_code=400, detail="origin and destination are required")
        try:
            route = runtime.storm_route_weather(origin, destination)
        except Exception as exc:
            logger.warning("apple_navigation_route: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc))

        route_info = route.get("route") if isinstance(route, dict) else {}
        samples = route.get("samples") if isinstance(route, dict) else []
        payload = {
            "origin": route.get("origin") or {},
            "destination": route.get("destination") or {},
            "summary": str(route.get("summary") or ""),
            "hazard_active": bool(route.get("hazard_active")),
            "route": {
                "distance_miles": route_info.get("distance_miles"),
                "duration_minutes": route_info.get("duration_minutes"),
                "coordinates": route_info.get("coordinates") if isinstance(route_info.get("coordinates"), list) else [],
                "steps": [
                    {
                        "sequence": int(step.get("sequence") or 0),
                        "instruction": str(step.get("instruction") or ""),
                        "distance_miles": step.get("distance_miles"),
                        "duration_minutes": step.get("duration_minutes"),
                        "maneuver": str(step.get("maneuver") or ""),
                        "modifier": str(step.get("modifier") or ""),
                        "name": str(step.get("name") or ""),
                    }
                    for step in (route_info.get("steps") or [])
                    if isinstance(step, dict)
                ],
            },
            "samples": [
                {
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "condition": str(item.get("condition") or ""),
                    "temperature_f": item.get("temperature_f"),
                    "rain_pct": item.get("rain_pct"),
                    "wind": str(item.get("wind") or ""),
                    "alerts": [str(alert) for alert in (item.get("alerts") or [])],
                }
                for item in samples
                if isinstance(item, dict)
            ],
        }
        return _ok(payload)

    # ------------------------------------------------------------------
    # GET /api/apple/navigation/stops
    # ------------------------------------------------------------------
    @app.get("/api/apple/navigation/stops")
    async def apple_navigation_stops(origin: str, destination: str):
        """Along-route stop suggestions for the Navigation tab."""
        origin = str(origin or "").strip()
        destination = str(destination or "").strip()
        if not origin or not destination:
            raise HTTPException(status_code=400, detail="origin and destination are required")

        try:
            route_packet = runtime.storm_route_weather(origin, destination)
        except Exception as exc:
            logger.warning("apple_navigation_stops.route: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc))

        route_info = route_packet.get("route") if isinstance(route_packet, dict) else {}
        route_points = _nav_route_points(route_info if isinstance(route_info, dict) else {})
        total_miles = float(route_info.get("distance_miles") or 0) if isinstance(route_info, dict) else 0.0
        if not route_points:
            return _ok({"sections": []})

        bridge = _nav_bridge()
        interval = 12.0
        if total_miles > 0 and total_miles < 24:
            interval = max(5.0, total_miles / 3)
        samples = sample_route_points(route_points, interval_miles=interval)

        # Approximate mile markers aligned to the sampled points.
        mile_markers: list[float] = []
        cumulative = 0.0
        next_threshold = interval
        mile_markers.append(0.0)
        for idx in range(1, len(route_points)):
            cumulative += haversine(
                route_points[idx - 1][0], route_points[idx - 1][1],
                route_points[idx][0], route_points[idx][1],
            )
            if cumulative >= next_threshold:
                mile_markers.append(round(cumulative, 1))
                next_threshold += interval
        while len(mile_markers) < len(samples):
            mile_markers.append(round(total_miles, 1))

        sections: list[dict[str, Any]] = []
        seen_by_category: dict[str, set[str]] = {}
        categories = ["food", "starbucks", "parks", "historic", "family", "gas"]

        try:
            for category in categories:
                seen_by_category[category] = set()
                radius_m = 50_000 if category in {"parks", "historic"} else 2400
                items: list[dict[str, Any]] = []
                for sample_idx, (slat, slng) in enumerate(samples):
                    marker = mile_markers[sample_idx] if sample_idx < len(mile_markers) else round(total_miles, 1)
                    for poi in bridge.search_places_near(slat, slng, category, radius_m=radius_m):
                        key = str(poi.get("place_id") or poi.get("name") or "")
                        if not key or key in seen_by_category[category]:
                            continue
                        seen_by_category[category].add(key)
                        items.append(
                            {
                                "name": str(poi.get("name") or ""),
                                "address": str(poi.get("address") or ""),
                                "description": "",
                                "url": "",
                                "lat": poi.get("lat"),
                                "lng": poi.get("lng"),
                                "rating": poi.get("rating"),
                                "route_mile_marker": marker,
                                "distance_from_route": None,
                            }
                        )
                items.sort(key=lambda item: item.get("route_mile_marker") or 0)

                # Blend in official NPS parks/sites for the parks category when possible.
                if category == "parks":
                    states = _nav_state_codes(
                        str((route_packet.get("origin") or {}).get("label") or ""),
                        str((route_packet.get("destination") or {}).get("label") or ""),
                    )
                    if states:
                        for park in _nav_nps_along_route(bridge, route_points, states):
                            key = f"nps:{park.get('name')}"
                            if key in seen_by_category[category]:
                                continue
                            seen_by_category[category].add(key)
                            items.append(park)
                        items.sort(key=lambda item: item.get("route_mile_marker") or 0)

                sections.append(
                    {
                        "id": category,
                        "label": _NAV_STOP_LABELS.get(category, category.title()),
                        "items": items[:8],
                    }
                )
        except Exception as exc:
            logger.warning("apple_navigation_stops.poi: %s", exc)

        return _ok({"sections": sections})

    # ------------------------------------------------------------------
    # GET /api/apple/needs
    # ------------------------------------------------------------------
    @app.get("/api/apple/needs")
    async def apple_needs():
        """
        Return the Needs You items formatted for Watch display:
        shorter text, action buttons included.
        """
        items: list[dict] = []
        try:
            pending = runtime.list_pending_approvals()
            raw = pending if isinstance(pending, list) else pending.get("items", [])
            for item in raw:
                items.append({
                    "id": str(item.get("id") or item.get("request_id") or uuid.uuid4()),
                    "text": _truncate(str(item.get("title") or item.get("text") or ""), 80),
                    "agent": str(item.get("agent") or item.get("requester") or "JARVIS"),
                    "risk": str(item.get("risk") or item.get("risk_tier") or "medium"),
                    "expires_in": item.get("expires_in"),
                })
        except Exception as exc:
            logger.warning("apple_needs: %s", exc)
        return _ok(items)

    # ------------------------------------------------------------------
    # POST /api/apple/speak
    # ------------------------------------------------------------------
    @app.post("/api/apple/speak")
    async def apple_speak(payload: dict):
        """
        Route a text command from Phone / Siri through the JARVIS agent router.
        """
        text = str(payload.get("text") or "").strip()
        actor_id = str(payload.get("actor_id") or "chris").strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")

        response_text = ""
        agent_name = "JARVIS"
        speak = True

        # Try the main respond path
        try:
            result = runtime.respond(actor_id, "apple", text)
            if isinstance(result, dict):
                response_text = str(
                    result.get("output_text")
                    or result.get("response")
                    or result.get("text")
                    or ""
                )
                agent_name = str(result.get("agent") or result.get("actor") or "JARVIS")
            else:
                response_text = str(result)
        except Exception as exc:
            logger.warning("apple_speak: respond failed: %s", exc)
            response_text = "I'm working on that for you, Sir."

        return _ok({
            "response": response_text or "Understood.",
            "agent": agent_name,
            "speak": speak,
        })

    # ------------------------------------------------------------------
    # GET /api/apple/health/summary
    # ------------------------------------------------------------------
    @app.get("/api/apple/health/summary")
    async def apple_health_summary(actor: str = "chris"):
        """Health summary for HealthKit display and Watch complication."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        agg = _health_store.get_summary(actor, today)

        # Thor note — best effort
        thor_note = "Keep it up today."
        try:
            snap = runtime.chamber_home_snapshot(actor)
            health_cards = [
                item for item in (snap.get("briefing_items") or snap.get("feed") or [])
                if isinstance(item, dict) and "health" in str(item.get("domain", "")).lower()
            ]
            if health_cards:
                thor_note = str(health_cards[0].get("text") or health_cards[0].get("sub") or thor_note)
        except Exception:
            pass

        # Readiness heuristic
        steps = agg.get("steps", 0)
        sleep = agg.get("sleep_hours", 0.0)
        hr = agg.get("heart_rate_avg", 0)
        if sleep >= 7 and steps >= 3000:
            readiness = "good"
        elif sleep >= 5:
            readiness = "moderate"
        else:
            readiness = "low"

        data = {
            "steps_today": agg["steps"],
            "heart_rate_avg": agg["heart_rate_avg"],
            "sleep_hours": agg["sleep_hours"],
            "active_calories": agg["active_calories"],
            "stand_hours": agg["stand_hours"],
            "hrv": agg["hrv"],
            "readiness": readiness,
            "thor_note": thor_note,
            "last_sync": agg["last_sync"],
        }
        return _ok(data)

    # ------------------------------------------------------------------
    # POST /api/apple/health/log
    # ------------------------------------------------------------------
    @app.post("/api/apple/health/log")
    async def apple_health_log(payload: dict):
        """
        Receive HealthKit samples pushed from iPhone and persist them.
        Body: {"actor_id": str, "samples": [{type, value, date, source}]}
        """
        actor_id = str(payload.get("actor_id") or "chris").strip()
        samples = payload.get("samples") or []
        if not isinstance(samples, list):
            raise HTTPException(status_code=400, detail="samples must be a list")

        logged = _health_store.log_samples(actor_id, samples)
        return _ok({"logged": logged})

    # ------------------------------------------------------------------
    # GET /api/apple/home/state
    # ------------------------------------------------------------------
    @app.get("/api/apple/home/state")
    async def apple_home_state():
        """Return current house state via HomeAssistantConnector."""
        try:
            from .data_connectors import get_ha
            ha = get_ha()
            if ha is not None:
                state = ha.get_house_state()
            else:
                state = _mock_home_state()
        except Exception as exc:
            logger.warning("apple_home_state: %s", exc)
            state = _mock_home_state()
        return _ok(state)

    # ------------------------------------------------------------------
    # POST /api/apple/home/command
    # ------------------------------------------------------------------
    @app.post("/api/apple/home/command")
    async def apple_home_command(payload: dict):
        """
        Stage a home command for approval before execution.
        Body: {"command": str, "entity_id": str, "service": str}
        """
        command = str(payload.get("command") or "").strip()
        entity_id = str(payload.get("entity_id") or "").strip()
        service = str(payload.get("service") or "").strip()
        if not command:
            raise HTTPException(status_code=400, detail="command is required")

        request_id = str(uuid.uuid4())
        try:
            from .approvals import get_approval_guard
            guard = get_approval_guard()
            if guard is not None:
                request_id = guard.request_approval(
                    title=command,
                    description=f"Home command: {service} on {entity_id}",
                    action_type="home_control",
                    payload={"command": command, "entity_id": entity_id, "service": service},
                )
        except Exception as exc:
            logger.warning("apple_home_command: approval guard failed: %s", exc)

        return _ok({"request_id": request_id, "status": "pending_approval"})

    # ------------------------------------------------------------------
    # POST /api/apple/presence
    # ------------------------------------------------------------------
    @app.post("/api/apple/presence")
    async def apple_presence(payload: dict):
        """
        Phone reports presence events (arrived_home / left_home).
        Fires the matching scheduler event so Home Assistant agents react.
        """
        actor_id = str(payload.get("actor_id") or "chris").strip()
        event = str(payload.get("event") or "").strip()
        lat = float(payload.get("lat") or 0)
        lon = float(payload.get("lon") or 0)

        if event not in ("arrived_home", "left_home"):
            raise HTTPException(status_code=400, detail="event must be arrived_home or left_home")

        # Fire scheduler event (non-fatal if scheduler unavailable)
        try:
            from .scheduler import get_scheduler, EVENT_HOME_ARRIVAL, EVENT_HOME_DEPARTURE
            scheduler = get_scheduler()
            if scheduler is not None:
                event_type = EVENT_HOME_ARRIVAL if event == "arrived_home" else EVENT_HOME_DEPARTURE
                scheduler.fire_event(event_type, {"actor": actor_id, "lat": lat, "lon": lon})
        except Exception as exc:
            logger.warning("apple_presence: scheduler fire_event failed: %s", exc)

        # Also call runtime presence update for immediate effect
        try:
            runtime.phone_presence_update(actor_id, event, lat=lat, lon=lon)
        except Exception:
            try:
                runtime.presence_update(actor_id, event)
            except Exception as exc2:
                logger.warning("apple_presence: runtime presence update failed: %s", exc2)

        return _ok({"event": event, "actor_id": actor_id, "ts": _ts()})

    # ------------------------------------------------------------------
    # GET /api/apple/notifications/pending
    # ------------------------------------------------------------------
    @app.get("/api/apple/notifications/pending")
    async def apple_notifications_pending():
        """
        Pull-based notification delivery.
        Returns any queued notifications and clears them so they are not
        delivered twice.
        """
        notifications = _notification_store.drain()
        return _ok({"notifications": notifications})

    # ------------------------------------------------------------------
    # GET /api/apple/voice/greeting
    # ------------------------------------------------------------------
    @app.get("/api/apple/voice/greeting")
    async def apple_voice_greeting(actor: str = "chris"):
        """Return a voice greeting suitable for wake-word or app launch."""
        greeting, mode = _time_of_day_greeting()
        return _ok({"greeting": greeting, "mode": mode})

    # ------------------------------------------------------------------
    # POST /api/apple/approvals/{request_id}/approve
    # ------------------------------------------------------------------
    @app.post("/api/apple/approvals/{request_id}/approve")
    async def apple_approve(request_id: str, payload: dict = {}):
        """One-tap approval from Watch or Phone."""
        from .approvals import get_approval_queue
        queue = get_approval_queue()
        if queue is None:
            raise HTTPException(status_code=503, detail="Approval system not initialised")

        approved_by = str(payload.get("approved_by") or "chris")
        from dataclasses import asdict as _asdict
        item = queue.approve(request_id, approved_by=approved_by)
        if item is None:
            raise HTTPException(status_code=404, detail="Pending approval request not found")

        try:
            item_dict = _asdict(item)
        except Exception:
            item_dict = dict(item) if hasattr(item, "__dict__") else {}

        # Push a confirmation to the approver's phone
        try:
            from .apns_sender import send_push
            title_text = item_dict.get("title") or "Request"
            import asyncio
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: send_push(
                    approved_by,
                    title="✅ Approved",
                    body=str(title_text)[:100],
                    category="approval",
                )
            )
        except Exception:
            pass

        return _ok({"status": "approved", "request": item_dict})

    # ── EventKit: Calendar ────────────────────────────────────────────────────

    @app.post("/api/apple/calendar")
    async def apple_calendar(payload: dict):
        """Receives Calendar events from EventKit on the iPhone.
        Writes to data/apple/calendar_events.json for the runtime to consume."""
        events = payload.get("events", [])
        out_path = Path("data/apple/calendar_events.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "events": events,
            "count":  len(events),
            "source": "eventkit",
            "synced_at": _ts(),
        }, indent=2))
        logger.info("EventKit calendar: stored %d events", len(events))
        return _ok({"stored": len(events)})

    # ── EventKit: Reminders ───────────────────────────────────────────────────

    @app.post("/api/apple/reminders")
    async def apple_reminders(payload: dict):
        """Receives Reminders from EventKit on the iPhone.
        Writes to data/apple/reminders.json."""
        reminders = payload.get("reminders", [])
        out_path = Path("data/apple/reminders.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "reminders": reminders,
            "count":     len(reminders),
            "source":    "eventkit",
            "synced_at": _ts(),
        }, indent=2))
        logger.info("EventKit reminders: stored %d items", len(reminders))
        return _ok({"stored": len(reminders)})

    # ── Focus Filter ─────────────────────────────────────────────────────────

    @app.post("/api/apple/focus")
    async def apple_focus(payload: dict):
        """Receives iOS Focus Filter state so JARVIS can adjust notification behavior."""
        out_path = Path("data/apple/focus_state.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        record = {**payload, "updated_at": _ts()}
        out_path.write_text(json.dumps(record, indent=2))

        try:
            from .service import broadcast_event
            broadcast_event("apple.focus", record)
        except Exception:
            pass

        return _ok({"stored": True, "focus_active": bool(payload.get("focus_active"))})

    # ── Sound Analysis ───────────────────────────────────────────────────────

    @app.post("/api/apple/sound-alert")
    async def apple_sound_alert(payload: dict):
        """Receives on-device SoundAnalysis alerts from the iPhone."""
        out_path = Path("data/apple/sound_alerts.jsonl")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        record = {**payload, "received_at": _ts()}
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

        try:
            from .service import broadcast_event
            broadcast_event("apple.sound_alert", record)
        except Exception:
            pass

        return _ok({"stored": True})

    # ── Vision Scan ──────────────────────────────────────────────────────────

    @app.post("/api/apple/vision/scan")
    async def apple_vision_scan(payload: dict):
        """Receives OCR/barcode scan text produced on-device by Vision."""
        out_path = Path("data/apple/vision_scans.jsonl")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        record = {**payload, "received_at": _ts()}
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

        try:
            from .service import broadcast_event
            broadcast_event("apple.vision_scan", {
                "context": payload.get("context"),
                "source": payload.get("source"),
                "text_preview": str(payload.get("text") or "")[:200],
            })
        except Exception:
            pass

        return _ok({"stored": True})

    # ── MusicKit: Now Playing ─────────────────────────────────────────────────

    @app.post("/api/apple/now-playing")
    async def apple_now_playing(payload: dict):
        """Receives Now Playing info from MediaPlayer on the iPhone."""
        out_path = Path("data/apple/now_playing.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            **{k: v for k, v in payload.items() if k != "artwork_b64"},
            "updated_at": _ts(),
        }, indent=2))
        # Persist artwork separately as a JPEG
        if artwork_b64 := payload.get("artwork_b64"):
            import base64
            artwork_path = Path("data/apple/now_playing_artwork.jpg")
            try:
                artwork_path.write_bytes(base64.b64decode(artwork_b64))
            except Exception:
                pass
        # Broadcast to web UI via SSE
        try:
            from .service import broadcast_event
            broadcast_event("apple.now_playing", {
                "title":  payload.get("title"),
                "artist": payload.get("artist"),
                "album":  payload.get("album"),
                "playing": payload.get("is_playing"),
            })
        except Exception:
            pass
        return _ok({"stored": True})

    # ── TTS via iOS (replaces ElevenLabs) ────────────────────────────────────

    @app.post("/api/apple/speak")
    async def apple_speak_push(payload: dict):
        """Push a 'speak this text' silent notification to the user's iPhone.
        The iOS app speaks it using AVSpeechSynthesizer (free, on-device)."""
        text   = str(payload.get("text") or "").strip()
        actor  = str(payload.get("actor") or "chris")
        if not text:
            return _ok({"sent": False, "reason": "empty text"})
        try:
            from .apns_sender import send_push
            send_push(
                actor,
                title="",
                body=text,
                category="speak",
                extra={"speak": text},
                content_available=True,
            )
            return _ok({"sent": True, "chars": len(text)})
        except Exception as exc:
            return _ok({"sent": False, "reason": str(exc)})


# ── Catalyst overview ────────────────────────────────────────────────────────

    @app.get("/api/apple/catalyst")
    async def apple_catalyst():
        """Lightweight Catalyst workspace overview for the iPhone Catalyst tab."""
        try:
            data_root = Path("data/catalyst")
            # Work lifecycle — active / in-review items
            wl_path = data_root / "work_lifecycle.json"
            wl_raw = json.loads(wl_path.read_text()) if wl_path.exists() else {}
            wl_items = list(wl_raw.values()) if isinstance(wl_raw, dict) else wl_raw
            active_work = [
                {
                    "work_id":  str(i.get("work_id") or ""),
                    "title":    _truncate(str(i.get("title") or ""), 60),
                    "domain":   str(i.get("domain") or ""),
                    "stage":    str(i.get("current_stage") or i.get("status") or ""),
                    "updated":  str(i.get("updated_at") or i.get("created_at") or ""),
                }
                for i in wl_items
                if str(i.get("status") or "").lower() not in ("done", "archived", "cancelled")
            ][:10]

            # Recent signals
            sig_path = data_root / "signals.json"
            sig_raw = json.loads(sig_path.read_text()) if sig_path.exists() else {}
            sig_items = list(sig_raw.values()) if isinstance(sig_raw, dict) else sig_raw
            signals = [
                {
                    "signal_id": str(s.get("signal_id") or ""),
                    "title":     _truncate(str(s.get("title") or s.get("content") or ""), 60),
                    "source":    str(s.get("source") or ""),
                    "tags":      s.get("tags") or [],
                    "timestamp": str(s.get("timestamp") or ""),
                }
                for s in (sig_items[-8:] if sig_items else [])
            ]

            # Pipeline portfolio summary
            pipeline_path = data_root / "pipeline_state.json"
            portfolio = {}
            if pipeline_path.exists():
                ps = json.loads(pipeline_path.read_text())
                portfolio = ps.get("portfolio") or {}

            return _ok({
                "active_work": active_work,
                "signals":     signals,
                "portfolio":   portfolio,
                "updated_at":  _ts(),
            })
        except Exception as exc:
            logger.exception("apple_catalyst failed: %s", exc)
            return _ok({"active_work": [], "signals": [], "portfolio": {}, "updated_at": _ts()})

    # ── Chronicle overview ────────────────────────────────────────────────────

    @app.get("/api/apple/chronicle")
    async def apple_chronicle(actor: str = "chris"):
        """Recent Chronicle entries and insights for the iPhone Chronicle tab."""
        try:
            entries_path = Path("data/chronicle/entries.jsonl")
            raw_entries = []
            if entries_path.exists():
                for line in entries_path.read_text().splitlines():
                    line = line.strip()
                    if line:
                        try:
                            raw_entries.append(json.loads(line))
                        except Exception:
                            pass

            entries = [
                {
                    "id":         str(e.get("entry_id") or e.get("id") or uuid.uuid4()),
                    "type":       str(e.get("entry_type") or e.get("theme") or "reflection"),
                    "title":      _truncate(str(e.get("title") or e.get("theme") or "Reflection"), 50),
                    "body":       _truncate(str(e.get("body") or e.get("note") or e.get("reflection") or ""), 200),
                    "scripture":  e.get("scripture_ref") or None,
                    "timestamp":  str(e.get("created_at") or e.get("timestamp") or ""),
                }
                for e in reversed(raw_entries)
                if e.get("actor") in (actor, None, "")
            ][:12]

            return _ok({"entries": entries, "updated_at": _ts()})
        except Exception as exc:
            logger.exception("apple_chronicle failed: %s", exc)
            return _ok({"entries": [], "updated_at": _ts()})

    @app.post("/api/apple/chronicle/capture")
    async def apple_chronicle_capture(payload: dict):
        """Capture a quick reflection or prayer from the phone."""
        try:
            entry_type = str(payload.get("type") or "reflection")
            note       = str(payload.get("note") or "").strip()
            actor      = str(payload.get("actor_id") or "chris")
            if not note:
                return _ok({"captured": False, "reason": "empty"})
            entry = {
                "entry_id":   str(uuid.uuid4()),
                "entry_type": entry_type,
                "title":      note[:50],
                "body":       note,
                "note":       note,
                "actor":      actor,
                "timestamp":  _ts(),
                "created_at": _ts(),
                "source":     "apple_phone",
            }
            entries_path = Path("data/chronicle/entries.jsonl")
            entries_path.parent.mkdir(parents=True, exist_ok=True)
            with entries_path.open("a") as f:
                f.write(json.dumps(entry) + "\n")
            return _ok({"captured": True, "entry_id": entry["entry_id"]})
        except Exception as exc:
            return _ok({"captured": False, "reason": str(exc)})

    # ── Faith daily word ──────────────────────────────────────────────────────

    @app.get("/api/apple/faith")
    async def apple_faith(actor: str = "chris"):
        """Daily word and faith formation context for the iPhone Faith tab."""
        try:
            fw_path = Path("data/settings/faith_daily_word.json")
            fw = {}
            if fw_path.exists():
                fw = json.loads(fw_path.read_text())

            # Morning spiritual context from chronicle bridge
            morning_context = {}
            try:
                from .chronicle_bridge import get_morning_context
                morning_context = await asyncio.to_thread(get_morning_context, actor)
            except Exception:
                pass

            return _ok({
                "daily_word": {
                    "agent":      str(fw.get("agent_name") or "JARVIS"),
                    "agent_title": str(fw.get("agent_title") or ""),
                    "word":       str(fw.get("word") or ""),
                    "passage":    str(fw.get("passage") or ""),
                    "domain":     str(fw.get("domain") or ""),
                    "generated_at": str(fw.get("generated_at") or ""),
                },
                "morning_context": morning_context,
                "updated_at": _ts(),
            })
        except Exception as exc:
            logger.exception("apple_faith failed: %s", exc)
            return _ok({"daily_word": {"agent": "JARVIS", "word": "", "passage": "", "domain": "", "agent_title": "", "generated_at": ""}, "morning_context": {}, "updated_at": _ts()})

    # ── Publishing dashboard ──────────────────────────────────────────────────

    @app.get("/api/apple/publishing")
    async def apple_publishing():
        """Publishing overview for the iPhone Publish tab."""
        try:
            pub_root = Path.home() / ".jarvis" / "publishing"

            # Projects
            proj_path = pub_root / "projects.json"
            proj_raw  = json.loads(proj_path.read_text()) if proj_path.exists() else {}
            proj_list = list(proj_raw.values()) if isinstance(proj_raw, dict) else proj_raw
            projects  = [
                {
                    "project_id": str(p.get("project_id") or ""),
                    "title":      str(p.get("title") or ""),
                    "type":       str(p.get("project_type") or ""),
                    "status":     str(p.get("status") or ""),
                    "platform":   str(p.get("platform") or ""),
                    "url":        p.get("url") or None,
                }
                for p in proj_list
                if str(p.get("status") or "") != "archived"
            ][:8]

            # Revenue streams total
            rev_path = pub_root / "revenue_streams.json"
            rev_raw  = json.loads(rev_path.read_text()) if rev_path.exists() else {}
            rev_list = list(rev_raw.values()) if isinstance(rev_raw, dict) else rev_raw
            active_rev  = [s for s in rev_list if s.get("active")]
            monthly_est = sum(float(s.get("monthly_estimate") or 0) for s in active_rev)
            revenue_summary = {
                "monthly_estimate": round(monthly_est, 2),
                "stream_count":     len(active_rev),
                "streams": [
                    {
                        "stream_id":   str(s.get("stream_id") or ""),
                        "type":        str(s.get("stream_type") or ""),
                        "source":      str(s.get("source") or ""),
                        "monthly_est": float(s.get("monthly_estimate") or 0),
                    }
                    for s in active_rev[:5]
                ],
            }

            # Upcoming calendar items
            cal_path  = pub_root / "content_calendar.jsonl"
            cal_items = []
            if cal_path.exists():
                for line in cal_path.read_text().splitlines():
                    if line.strip():
                        try:
                            cal_items.append(json.loads(line))
                        except Exception:
                            pass
            upcoming = [
                {
                    "item_id":      str(c.get("item_id") or ""),
                    "title":        _truncate(str(c.get("title") or ""), 50),
                    "content_type": str(c.get("content_type") or ""),
                    "platform":     str(c.get("platform") or ""),
                    "planned_date": str(c.get("planned_date") or ""),
                    "status":       str(c.get("status") or ""),
                }
                for c in cal_items
                if str(c.get("status") or "") not in ("published", "archived")
            ][-6:]

            return _ok({
                "projects":        projects,
                "revenue_summary": revenue_summary,
                "upcoming":        upcoming,
                "updated_at":      _ts(),
            })
        except Exception as exc:
            logger.exception("apple_publishing failed: %s", exc)
            return _ok({"projects": [], "revenue_summary": {"monthly_estimate": 0.0, "stream_count": 0, "streams": []}, "upcoming": [], "updated_at": _ts()})

    # ── Huddle ────────────────────────────────────────────────────────────────

    @app.get("/api/apple/huddle")
    async def apple_huddle():
        """Agent standup huddle for the iPhone Huddle tab."""
        try:
            from .standup import collect_all_standups
            from dataclasses import asdict
            huddle = await asyncio.to_thread(
                collect_all_standups,
                None,
                runtime,
                False,
            )
            h = asdict(huddle)
            # Flatten to phone-friendly shape
            reports = []
            for r in (h.get("agent_reports") or []):
                reports.append({
                    "agent_id":   str(r.get("agent_id") or ""),
                    "agent_name": str(r.get("agent_name") or r.get("agent_id") or ""),
                    "status":     str(r.get("status") or "ok"),
                    "summary":    _truncate(str(r.get("summary") or r.get("headline") or ""), 80),
                    "blockers":   [str(b)[:60] for b in (r.get("blockers") or [])[:2]],
                })
            return _ok({
                "reports":    reports[:15],
                "blockers":   [str(b)[:80] for b in (h.get("blockers") or [])[:5]],
                "highlights": [str(hl)[:80] for hl in (h.get("highlights") or [])[:5]],
                "updated_at": _ts(),
            })
        except Exception as exc:
            logger.exception("apple_huddle failed: %s", exc)
            return _ok({"reports": [], "blockers": [], "highlights": [], "updated_at": _ts()})

    # ── Forge 3-D models ──────────────────────────────────────────────────────

    _FORGE_DB = Path("data/forge/models.jsonl")

    @app.get("/api/apple/forge")
    async def apple_forge():
        """Return saved photogrammetry model records for the Forge tab."""
        try:
            records = []
            if _FORGE_DB.exists():
                for line in _FORGE_DB.read_text().splitlines():
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except Exception:
                            pass
            return _ok({"models": list(reversed(records[-20:]))})
        except Exception as exc:
            logger.exception("apple_forge failed: %s", exc)
            return _ok({"models": []})

    @app.post("/api/apple/forge/submit")
    async def apple_forge_submit(payload: dict):
        """Receive photos from the phone and queue a photogrammetry job."""
        try:
            import base64
            job_id   = str(uuid.uuid4())
            name     = str(payload.get("name") or "Model")
            photos   = payload.get("photos") or []
            job_dir  = Path(f"data/forge/jobs/{job_id}")
            job_dir.mkdir(parents=True, exist_ok=True)

            # Write photos to disk
            saved = 0
            for photo in photos:
                try:
                    data     = base64.b64decode(photo["data"])
                    filename = photo.get("filename") or f"photo_{photo.get('index',saved):04d}.jpg"
                    (job_dir / filename).write_bytes(data)
                    saved += 1
                except Exception:
                    pass

            # Write job manifest
            manifest = {
                "job_id":      job_id,
                "name":        name,
                "photo_count": saved,
                "status":      "queued",
                "created_at":  _ts(),
                "job_dir":     str(job_dir),
            }
            (job_dir / "manifest.json").write_text(json.dumps(manifest))

            # Append to global job queue
            queue_path = Path("data/forge/queue.jsonl")
            queue_path.parent.mkdir(parents=True, exist_ok=True)
            with queue_path.open("a") as f:
                f.write(json.dumps(manifest) + "\n")

            return _ok({"queued": True, "job_id": job_id, "photo_count": saved})
        except Exception as exc:
            logger.exception("apple_forge_submit failed: %s", exc)
            return _ok({"queued": False, "job_id": "", "reason": str(exc)})

    @app.post("/api/apple/forge/save")
    async def apple_forge_save(payload: dict):
        """Persist a completed forge model record from the phone."""
        try:
            record = {
                "id":          str(payload.get("id") or uuid.uuid4()),
                "name":        str(payload.get("name") or "Model"),
                "photo_count": int(payload.get("photo_count") or payload.get("photoCount") or 0),
                "created_at":  str(payload.get("created_at") or payload.get("createdAt") or _ts()),
                "usdz_path":   payload.get("usdz_path") or payload.get("usdzPath"),
                "saved_at":    _ts(),
            }
            _FORGE_DB.parent.mkdir(parents=True, exist_ok=True)
            with _FORGE_DB.open("a") as f:
                f.write(json.dumps(record) + "\n")
            return _ok({"saved": True, "id": record["id"]})
        except Exception as exc:
            return _ok({"saved": False, "reason": str(exc)})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _normalise_briefing_item(raw: dict) -> dict:
    """Convert any internal feed-item shape → Swift BriefingItem fields."""
    kind = str(raw.get("kind") or raw.get("priority") or "normal").lower()
    priority = "high" if kind in ("priority", "high", "urgent", "critical") else "normal"
    sub = raw.get("sub") or raw.get("body") or None
    if isinstance(sub, list):
        sub = "\n".join(str(item) for item in sub if str(item).strip()) or None
    elif sub is not None:
        sub = str(sub)
    return {
        "id":        str(raw.get("id") or uuid.uuid4()),
        "text":      str(raw.get("text") or raw.get("title") or ""),
        "sub":       sub,
        "priority":  priority,
        "agent":     str(raw.get("agent") or raw.get("source") or "JARVIS"),
        "timestamp": str(raw.get("timestamp") or raw.get("ts") or _ts()),
    }


def _normalise_working_item(raw: dict) -> dict:
    """Convert any internal working-item shape → Swift WorkingItem fields."""
    return {
        "id":        str(raw.get("id") or uuid.uuid4()),
        "agent":     str(raw.get("agent") or raw.get("source") or raw.get("title") or "JARVIS"),
        "action":    str(raw.get("action") or raw.get("body") or raw.get("text") or "Working…"),
        "timestamp": str(raw.get("timestamp") or raw.get("ts") or _ts()),
    }


def _normalise_needs_item(raw: dict) -> dict:
    """Convert any internal needs-item shape → Swift NeedsItem fields."""
    risk = str(raw.get("risk") or raw.get("risk_tier") or raw.get("kind") or "medium").lower()
    if risk not in ("low", "medium", "high"):
        risk = "medium"
    return {
        "id":         str(raw.get("id") or raw.get("request_id") or uuid.uuid4()),
        "text":       _truncate(str(raw.get("text") or raw.get("title") or ""), 80),
        "agent":      str(raw.get("agent") or raw.get("requester") or "JARVIS"),
        "risk":       risk,
        "expires_in": raw.get("expires_in"),
    }


def _normalise_drift_item(raw: dict) -> dict:
    """Convert any internal drift-item shape → Swift DriftItem fields."""
    kind = str(raw.get("severity") or raw.get("kind") or "gentle").lower()
    severity = kind if kind in ("gentle", "moderate", "significant") else "gentle"
    return {
        "id":       str(raw.get("id") or uuid.uuid4()),
        "text":     str(raw.get("text") or raw.get("title") or ""),
        "severity": severity,
        "agent":    str(raw.get("agent") or raw.get("source") or "JARVIS"),
    }


def _is_live_apple_item(raw: dict, *, zone: str) -> bool:
    """Keep mock/demo/seeded material out of the iPhone app's truth surfaces."""
    source = str(raw.get("source") or raw.get("source_type") or "").strip().lower()
    if source in {"mock", "fallback", "demo", "sample", "fixture", "test"}:
        return False

    agent = str(raw.get("agent") or raw.get("source") or raw.get("requester") or "").strip().lower()
    text = " ".join(
        str(raw.get(key) or "")
        for key in ("text", "title", "body", "summary")
    ).strip().lower()

    if "partly cloudy, 72.0" in text and agent == "storm":
        return False
    if "no activity logged yet" in text:
        return False
    if "last contact: never" in text:
        return False

    seeded_growth_agents = {"agatha", "gamora", "thor", "spider-man", "spiderman"}
    evidence_keys = {
        "id",
        "request_id",
        "source_signal_id",
        "work_id",
        "drift_id",
        "approval_id",
        "created_at",
        "completed_at",
    }
    if zone in {"briefing", "drift"} and agent in seeded_growth_agents:
        has_evidence = any(str(raw.get(key) or "").strip() for key in evidence_keys)
        if not has_evidence:
            return False

    return True


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _mock_home_state() -> dict:
    """Stub home state returned when HomeAssistant is not configured."""
    return {
        "present_members": [],
        "doors": {"front": "locked", "garage": "closed"},
        "temperature": {"inside": 70.0, "target": 72.0, "mode": "cool"},
        "lights_on": [],
        "alerts": [],
        "source": "mock",
    }

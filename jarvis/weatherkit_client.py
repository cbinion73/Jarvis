"""
WeatherKit REST API client — drop-in replacement for OpenWeatherMap.

Uses the same Apple .p8 key as APNs (key must have WeatherKit enabled).
Config file: data/settings/apns_config.json
  {
    "key_id":    "XXXXXXXXXX",
    "team_id":   "LGNJ56Y22G",
    "bundle_id": "com.binion.jarvisphone",
    "sandbox":   true
  }
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── Config paths ─────────────────────────────────────────────────────────────

_CONFIG_PATH = Path("data/settings/apns_config.json")
_KEY_PATH    = Path("data/settings/apns_key.p8")

# WeatherKit REST base URL
_WK_BASE = "https://weatherkit.apple.com/api/v1"

# Cache JWT for 25 minutes (Apple allows up to 30)
_jwt_cache: dict[str, Any] = {"token": None, "expires_at": 0}

# ── Condition-code → JARVIS visual_key map ────────────────────────────────────

_CONDITION_TO_VISUAL: dict[str, str] = {
    # Day-agnostic (daylight flag checked separately in _visual_key)
    "Clear":                   "clear",
    "MostlyClear":             "clear",
    "PartlyCloudy":            "partly_cloudy_day",
    "MostlyCloudy":            "partly_cloudy_day",
    "Cloudy":                  "partly_cloudy_day",
    "Overcast":                "partly_cloudy_day",
    "Fog":                     "partly_cloudy_day",
    "Haze":                    "partly_cloudy_day",
    "Smoke":                   "partly_cloudy_day",
    "BlowingDust":             "partly_cloudy_day",
    "Drizzle":                 "light_rain",
    "FreezingDrizzle":         "light_rain",
    "Rain":                    "light_rain",
    "SunShowers":              "light_rain",
    "HeavyRain":               "heavy_rain",
    "IsolatedThunderstorms":   "thunderstorm",
    "ScatteredThunderstorms":  "thunderstorm",
    "Thunderstorms":           "thunderstorm",
    "StrongStorms":            "thunderstorm",
    "TropicalStorm":           "thunderstorm",
    "Hurricane":               "thunderstorm",
    "Tornado":                 "thunderstorm",
    "Flurries":                "light_snow",
    "SunFlurries":             "light_snow",
    "Snow":                    "light_snow",
    "FreezingRain":            "light_snow",
    "Sleet":                   "light_snow",
    "WintryMix":               "light_snow",
    "BlowingSnow":             "heavy_snow",
    "HeavySnow":               "heavy_snow",
    "Blizzard":                "blizzard",
    "Frigid":                  "light_snow",
    "Breezy":                  "clear",
    "Windy":                   "clear",
    "Hot":                     "clear_day",
    "ScatteredShowers":        "light_rain",
}

_CONDITION_TO_EMOJI: dict[str, str] = {
    "Clear": "☀", "MostlyClear": "🌤", "PartlyCloudy": "⛅",
    "MostlyCloudy": "🌥", "Cloudy": "☁", "Overcast": "☁",
    "Fog": "🌫", "Haze": "🌫", "Smoke": "🌫",
    "Drizzle": "🌦", "Rain": "🌧", "HeavyRain": "⛈",
    "SunShowers": "🌦",
    "Thunderstorms": "⛈", "StrongStorms": "⛈",
    "Flurries": "🌨", "Snow": "❄", "HeavySnow": "❄",
    "Blizzard": "🌨", "FreezingRain": "🌧",
}


def _visual_key(condition_code: str, is_daylight: bool) -> str:
    base = _CONDITION_TO_VISUAL.get(condition_code, "clear")
    if base == "clear":
        return "clear_day" if is_daylight else "clear_night_no_moon"
    return base


def _emoji(condition_code: str) -> str:
    return _CONDITION_TO_EMOJI.get(condition_code, "⛅")


# ── JWT ───────────────────────────────────────────────────────────────────────

def _load_config() -> dict | None:
    if not _CONFIG_PATH.exists():
        return None
    try:
        return json.loads(_CONFIG_PATH.read_text())
    except Exception:
        return None


def _make_jwt() -> str | None:
    """Return a cached or freshly-signed WeatherKit JWT."""
    now = time.time()
    if _jwt_cache["token"] and _jwt_cache["expires_at"] > now + 60:
        return _jwt_cache["token"]

    cfg = _load_config()
    if not cfg:
        logger.warning("WeatherKit: apns_config.json not found — falling back to mock")
        return None
    if not _KEY_PATH.exists():
        logger.warning("WeatherKit: apns_key.p8 not found — falling back to mock")
        return None

    try:
        import jwt as pyjwt

        key_id   = cfg["key_id"]
        team_id  = cfg["team_id"]
        bundle_id = cfg.get("bundle_id", "com.binion.jarvisphone")
        private_key = _KEY_PATH.read_text()

        payload = {
            "iss": team_id,
            "iat": int(now),
            "exp": int(now) + 1800,
            "sub": bundle_id,
        }
        headers = {
            "kid": key_id,
            "id":  f"{team_id}.{bundle_id}",
        }
        token = pyjwt.encode(
            payload, private_key, algorithm="ES256", headers=headers
        )
        _jwt_cache["token"]      = token
        _jwt_cache["expires_at"] = int(now) + 1800
        return token

    except Exception as exc:
        logger.error("WeatherKit JWT error: %s", exc)
        return None


# ── Fetch ─────────────────────────────────────────────────────────────────────

def _fetch(lat: float, lon: float) -> dict | None:
    token = _make_jwt()
    if not token:
        return None

    url = f"{_WK_BASE}/weather/en/{lat}/{lon}"
    params = {
        "dataSets":    "currentWeather,forecastDaily,forecastHourly",
        "timezone":    "America/New_York",
    }
    try:
        resp = httpx.get(
            url, params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("WeatherKit fetch error: %s", exc)
        return None


# ── Public helpers (same interface as WeatherConnector in data_connectors.py) ─

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_current(lat: float, lon: float) -> dict:
    """Return current conditions in JARVIS WeatherConnector format."""
    data = _fetch(lat, lon)
    if data is None:
        return _mock_current()

    try:
        cur  = data["currentWeather"]
        code = cur.get("conditionCode", "Clear")
        is_day = cur.get("isDaytime", True)

        # Convert Celsius to Fahrenheit
        def c2f(c: float) -> float:
            return round(c * 9 / 5 + 32, 1)

        temp_c      = float(cur.get("temperature", 22))
        feels_c     = float(cur.get("temperatureApparent", 22))
        wind_kph    = float(cur.get("windSpeed", 0))
        wind_deg    = float(cur.get("windDirection", 0))
        vis_m       = float(cur.get("visibility", 16000))
        humidity    = float(cur.get("humidity", 0.5))
        pressure    = float(cur.get("pressure", 1013))

        return {
            "temp_f":           c2f(temp_c),
            "feels_like_f":     c2f(feels_c),
            "condition":        code.replace("MostlyClear", "Mostly Clear")
                                    .replace("PartlyCloudy", "Partly Cloudy")
                                    .replace("MostlyCloudy", "Mostly Cloudy")
                                    .replace("HeavyRain", "Heavy Rain")
                                    .replace("HeavySnow", "Heavy Snow"),
            "humidity":         int(humidity * 100),
            "wind_mph":         round(wind_kph * 0.621371, 1),
            "wind_dir":         _deg_to_dir(wind_deg),
            "visibility_miles": round(vis_m / 1609.34, 1),
            "uv_index":         int(cur.get("uvIndex", 0)),
            "pressure_hpa":     round(pressure, 1),
            "visual_key":       _visual_key(code, is_day),
            "icon":             _emoji(code),
            "alerts":           [],
            "source":           "weatherkit",
            "fetched_at":       _now_iso(),
        }
    except Exception as exc:
        logger.error("WeatherKit parse error: %s", exc)
        return _mock_current()


def get_forecast(lat: float, lon: float, days: int = 7) -> dict:
    """Return daily + hourly forecast in JARVIS WeatherConnector format."""
    data = _fetch(lat, lon)
    if data is None:
        return _mock_forecast()

    try:
        def c2f(c: float) -> float:
            return round(c * 9 / 5 + 32, 1)

        # Daily
        daily_out = []
        for d in (data.get("forecastDaily", {}).get("days") or [])[:days]:
            code = d.get("conditionCode", "Clear")
            hi   = d.get("temperatureMax", 22)
            lo   = d.get("temperatureMin", 15)
            ts   = d.get("forecastStart", "")
            try:
                dt   = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                name = dt.strftime("%a").upper()
            except Exception:
                name = "—"

            daily_out.append({
                "name":          name,
                "high_f":        c2f(hi),
                "low_f":         c2f(lo),
                "condition":     code,
                "icon":          _emoji(code),
                "visual_key":    _visual_key(code, True),
                "rain_pct":      int(d.get("precipitationChance", 0) * 100),
            })

        # Hourly (first 8 hours)
        hourly_out = []
        for h in (data.get("forecastHourly", {}).get("hours") or [])[:8]:
            code   = h.get("conditionCode", "Clear")
            is_day = h.get("isDaytime", True)
            ts     = h.get("forecastStart", "")
            try:
                dt    = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                label = dt.astimezone().strftime("%-I%p").lower()
            except Exception:
                label = "—"

            hourly_out.append({
                "hour":      label,
                "temp_f":    c2f(float(h.get("temperature", 22))),
                "condition": code,
                "icon":      _emoji(code),
                "rain_pct":  int(h.get("precipitationChance", 0) * 100),
            })

        today = (data.get("forecastDaily", {}).get("days") or [{}])[0]

        return {
            "daily":          daily_out,
            "hourly":         hourly_out,
            "daily_high_f":   round(today.get("temperatureMax", 0) * 9 / 5 + 32, 1),
            "daily_low_f":    round(today.get("temperatureMin", 0) * 9 / 5 + 32, 1),
            "source":         "weatherkit",
            "fetched_at":     _now_iso(),
        }

    except Exception as exc:
        logger.error("WeatherKit forecast parse error: %s", exc)
        return _mock_forecast()


# ── Direction helper ──────────────────────────────────────────────────────────

def _deg_to_dir(deg: float) -> str:
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
            "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg / 22.5) % 16]


def _mock_current() -> dict:
    return {
        "temp_f": 72.0, "feels_like_f": 70.0, "condition": "Partly Cloudy",
        "humidity": 55, "wind_mph": 8.5, "wind_dir": "SW",
        "visibility_miles": 10.0, "uv_index": 3, "pressure_hpa": 1013.0,
        "visual_key": "partly_cloudy_day", "icon": "⛅",
        "alerts": [], "source": "mock", "fetched_at": _now_iso(),
    }


def _mock_forecast() -> dict:
    return {
        "daily": [], "hourly": [],
        "daily_high_f": 78.0, "daily_low_f": 62.0,
        "source": "mock", "fetched_at": _now_iso(),
    }

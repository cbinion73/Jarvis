"""
JARVIS · Dining Intelligence
Google Places API wrapper with smart Sam-aware restaurant recommendations.
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GOOGLE_PLACES_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
PLACES_NEARBY_URL  = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_DETAIL_URL  = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_TEXT_URL    = "https://maps.googleapis.com/maps/api/place/textsearch/json"

# Home base — Alexandria KY
DEFAULT_LAT = 38.9598
DEFAULT_LNG = -84.3877
DEFAULT_RADIUS_M = 16000   # ~10 miles — reaches Cincinnati metro

CACHE_TTL = 2 * 3600       # 2 hours
CACHE_PATH = Path("data/cache/dining_cache.json")
FAVORITES_PATH = Path("data/settings/dining_favorites.json")
_cache_lock = threading.Lock()

# Cuisine type → Google Places type mapping
CUISINE_MAP: dict[str, str] = {
    "any":        "restaurant",
    "pizza":      "restaurant",
    "sushi":      "restaurant",
    "mexican":    "mexican_restaurant",
    "italian":    "italian_restaurant",
    "chinese":    "chinese_restaurant",
    "american":   "american_restaurant",
    "barbecue":   "barbecue_restaurant",
    "thai":       "thai_restaurant",
    "indian":     "indian_restaurant",
    "burgers":    "hamburger_restaurant",
    "sandwiches": "sandwich_shop",
    "breakfast":  "breakfast_restaurant",
    "seafood":    "seafood_restaurant",
    "steak":      "steak_house",
    "fast food":  "fast_food_restaurant",
    "coffee":     "coffee_shop",
    "bakery":     "bakery",
}

# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    try:
        if CACHE_PATH.exists():
            return json.loads(CACHE_PATH.read_text())
    except Exception:
        pass
    return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, indent=2))
    except Exception as exc:
        logger.warning("dining: cache write failed: %s", exc)


def _cache_get(key: str) -> list[dict] | None:
    with _cache_lock:
        cache = _load_cache()
        entry = cache.get(key)
        if entry and time.time() - entry.get("ts", 0) < CACHE_TTL:
            return entry["data"]
    return None


def _cache_set(key: str, data: list[dict]) -> None:
    with _cache_lock:
        cache = _load_cache()
        cache[key] = {"ts": time.time(), "data": data}
        _save_cache(cache)


# ---------------------------------------------------------------------------
# Core API calls
# ---------------------------------------------------------------------------

def _places_nearby(
    lat: float,
    lng: float,
    radius: int,
    place_type: str,
    open_now: bool,
    keyword: str = "",
) -> list[dict]:
    """Call Google Places Nearby Search and return raw results (up to 20)."""
    if not GOOGLE_PLACES_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY not set")

    params: dict[str, Any] = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": place_type,
        "key": GOOGLE_PLACES_KEY,
    }
    if open_now:
        params["opennow"] = "true"
    if keyword:
        params["keyword"] = keyword

    resp = httpx.get(PLACES_NEARBY_URL, params=params, timeout=8)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Places API error: {data.get('status')} — {data.get('error_message','')}")
    return data.get("results", [])


def _place_details(place_id: str) -> dict:
    """Fetch rich details for a single place (phone, website, hours, price_level)."""
    if not GOOGLE_PLACES_KEY:
        return {}
    fields = "name,formatted_phone_number,website,opening_hours,price_level,rating,user_ratings_total,formatted_address"
    resp = httpx.get(
        PLACES_DETAIL_URL,
        params={"place_id": place_id, "fields": fields, "key": GOOGLE_PLACES_KEY},
        timeout=8,
    )
    resp.raise_for_status()
    return resp.json().get("result", {})


# ---------------------------------------------------------------------------
# Distance helper
# ---------------------------------------------------------------------------

def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _format_place(raw: dict, home_lat: float = DEFAULT_LAT, home_lng: float = DEFAULT_LNG) -> dict:
    """Normalise a raw Places result into a clean JARVIS dict."""
    loc = raw.get("geometry", {}).get("location", {})
    lat, lng = loc.get("lat", 0), loc.get("lng", 0)
    distance_miles = round(_haversine_miles(home_lat, home_lng, lat, lng), 1)

    price = raw.get("price_level")
    price_str = ("$" * price) if price else ""

    return {
        "place_id":    raw.get("place_id", ""),
        "name":        raw.get("name", ""),
        "address":     raw.get("vicinity", raw.get("formatted_address", "")),
        "rating":      raw.get("rating"),
        "review_count": raw.get("user_ratings_total", 0),
        "price":       price_str,
        "open_now":    raw.get("opening_hours", {}).get("open_now"),
        "distance_mi": distance_miles,
        "lat":         lat,
        "lng":         lng,
        "types":       raw.get("types", []),
        "photo_ref":   (raw.get("photos") or [{}])[0].get("photo_reference"),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def nearby_restaurants(
    cuisine: str = "any",
    open_now: bool = False,
    min_rating: float = 3.5,
    radius_miles: float = 10.0,
    limit: int = 10,
    lat: float = DEFAULT_LAT,
    lng: float = DEFAULT_LNG,
) -> list[dict]:
    """Return nearby restaurants, sorted by rating × review_count score."""
    radius_m = min(int(radius_miles * 1609), 50000)
    place_type = CUISINE_MAP.get(cuisine.lower(), "restaurant")
    keyword = cuisine if cuisine.lower() not in ("any", "restaurant") else ""
    cache_key = f"nearby:{lat:.4f}:{lng:.4f}:{radius_m}:{place_type}:{keyword}:{open_now}"

    cached = _cache_get(cache_key)
    if cached is not None:
        results = cached
    else:
        raw = _places_nearby(lat, lng, radius_m, place_type, open_now, keyword)
        results = [_format_place(r, lat, lng) for r in raw]
        _cache_set(cache_key, results)

    # Filter
    if min_rating:
        results = [r for r in results if r.get("rating") and r["rating"] >= min_rating]

    # Sort by a weighted score: rating * log(reviews+1)
    def _score(r: dict) -> float:
        rating = r.get("rating") or 0
        reviews = r.get("review_count") or 0
        return rating * math.log(reviews + 1)

    results = sorted(results, key=_score, reverse=True)
    return results[:limit]


def get_place_details(place_id: str) -> dict:
    """Return enriched details for a place (phone, website, hours)."""
    cache_key = f"detail:{place_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached[0] if cached else {}
    detail = _place_details(place_id)
    _cache_set(cache_key, [detail])
    return detail


def photo_url(photo_ref: str, max_width: int = 400) -> str:
    """Build a Google Places photo URL."""
    if not photo_ref or not GOOGLE_PLACES_KEY:
        return ""
    return (
        f"https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={max_width}&photo_reference={photo_ref}&key={GOOGLE_PLACES_KEY}"
    )


# ---------------------------------------------------------------------------
# Sam-aware recommendations
# ---------------------------------------------------------------------------

def recommend_restaurants(runtime=None, limit: int = 3) -> dict:
    """
    Return a curated short-list using Sam's knowledge of health goals,
    food prefs, time of day, and recent meals.
    """
    # Load food prefs
    prefs: dict = {}
    try:
        fp = Path("data/settings/sam_food_prefs.json")
        if fp.exists():
            prefs = json.loads(fp.read_text())
    except Exception:
        pass

    allergies: list[str] = prefs.get("allergies") or []
    dislikes:  list[str] = prefs.get("dislikes")  or []
    goals:     str       = prefs.get("goals") or ""

    # Time-of-day context
    hour = datetime.now().hour
    if hour < 11:
        meal_type = "breakfast"
        open_now = True
    elif hour < 15:
        meal_type = "lunch"
        open_now = True
    else:
        meal_type = "dinner"
        open_now = hour < 22  # after 10pm don't filter

    # Pull candidates — no cuisine filter so we get variety
    try:
        candidates = nearby_restaurants(
            cuisine="any",
            open_now=open_now,
            min_rating=4.0,
            radius_miles=12.0,
            limit=20,
        )
    except Exception as exc:
        return {"error": str(exc), "recommendations": []}

    # Filter out places with disliked keywords in name
    def _is_ok(place: dict) -> bool:
        name_lower = place["name"].lower()
        for d in dislikes:
            if d.lower() in name_lower:
                return False
        return True

    candidates = [c for c in candidates if _is_ok(c)]

    # Score boost for meal type alignment
    def _meal_boost(place: dict) -> float:
        types = place.get("types", [])
        name = place["name"].lower()
        if meal_type == "breakfast" and ("breakfast" in types or "breakfast" in name or "coffee" in types):
            return 2.0
        if meal_type == "lunch" and "fast_food" not in types:
            return 1.2
        return 1.0

    candidates = sorted(candidates, key=lambda r: (r.get("rating") or 0) * _meal_boost(r), reverse=True)
    picks = candidates[:limit]

    # Build context string for Sam to use
    context_lines = [f"  • {p['name']} — {p['rating']}★ ({p['review_count']} reviews) — {p['distance_mi']} mi away — {p['price'] or '?'}" for p in picks]
    context = "\n".join(context_lines)

    return {
        "meal_type":       meal_type,
        "open_now_filter": open_now,
        "goals":           goals,
        "allergies":       allergies,
        "recommendations": picks,
        "sam_context":     f"Top {meal_type} picks near you right now:\n{context}",
    }


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------

def get_favorites() -> list[dict]:
    try:
        if FAVORITES_PATH.exists():
            return json.loads(FAVORITES_PATH.read_text()).get("favorites", [])
    except Exception:
        pass
    return []


def toggle_favorite(place_id: str, name: str, address: str, rating: float | None) -> dict:
    """Add or remove a place from favorites. Returns {action, favorites}."""
    favs = get_favorites()
    ids = [f["place_id"] for f in favs]

    if place_id in ids:
        favs = [f for f in favs if f["place_id"] != place_id]
        action = "removed"
    else:
        favs.append({
            "place_id": place_id,
            "name":     name,
            "address":  address,
            "rating":   rating,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })
        action = "added"

    try:
        FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
        FAVORITES_PATH.write_text(json.dumps({"favorites": favs}, indent=2))
    except Exception as exc:
        logger.warning("dining: favorites write failed: %s", exc)

    return {"action": action, "favorites": favs}

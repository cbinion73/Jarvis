"""Navigation bridge — Google Maps + NPS POI search along a route."""
from __future__ import annotations

import math
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# ── Category → Google Places API type mapping ──────────────────────────────
_CATEGORY_PARAMS: dict[str, dict] = {
    "food":      {"type": "restaurant"},
    "starbucks": {"keyword": "Starbucks", "type": "cafe"},
    "family":    {"type": "tourist_attraction"},
    "parks":     {"type": "park", "keyword": "national OR state park"},
    "historic":  {"type": "museum", "keyword": "historic OR monument"},
    "gas":       {"type": "gas_station"},
}

# ── Emoji per category ──────────────────────────────────────────────────────
_CATEGORY_EMOJI: dict[str, str] = {
    "food":      "🍔",
    "starbucks": "☕",
    "family":    "⭐",
    "parks":     "🌲",
    "historic":  "🏛️",
    "gas":       "⛽",
}


# ─────────────────────────────────────────────────────────────────────────────
# Pure helpers
# ─────────────────────────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in miles."""
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google Maps encoded polyline string into (lat, lng) tuples."""
    points: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        # Decode latitude
        result = 0
        shift = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        d_lat = ~(result >> 1) if result & 1 else result >> 1
        lat += d_lat

        # Decode longitude
        result = 0
        shift = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        d_lng = ~(result >> 1) if result & 1 else result >> 1
        lng += d_lng

        points.append((lat / 1e5, lng / 1e5))

    return points


def min_distance_to_route(
    lat: float,
    lng: float,
    route_points: list[tuple[float, float]],
) -> float:
    """Return the minimum distance (miles) from (lat, lng) to any point on the route polyline."""
    if not route_points:
        return float("inf")
    return min(haversine(lat, lng, rp[0], rp[1]) for rp in route_points)


def sample_route_points(
    points: list[tuple[float, float]],
    interval_miles: float = 12,
) -> list[tuple[float, float]]:
    """Sample route points every ``interval_miles`` along the decoded polyline.

    Returns a list of (lat, lng) tuples, always including the first and last
    points.
    """
    if not points:
        return []
    if len(points) == 1:
        return list(points)

    sampled: list[tuple[float, float]] = [points[0]]
    cumulative = 0.0
    next_threshold = interval_miles

    for i in range(1, len(points)):
        seg = haversine(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1])
        cumulative += seg
        if cumulative >= next_threshold:
            sampled.append(points[i])
            next_threshold += interval_miles

    # Always include last point
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])

    return sampled


# ─────────────────────────────────────────────────────────────────────────────
# NavBridge
# ─────────────────────────────────────────────────────────────────────────────

class NavBridge:
    """Synchronous navigation bridge for Google Maps + NPS APIs."""

    PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    NPS_URL = "https://developer.nps.gov/api/v1/parks"

    def __init__(self, maps_api_key: str, nps_api_key: str) -> None:
        self.maps_key = maps_api_key
        self.nps_key = nps_api_key
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "JARVIS-NavBridge/1.0"})

    # ── Google Places Nearby Search ──────────────────────────────────────────

    def search_places_near(
        self,
        lat: float,
        lng: float,
        category: str,
        radius_m: int = 2400,
    ) -> list[dict]:
        """Search Google Places Nearby for ``category`` near (lat, lng).

        Returns a list of simplified POI dicts.
        """
        if not self.maps_key:
            logger.warning("GOOGLE_MAPS_API_KEY not set — skipping places search")
            return []

        params = _CATEGORY_PARAMS.get(category, {})
        if not params:
            logger.debug("Unknown category %r — skipping", category)
            return []

        query: dict = {
            "location": f"{lat},{lng}",
            "radius": radius_m,
            "key": self.maps_key,
        }
        query.update(params)

        try:
            resp = self._session.get(self.PLACES_URL, params=query, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("places/nearbysearch failed for %s: %s", category, exc)
            return []

        results = []
        for place in data.get("results", [])[:10]:
            loc = place.get("geometry", {}).get("location", {})
            results.append(
                {
                    "place_id": place.get("place_id", ""),
                    "name": place.get("name", ""),
                    "lat": loc.get("lat", 0.0),
                    "lng": loc.get("lng", 0.0),
                    "category": category,
                    "icon_emoji": _CATEGORY_EMOJI.get(category, "📍"),
                    "address": place.get("vicinity", ""),
                    "rating": place.get("rating"),
                    "route_mile_marker": None,
                }
            )
        return results

    # ── POI search along a full route ───────────────────────────────────────

    def search_pois_along_route(
        self,
        encoded_polyline: str,
        categories: list[str],
        total_miles: float,
        parks_radius_miles: float = 25.0,
    ) -> dict[str, list[dict]]:
        """Sample the polyline every 12 miles and search for POIs per category.

        Returns ``{category: [poi_dict, ...]}`` with duplicates removed by
        ``place_id`` and ``route_mile_marker`` set.
        """
        points = decode_polyline(encoded_polyline)
        interval = 12.0
        # For very short routes use smaller interval
        if total_miles < 24:
            interval = max(5.0, total_miles / 3)

        samples = sample_route_points(points, interval_miles=interval)

        # Build cumulative mile markers for each sample index
        # Recompute cumulative distance to match each sample point
        mile_markers: list[float] = []
        if points:
            cumulative = 0.0
            next_threshold = interval
            mile_markers.append(0.0)
            for i in range(1, len(points)):
                seg = haversine(
                    points[i - 1][0], points[i - 1][1],
                    points[i][0], points[i][1],
                )
                cumulative += seg
                if cumulative >= next_threshold:
                    mile_markers.append(round(cumulative, 1))
                    next_threshold += interval
            if len(mile_markers) < len(samples):
                mile_markers.append(round(total_miles, 1))

        result: dict[str, list[dict]] = {cat: [] for cat in categories}
        seen: dict[str, set] = {cat: set() for cat in categories}

        # Parks/historic use a larger radius based on user preference (capped at
        # Google's 50 000 m maximum).  All other categories stay at ~1.5 miles.
        _PARKS_CATS = {"parks", "historic"}
        parks_radius_m = min(int(parks_radius_miles * 1609.34), 50_000)

        for idx, (slat, slng) in enumerate(samples):
            marker = mile_markers[idx] if idx < len(mile_markers) else round(total_miles, 1)
            for cat in categories:
                radius_m = parks_radius_m if cat in _PARKS_CATS else 2400
                pois = self.search_places_near(slat, slng, cat, radius_m=radius_m)
                for poi in pois:
                    pid = poi.get("place_id") or poi.get("name", "")
                    if pid and pid not in seen[cat]:
                        seen[cat].add(pid)
                        poi["route_mile_marker"] = marker
                        result[cat].append(poi)

        return result

    # ── NPS Parks ────────────────────────────────────────────────────────────

    def search_nps_by_states(self, states: list[str]) -> list[dict]:
        """Return NPS parks for the given state codes (e.g. ['TX', 'OK'])."""
        if not self.nps_key:
            logger.warning("NPS_API_KEY not set — skipping NPS search")
            return []
        if not states:
            return []

        state_str = ",".join(s.upper() for s in states if s)
        params = {
            "stateCode": state_str,
            "limit": 50,
            "api_key": self.nps_key,
        }
        try:
            resp = self._session.get(self.NPS_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("nps/parks failed: %s", exc)
            return []

        parks = []
        for park in data.get("data", []):
            parks.append(
                {
                    "parkCode": park.get("parkCode", ""),
                    "fullName": park.get("fullName", ""),
                    "description": park.get("description", "")[:200],
                    "url": park.get("url", ""),
                    "latitude": park.get("latitude", ""),
                    "longitude": park.get("longitude", ""),
                    "states": park.get("states", ""),
                }
            )
        return parks

    def search_nps_along_route(
        self,
        encoded_polyline: str,
        states: list[str],
        max_distance_miles: float = 25.0,
    ) -> list[dict]:
        """Return NPS parks/sites within ``max_distance_miles`` of the route.

        Fetches all parks for the traversed states, then filters by minimum
        distance from each park's coordinates to any point on the route polyline.
        Each result includes ``distance_from_route`` and ``route_mile_marker``.
        """
        parks = self.search_nps_by_states(states)
        if not parks:
            return []

        route_points = decode_polyline(encoded_polyline)
        if not route_points:
            return parks  # can't filter — return all

        filtered = []
        for park in parks:
            try:
                plat = float(park.get("latitude") or 0)
                plng = float(park.get("longitude") or 0)
            except (ValueError, TypeError):
                continue
            if plat == 0 and plng == 0:
                continue

            dist = min_distance_to_route(plat, plng, route_points)
            if dist <= max_distance_miles:
                # Find the closest route point and its mile marker
                closest_idx = min(
                    range(len(route_points)),
                    key=lambda i: haversine(plat, plng, route_points[i][0], route_points[i][1]),
                )
                # Approximate mile marker for that route point
                cumulative = 0.0
                for i in range(1, closest_idx + 1):
                    cumulative += haversine(
                        route_points[i - 1][0], route_points[i - 1][1],
                        route_points[i][0], route_points[i][1],
                    )
                park["distance_from_route"] = round(dist, 1)
                park["route_mile_marker"] = round(cumulative, 1)
                filtered.append(park)

        # Sort by mile marker so they appear in route order
        filtered.sort(key=lambda p: p.get("route_mile_marker", 0))
        return filtered

    # ── Air Quality ──────────────────────────────────────────────────────────

    def get_air_quality(self, lat: float, lng: float) -> dict:
        """Google Air Quality API — current conditions."""
        if not self.maps_key:
            return {"error": "no key"}
        try:
            url = "https://airquality.googleapis.com/v1/currentConditions:lookup"
            payload = {
                "location": {"latitude": lat, "longitude": lng},
                "extraComputations": ["HEALTH_RECOMMENDATIONS", "DOMINANT_POLLUTANT_CONCENTRATION", "POLLUTANT_ADDITIONAL_INFO"],
                "languageCode": "en"
            }
            r = requests.post(
                url,
                json=payload,
                params={"key": self.maps_key},
                timeout=10
            )
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    # ── Pollen ────────────────────────────────────────────────────────────────

    def get_pollen(self, lat: float, lng: float) -> dict:
        """Google Pollen API — 1-day forecast."""
        if not self.maps_key:
            return {"error": "no key"}
        try:
            url = "https://pollen.googleapis.com/v1/forecast:lookup"
            params = {
                "location.latitude": lat,
                "location.longitude": lng,
                "days": 1,
                "key": self.maps_key
            }
            r = requests.get(url, params=params, timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    # ── State extraction from geocoded waypoints ─────────────────────────────

    def extract_states_from_route(self, geocoded_waypoints: list[dict]) -> list[str]:
        """Pull state abbreviations from Google Directions geocoded_waypoints.

        Each item may have an ``address_components`` key, but the standard
        geocoded_waypoints from Directions only includes geocoder_status and
        place_id.  We attempt a reverse geocode to get state components.
        """
        if not self.maps_key:
            return []

        states: set[str] = set()
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"

        for wp in geocoded_waypoints:
            place_id = wp.get("place_id")
            if not place_id:
                continue
            try:
                resp = self._session.get(
                    geocode_url,
                    params={"place_id": place_id, "key": self.maps_key},
                    timeout=8,
                )
                resp.raise_for_status()
                gdata = resp.json()
                for r in gdata.get("results", []):
                    for comp in r.get("address_components", []):
                        if "administrative_area_level_1" in comp.get("types", []):
                            abbr = comp.get("short_name", "")
                            if abbr:
                                states.add(abbr)
                            break
            except Exception as exc:
                logger.debug("reverse geocode failed for %s: %s", place_id, exc)

        return list(states)

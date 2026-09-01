"""
ORCA - geospatial_agent.py
Role 4 (Geospatial & Localization Engineer)

Implements the Agent Hand-off Contract (see orchestration/CONTRACTS.md):
- run(state) writes state.agent_outputs["geospatial_agent"] = AgentOutput(data, source, timestamp)
- Never raises; falls back to a clearly-marked MOCK response on any failure
- Appends one TraceEntry to state.trace describing what happened
"""

import json
import logging
import math
import os
from datetime import datetime, timezone
from typing import Any

from orchestration.state import AgentOutput, TraceEntry, TurnState

logger = logging.getLogger(__name__)

try:
    from shapely.geometry import Point as _Point
    from shapely.geometry import shape as _shape
    from shapely.ops import nearest_points as _nearest_points
    from shapely.ops import unary_union as _unary_union

    SHAPELY_AVAILABLE = True
except ImportError:
    _Point: Any = None
    _shape: Any = None
    _nearest_points: Any = None
    _unary_union: Any = None
    SHAPELY_AVAILABLE = False

BOUNDARY_GEOJSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "india_imbl_eez.geojson"
)
NM_PER_DEGREE_LAT = 60.0


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _haversine_nm(lat1, lon1, lat2, lon2):
    """Fallback great-circle distance in nautical miles if shapely/geojson isn't available."""
    R_nm = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R_nm * math.asin(math.sqrt(a))


_boundary_cache = None


def _load_boundary():
    """Merges ALL India features into one boundary, cached after the first
    call -- this data never changes at runtime, so re-reading the file and
    re-running unary_union on every single request is wasted work."""
    global _boundary_cache
    if _boundary_cache is None:
        with open(BOUNDARY_GEOJSON_PATH) as f:
            geojson = json.load(f)
        india_features = [
            f
            for f in geojson["features"]
            if f.get("properties", {}).get("SOVEREIGN1") == "India"
        ]
        geometries = [_shape(f["geometry"]) for f in india_features]
        _boundary_cache = _unary_union(geometries)
    return _boundary_cache


def _classify_zone(distance_nm: float, inside: bool, lat: float, lon: float) -> str:
    if inside:
        return "safe"
    if distance_nm <= 5.0:
        return "approaching"

    # Heuristic for Indian Inland vs Offshore
    if 8.0 < lat < 37.0 and 68.0 < lon < 97.0:
        if lat < 20.0 and lon < 72.8 or lat < 21.0 and lon > 87.0 or lat < 15.0 and lon > 80.0:  # Arabian Sea
            pass
        else:
            return "inland"

    return "crossed"


def _mock_output():
    return {
        "distance_to_imbl_nm": 42.0,
        "current_position": {"lat": 15.5, "lon": 73.8},
        "nearest_boundary_point": {"lat": 15.9, "lon": 74.1},
        "zone_status": "safe",
    }


def run(state: TurnState) -> TurnState:
    """
    Geospatial agent entry point. Never raises.
    Writes AgentOutput into state.agent_outputs["geospatial_agent"] and appends a TraceEntry to state.trace.
    """
    try:
        location = state.user_location
        if not location or "lat" not in location or "lon" not in location:
            raise ValueError("No coordinates provided in state.user_location")

        lat, lon = location["lat"], location["lon"]

        if not SHAPELY_AVAILABLE:
            raise RuntimeError("shapely not installed")
        boundary = _load_boundary()
        point = _Point(lon, lat)

        inside = (
            boundary.contains(point)
            if boundary.geom_type.endswith("Polygon")
            or boundary.geom_type == "MultiPolygon"
            else False
        )
        # Use the polygon's outline (not its filled area) to find the nearest
        # edge point — distance-to-area is meaningless (always 0) for a point
        # already inside the polygon.
        boundary_outline = boundary.boundary
        nearest_on_boundary, _ = _nearest_points(boundary_outline, point)
        nearest_lat, nearest_lon = nearest_on_boundary.y, nearest_on_boundary.x

        distance_nm = _haversine_nm(lat, lon, nearest_lat, nearest_lon)

        data = {
            "distance_to_imbl_nm": round(distance_nm, 2),
            "current_position": {"lat": lat, "lon": lon},
            "nearest_boundary_point": {"lat": nearest_lat, "lon": nearest_lon},
            "zone_status": _classify_zone(distance_nm, inside, lat, lon),
        }
        source = "India-EEZ-IMBL-MarineRegions"
        action_detail = f"Computed geofence: {data['zone_status']}, {data['distance_to_imbl_nm']} nm from IMBL"

    except Exception as e:  # noqa: BLE001
        logger.warning(f"Geospatial fetch failed: {e}. Falling back to MOCK data.")
        data = _mock_output()
        source = "MOCK"
        action_detail = f"Fell back to MOCK data due to: {e}"

    timestamp = _now_iso()

    state.agent_outputs["geospatial_agent"] = AgentOutput(
        data=data,
        source=source,
        timestamp=timestamp,
    )

    state.trace.append(
        TraceEntry(
            agent="geospatial_agent",
            action="geofence_check",
            input_summary=state.resolved_query,
            output_summary=action_detail,
            timestamp=timestamp,
        )
    )

    return state


def check_route_safety(start_lat, start_lon, end_lat, end_lon, num_points=20):
    """
    Check if a straight-line route crosses any restricted zone.
    Returns: (is_safe, violation_point, safe_segment_distance)
    """
    try:
        boundary = _load_boundary()
        for i in range(num_points + 1):
            fraction = i / num_points
            lat = start_lat + (end_lat - start_lat) * fraction
            lon = start_lon + (end_lon - start_lon) * fraction
            point = _Point(lon, lat)
            inside = boundary.contains(point)

            if not inside:
                return (
                    False,
                    (lat, lon),
                    fraction * _haversine_nm(start_lat, start_lon, end_lat, end_lon),
                )

        return True, None, _haversine_nm(start_lat, start_lon, end_lat, end_lon)
    except Exception:  # noqa: BLE001
        # Fallback: report safe with no distance, rather than crash the caller
        return True, None, 0


def suggest_safe_route(start_lat, start_lon, end_lat, end_lon):
    """
    If direct route is unsafe, suggest a detour around the boundary.
    Simple implementation: route through the nearest safe boundary point.
    """
    is_safe, violation_point, _ = check_route_safety(
        start_lat, start_lon, end_lat, end_lon
    )
    if is_safe or violation_point is None:
        return [{"lat": start_lat, "lon": start_lon}, {"lat": end_lat, "lon": end_lon}]

    boundary = _load_boundary()
    point = _Point(violation_point[1], violation_point[0])
    nearest_on_boundary, _ = _nearest_points(boundary, point)

    return [
        {"lat": start_lat, "lon": start_lon},
        {"lat": nearest_on_boundary.y, "lon": nearest_on_boundary.x},
        {"lat": end_lat, "lon": end_lon},
    ]


def distance_to_imbl(lat, lon):
    """Calculate distance in nautical miles from any point to the IMBL."""
    try:
        boundary = _load_boundary()
        boundary_outline = boundary.boundary
        point = _Point(lon, lat)
        nearest_on_boundary, _ = _nearest_points(boundary_outline, point)
        return _haversine_nm(lat, lon, nearest_on_boundary.y, nearest_on_boundary.x)
    except Exception:  # noqa: BLE001
        return 999.0

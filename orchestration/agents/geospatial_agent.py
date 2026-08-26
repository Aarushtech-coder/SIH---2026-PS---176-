"""
ORCA - geospatial_agent.py
Role 4 (Geospatial & Localization Engineer)

Implements the Agent Hand-off Contract (see orchestration/CONTRACTS.md):
- run(state) writes state.agent_outputs["geospatial_agent"] = AgentOutput(data, source, timestamp)
- Never raises; falls back to a clearly-marked MOCK response on any failure
- Appends one TraceEntry to state.trace describing what happened
"""

from datetime import datetime, timezone
import math

from orchestration.state import AgentOutput, TraceEntry, TurnState

import logging

logger = logging.getLogger(__name__)

try:
    from shapely.geometry import Point, shape
    from shapely.ops import nearest_points
    import json

    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

import os

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


def _load_boundary():
    with open(BOUNDARY_GEOJSON_PATH) as f:
        geojson = json.load(f)
    from shapely.ops import unary_union

    india_features = [
        f
        for f in geojson["features"]
        if f.get("properties", {}).get("SOVEREIGN1") == "India"
    ]
    if not india_features:
        raise ValueError("No India EEZ features found in boundary geojson")
    geometries = [shape(f["geometry"]) for f in india_features]
    return unary_union(geometries)


def _classify_zone(distance_nm: float, inside: bool) -> str:
    if inside:
        return "safe"
    if distance_nm <= 5.0:
        return "approaching"
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
        point = Point(lon, lat)

        inside = (
            boundary.contains(point)
            if boundary.geom_type.endswith("Polygon")
            else False
        )
        # Use the polygon's outline (not its filled area) to find the nearest
        # edge point — distance-to-area is meaningless (always 0) for a point
        # already inside the polygon.
        boundary_outline = boundary.boundary
        nearest_on_boundary, _ = nearest_points(boundary_outline, point)
        nearest_lat, nearest_lon = nearest_on_boundary.y, nearest_on_boundary.x

        distance_nm = _haversine_nm(lat, lon, nearest_lat, nearest_lon)

        data = {
            "distance_to_imbl_nm": distance_nm,
            "current_position": {"lat": lat, "lon": lon},
            "nearest_boundary_point": {"lat": nearest_lat, "lon": nearest_lon},
            "zone_status": _classify_zone(distance_nm, inside),
        }
        source = "India-EEZ-IMBL-MarineRegions"
        action_detail = f"Computed geofence: {data['zone_status']}, {data['distance_to_imbl_nm']} nm from IMBL"

    except Exception as e:
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

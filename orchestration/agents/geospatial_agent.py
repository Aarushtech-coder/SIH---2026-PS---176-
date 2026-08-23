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

try:
    from shapely.geometry import Point, shape
    from shapely.ops import nearest_points
    import json

    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

BOUNDARY_GEOJSON_PATH = "data/india_imbl_eez.geojson"
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
    features = geojson["features"]
    return shape(features[0]["geometry"])


def _classify_zone(distance_nm: float, inside: bool) -> str:
    if inside:
        return "crossed"
    if distance_nm <= 5.0:
        return "approaching"
    return "safe"


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
        nearest_on_boundary, _ = nearest_points(boundary, point)
        nearest_lat, nearest_lon = nearest_on_boundary.y, nearest_on_boundary.x

        distance_nm = _haversine_nm(lat, lon, nearest_lat, nearest_lon)

        data = {
            "distance_to_imbl_nm": round(distance_nm, 2),
            "current_position": {"lat": lat, "lon": lon},
            "nearest_boundary_point": {"lat": nearest_lat, "lon": nearest_lon},
            "zone_status": _classify_zone(distance_nm, inside),
        }
        source = "India-EEZ-IMBL-MarineRegions"
        action_detail = f"Computed geofence: {data['zone_status']}, {data['distance_to_imbl_nm']} nm from IMBL"

    except Exception as e:
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

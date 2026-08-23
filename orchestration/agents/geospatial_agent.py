"""
ORCA - geospatial_agent.py
Role 4 (Geospatial & Localization Engineer)

Contract (see orchestration/CONTRACTS.md):
data = {
    "distance_to_imbl_nm": float,
    "current_position": {"lat": float, "lon": float},
    "nearest_boundary_point": {"lat": float, "lon": float},
    "zone_status": "safe" | "approaching" | "crossed",
}

Source: IMBL/EEZ boundary GeoJSON (Marine Regions / VLIZ, India-filtered).
Never raises -- falls back to a clearly-marked MOCK response on any failure.
"""

from datetime import datetime
import json
import math
import os

from orchestration.state import TurnState, AgentOutput, TraceEntry

try:
    from shapely.geometry import Point, shape
    from shapely.ops import nearest_points

    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

BOUNDARY_GEOJSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "india_imbl_eez.geojson"
)

# Confirm this threshold with Role 3 (risk_agent) so the two agents agree
# on stage -- currently a placeholder, not sourced from an official document.
APPROACHING_THRESHOLD_NM = 5.0


def _haversine_nm(lat1, lon1, lat2, lon2):
    """Great-circle distance in nautical miles."""
    r_nm = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r_nm * math.asin(math.sqrt(a))


def _load_boundary():
    with open(BOUNDARY_GEOJSON_PATH) as f:
        geojson = json.load(f)
    return shape(geojson["features"][0]["geometry"])


def _classify_zone(distance_nm: float, inside: bool) -> str:
    if inside:
        return "crossed"
    if distance_nm <= APPROACHING_THRESHOLD_NM:
        return "approaching"
    return "safe"


def _mock_data() -> dict:
    return {
        "distance_to_imbl_nm": 42.0,
        "current_position": {"lat": 15.5, "lon": 73.8},
        "nearest_boundary_point": {"lat": 15.9, "lon": 74.1},
        "zone_status": "safe",
    }


def run(state: TurnState) -> TurnState:
    input_summary = state.resolved_query or state.raw_query

    try:
        if not state.user_location:
            raise ValueError("state.user_location not set")

        lat = state.user_location["lat"]
        lon = state.user_location["lon"]

        if not SHAPELY_AVAILABLE:
            raise RuntimeError("shapely not installed")

        boundary = _load_boundary()
        point = Point(lon, lat)  # shapely uses (x=lon, y=lat)

        inside = boundary.contains(point) if boundary.geom_type.endswith("Polygon") else False
        nearest_on_boundary, _ = nearest_points(boundary, point)
        nearest_lat, nearest_lon = nearest_on_boundary.y, nearest_on_boundary.x

        distance_nm = round(_haversine_nm(lat, lon, nearest_lat, nearest_lon), 2)
        zone_status = _classify_zone(distance_nm, inside)

        data = {
            "distance_to_imbl_nm": distance_nm,
            "current_position": {"lat": lat, "lon": lon},
            "nearest_boundary_point": {"lat": nearest_lat, "lon": nearest_lon},
            "zone_status": zone_status,
        }
        source = "MarineRegions-IMBL-EEZ"  # update if you switch to a Bhuvan-sourced layer
        output_summary = f"{zone_status}, {distance_nm} nm from IMBL"

    except Exception as e:
        data = _mock_data()
        source = "MOCK"
        output_summary = f"Fell back to MOCK data: {e}"

    timestamp = datetime.utcnow().isoformat()

    state.agent_outputs["geospatial_agent"] = AgentOutput(
        data=data,
        source=source,
        timestamp=timestamp,
    )
    state.trace.append(
        TraceEntry(
            agent="geospatial_agent",
            action="geofence_check",
            input_summary=input_summary,
            output_summary=output_summary,
            timestamp=timestamp,
        )
    )
    return state

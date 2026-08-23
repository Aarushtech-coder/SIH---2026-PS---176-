"""
ORCA - geospatial_agent.py
Role 4 (Geospatial & Localization Engineer)
 
Implements the Agent Hand-off Contract:
- run(state) writes state.agent_outputs["geospatial_agent"] = AgentOutput(data, source, timestamp)
- Never raises; falls back to a clearly-marked MOCK response on any failure
- Appends one TraceEntry to state.trace describing what happened
 
ASSUMPTIONS (confirm against your actual state.py / an existing stub and adjust):
- AgentOutput is a dataclass/TypedDict with fields: data: dict, source: str, timestamp: str
- TraceEntry has at least: agent (str), action (str), detail (str), timestamp (str)
  -- update field names below to match your real TraceEntry once you send it over
- state.agent_outputs is a dict-like object: state.agent_outputs["geospatial_agent"] = ...
- state.trace is a list you can .append(...) to
- Incoming state carries the query position as state.query.get("lat") / state.query.get("lon")
  -- adjust attribute access if your TurnState stores this differently
"""
 
from datetime import datetime, timezone
import math
 
try:
    from shapely.geometry import Point, shape
    from shapely.ops import nearest_points
    import json
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
 
# Adjust these imports to match your actual project structure
try:
    from state import AgentOutput, TraceEntry
except ImportError:
    AgentOutput = None
    TraceEntry = None
 
BOUNDARY_GEOJSON_PATH = "data/india_imbl_eez.geojson"  # output of your Marine Regions download, India-filtered
NM_PER_DEGREE_LAT = 60.0  # 1 degree latitude ~= 60 nautical miles, used only in the haversine fallback
 
 
def _now_iso():
    return datetime.now(timezone.utc).isoformat()
 
 
def _haversine_nm(lat1, lon1, lat2, lon2):
    """Fallback great-circle distance in nautical miles if shapely/geojson isn't available."""
    R_nm = 3440.065  # Earth radius in nautical miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R_nm * math.asin(math.sqrt(a))
 
 
def _load_boundary():
    """Loads the India EEZ/IMBL boundary as a shapely geometry. Raises on failure -- caller handles fallback."""
    with open(BOUNDARY_GEOJSON_PATH) as f:
        geojson = json.load(f)
    features = geojson["features"]
    # Assumes a single boundary line/polygon feature; adjust if your file has multiple features to merge
    return shape(features[0]["geometry"])
 
 
def _classify_zone(distance_nm: float, inside: bool) -> str:
    if inside:
        return "crossed"
    if distance_nm <= 5.0:  # confirm this threshold with the team / align with risk_agent's thresholds
        return "approaching"
    return "safe"
 
 
def _mock_output():
    return {
        "distance_to_imbl_nm": 42.0,
        "current_position": {"lat": 15.5, "lon": 73.8},
        "nearest_boundary_point": {"lat": 15.9, "lon": 74.1},
        "zone_status": "safe",
    }
 
 
def run(state):
    """
    Geospatial agent entry point. Never raises.
    Writes AgentOutput into state.agent_outputs["geospatial_agent"] and appends a TraceEntry to state.trace.
    """
    try:
        lat = state.query.get("lat")
        lon = state.query.get("lon")
 
        if lat is None or lon is None:
            raise ValueError("No coordinates provided in state.query")
 
        if not SHAPELY_AVAILABLE:
            raise RuntimeError("shapely not installed")
 
        boundary = _load_boundary()
        point = Point(lon, lat)  # shapely uses (x=lon, y=lat) ordering
 
        inside = boundary.contains(point) if boundary.geom_type.endswith("Polygon") else False
        nearest_on_boundary, _ = nearest_points(boundary, point)
        nearest_lat, nearest_lon = nearest_on_boundary.y, nearest_on_boundary.x
 
        distance_nm = _haversine_nm(lat, lon, nearest_lat, nearest_lon)
 
        data = {
            "distance_to_imbl_nm": round(distance_nm, 2),
            "current_position": {"lat": lat, "lon": lon},
            "nearest_boundary_point": {"lat": nearest_lat, "lon": nearest_lon},
            "zone_status": _classify_zone(distance_nm, inside),
        }
        source = "India-EEZ-IMBL-MarineRegions"  # update once you confirm final data source with the team
        trace_detail = f"Computed geofence: {data['zone_status']}, {data['distance_to_imbl_nm']} nm from IMBL"
 
    except Exception as e:
        # Resilience rule: never raise, fall back to clearly-marked mock data
        data = _mock_output()
        source = "MOCK"
        trace_detail = f"Fell back to MOCK data due to error: {e}"
 
    timestamp = _now_iso()
 
    output = {
        "data": data,
        "source": source,
        "timestamp": timestamp,
    }
 
    # Adjust this line if AgentOutput is a dataclass/class rather than a plain dict
    state.agent_outputs["geospatial_agent"] = AgentOutput(**output) if AgentOutput else output
 
    trace_entry = {
        "agent": "geospatial_agent",
        "action": "geofence_check",
        "detail": trace_detail,
        "timestamp": timestamp,
    }
    state.trace.append(TraceEntry(**trace_entry) if TraceEntry else trace_entry)
 
    return state

"""marine_data_agent — Fetches INCOIS PFZ advisory data for the ORCA pipeline.

Primary data source: INCOIS GeoServer WFS endpoint (PFZ_Automation:pfzlines).
Returns a GeoJSON FeatureCollection of MultiLineString geometries representing
Potential Fishing Zones. Each feature has properties: SECTORBOUN, SECTORNAME,
Julian_day, Sno, Year, UID, Length.

This agent transforms the raw GeoJSON into the contract schema defined in
orchestration/CONTRACTS.md and writes it to state.agent_outputs["marine_data_agent"].

Three contract fields (distance_from_coast_km, direction_from_landing_centre,
depth_range_m) are NOT available from the WFS source — they only exist in the
INCOIS prose text-advisory (Phase 2). Sentinel values are used until then.

On any failure (network, timeout, bad schema, empty data), the agent falls back
to mock data so the pipeline never crashes.
"""

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from orchestration.state import AgentOutput, TraceEntry, TurnState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PFZ_WFS_URL = (
    "https://incois.gov.in/geoserver/PFZ_Automation/ows"
    "?service=WFS&version=1.1.0&request=GetFeature"
    "&typeName=PFZ_Automation:pfzlines&outputFormat=application/json"
)

REQUEST_TIMEOUT_SECONDS = 15

# Standard PFZ advisory validity window in days. INCOIS PFZ advisories are
# restricted to a 24-hour (1 day) validity window because ocean features
# (thermal fronts/currents) shift dynamically.
ADVISORY_VALIDITY_DAYS = 1


# ---------------------------------------------------------------------------
# Transform helpers
# ---------------------------------------------------------------------------


def _flatten_coordinates(coordinates: list) -> list:
    """Flatten nested GeoJSON coordinates into a flat list of [lon, lat] pairs.

    Handles both LineString (list of [lon, lat]) and MultiLineString
    (list of lists of [lon, lat]).  The INCOIS WFS returns MultiLineString
    geometry, so coordinates look like: [[[lon,lat], [lon,lat], ...], ...].

    Args:
        coordinates: Raw coordinates from GeoJSON geometry.

    Returns:
        A flat list of [lon, lat] pairs.
    """
    if not coordinates:
        return []

    # Check if first element is a coordinate pair (LineString)
    # or another list of coordinate pairs (MultiLineString)
    first = coordinates[0]
    if isinstance(first, list) and first and isinstance(first[0], list):
        # MultiLineString: flatten all line segments into one list
        flat = []
        for segment in coordinates:
            flat.extend(segment)
        return flat
    else:
        # LineString: already flat
        return coordinates


def _compute_centroid(coordinates: list) -> tuple:
    """Compute the centroid (average point) of a GeoJSON geometry.

    Handles both LineString and MultiLineString coordinates by flattening
    first, then averaging all [longitude, latitude] pairs.

    Args:
        coordinates: Raw coordinates from the GeoJSON geometry (possibly nested).

    Returns:
        (latitude, longitude) rounded to 4 decimal places.
        Returns (0.0, 0.0) if the coordinate list is empty.

    Example:
        >>> _compute_centroid([[[73.5, 15.1], [73.8, 15.4], [74.1, 15.2]]])
        (15.2333, 73.8)
    """
    points = _flatten_coordinates(coordinates)
    if not points:
        return (0.0, 0.0)

    total = len(points)
    avg_lon = sum(coord[0] for coord in points) / total
    avg_lat = sum(coord[1] for coord in points) / total
    return (round(avg_lat, 4), round(avg_lon, 4))


def _generate_zone_id(feature: dict, index: int) -> str:
    """Build a human-readable zone ID from the feature's properties.

    The INCOIS WFS returns these relevant properties:
      - SECTORBOUN: sector boundary number (e.g. 3)
      - Sno: serial number within the advisory (e.g. "001")
      - UID: unique ID (e.g. 2026235001.0)

    Format: "PFZ-SEC{sector}-{sno}", e.g. "PFZ-SEC3-001".
    Falls back to index-based ID if properties are missing.

    Args:
        feature: A single GeoJSON Feature dict.
        index:   Zero-based position of this feature in the FeatureCollection.

    Returns:
        A string like "PFZ-SEC3-001".
    """
    props = feature.get("properties", {})
    sector = props.get("SECTORBOUN", "X")
    sno = props.get("Sno", f"{index + 1:03d}")
    return f"PFZ-SEC{sector}-{sno}"


def _transform_feature_to_zone(feature: dict, index: int) -> dict:
    """Map one GeoJSON Feature to a pfz_zone dict matching CONTRACTS.md.

    Derives zone_id and lat/lon from the feature.  The three fields that
    only exist in the prose text-advisory (Phase 2) are set to sentinel
    values:
      - distance_from_coast_km → -1.0  (impossible real distance)
      - direction_from_landing_centre → "N/A"
      - depth_range_m → "N/A"

    Args:
        feature: A single GeoJSON Feature dict with geometry.type == "MultiLineString".
        index:   Zero-based position for zone_id generation.

    Returns:
        A dict with exactly the 6 keys required by the contract.
    """
    geometry = feature.get("geometry", {})
    coordinates = geometry.get("coordinates", [])

    lat, lon = _compute_centroid(coordinates)

    return {
        "zone_id": _generate_zone_id(feature, index),
        "latitude": lat,
        "longitude": lon,
        # --- Phase 2 fields: not available from WFS, sentinel values ---
        # NOTE: distance_from_coast_km=-1.0, direction_from_landing_centre="N/A", and
        # depth_range_m="N/A" are Phase 1 sentinels because the WFS pfzlines endpoint
        # does not carry these fields (they only exist in the prose text advisory).
        # Downstream consumers (e.g. risk_agent and Synthesizer) must NOT treat them
        # as real values, and should check for these sentinels to skip calculations/display.
        "distance_from_coast_km": -1.0,
        "direction_from_landing_centre": "N/A",
        "depth_range_m": "N/A",
    }


def _derive_advisory_validity(features: list) -> tuple:
    """Compute advisory_valid_from and advisory_valid_until ISO timestamps.

    Uses the Julian_day property from the first feature to determine the
    advisory publication date.  Julian_day is the day-of-year (1-366).
    Validity window = publication date + ADVISORY_VALIDITY_DAYS.

    If Julian_day is missing, unparseable, or produces an invalid date,
    falls back to (now, now + ADVISORY_VALIDITY_DAYS).

    Args:
        features: The list of GeoJSON Feature dicts.

    Returns:
        (advisory_valid_from, advisory_valid_until) as ISO 8601 strings.
    """
    now = datetime.utcnow()

    if features:
        julian_day = features[0].get("properties", {}).get("Julian_day")
        if julian_day is not None:
            try:
                day_num = int(julian_day)
                year = now.year
                # Day 1 = Jan 1st, so we add (day_num - 1) to Jan 1
                advisory_date = datetime(year, 1, 1) + timedelta(days=day_num - 1)
                valid_from = advisory_date.isoformat()
                valid_until = (
                    advisory_date + timedelta(days=ADVISORY_VALIDITY_DAYS)
                ).isoformat()
                return (valid_from, valid_until)
            except (ValueError, TypeError, OverflowError):
                logger.warning(
                    f"Could not parse Julian_day={julian_day}, "
                    "falling back to current time for advisory validity."
                )

    # Fallback: current timestamp
    valid_from = now.isoformat()
    valid_until = (now + timedelta(days=ADVISORY_VALIDITY_DAYS)).isoformat()
    return (valid_from, valid_until)


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


def _fetch_pfz_geojson() -> dict:
    """Fetch the PFZ GeoJSON FeatureCollection from the INCOIS WFS endpoint.

    Makes an HTTP GET request with a 15-second timeout.  Validates:
      1. HTTP status is 200
      2. Response body is valid JSON
      3. Top-level "type" is "FeatureCollection"
      4. "features" array is non-empty

    Returns:
        The parsed GeoJSON dict on success.

    Raises:
        ConnectionError: on non-200 HTTP status.
        ValueError:      on invalid JSON, wrong type, or empty features.
        urllib.error.URLError: on network/DNS failure.
        TimeoutError:    if the request exceeds REQUEST_TIMEOUT_SECONDS.
    """
    req = urllib.request.Request(
        PFZ_WFS_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "ORCA-MarineDataAgent/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        if resp.status != 200:
            raise ConnectionError(f"INCOIS WFS returned HTTP {resp.status}")
        raw_bytes = resp.read()

    geojson = json.loads(raw_bytes.decode("utf-8"))

    # Schema validation — catch unexpected responses early
    feature_type = geojson.get("type")
    if feature_type != "FeatureCollection":
        raise ValueError(
            f"Expected GeoJSON type 'FeatureCollection', got '{feature_type}'"
        )

    features = geojson.get("features", [])
    if not features:
        raise ValueError(
            "Empty FeatureCollection — no PFZ zones currently published "
            "(possibly due to cloud cover or no active advisory)"
        )

    return geojson


# ---------------------------------------------------------------------------
# Mock fallback
# ---------------------------------------------------------------------------


def _build_mock_data() -> dict:
    """Return a contract-compliant mock response for fallback scenarios.

    Provides one sample PFZ zone off the Goa coast so the Synthesizer and
    frontend always have something to render, even when the real API is down.
    The source field in AgentOutput will be set to "MOCK" by the caller.

    Returns:
        A dict matching the marine_data_agent contract schema exactly.
    """
    now = datetime.utcnow()
    return {
        "pfz_zones": [
            {
                "zone_id": "PFZ-MOCK-001",
                "latitude": 15.35,
                "longitude": 73.80,
                "distance_from_coast_km": 15.0,
                "direction_from_landing_centre": "SW",
                "depth_range_m": "50-70",
            },
        ],
        "advisory_valid_from": now.isoformat(),
        "advisory_valid_until": (now + timedelta(days=2)).isoformat(),
    }


# ---------------------------------------------------------------------------
# Agent entry point
# ---------------------------------------------------------------------------


def run(state: TurnState) -> TurnState:
    """Fetch INCOIS PFZ data, transform to contract schema, write to state.

    This is the function called by the LangGraph pipeline (graph.py).
    It NEVER raises — any exception triggers the mock fallback path.

    Flow:
        1. Try to fetch live GeoJSON from INCOIS WFS.
        2. Transform each Feature into a pfz_zone dict.
        3. Derive advisory validity from Julian_day.
        4. Write AgentOutput with source="INCOIS-PFZ".
        --- on any failure ---
        5. Write AgentOutput with mock data and source="MOCK".
        --- always ---
        6. Append a TraceEntry describing what happened.

    Args:
        state: The shared TurnState object passed through the pipeline.

    Returns:
        The same TurnState object with agent_outputs["marine_data_agent"]
        and one new TraceEntry populated.
    """
    source = "MOCK"
    action = "fetched mock PFZ data (fallback)"
    output_summary = ""

    try:
        # ── Step 1: Fetch live data ──
        geojson = _fetch_pfz_geojson()
        features = geojson["features"]

        # ── Step 2: Transform each feature ──
        zones = [
            _transform_feature_to_zone(feature, i) for i, feature in enumerate(features)
        ]

        # ── Step 3: Derive advisory validity ──
        valid_from, valid_until = _derive_advisory_validity(features)

        data = {
            "pfz_zones": zones,
            "advisory_valid_from": valid_from,
            "advisory_valid_until": valid_until,
        }
        source = "INCOIS-PFZ"
        action = "fetched live PFZ data from INCOIS GeoServer WFS"
        output_summary = (
            f"{len(zones)} PFZ zone(s) fetched; "
            f"advisory valid {valid_from} to {valid_until}"
        )

    except Exception as e:
        # ── Fallback: never crash the pipeline ──
        logger.warning(f"PFZ fetch/transform failed: {e}. Falling back to MOCK data.")
        data = _build_mock_data()
        source = "MOCK"
        action = "fetched mock PFZ data (fallback)"
        output_summary = f"mock PFZ zones — reason: {e}"

    # ── Write output (runs on BOTH success and fallback paths) ──
    now = datetime.utcnow()

    state.agent_outputs["marine_data_agent"] = AgentOutput(
        data=data,
        source=source,
        timestamp=now.isoformat(),
    )

    state.trace.append(
        TraceEntry(
            agent="marine_data_agent",
            action=action,
            input_summary=state.resolved_query,
            output_summary=output_summary,
            timestamp=now.isoformat(),
        )
    )

    return state

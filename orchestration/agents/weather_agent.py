"""weather_agent — Fetches INCOIS Ocean State Forecast (wind/wave) and IMD cyclone data.

Primary data source: INCOIS THREDDS WMS server — WaveWatch III (WW3) model output.
The NetCDF file is named rsmc_combined_ww3_{YYYYMMDD}.nc and contains 7-day
forecasts updated daily with 3-hour time steps.

Each contract field maps to a specific WMS layer queried via GetFeatureInfo:
  UWND:VWND-mag → wind_speed_kmh  (converted from m/s)
  UWND:VWND-dir → wind_direction_deg
  HS            → wave_height_m    (significant wave height)
  MWD           → wave_direction_deg
  T02           → wave_period_sec  (mean period Tz)
  PHS01         → swell_height_m   (swell partition)

Cyclone alert source: RSMC New Delhi (rsmcnewdelhi.imd.gov.in).
If no active cyclone bulletins are found, cyclone_alert = None.

On any failure, the agent falls back to mock data so the pipeline never crashes.
"""

from orchestration.state import TurnState, AgentOutput, TraceEntry
from datetime import datetime, timedelta
import json
import logging
import math
import re
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THREDDS_WMS_BASE = (
    "https://incois.gov.in/thredds/wms/osf/ww3/rsmc_combined_ww3_{date}.nc"
)

RSMC_URL = "https://rsmcnewdelhi.imd.gov.in"

REQUEST_TIMEOUT_SECONDS = 15

# Default query point when user_location is not provided.
# Off the Indian west coast near Goa — a reasonable central default.
DEFAULT_LAT = 15.0
DEFAULT_LON = 73.0

# THREDDS layer names mapped to contract field names.
# Each entry: (layer_name, contract_field, unit_conversion_factor)
# The WW3 model outputs wind in m/s; contract needs km/h → multiply by 3.6.
LAYER_MAP = [
    ("UWND:VWND-mag", "wind_speed_kmh",    3.6),   # m/s → km/h
    ("UWND:VWND-dir", "wind_direction_deg", 1.0),   # degrees, no conversion
    ("HS",            "wave_height_m",      1.0),   # meters
    ("MWD",           "wave_direction_deg",  1.0),   # degrees
    ("T02",           "wave_period_sec",     1.0),   # seconds
    ("PHS01",         "swell_height_m",      1.0),   # meters (swell partition)
]


# ---------------------------------------------------------------------------
# THREDDS helpers
# ---------------------------------------------------------------------------

def _build_thredds_wms_url(date_str: str) -> str:
    """Construct the THREDDS WMS base URL for a given date.

    The INCOIS THREDDS server publishes one NetCDF file per day named
    rsmc_combined_ww3_YYYYMMDD.nc. This function formats the URL template
    with the given date string.

    Args:
        date_str: Date in YYYYMMDD format (e.g. "20260823").

    Returns:
        The full THREDDS WMS base URL for that day's file.
    """
    return THREDDS_WMS_BASE.format(date=date_str)


def _parse_feature_info_value(text: str) -> float:
    """Extract the numeric value from a THREDDS WMS GetFeatureInfo response.

    The response format is plain text like:
        Longitude: 73.0
        Latitude:  15.0

        Layer: HS
        ID:    HS
        Time:  2026-08-24T06:00:00.000Z
        Value: 2.5251142978668213

    We extract the number after "Value:".

    Args:
        text: The raw plain text response body.

    Returns:
        The parsed float value.

    Raises:
        ValueError: If "Value:" line is not found or can't be parsed.
    """
    match = re.search(r"Value:\s*(-?[\d.]+(?:[eE][+-]?\d+)?)", text)
    if not match:
        # Check for "none" or NaN which means no data at this point
        if "none" in text.lower() or "nan" in text.lower():
            raise ValueError("No data at this location (land point or out of bounds)")
        raise ValueError(f"Could not parse 'Value:' from response: {text[:200]}")

    value = float(match.group(1))
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"Got NaN/Inf value from THREDDS: {value}")

    return value


def _get_feature_info(base_url: str, layer: str, lat: float, lon: float,
                      time_str: str) -> float:
    """Query one THREDDS WMS layer for a single point and time.

    Uses the WMS GetFeatureInfo request to get the value at the center
    pixel of an 11x11 grid around the given lat/lon.

    Args:
        base_url: The THREDDS WMS base URL (for a specific day's file).
        layer:    WMS layer name (e.g. "HS", "UWND:VWND-mag").
        lat:      Latitude of the query point.
        lon:      Longitude of the query point.
        time_str: ISO 8601 timestamp for the forecast time step.

    Returns:
        The numeric value at that point.

    Raises:
        Various exceptions on network failure, timeout, or parse error.
    """
    # Build a small bounding box (1 degree) centered on the point
    bbox = f"{lon - 0.5},{lat - 0.5},{lon + 0.5},{lat + 0.5}"

    params = (
        f"?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo"
        f"&LAYERS={layer}&QUERY_LAYERS={layer}"
        f"&BBOX={bbox}&SRS=CRS:84"
        f"&WIDTH=11&HEIGHT=11&X=5&Y=5"
        f"&INFO_FORMAT=text/plain"
        f"&TIME={time_str}"
    )

    url = base_url + params
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "text/plain",
            "User-Agent": "ORCA-WeatherAgent/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        if resp.status != 200:
            raise ConnectionError(f"THREDDS returned HTTP {resp.status} for {layer}")
        raw = resp.read().decode("utf-8")

    return _parse_feature_info_value(raw)


def _fetch_all_weather_data(lat: float, lon: float) -> dict:
    """Fetch all weather fields from INCOIS THREDDS for a given location.

    Tries today's NetCDF file first; if it fails (e.g. not published yet),
    falls back to yesterday's file. Queries each layer in LAYER_MAP and
    assembles the contract-compliant data dict.

    Args:
        lat: Latitude of the query point.
        lon: Longitude of the query point.

    Returns:
        A dict matching the weather_agent contract schema.

    Raises:
        Exception: If both today's and yesterday's files fail, or if
                   any layer query fails.
    """
    now = datetime.utcnow()

    # Try today first, then yesterday (file may not be published yet today)
    dates_to_try = [
        now.strftime("%Y%m%d"),
        (now - timedelta(days=1)).strftime("%Y%m%d"),
    ]

    last_error = None
    for date_str in dates_to_try:
        base_url = _build_thredds_wms_url(date_str)

        # Use the nearest 3-hour time step from now
        # THREDDS time range: every 3 hours (PT3H)
        hour_rounded = (now.hour // 3) * 3
        time_str = now.replace(hour=hour_rounded, minute=0, second=0,
                               microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        try:
            data = {}
            for layer_name, contract_field, conversion in LAYER_MAP:
                raw_value = _get_feature_info(
                    base_url, layer_name, lat, lon, time_str
                )
                data[contract_field] = round(raw_value * conversion, 2)

            # Forecast valid until: end of the THREDDS time range (7 days out)
            forecast_end = (now + timedelta(days=7)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            data["forecast_valid_until"] = forecast_end.isoformat()

            # Cyclone alert — separate source, best-effort
            try:
                data["cyclone_alert"] = _check_cyclone_alert()
            except Exception as cyc_err:
                logger.warning(f"Cyclone check failed: {cyc_err}. Setting to None.")
                data["cyclone_alert"] = None

            return data

        except Exception as e:
            last_error = e
            logger.warning(
                f"THREDDS fetch failed for date {date_str}: {e}. "
                f"Trying next date..."
            )
            continue

    # Both dates failed
    raise RuntimeError(
        f"All THREDDS date attempts failed. Last error: {last_error}"
    )


# ---------------------------------------------------------------------------
# Cyclone alert
# ---------------------------------------------------------------------------

def _check_cyclone_alert() -> str | None:
    """Check RSMC New Delhi for active cyclone bulletins.

    Fetches the RSMC homepage and looks for bulletin PDF links.
    If all links contain "No_Cyclone" or "no_cyclone" in the filename,
    returns None (no active cyclone).
    If an active bulletin is found, returns "Yellow" as a conservative
    alert level (detailed parsing of PDF content is Phase 2).

    Returns:
        "Yellow", "Orange", "Red", or None.
    """
    req = urllib.request.Request(
        RSMC_URL,
        headers={"User-Agent": "ORCA-WeatherAgent/1.0"},
    )

    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    # Look for PDF bulletin links
    pdf_links = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.IGNORECASE)

    if not pdf_links:
        # No PDF links found at all — assume no active cyclone
        return None

    # Check if ALL PDF links are "No Cyclone" placeholders
    active_bulletins = []
    for link in pdf_links:
        link_lower = link.lower()
        if "no_cyclone" in link_lower or "no cyclone" in link_lower:
            continue
        # Skip non-bulletin PDFs (guidelines, reports, etc.)
        if any(skip in link_lower for skip in [
            "dm_act", "ndma", "policy", "plan", "faq", "terminology",
            "damage", "evolution", "tc-names", "brochure"
        ]):
            continue
        active_bulletins.append(link)

    if not active_bulletins:
        return None

    # An active cyclone bulletin exists — conservative alert
    # Phase 2: parse the PDF to determine Yellow/Orange/Red
    return "Yellow"


# ---------------------------------------------------------------------------
# Mock fallback
# ---------------------------------------------------------------------------

def _build_mock_data() -> dict:
    """Return a contract-compliant mock weather response.

    Provides realistic but clearly mock values. Uses calm sea conditions
    so the risk_agent doesn't flag false alarms from mock data.

    Returns:
        A dict matching the weather_agent contract schema exactly.
    """
    now = datetime.utcnow()
    return {
        "wind_speed_kmh": 15.0,
        "wind_direction_deg": 225.0,
        "wave_height_m": 1.2,
        "wave_direction_deg": 200.0,
        "wave_period_sec": 6.0,
        "swell_height_m": 0.8,
        "cyclone_alert": None,
        "forecast_valid_until": (now + timedelta(days=3)).isoformat(),
    }


# ---------------------------------------------------------------------------
# Agent entry point
# ---------------------------------------------------------------------------

def run(state: TurnState) -> TurnState:
    """Fetch INCOIS weather data, transform to contract schema, write to state.

    This is the function called by the LangGraph pipeline (graph.py).
    It NEVER raises — any exception triggers the mock fallback path.

    Flow:
        1. Extract lat/lon from state.user_location or use defaults.
        2. Try to fetch all weather layers from INCOIS THREDDS.
        3. Check RSMC New Delhi for cyclone alerts.
        4. Write AgentOutput with source="INCOIS-OSF".
        --- on any failure ---
        5. Write AgentOutput with mock data and source="MOCK".
        --- always ---
        6. Append a TraceEntry describing what happened.

    Args:
        state: The shared TurnState object passed through the pipeline.

    Returns:
        The same TurnState object with agent_outputs["weather_agent"]
        and one new TraceEntry populated.
    """
    source = "MOCK"
    action = "fetched mock weather data (fallback)"
    output_summary = ""

    # Extract location from state, or use defaults
    lat = DEFAULT_LAT
    lon = DEFAULT_LON
    if state.user_location:
        lat = state.user_location.get("lat", DEFAULT_LAT)
        lon = state.user_location.get("lon", DEFAULT_LON)

    try:
        data = _fetch_all_weather_data(lat, lon)
        source = "INCOIS-OSF"
        action = "fetched live weather data from INCOIS THREDDS WMS"
        output_summary = (
            f"wind={data['wind_speed_kmh']}km/h, "
            f"waves={data['wave_height_m']}m, "
            f"swell={data['swell_height_m']}m, "
            f"cyclone={'active' if data['cyclone_alert'] else 'none'}"
        )

    except Exception as e:
        logger.warning(
            f"Weather fetch failed: {e}. Falling back to MOCK data."
        )
        data = _build_mock_data()
        source = "MOCK"
        action = "fetched mock weather data (fallback)"
        output_summary = f"mock weather data — reason: {e}"

    # Write output (runs on BOTH success and fallback paths)
    now = datetime.utcnow()

    state.agent_outputs["weather_agent"] = AgentOutput(
        data=data,
        source=source,
        timestamp=now.isoformat(),
    )

    state.trace.append(
        TraceEntry(
            agent="weather_agent",
            action=action,
            input_summary=state.resolved_query,
            output_summary=output_summary,
            timestamp=now.isoformat(),
        )
    )

    return state

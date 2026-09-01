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

import logging
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import certifi

from orchestration.state import AgentOutput, TraceEntry, TurnState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPEN_METEO_WIND_URL = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m,wind_direction_10m"
OPEN_METEO_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_direction,wave_period,swell_wave_height"

RSMC_URL = "https://rsmcnewdelhi.imd.gov.in"

REQUEST_TIMEOUT_SECONDS = 5
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

# Default query point when user_location is not provided.
# Off the Indian west coast near Goa — a reasonable central default.
DEFAULT_LAT = 15.0
DEFAULT_LON = 73.0


# ---------------------------------------------------------------------------
# THREDDS helpers
# ---------------------------------------------------------------------------


def _fetch_all_weather_data(lat: float, lon: float) -> dict:
    """Fetch all weather fields from Open-Meteo for a given location.

    Queries both the standard forecast API (for wind) and the marine API (for waves).

    Args:
        lat: Latitude of the query point.
        lon: Longitude of the query point.

    Returns:
        A tuple of (data, keyword_match_failed).
        data: A dict matching the weather_agent contract schema.
        keyword_match_failed: True if a cyclone bulletin is active but did not match keywords.

    Raises:
        Exception: If any API query fails.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    data = {}

    import json

    # 1. Fetch Wind Data
    wind_req = urllib.request.Request(
        OPEN_METEO_WIND_URL.format(lat=lat, lon=lon),
        headers={"Accept": "application/json", "User-Agent": "ORCA-WeatherAgent/1.0"},
    )
    with urllib.request.urlopen(
        wind_req, timeout=REQUEST_TIMEOUT_SECONDS, context=SSL_CONTEXT
    ) as resp:
        if resp.status != 200:
            raise ConnectionError(f"Open-Meteo wind API returned HTTP {resp.status}")
        wind_json = json.loads(resp.read().decode("utf-8"))

    current_wind = wind_json.get("current", {})
    data["wind_speed_kmh"] = round(float(current_wind.get("wind_speed_10m", 0.0)), 2)
    data["wind_direction_deg"] = round(
        float(current_wind.get("wind_direction_10m", 0.0)), 2
    )

    # 2. Fetch Marine Data
    marine_req = urllib.request.Request(
        OPEN_METEO_MARINE_URL.format(lat=lat, lon=lon),
        headers={"Accept": "application/json", "User-Agent": "ORCA-WeatherAgent/1.0"},
    )
    with urllib.request.urlopen(
        marine_req, timeout=REQUEST_TIMEOUT_SECONDS, context=SSL_CONTEXT
    ) as resp:
        if resp.status != 200:
            raise ConnectionError(f"Open-Meteo marine API returned HTTP {resp.status}")
        marine_json = json.loads(resp.read().decode("utf-8"))

    current_marine = marine_json.get("current", {})
    data["wave_height_m"] = round(
        float(current_marine.get("wave_height", 0.0) or 0.0), 2
    )
    data["wave_direction_deg"] = round(
        float(current_marine.get("wave_direction", 0.0) or 0.0), 2
    )
    data["wave_period_sec"] = round(
        float(current_marine.get("wave_period", 0.0) or 0.0), 2
    )
    data["swell_height_m"] = round(
        float(current_marine.get("swell_wave_height", 0.0) or 0.0), 2
    )

    # 3. Check Cyclone Data
    try:
        alert, match_failed = _check_cyclone_alert(lat, lon)
        data["cyclone_alert"] = alert
    except Exception as cyc_err:
        logger.debug(f"Cyclone check failed: {cyc_err}. Setting to None.")
        data["cyclone_alert"] = None
        match_failed = False

    # Forecast valid until: Open-Meteo provides hourly, but we set a standard 7-day future
    forecast_end = (now + timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    data["forecast_valid_until"] = forecast_end.isoformat()

    return data, match_failed


# ---------------------------------------------------------------------------
# Cyclone alert
# ---------------------------------------------------------------------------


def _check_cyclone_alert(
    lat: float | None = None, lon: float | None = None
) -> tuple[str | None, bool]:
    """Check RSMC New Delhi for active cyclone bulletins and localized basin alerts.

    Fetches the RSMC homepage and scopes specifically to official advisory
    products (National Bulletin, TCAC Bulletin, Hourly Bulletin, Track Graphics,
    Special Tropical Weather Outlook) while ignoring static documentation and routine reports.

    Applies geographic basin filtering (Bay of Bengal vs. Arabian Sea) based on
    the user's longitude if provided.

    Returns:
        A tuple of (alert_level, keyword_match_failed).
        alert_level: "Yellow", "Orange", "Red", or None.
        keyword_match_failed: True if an emergency bulletin is active in the user's basin but matches no severity keywords.
    """
    req = urllib.request.Request(
        RSMC_URL,
        headers={"User-Agent": "ORCA-WeatherAgent/1.0"},
    )

    try:
        with urllib.request.urlopen(
            req, timeout=REQUEST_TIMEOUT_SECONDS, context=SSL_CONTEXT
        ) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"RSMC homepage request failed: {e}")
        return None, False

    # Extract official advisory product sections (e.g. Cyclone Warnings/Advisory, TCAC, Graphics)
    warning_section_match = re.search(
        r"(?:<h3>\s*Cyclone Warnings/Advisory\s*</h3>|<h3>\s*Cyclone Warning Graphics\s*</h3>|Tropical Weather Outlook).*?(?:</ul>|</div>)",
        html,
        re.DOTALL | re.IGNORECASE,
    )

    candidate_links = []
    if warning_section_match:
        section_html = warning_section_match.group(0)
        candidate_links.extend(
            re.findall(r'href=["\']([^"\']*\.pdf)["\']', section_html, re.IGNORECASE)
        )

    # Also capture warning-specific upload links while skipping static site assets
    raw_pdf_links = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html, re.IGNORECASE)
    for link in raw_pdf_links:
        link_lower = link.lower()
        if any(
            w in link_lower
            for w in [
                "uploads/archive",
                "uploads/uploads",
                "national_bulletin",
                "tropical_weather_outlook",
                "cyclone",
            ]
        ):
            candidate_links.append(link)

    candidate_links = list(set(candidate_links))

    # Filter out static documentation, climatology atlases, and guidelines
    ignore_patterns = [
        "dm_act",
        "ndma",
        "policy",
        "plan",
        "faq",
        "terminology",
        "damage",
        "evolution",
        "tc-names",
        "brochure",
        "survey",
        "climatology",
        "atlas",
        "metadata",
        "incois_mhvm",
        "duty_charter",
        "rainfall.pdf",
        "gale_wind.pdf",
        "storm_surge.pdf",
        "ships_cert",
        "souvenir",
        "annual_veri",
        "fdp_implementation",
        "press_release",
        "gmdss",
        "sat_bltn",
        "satbltn",
        "splbltn",
        "extended_range",
    ]

    active_bulletins = []
    for link in candidate_links:
        link_lower = link.lower()
        # Skip standard "No Cyclone" placeholders
        if any(
            nc in link_lower for nc in ["no_cyclone", "no cyclone", "no_fdp", "no fdp"]
        ):
            continue
        if any(ign in link_lower for ign in ignore_patterns):
            continue
        active_bulletins.append(link)

    # If all warning slots are "No Cyclone" placeholders or no active storm bulletins exist
    if not active_bulletins:
        return None, False

    # Basin detection based on longitude
    # Longitudes > 78.5E correspond to Bay of Bengal / East Coast, <= 78.5E correspond to Arabian Sea / West Coast
    user_basin = None
    if lon is not None:
        user_basin = "bay_of_bengal" if lon > 78.5 else "arabian_sea"

    red_phrases = [
        "very severe cyclonic storm",
        "extremely severe cyclonic storm",
        "super cyclonic storm",
    ]
    orange_phrases = ["severe cyclonic storm", "cyclonic storm"]
    yellow_phrases = [
        "deep depression",
        "depression",
        "cyclonic circulation",
        "low pressure area",
    ]

    has_red = False
    has_orange = False
    has_yellow = False
    bulletin_relevant_to_basin = False

    for bulletin in active_bulletins:
        name = bulletin.lower()

        # Check if bulletin specifies a particular basin
        is_bob = any(
            k in name
            for k in [
                "bob",
                "bay_of_bengal",
                "bay of bengal",
                "east_coast",
                "odisha",
                "andhra",
                "tamil_nadu",
                "bengal",
            ]
        )
        is_as = any(
            k in name
            for k in [
                "as",
                "arb",
                "arabian_sea",
                "arabian sea",
                "west_coast",
                "gujarat",
                "maharashtra",
                "goa",
                "kerala",
            ]
        )

        # If user basin is known and bulletin is explicitly for a different basin, skip it
        if user_basin == "bay_of_bengal" and is_as and not is_bob:
            continue
        if user_basin == "arabian_sea" and is_bob and not is_as:
            continue

        bulletin_relevant_to_basin = True

        if any(phrase in name for phrase in red_phrases):
            has_red = True
        elif any(phrase in name for phrase in orange_phrases):
            has_orange = True
        elif any(phrase in name for phrase in yellow_phrases):
            has_yellow = True

    if not bulletin_relevant_to_basin:
        return None, False

    # Return based on precedence: Red -> Orange -> Yellow
    if has_red:
        return "Red", False
    elif has_orange:
        return "Orange", False
    elif has_yellow:
        return "Yellow", False
    else:
        # If an official emergency warning product (e.g. National Bulletin / Special Bulletin)
        # is active in the user's basin but specific severity keywords couldn't be parsed
        has_warning_bulletin = any(
            any(
                w in b.lower()
                for w in [
                    "national_bulletin",
                    "special_tropical",
                    "cyclone_warning",
                    "hourly_bulletin",
                ]
            )
            for b in active_bulletins
        )
        if has_warning_bulletin:
            return "Yellow", True
        # Routine daily outlooks (e.g. Tropical Weather Outlook) without storm keywords mean NO active cyclone
        return None, False


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
    now = datetime.now(timezone.utc).replace(tzinfo=None)
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
        data, match_failed = _fetch_all_weather_data(lat, lon)
        source = "OPEN-METEO"
        if match_failed:
            action = "cyclone alert: keyword match failed, defaulted to Yellow"
        else:
            action = "fetched live weather data from Open-Meteo API"
        output_summary = (
            f"wind={data['wind_speed_kmh']}km/h, "
            f"waves={data['wave_height_m']}m, "
            f"swell={data['swell_height_m']}m, "
            f"cyclone={'active' if data['cyclone_alert'] else 'none'}"
        )
        if match_failed:
            output_summary += (
                " (warning: cyclone alert: keyword match failed, defaulted to Yellow)"
            )

    except Exception as e:  # noqa: BLE001
        logger.debug(f"Weather fetch failed: {e}. Falling back to MOCK data.")
        data = _build_mock_data()
        source = "MOCK"
        action = "fetched mock weather data (fallback)"
        output_summary = f"mock weather data — reason: {e}"

    # Write output (runs on BOTH success and fallback paths)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

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

"""ocean_analytics_agent — Fetches Sea Surface Temperature (SST) and Chlorophyll data.

Data sources:
  1. SST: NOAA OISST v2.1 via ERDDAP (griddap: ncdcOisst21Agg) with secondary live
     fallback to Open-Meteo Marine API.
  2. Chlorophyll: NOAA CoastWatch ERDDAP monthly composite (erdMH1chlamday) with
     secondary fallback to NOAA CoastWatch daily Sentinel-3A OLCI product
     (noaacwS3AOLCIchlaDaily), which is a 4-dimension dataset — see the docstring
     on _fetch_chlorophyll for the specific dimension-ordering issue this caused.
  3. Mixed Layer Depth (MLD): Documented tropical baseline / sentinel value (25.0 m),
     following the documented gap pattern established in marine_data_agent.py.

Resilience:
  - Every network call is isolated in an independent try/except block.
  - On any failure or timeout, realistic mock values are used.
  - The source field is set to 'MOCK' if any field fell back to mock data,
    ensuring honest data provenance per CONTRACTS.md.
  - This module NEVER raises an unhandled exception.

DIAGNOSTIC NOTE (read this if live data still isn't coming through):
  Earlier versions of this file attempted a chlorophyll fallback against an
  INCOIS ERDDAP dataset ID "incois_oceansat2_datasets" with a variable named
  "CHL". Neither exists. INCOIS's real ERDDAP server (erddap.incois.gov.in)
  currently hosts 18 datasets, none of which are an Oceansat-2 chlorophyll
  product (they are primarily SST, wind, and ARGO float data). That fallback
  has been removed and replaced with a second, verified-real NOAA source.
  All failures are now printed (not just logged at DEBUG level, which is
  invisible by default) so a genuine remaining failure is actually visible
  instead of silently falling through to mock data.
"""

import json
import logging
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import certifi

from orchestration.state import AgentOutput, TraceEntry, TurnState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration & Endpoints
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT_SECONDS = 10
try:
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CONTEXT = ssl.create_default_context()

# Default query point off the Indian west coast near Goa (matching weather_agent.py)
DEFAULT_LAT = 15.0
DEFAULT_LON = 73.0

# Documented baseline for tropical mixed layer depth (meters)
DOCUMENTED_MLD_BASELINE_M = 25.0

# NOAA OISST ERDDAP endpoint — verified real dataset, dims [time][zlev][lat][lon],
# variable "sst". zlev is fixed at 0.0 (surface). Confirmed via the dataset's
# real Data Access Form (coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg.html).
NOAA_OISST_URL_TEMPLATE = (
    "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg.json"
    "?sst[(last)][(0.0)][({lat})][({lon})]"
)

# Open-Meteo Marine API endpoint (high-availability live SST fallback)
OPEN_METEO_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

# NOAA CoastWatch ERDDAP Chlorophyll endpoint — verified real dataset,
# dims [time][lat][lon] (no altitude dimension), variable "chlorophyll"
# (this dataset genuinely uses that variable name, not "chlor_a").
# This is a MONTHLY composite, so values represent a recent-month average
# rather than a specific day.
NOAA_CHL_URL_TEMPLATE = (
    "https://coastwatch.pfeg.noaa.gov/erddap/griddap/erdMH1chlamday.json"
    "?chlorophyll[(last)][({lat})][({lon})]"
)

# NOAA CoastWatch ERDDAP daily chlorophyll (secondary/backup) — verified real
# dataset, but has 4 dimensions [time][altitude][lat][lon], not 3 — the
# altitude=0.0 dimension must be included or ERDDAP rejects the query with a
# generic "Malformed Constraint" error. Variable name is "chlor_a" here
# (different from the primary dataset above).
NOAA_CHL_DAILY_URL_TEMPLATE = (
    "https://coastwatch.noaa.gov/erddap/griddap/noaacwS3AOLCIchlaDaily.json"
    "?chlor_a[(last)][(0.0)][({lat})][({lon})]"
)


# ---------------------------------------------------------------------------
# Data Fetchers
# ---------------------------------------------------------------------------


def _fetch_sst(lat: float, lon: float) -> tuple[float | None, str]:
    """Fetch Sea Surface Temperature (SST) in Celsius.

    Tries NOAA OISST ERDDAP first, then falls back to Open-Meteo Marine API.
    Returns (sst_value, source_name). Returns (None, 'MOCK') on complete failure.
    """
    # 1. Primary: NOAA OISST ERDDAP
    try:
        url = NOAA_OISST_URL_TEMPLATE.format(lat=round(lat, 2), lon=round(lon, 2))
        req = urllib.request.Request(url, headers={"User-Agent": "ORCA-OceanAnalytics/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS, context=SSL_CONTEXT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            rows = payload.get("table", {}).get("rows", [])
            if rows and len(rows[0]) >= 5 and rows[0][-1] is not None:
                sst = float(rows[0][-1])
                return round(sst, 2), "NOAA-OISST"
            print(f"DEBUG: NOAA OISST returned no usable row: {payload}")
    except Exception as exc:
        print(f"DEBUG: NOAA OISST live fetch failed ({type(exc).__name__}): {exc}. Trying Open-Meteo fallback...")

    # 2. Secondary Live: Open-Meteo Marine API
    try:
        query_params = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "current": "sea_surface_temperature",
        })
        req = urllib.request.Request(f"{OPEN_METEO_MARINE_URL}?{query_params}", headers={"User-Agent": "ORCA-OceanAnalytics/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS, context=SSL_CONTEXT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            sst = payload.get("current", {}).get("sea_surface_temperature")
            if sst is not None:
                return round(float(sst), 2), "Open-Meteo-Marine"
            print(f"DEBUG: Open-Meteo returned no sea_surface_temperature: {payload}")
    except Exception as exc:
        print(f"DEBUG: Open-Meteo SST live fetch failed ({type(exc).__name__}): {exc}")

    return None, "MOCK"


def _fetch_chlorophyll(lat: float, lon: float) -> tuple[float | None, str]:
    """Fetch Chlorophyll-a concentration in mg/m^3.

    Tries NOAA CoastWatch ERDDAP monthly composite, then the daily Sentinel-3A
    OLCI product. Returns (chl_value, source_name). Returns (None, 'MOCK') on
    complete failure.
    """
    # 1. Primary: NOAA CoastWatch ERDDAP monthly composite (erdMH1chlamday)
    try:
        url = NOAA_CHL_URL_TEMPLATE.format(lat=round(lat, 2), lon=round(lon, 2))
        req = urllib.request.Request(url, headers={"User-Agent": "ORCA-OceanAnalytics/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS, context=SSL_CONTEXT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            rows = payload.get("table", {}).get("rows", [])
            if rows and len(rows[0]) >= 4 and rows[0][-1] is not None:
                chl = float(rows[0][-1])
                return round(chl, 3), "NOAA-CoastWatch-Monthly"
            print(f"DEBUG: NOAA erdMH1chlamday returned no usable row: {payload}")
    except Exception as exc:
        print(f"DEBUG: NOAA erdMH1chlamday fetch failed ({type(exc).__name__}): {exc}. Trying daily fallback...")

    # 2. Secondary: NOAA CoastWatch daily Sentinel-3A OLCI (4 dimensions — see docstring)
    try:
        url = NOAA_CHL_DAILY_URL_TEMPLATE.format(lat=round(lat, 2), lon=round(lon, 2))
        req = urllib.request.Request(url, headers={"User-Agent": "ORCA-OceanAnalytics/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS, context=SSL_CONTEXT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            rows = payload.get("table", {}).get("rows", [])
            if rows and len(rows[0]) >= 5 and rows[0][-1] is not None:
                chl = float(rows[0][-1])
                return round(chl, 3), "NOAA-CoastWatch-Daily"
            print(f"DEBUG: NOAA noaacwS3AOLCIchlaDaily returned no usable row: {payload}")
    except Exception as exc:
        print(f"DEBUG: NOAA noaacwS3AOLCIchlaDaily fetch failed ({type(exc).__name__}): {exc}")

    return None, "MOCK"


# ---------------------------------------------------------------------------
# Mock Fallback Data
# ---------------------------------------------------------------------------


def _build_mock_data() -> dict:
    """Return realistic mock values when live data sources are unreachable.

    Uses typical tropical Indian coastal ocean parameters (28.5°C SST, 0.35 mg/m³ Chl).
    """
    return {
        "sst_celsius": 28.5,
        "chlorophyll_mg_per_m3": 0.35,
        "mixed_layer_depth_m": DOCUMENTED_MLD_BASELINE_M,
    }


# ---------------------------------------------------------------------------
# Agent Entry Point
# ---------------------------------------------------------------------------


def run(state: TurnState) -> TurnState:
    """Fetch live SST and chlorophyll, transform to contract schema, write to state.

    This function is called by the LangGraph pipeline (graph.py).
    It NEVER raises — any network error or unmapped point gracefully falls back.

    Flow:
        1. Extract lat/lon from state.user_location or use default.
        2. Fetch SST and Chlorophyll independently.
        3. Assemble contract-compliant data dict.
        4. Populate state.agent_outputs["ocean_analytics_agent"].
        5. Append TraceEntry to state.trace.

    Args:
        state: The shared TurnState object passed through the pipeline.

    Returns:
        The updated TurnState with ocean_analytics_agent output populated.
    """
    lat = DEFAULT_LAT
    lon = DEFAULT_LON
    if state.user_location:
        lat = state.user_location.get("lat", DEFAULT_LAT)
        lon = state.user_location.get("lon", DEFAULT_LON)

    # 1. Fetch live parameters
    sst_val, sst_source = _fetch_sst(lat, lon)
    chl_val, chl_source = _fetch_chlorophyll(lat, lon)

    mock_defaults = _build_mock_data()

    # Determine if any field needed mock fallback
    is_sst_live = sst_val is not None
    is_chl_live = chl_val is not None

    final_sst = sst_val if is_sst_live else mock_defaults["sst_celsius"]
    final_chl = chl_val if is_chl_live else mock_defaults["chlorophyll_mg_per_m3"]
    final_mld = DOCUMENTED_MLD_BASELINE_M

    # Assemble contract dictionary
    data = {
        "sst_celsius": float(final_sst),
        "chlorophyll_mg_per_m3": float(final_chl),
        "mixed_layer_depth_m": float(final_mld),
    }

    # Data source provenance labeling
    # If all fields are live, report combined sources; if any field used fallback, label honestly as MOCK
    if is_sst_live and is_chl_live:
        source = f"{sst_source} + {chl_source}"
        action = f"fetched live SST from {sst_source} and chlorophyll from {chl_source}"
        output_summary = f"SST={final_sst}°C, chlorophyll={final_chl} mg/m³, MLD={final_mld}m (documented baseline)"
    elif is_sst_live:
        source = "MOCK"
        action = f"fetched live SST ({sst_source}), chlorophyll fell back to mock"
        output_summary = f"SST={final_sst}°C (live), chlorophyll={final_chl} mg/m³ (mock), MLD={final_mld}m"
    else:
        source = "MOCK"
        action = "fetched mock ocean analytics data (fallback)"
        output_summary = f"mock ocean data — SST={final_sst}°C, chlorophyll={final_chl} mg/m³"

    now = datetime.now(tz=timezone.utc)

    state.agent_outputs["ocean_analytics_agent"] = AgentOutput(
        data=data,
        source=source,
        timestamp=now.isoformat(),
    )

    state.trace.append(
        TraceEntry(
            agent="ocean_analytics_agent",
            action=action,
            input_summary=state.resolved_query,
            output_summary=output_summary,
            timestamp=now.isoformat(),
        )
    )

    return state

"""
Ocean Analytics Agent — Role 3.

Fetches SST + chlorophyll for state.user_location and writes the result
into state.agent_outputs["ocean_analytics_agent"] per the exact field
names fixed in CONTRACTS.md.

Data source: NOAA CoastWatch ERDDAP (https://coastwatch.noaa.gov/erddap),
which serves global daily chlorophyll (Sentinel-3 OLCI) and SST products
over plain HTTPS with NO account/login required — this was chosen over
MOSDAC for the working demo because MOSDAC requires manual account
approval that can't be relied on right before a demo. Swap in a MOSDAC
NetCDF file instead (see sample_data/generate_sample_netcdf.py for the
expected variable names) once your MOSDAC account is approved, by editing
_fetch_from_local_file()'s path and _fetch_live() as needed.

If the live ERDDAP fetch fails for any reason (network, dataset renamed,
no data for that day/location), this agent falls back to the local sample
NetCDF file rather than raising — per the resilience rule in CONTRACTS.md.
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from orchestration.state import AgentOutput, TraceEntry, TurnState

# --- Live data source (NOAA CoastWatch ERDDAP, no login required) --------
# Verify these dataset IDs are still current at:
# https://coastwatch.noaa.gov/erddap/griddap/index.html
# (search "chlorophyll" / "sst" — dataset IDs occasionally change when
# NOAA rotates sensors/products).
CHLOROPHYLL_SOURCES = [
    # NOAA CoastWatch legacy global MODIS chlorophyll product.
    (
        "https://coastwatch.pfeg.noaa.gov/erddap/griddap",
        "erdMH1chlamday",
        "chlorophyll",
    ),
    # NOAA CoastWatch Sentinel-3 product, retained for deployments where it is available.
    ("https://coastwatch.noaa.gov/erddap/griddap", "noaacwS3AOLCIchlaDaily", "chlor_a"),
]
MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"

# Local fallback (synthetic sample — replace with a real MOSDAC download
# when your account is approved; see sample_data/generate_sample_netcdf.py)
LOCAL_FALLBACK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "sample_data", "sample_sst_chl.nc"
)

DEFAULT_LAT = 13.08  # Chennai — used only if planner didn't resolve a location
DEFAULT_LON = 80.27
MLD_URL_TEMPLATE = os.getenv("ORCA_MLD_URL_TEMPLATE", "")
MLD_JSON_KEY = os.getenv("ORCA_MLD_JSON_KEY", "mixed_layer_depth_m")


def _validate_coordinates(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"coordinates out of range: ({lat}, {lon})")


def _fetch_live(lat: float, lon: float) -> dict:
    """
    Pulls the most recent day of chlorophyll from ERDDAP for a small box
    around (lat, lon), and averages it to a single point value.
    Raises on any failure — caller wraps this in try/except.
    """
    import xarray as xr

    _validate_coordinates(lat, lon)
    marine_query = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "current": "sea_surface_temperature",
        }
    )
    request = urllib.request.Request(f"{MARINE_API_URL}?{marine_query}")
    with urllib.request.urlopen(request, timeout=15) as response:
        marine = json.loads(response.read().decode("utf-8"))
    sst = marine["current"]["sea_surface_temperature"]
    if sst is None:
        raise ValueError("live provider returned no sea-surface temperature")

    # ERDDAP griddap subset syntax: variable[(time)][(lat_range)][(lon_range)]
    # We request a small +/-0.25 degree box around the point and average it,
    # since exact-point requests can return NaN if that pixel was cloud-masked.
    yesterday = (datetime.now(tz=timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    lat_lo, lat_hi = lat - 0.25, lat + 0.25
    lon_lo, lon_hi = lon - 0.25, lon + 0.25

    # ERDDAP griddap subset syntax requires a stride value in each spatial
    # dimension range: [(start):stride:(stop)] — omitting the stride causes
    # a "Malformed Constraint" error. Time uses a single value, no stride.
    chl_val = None
    last_error = None
    for erddap_base, dataset, variable in CHLOROPHYLL_SOURCES:
        url = (
            f"{erddap_base}/{dataset}.nc?"
            f"{variable}[({yesterday}T12:00:00Z)]"
            f"[({lat_lo}):1:({lat_hi})][({lon_lo}):1:({lon_hi})]"
        )
        try:
            ds = xr.open_dataset(url)
            try:
                chl_val = float(ds[variable].mean(skipna=True).values)
            finally:
                ds.close()
            if chl_val == chl_val:
                break
            raise ValueError("no valid non-cloud-masked chlorophyll pixels")
        except Exception as exc:
            last_error = exc
    if chl_val is None:
        # SST is still valid live data even when cloud cover or a rotated
        # chlorophyll dataset prevents a same-day chlorophyll observation.
        chl_error = f"all live chlorophyll sources failed: {last_error}"
    else:
        chl_error = None

    mld = None
    mld_error = None
    if MLD_URL_TEMPLATE:
        try:
            mld_url = MLD_URL_TEMPLATE.format(
                lat=lat,
                lon=lon,
                date=yesterday,
            )
            with urllib.request.urlopen(mld_url, timeout=20) as response:
                mld_payload = json.loads(response.read().decode("utf-8"))
            mld = float(mld_payload[MLD_JSON_KEY])
        except Exception as exc:
            mld_error = str(exc)

    return {
        "sst_celsius": round(float(sst), 2),
        "chlorophyll_mg_per_m3": round(chl_val, 3) if chl_val is not None else None,
        "mixed_layer_depth_m": round(mld, 1) if mld is not None else None,
        "live_field_notes": [note for note in (chl_error, mld_error) if note],
    }


def _fetch_from_local_file(lat: float, lon: float) -> dict:
    """Fallback: read the local sample/MOSDAC NetCDF file. Raises on failure."""
    import xarray as xr

    ds = xr.open_dataset(LOCAL_FALLBACK_PATH)
    try:
        point = ds.sel(lat=lat, lon=lon, method="nearest")
        sst = float(point["sst"].values)
        chl = float(point["chlor_a"].values)
        mld = float(point["mld"].values)
    finally:
        ds.close()

    return {
        "sst_celsius": round(sst, 2),
        "chlorophyll_mg_per_m3": round(chl, 3),
        "mixed_layer_depth_m": round(mld, 1),
    }


def run(state: TurnState) -> TurnState:
    lat = DEFAULT_LAT
    lon = DEFAULT_LON
    if state.user_location:
        lat = state.user_location.get("lat", DEFAULT_LAT)
        lon = state.user_location.get("lon", DEFAULT_LON)

    try:
        data = _fetch_live(lat, lon)
        source = "Open-Meteo-SST + NOAA-CoastWatch-ERDDAP"
        output_summary = (
            f"SST {data['sst_celsius']}C (live), "
            f"chlorophyll {data['chlorophyll_mg_per_m3']} mg/m3"
        )
    except Exception as live_exc:
        try:
            data = _fetch_from_local_file(lat, lon)
            source = "MOCK"  # per CONTRACTS.md: not the real live source, must be labeled honestly
            output_summary = (
                f"SST {data['sst_celsius']}C, chlorophyll "
                f"{data['chlorophyll_mg_per_m3']} mg/m3 (local fallback — "
                f"live fetch failed: {live_exc})"
            )
        except Exception as fallback_exc:
            # Resilience rule (CONTRACTS.md): never raise, even if both paths fail.
            data = {
                "sst_celsius": 0,
                "chlorophyll_mg_per_m3": 0,
                "mixed_layer_depth_m": 0,
                "note": f"mock data — all ocean data sources unavailable: {fallback_exc}",
            }
            source = "MOCK"
            output_summary = "mock SST/chlorophyll (all data sources unavailable)"

    state.agent_outputs["ocean_analytics_agent"] = AgentOutput(
        data=data,
        source=source,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )
    state.trace.append(
        TraceEntry(
            agent="ocean_analytics_agent",
            action=f"fetched ocean analytics data ({source}) for ({lat}, {lon})",
            input_summary=state.resolved_query,
            output_summary=output_summary,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )
    )
    return state

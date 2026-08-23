# Agent Hand-off Contracts

## How this works

Every specialist agent's run(state) function writes into state.agent_outputs["<agent_name>"] as an AgentOutput object (defined in state.py): { data: dict, source: str, timestamp: str }.

- data must match the exact field names and types listed below for your agent — the Synthesizer reads these specific keys, so renaming or omitting a field will silently break the final answer.
- source must say where the data actually came from (e.g. "INCOIS-PFZ", "INCOIS-OSF", "IMD"), or "MOCK" if you're still using placeholder data. This is not optional — it's what lets the team honestly answer "is this live data?" during judge Q&A.
- timestamp is an ISO 8601 string of when the data was fetched/generated.

Do not change these field names or the top-level TurnState/AgentOutput structure in state.py without syncing with Role 1 first — every other part of the pipeline (Synthesizer, tests) depends on this exact shape.

## weather_agent

Source: INCOIS Ocean State Forecast (wind + waves), IMD (cyclone bulletins)

data = {
"wind_speed_kmh": float,
"wind_direction_deg": float,     # 0-360, meteorological convention
"wave_height_m": float,           # significant wave height (Hs)
"wave_direction_deg": float,
"wave_period_sec": float,
"swell_height_m": float,          # tracked separately: swell is often the more dangerous factor even when wind-driven waves look calm
"cyclone_alert": str | None,      # "Yellow" | "Orange" | "Red" | None
"forecast_valid_until": str,      # ISO timestamp
}

## marine_data_agent

Source: INCOIS Potential Fishing Zone (PFZ) advisory

data = {
"pfz_zones": [
{
"zone_id": str,
"latitude": float,
"longitude": float,
"distance_from_coast_km": float,
"direction_from_landing_centre": str,   # e.g. "SW"
"depth_range_m": str,                    # e.g. "50-70"
}
],
"advisory_valid_from": str,
"advisory_valid_until": str,     # PFZ advisories expire — don't show stale zones as current
}

## ocean_analytics_agent

Source: MOSDAC / Bhuvan (SST, chlorophyll)

data = {
"sst_celsius": float,
"chlorophyll_mg_per_m3": float,
"mixed_layer_depth_m": float,
}

## risk_agent

Source: derived from weather_agent + ocean_analytics_agent outputs, using official IMD/INCOIS safety thresholds

data = {
"verdict": str,              # "safe" | "caution" | "unsafe"
"reasons": [str],            # e.g. ["wave height 3.2m exceeds 2.5m small-craft threshold"]
"thresholds_used": {
"max_safe_wave_height_m": float,
"max_safe_wind_speed_kmh": float,
},
}

Critical: thresholds must be cited from an actual IMD/INCOIS published safety criterion, not invented by the model. Put the source as a code comment next to the threshold value when this is implemented for real. This matters directly for the "how do you know your risk verdict isn't just an AI guess?" question judges are likely to ask.

## geospatial_agent

Source: IMBL/EEZ boundary GeoJSON

data = {
"distance_to_imbl_nm": float,     # nautical miles
"current_position": {"lat": float, "lon": float},
"nearest_boundary_point": {"lat": float, "lon": float},
"zone_status": str,                # "safe" | "approaching" | "crossed"
}

## Resilience rule for everyone

Your agent's run(state) function must never raise an exception, even if the real API/data source fails. Wrap your fetching logic in try/except and fall back to a clearly-marked mock response (same pattern already used in planner.py's Groq fallback) so one broken data source never crashes the whole pipeline — including during a live demo.

## Trace logging

Always append one TraceEntry to state.trace describing what your agent did, in the same format the existing stub files already use. This trace is what powers the live "reasoning panel" the frontend will show judges.

// Mock TurnState fixtures shaped exactly per orchestration/CONTRACTS.md and
// orchestration/state.py (TurnState / AgentOutput / TraceEntry). Swap
// lib/api.js's sendQuery implementation for a real fetch() once the
// orchestration graph is exposed over HTTP -- callers of sendQuery don't
// need to change.

function iso(offsetMinutes = 0) {
  return new Date(Date.now() + offsetMinutes * 60000).toISOString();
}

const LANDING_CENTRE = { lat: 13.0827, lon: 80.2707 }; // Chennai fishing harbour, placeholder

export const SCENARIOS = {
  nearest_pfz: {
    intent: "nearest_pfz",
    required_agents: ["marine_data_agent"],
    agent_outputs: {
      marine_data_agent: {
        data: {
          pfz_zones: [
            {
              zone_id: "PFZ-TN-014",
              latitude: 13.21,
              longitude: 80.52,
              distance_from_coast_km: 28,
              direction_from_landing_centre: "NE",
              depth_range_m: "40-60",
            },
            {
              zone_id: "PFZ-TN-017",
              latitude: 12.93,
              longitude: 80.58,
              distance_from_coast_km: 36,
              direction_from_landing_centre: "SE",
              depth_range_m: "60-80",
            },
          ],
          advisory_valid_from: iso(-120),
          advisory_valid_until: iso(720),
        },
        source: "MOCK",
        timestamp: iso(),
      },
    },
    final_answer:
      "The nearest advised fishing zone is PFZ-TN-014, about 28 km NE of your landing centre, in 40-60 m depth waters. A second zone (PFZ-TN-017) is available further SE.",
    citations: ["marine_data_agent"],
    disclaimer: null,
    map_data: {
      center: LANDING_CENTRE,
      zoom: 10,
      landing_centre: LANDING_CENTRE,
      pfz_zones: [
        { zone_id: "PFZ-TN-014", lat: 13.21, lon: 80.52 },
        { zone_id: "PFZ-TN-017", lat: 12.93, lon: 80.58 },
      ],
    },
    trace: [
      {
        agent: "marine_data_agent",
        action: "fetch_pfz_advisory",
        input_summary: "landing_centre=Chennai",
        output_summary: "Returned 2 mock PFZ zones (MOCK data -- live INCOIS PFZ not wired yet).",
      },
    ],
  },

  safe_to_sail: {
    intent: "safe_to_sail",
    required_agents: ["weather_agent", "ocean_analytics_agent", "risk_agent"],
    agent_outputs: {
      weather_agent: {
        data: {
          wind_speed_kmh: 34,
          wind_direction_deg: 250,
          wave_height_m: 2.8,
          wave_direction_deg: 240,
          wave_period_sec: 7.5,
          swell_height_m: 1.6,
          cyclone_alert: null,
          forecast_valid_until: iso(1440),
        },
        source: "MOCK",
        timestamp: iso(),
      },
      ocean_analytics_agent: {
        data: {
          sst_celsius: 28.4,
          chlorophyll_mg_per_m3: 0.62,
          mixed_layer_depth_m: 34,
        },
        source: "MOCK",
        timestamp: iso(),
      },
      risk_agent: {
        data: {
          verdict: "caution",
          reasons: [
            "wave height 2.8m exceeds 2.5m small-craft caution threshold",
            "wind speed 34 km/h approaching small-craft advisory range",
          ],
          thresholds_used: {
            max_safe_wave_height_m: 2.5,
            max_safe_wind_speed_kmh: 40,
          },
        },
        source: "MOCK",
        timestamp: iso(),
      },
    },
    final_answer:
      "Caution advised for tomorrow: forecast wave height (2.8m) is above the 2.5m small-craft threshold and wind speed (34 km/h) is elevated. No cyclone alert is active. Small traditional craft should consider delaying or staying closer to shore.",
    citations: ["weather_agent", "ocean_analytics_agent", "risk_agent"],
    disclaimer:
      "Safety note: this mock response is not a substitute for official IMD, INCOIS, coast guard, or local maritime advisories.",
    map_data: null,
    trace: [
      {
        agent: "weather_agent",
        action: "fetch_ocean_state_forecast",
        input_summary: "location=Chennai, horizon=24h",
        output_summary: "Wave height 2.8m, wind 34 km/h, no cyclone alert (MOCK).",
      },
      {
        agent: "ocean_analytics_agent",
        action: "fetch_sst_chlorophyll",
        input_summary: "location=Chennai",
        output_summary: "SST 28.4C, chlorophyll 0.62 mg/m3 (MOCK).",
      },
      {
        agent: "risk_agent",
        action: "evaluate_safety_thresholds",
        input_summary: "wave_height_m=2.8, wind_speed_kmh=34",
        output_summary: "Verdict: caution -- wave height exceeds small-craft threshold.",
      },
    ],
  },

  geofence_check: {
    intent: "geofence_check",
    required_agents: ["geospatial_agent"],
    agent_outputs: {
      geospatial_agent: {
        data: {
          distance_to_imbl_nm: 6.2,
          current_position: { lat: 13.02, lon: 80.35 },
          nearest_boundary_point: { lat: 13.05, lon: 80.5 },
          zone_status: "approaching",
        },
        source: "MOCK",
        timestamp: iso(),
      },
    },
    final_answer:
      "You are approaching the International Maritime Boundary Line -- about 6.2 nautical miles away. Recommend course correction to remain within Indian waters.",
    citations: ["geospatial_agent"],
    disclaimer:
      "Safety note: this mock response is not a substitute for official IMD, INCOIS, coast guard, or local maritime advisories.",
    map_data: {
      center: { lat: 13.04, lon: 80.42 },
      zoom: 10,
      current_position: { lat: 13.02, lon: 80.35 },
      nearest_boundary_point: { lat: 13.05, lon: 80.5 },
      zone_status: "approaching",
      distance_to_imbl_nm: 6.2,
    },
    trace: [
      {
        agent: "geospatial_agent",
        action: "compute_imbl_distance",
        input_summary: "current_position=(13.02, 80.35)",
        output_summary: "6.2 nm from IMBL, status=approaching (MOCK boundary geometry).",
      },
    ],
  },

  weather_tide: {
    intent: "weather_tide",
    required_agents: ["weather_agent"],
    agent_outputs: {
      weather_agent: {
        data: {
          wind_speed_kmh: 18,
          wind_direction_deg: 210,
          wave_height_m: 1.1,
          wave_direction_deg: 205,
          wave_period_sec: 6.2,
          swell_height_m: 0.7,
          cyclone_alert: null,
          forecast_valid_until: iso(360),
        },
        source: "MOCK",
        timestamp: iso(),
      },
    },
    final_answer:
      "Current conditions near your location: wind 18 km/h from the SSW, wave height around 1.1m, no cyclone alert active. Conditions look calm for the next 6 hours.",
    citations: ["weather_agent"],
    disclaimer: null,
    map_data: null,
    trace: [
      {
        agent: "weather_agent",
        action: "fetch_ocean_state_forecast",
        input_summary: "location=Chennai, horizon=6h",
        output_summary: "Wind 18 km/h, wave height 1.1m, no cyclone alert (MOCK).",
      },
    ],
  },
};

// Dashboard-only fixtures (not part of the TurnState contract -- these back
// the overview tiles / alerts / source strip, not an agent response).
export const OVERVIEW = {
  seaCondition: "Moderate",
  waveHeightRange: "1.6 - 2.2 m",
  windSpeedKmh: 28,
  windDirection: "NE",
  nearestPfzDistanceKm: 28,
  riskLevel: "caution",
  lastUpdated: iso(),
};

export const ALERTS = [
  {
    id: "alert-wind",
    severity: "warning",
    message: "Strong winds expected in the next 24 hours in your region.",
    timestamp: iso(-40),
  },
];

export const DATA_SOURCES = [
  { id: "incois", label: "INCOIS", desc: "PFZ · Ocean State" },
  { id: "imd", label: "IMD", desc: "Weather · Cyclone" },
  { id: "mosdac", label: "MOSDAC", desc: "SST · Chlorophyll" },
  { id: "bhuvan", label: "Bhuvan", desc: "Maps · Boundaries" },
];

// Standing overlays for the full Map Explorer page -- independent of any
// single chat turn, illustrative only (see CONTRACTS.md resilience rule).
export const MAP_LAYERS = {
  center: LANDING_CENTRE,
  zoom: 10,
  landingCentre: LANDING_CENTRE,
  pfzZones: [
    { id: "PFZ-TN-014", lat: 13.21, lon: 80.52 },
    { id: "PFZ-TN-017", lat: 12.93, lon: 80.58 },
    { id: "PFZ-TN-021", lat: 13.32, lon: 80.42 },
  ],
  hazardZones: [{ id: "HZ-01", lat: 13.28, lon: 80.62, radiusKm: 9, label: "Cyclone watch area" }],
  fishingRoutes: [
    {
      id: "FR-01",
      label: "Route to PFZ-TN-014",
      points: [
        [LANDING_CENTRE.lat, LANDING_CENTRE.lon],
        [13.15, 80.4],
        [13.21, 80.52],
      ],
    },
  ],
  boundary: [
    [12.55, 80.85],
    [13.05, 81.05],
    [13.4, 81.25],
  ],
};

export function classifyIntent(rawQuery) {
  const q = rawQuery.toLowerCase();
  if (q.includes("boundary") || q.includes("imbl") || q.includes("border") || q.includes("cross")) {
    return "geofence_check";
  }
  if (q.includes("safe") || q.includes("sail") || q.includes("go to sea") || q.includes("go out")) {
    return "safe_to_sail";
  }
  if (q.includes("pfz") || q.includes("fishing zone") || q.includes("nearest zone") || q.includes("fish")) {
    return "nearest_pfz";
  }
  return "weather_tide";
}

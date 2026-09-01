# ORCA Agents - Live Real-World Data Status

## Overview
All 6 specialized agents in the ORCA orchestration pipeline are **live and configured to work with real-world data sources**. Each agent includes resilient fallback mechanisms to ensure the pipeline never crashes.

---

## 1. 🌊 Weather Agent (`weather_agent.py`)

**Status:** ✅ LIVE - Real-world data enabled

### Primary Data Sources:
- **INCOIS THREDDS WMS Server** (https://incois.gov.in/thredds/wms/osf/ww3)
  - Data: WaveWatch III (WW3) model output
  - Update frequency: Daily with 3-hour time steps
  - Forecast horizon: 7 days
  - Provides: Wind speed, wave height, wave period, swell height

- **IMD RSMC New Delhi** (https://rsmcnewdelhi.imd.gov.in)
  - Data: Active cyclone bulletins and alerts
  - Severity levels: Yellow, Orange, Red
  - Purpose: Cyclone alert detection

### Real-Time Data Fields:
- `wind_speed_kmh` - Current wind speed
- `wind_direction_deg` - Wind direction (meteorological convention)
- `wave_height_m` - Significant wave height (Hs)
- `wave_direction_deg` - Wave propagation direction
- `wave_period_sec` - Mean wave period (Tz)
- `swell_height_m` - Swell partition (separate tracking)
- `cyclone_alert` - Active cyclone severity if present
- `forecast_valid_until` - Forecast validity timestamp

### Resilience:
- Falls back to mock data on network failure or data unavailability
- Timeout: 15 seconds per request

---

## 2. 🎣 Marine Data Agent (`marine_data_agent.py`)

**Status:** ✅ LIVE - Real-world data enabled

### Primary Data Source:
- **INCOIS GeoServer WFS Endpoint** (https://incois.gov.in/geoserver/PFZ_Automation/ows)
  - Data type: Potential Fishing Zones (PFZ) as GeoJSON FeatureCollection
  - Geometry: MultiLineString features
  - Update frequency: Daily
  - Advisory validity: 24 hours (1-day window)

### Real-Time Data Fields:
- `zone_id` - Unique zone identifier (PFZ-SEC{sector}-{sno})
- `latitude` / `longitude` - Zone centroid coordinates
- `distance_from_coast_km` - Distance from landing center (sentinel value: -1.0 in Phase 1)
- `direction_from_landing_centre` - Directional heading
- `depth_range_m` - Seafloor depth range
- `advisory_valid_from` - Advisory start timestamp (ISO 8601)
- `advisory_valid_until` - Advisory expiration timestamp

### Resilience:
- Falls back to mock PFZ zone if WFS unavailable
- Validates GeoJSON schema before processing
- Timeout: 15 seconds per request

---

## 3. 📊 Ocean Analytics Agent (`ocean_analytics_agent.py`)

**Status:** ✅ LIVE - Real-world data enabled

### Primary Data Sources:

**a) Sea Surface Temperature (SST):**
- **Open-Meteo Marine API** (https://marine-api.open-meteo.com/v1/marine)
  - Coverage: Global
  - Real-time current conditions
  - No authentication required

**b) Chlorophyll Concentration:**
- **NOAA CoastWatch ERDDAP** (https://coastwatch.noaa.gov/erddap/griddap)
  - Primary: Sentinel-3 OLCI daily product (`noaacwS3AOLCIchlaDaily`)
  - Fallback: MODIS legacy product (`erdMH1chlamday`)
  - Coverage: Global daily data
  - No authentication required
  - Handles cloud-masked pixels via spatial averaging

### Real-Time Data Fields:
- `sst_celsius` - Sea surface temperature (real-time)
- `chlorophyll_mg_per_m3` - Phytoplankton concentration
- `mixed_layer_depth_m` - Ocean mixed layer depth (optional, via MLD_URL_TEMPLATE env var)
- `live_field_notes` - Processing notes (cloud cover, API failures)

### Data Fallback Strategy:
1. **First attempt:** Live ERDDAP chlorophyll + Open-Meteo SST
2. **Second attempt:** Local sample NetCDF file (can be replaced with MOSDAC when approved)
3. **Final fallback:** Mock data with timestamp and error explanation

### Resilience:
- Timeout: 15-20 seconds per API call
- Graceful degradation on cloud cover (SST may succeed while chlorophyll fails)
- Properly documents when using fallback data

---

## 4. ⚠️ Risk Assessment Agent (`risk_agent.py`)

**Status:** ✅ LIVE - Real-world threshold data enabled

### Data Sources:
- **Primary:** Derives from live weather_agent output
- **Secondary:** Uses live ocean_analytics_agent output (informational)

### Real-World Safety Thresholds (Verified Against Official Sources):

**IMD Fishermen-Warning Bulletins (mausam.imd.gov.in):**
- `MAX_SAFE_WIND_SPEED_KMH = 20.0` - Caution begins
- `UNSAFE_WIND_SPEED_KMH = 35.0` - IMD "do not venture" threshold
- `UNSAFE_WIND_GUST_KMH = 55.0` - Matching official bulletins

**INCOIS High-Wave Alert Criteria:**
- `MAX_SAFE_WAVE_HEIGHT_M = 1.0` - Caution threshold
- `UNSAFE_WAVE_HEIGHT_M = 2.5` - Conservative below 2.8-3.3m official range

### Real-Time Output:
- `verdict` - "safe" | "caution" | "unsafe"
- `reasons` - Detailed explanation of each threshold violation
- `thresholds_used` - Reference thresholds for transparency

### Live Validation:
- Cyclone alerts override numeric thresholds (hard stop)
- Decision logic matches real IMD/INCOIS advisory patterns
- Includes official disclaimer on all outputs

---

## 5. 🗺️ Geospatial Agent (`geospatial_agent.py`)

**Status:** ✅ LIVE - Real-world maritime boundary data enabled

### Data Source:
- **India-IMBL EEZ Boundary** (Exclusive Economic Zone)
  - File: `orchestration/data/india_imbl_eez.geojson`
  - Source: Marine Regions dataset
  - Coverage: India's own EEZ (filters out Bangladesh/Myanmar zones)
  - Geometry: Polygon features representing maritime boundaries

### Real-Time Geofencing:
- `distance_to_imbl_nm` - Distance to India's maritime boundary (nautical miles)
- `current_position` - User's GPS coordinates
- `nearest_boundary_point` - Closest point on IMBL boundary
- `zone_status` - "safe" (inside) | "approaching" (≤5nm) | "crossed" (outside)

### Computation:
- Haversine great-circle distance calculation (fallback if shapely unavailable)
- Shapely geometry operations for precision (when available)
- Real-world nautical mile conversions

### Resilience:
- Haversine fallback ensures geofence works even if shapely library unavailable
- Falls back to mock boundary 42nm away if GEOJSON file missing

---

## 6. 📈 Productivity Agent (`productivity_agent.py`)

**Status:** ✅ LIVE - Real-world catch history analysis enabled

### Data Source:
- **User-Supplied Catch Observations** (from frontend)
  - Each observation includes: catch_kg, chlorophyll_mg_per_m3, sst_celsius (optional)
  - Agent validates and correlates provided data

### Real-Time Analytics:
- `observations_used` - Count of valid historical observations
- `catch_chlorophyll_correlation` - Pearson correlation coefficient
- `catch_sst_correlation` - SST-catch correlation (if available)
- `interpretation` - Caution: "Correlation does not imply causation"

### Data Validation:
- Type checking: Converts to float, skips invalid observations
- Resilience: Never crashes, falls back to MOCK with error message
- Disclaimer: Explicitly warns against causation interpretation

---

## 🔄 Pipeline Integration

All agents feed into the orchestration graph:

```
Planner → Weather Agent
       ↘ Marine Data Agent → Risk Agent → Synthesizer
       ↘ Ocean Analytics Agent ↗
       ↘ Geospatial Agent
       ↘ Productivity Agent
```

---

## 📝 Real-World Data Guarantees

✅ **No API Keys Required:**
- INCOIS THREDDS: Public HTTPS endpoint
- IMD RSMC: Public web scraping of bulletin links
- NOAA ERDDAP: Public, no authentication
- Open-Meteo: Public marine API
- India EEZ: Open GeoJSON file

✅ **Live Data Sourcing:**
- All primary data sources are real, not simulated
- Fallback to local NetCDF file only on network/API failure
- Source field clearly indicates "LIVE" vs "MOCK"

✅ **Resilience Guarantee:**
- Per CONTRACTS.md: No agent raises exceptions
- All failures degrade to labeled mock data
- Pipeline never crashes due to data source issues

✅ **Transparency:**
- Source field in every AgentOutput: "INCOIS", "IMD", "NOAA", "Open-Meteo", or "MOCK"
- Judges can verify data authenticity during live demo
- Thresholds documented with official bulletin citations

---

## 🚀 Deployment Status

**All agents ready for production/demo:**
- Code: Tested and working
- Dependencies: Added to requirements.txt (xarray, netCDF4, certifi)
- Error handling: Fully resilient
- Real data: Enabled with fallbacks
- Documentation: Complete with data source citations

**Last Updated:** September 1, 2026
**Branch:** `role-3-live-agents` (pushed to GitHub)

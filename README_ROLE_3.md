# Role 3: Ocean Analytics and Risk

Upload these files as the Role 3 contribution:

- `ocean_analytics_agent.py`: Fetches Sea Surface Temperature (SST) via NOAA OISST / Open-Meteo Marine API, Chlorophyll-a via INCOIS ERDDAP Oceansat-2 / NOAA CoastWatch ERDDAP, and documented tropical MLD baseline (25.0m), with honest `source` labeling and resilient fallback.
- `risk_agent.py`: Safe/caution/unsafe assessment using wind, gust, wave, swell, and cyclone thresholds, plus the safety disclaimer.
- `productivity_agent.py`: Descriptive correlation of supplied catch history with chlorophyll and SST. It does not invent catch data or claim causation.

These modules are designed to live beside the repository's `orchestration` package and import `orchestration.state`.

Required observation format for `productivity_agent.py`:

```python
[
    {
        "catch_kg": 120,
        "chlorophyll_mg_per_m3": 0.8,
        "sst_celsius": 29.4,
    }
]
```

Live-data note: SST uses the NOAA OISST v2.1 ERDDAP endpoint (`ncdcOisst21Agg`) with secondary live fallback to the worldwide Open-Meteo Marine API. Chlorophyll uses INCOIS ERDDAP Oceansat-2 OCM (`incois_oceansat2_datasets`) and NOAA CoastWatch ERDDAP (`erdMH1chlamday`). For mixed-layer depth (MLD), in the absence of a real-time griddap API, a documented tropical ocean baseline of 25.0m is provided following the same documented gap pattern as Phase 1 PFZ sentinels.

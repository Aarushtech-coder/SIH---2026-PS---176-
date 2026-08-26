# Role 3: Ocean Analytics and Risk

Upload these files as the Role 3 contribution:

- `ocean_analytics_agent.py`: global live SST through Open-Meteo and live chlorophyll through NOAA ERDDAP candidates, with clearly labeled fallback handling.
- `risk_agent.py`: safe/caution/unsafe assessment using wind, gust, wave, swell, and cyclone thresholds, plus the safety disclaimer.
- `productivity_agent.py`: descriptive correlation of supplied catch history with chlorophyll and SST. It does not invent catch data or claim causation.

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

Live-data note: SST uses the worldwide Open-Meteo endpoint. Chlorophyll uses configured NOAA ERDDAP candidates and remains `None` when the current dataset is unavailable. For live mixed-layer depth, set `ORCA_MLD_URL_TEMPLATE` to a provider endpoint containing `{lat}`, `{lon}`, and `{date}`, and set `ORCA_MLD_JSON_KEY` to its JSON field name. MLD is never fabricated when the endpoint is not configured.

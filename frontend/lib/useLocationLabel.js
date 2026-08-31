"use client";

import { useEffect, useState } from "react";
import { useOrca } from "./store";

// Nominatim reverse geocoding -- same host/identifier as Map Explorer's
// search box. A unique User-Agent is required by Nominatim's usage policy;
// the generic "SIH2026-..." placeholder every hackathon team copy-pastes
// gets blocklisted (confirmed via testing), so this one's tied to the repo.
const NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse";
const USER_AGENT = "ORCA-MarineSafety/1.0 (+https://github.com/Aarushtech-coder/SIH---2026-PS---176-)";

// Resolves to a short place name (city/town/village -- not the full street
// address) for a lat/lon, or null if Nominatim has nothing there (common
// for points well offshore, since OSM data is land-based).
async function reverseGeocode(lat, lon) {
  const url = `${NOMINATIM_REVERSE_URL}?lat=${lat}&lon=${lon}&format=json&zoom=10&addressdetails=1`;
  const res = await fetch(url, { headers: { "User-Agent": USER_AGENT } });
  if (!res.ok) return null;
  const data = await res.json();
  const addr = data.address || {};
  return (
    addr.city ||
    addr.town ||
    addr.village ||
    addr.suburb ||
    addr.county ||
    addr.state_district ||
    addr.state ||
    null
  );
}

// Shared by any UI chrome that shows "where am I" (Dashboard's LocationChip,
// Sidebar's user chip, ...) so they always agree and only make the Nominatim
// call once per location change, not once per consumer.
//
// Reverse-geocodes dashboardSnapshot.location into a place name, re-resolving
// every time the dashboard's actual location changes (GPS, map search, or a
// pin) -- coordinates alone aren't useful to a fisherman glancing at the UI,
// a place name is.
export function useLocationLabel() {
  const { dashboardSnapshot } = useOrca();
  const { location, source } = dashboardSnapshot;
  const [placeName, setPlaceName] = useState(null);

  useEffect(() => {
    if (!location || source === "default") {
      setPlaceName(null);
      return;
    }
    let cancelled = false;
    setPlaceName(null); // show coords while the new name is resolving
    reverseGeocode(location.latitude, location.longitude)
      .then((name) => {
        if (!cancelled) setPlaceName(name);
      })
      .catch(() => {
        if (!cancelled) setPlaceName(null);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location?.latitude, location?.longitude, source]);

  const coordLabel = location
    ? `${location.latitude.toFixed(4)}°, ${location.longitude.toFixed(4)}°`
    : null;

  const label =
    source === "default" ? "Chennai, India (default)" : placeName || coordLabel || "Chennai, India";

  return { label, source, location };
}

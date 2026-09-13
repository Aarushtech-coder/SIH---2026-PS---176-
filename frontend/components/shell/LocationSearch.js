"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useOrca } from "@/lib/store";
import { useLocale } from "@/lib/i18n/LocaleContext";
import { IconSearch } from "@/components/icons/Icons";
import styles from "./LocationSearch.module.css";

// ─── Nominatim geocoding ────────────────────────────────────────────────────
const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";
const USER_AGENT = "ORCA-MarineSafety/1.0 (+https://github.com/Aarushtech-coder/SIH---2026-PS---176-)";

async function geocode(query) {
  const url = `${NOMINATIM_URL}?q=${encodeURIComponent(query)}&format=json&limit=5&addressdetails=0`;
  const res = await fetch(url, { headers: { "User-Agent": USER_AGENT } });
  if (!res.ok) return [];
  const data = await res.json();
  return data.map((r) => ({
    id: r.place_id,
    label: r.display_name,
    lat: parseFloat(r.lat),
    lon: parseFloat(r.lon),
  }));
}

// Shared "search a place" box used by both the map page and the dashboard.
// Selecting a result updates the app-wide location (manualLocation) and
// re-runs the map query + dashboard snapshot, so every page reading from
// useOrca() picks up the new location. `onSelect` is an optional extra hook
// for page-specific behavior (e.g. the map page also pans/recenters itself).
export function LocationSearch({ onSelect, className }) {
  const { runMapQuery, refreshDashboardSnapshot, setManualLocation } = useOrca();
  const { t } = useLocale();

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  const debounceRef = useRef(null);

  // Debounced Nominatim fetch
  useEffect(() => {
    const q = searchQuery.trim();
    if (!q) {
      setSearchResults([]);
      setSearchOpen(false);
      return;
    }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSearchLoading(true);
      setSearchOpen(true);
      try {
        const results = await geocode(q);
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [searchQuery]);

  const handleSelect = useCallback(
    (result) => {
      const coords = { latitude: result.lat, longitude: result.lon };
      setManualLocation(coords);
      setSearchQuery(result.label);
      setSearchOpen(false);
      runMapQuery(coords);
      refreshDashboardSnapshot(coords);
      onSelect?.(result, coords);
    },
    [runMapQuery, refreshDashboardSnapshot, setManualLocation, onSelect],
  );

  return (
    <div className={`${styles.searchWrapper} ${className ?? ""}`}>
      <div className={styles.searchBox}>
        <IconSearch size={15} />
        <input
          placeholder={t("map.searchPlaceholder")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onFocus={() => searchResults.length > 0 && setSearchOpen(true)}
          onBlur={() => setTimeout(() => setSearchOpen(false), 150)}
          autoComplete="off"
        />
        {searchLoading && <span className={styles.searchSpinner} />}
      </div>
      {searchOpen && (
        <div className={styles.searchDropdown}>
          {searchLoading && <div className={styles.searchEmpty}>Searching…</div>}
          {!searchLoading && searchResults.length === 0 && searchQuery.trim() && (
            <div className={styles.searchEmpty}>No results found</div>
          )}
          {!searchLoading &&
            searchResults.map((r) => (
              <button
                key={r.id}
                type="button"
                className={styles.searchItem}
                onMouseDown={() => handleSelect(r)}
              >
                {r.label}
              </button>
            ))}
        </div>
      )}
    </div>
  );
}

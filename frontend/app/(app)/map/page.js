"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import dynamic from "next/dynamic";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchBoundary, fetchSafeRoute } from "@/lib/api";
import { Topbar } from "@/components/shell/Topbar";
import { useOrca } from "@/lib/store";
import { useLocale } from "@/lib/i18n/LocaleContext";
import { MAP_LAYERS } from "@/lib/mockData";
import { IconSearch } from "@/components/icons/Icons";
import styles from "./page.module.css";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

const LAYER_TOGGLES = [
  { key: "pfz", labelKey: "layer.pfzZones", swatch: "#16a34a" },
  { key: "hazard", labelKey: "layer.hazardZones", swatch: "#dc2626" },
  { key: "routes", labelKey: "layer.fishingRoutes", swatch: "#2a6fdb" },
  { key: "boundary", labelKey: "layer.boundaries", swatch: "#5b6b83" },
];

const ZONE_STATUS_KEYS = {
  safe: "zoneStatus.safe",
  approaching: "zoneStatus.approaching",
  crossed: "zoneStatus.crossed",
};

function InfoTile({ label, value }) {
  return (
    <div className={styles.infoTile}>
      <div className={styles.infoLabel}>{label}</div>
      <div className={styles.infoValue}>{value}</div>
    </div>
  );
}

const SEA_CONDITION_KEY = {
  safe: "seaCondition.calm",
  caution: "seaCondition.moderate",
  unsafe: "seaCondition.rough",
};

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

// ─── Inner page (needs Suspense for useSearchParams) ────────────────────────
function MapExplorerInner() {
  const {
    mapData,
    geoLocation,
    geoStatus,
    runMapQuery,
    loading,
    dashboardSnapshot,
    refreshDashboardSnapshot,
    manualLocation,
    setManualLocation,
  } = useOrca();
  const { t } = useLocale();
  const searchParams = useSearchParams();
  const router = useRouter();

  // ── Layer visibility ──────────────────────────────────────────────────────
  const [visibility, setVisibility] = useState({
    pfz: true, hazard: true, routes: true, boundary: true,
  });

  function toggleLayer(key) {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  }
  const [realBoundary, setRealBoundary] = useState(null);

useEffect(() => {
  fetchBoundary()
    .then(setRealBoundary)
    .catch((err) => console.error("Failed to fetch boundary:", err));
}, []);

  const [safeRouteData, setSafeRouteData] = useState(null);
  const activeLoc = manualLocation || geoLocation;
  const gpsCenter = activeLoc
    ? { lat: activeLoc.latitude, lon: activeLoc.longitude }
    : null;

  useEffect(() => {
    if (activeLoc) {
      fetchSafeRoute({ latitude: activeLoc.latitude, longitude: activeLoc.longitude })
        .then((data) => {
          if (data && data.route) {
            setSafeRouteData([
              {
                id: "dynamic-safe-route",
                label: "Suggested Safe Route to nearest PFZ",
                points: data.route.map((p) => [p.lat, p.lon]),
              },
            ]);
          }
        })
        .catch((err) => console.error("Failed to fetch safe route:", err));
    }
  }, [activeLoc]);
  // ── Map center override (set by search or incoming ?lat/?lon param) ───────
  const [mapCenter, setMapCenter] = useState(null); // {lat, lon} or null

  // ── Search state ──────────────────────────────────────────────────────────
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

  // When user picks a search result: pan map, change global location, trigger silent query
  const handleSearchSelect = useCallback(
    (result) => {
      const coords = { latitude: result.lat, longitude: result.lon };
      setManualLocation(coords);
      setMapCenter({ lat: result.lat, lon: result.lon });
      setSearchQuery(result.label);
      setSearchOpen(false);
      runMapQuery(coords);
      refreshDashboardSnapshot(coords);
    },
    [runMapQuery, refreshDashboardSnapshot, setManualLocation],
  );

  // ── GPS auto-fetch (once per mount) ──────────────────────────────────────
  const autoFetchedRef = useRef(false);

  useEffect(() => {
    if (autoFetchedRef.current) return;

    // If the page was opened from the preview card with explicit coords, use
    // those instead of GPS so we respect what the user was looking at.
    const paramLat = parseFloat(searchParams.get("lat"));
    const paramLon = parseFloat(searchParams.get("lon"));
    if (!isNaN(paramLat) && !isNaN(paramLon)) {
      autoFetchedRef.current = true;
      const coords = { latitude: paramLat, longitude: paramLon };
      setMapCenter({ lat: paramLat, lon: paramLon });
      runMapQuery(coords);
      refreshDashboardSnapshot(coords);
      // Clean up the URL so these params don't persist on refresh
      router.replace("/map");
      return;
    }

    // GPS path: wait until the browser resolves the position
    if (geoStatus === "granted" && geoLocation) {
      autoFetchedRef.current = true;
      const coords = { latitude: geoLocation.latitude, longitude: geoLocation.longitude };
      runMapQuery(coords);
      refreshDashboardSnapshot(coords);
      return;
    }

    // GPS denied/unavailable — mark as fetched so we don't retry, and let the
    // fallback banner show. The dashboard snapshot will still run with
    // the Chennai default inside refreshDashboardSnapshot.
    if (geoStatus === "denied" || geoStatus === "unavailable") {
      autoFetchedRef.current = true;
      if (dashboardSnapshot.status === "idle") refreshDashboardSnapshot();
    }
  }, [
    geoStatus,
    geoLocation,
    searchParams,
    runMapQuery,
    refreshDashboardSnapshot,
    router,
    dashboardSnapshot.status,
  ]);

  // ── Derived data ──────────────────────────────────────────────────────────
  const geo = mapData?.current_position ? mapData : null;
  const realPfzZones = dashboardSnapshot.pfzZones
    ?.filter((z) => typeof z.latitude === "number" && typeof z.longitude === "number")
    .map((z) => ({ id: z.zone_id, lat: z.latitude, lon: z.longitude }));

  // If we have an explicit mapCenter from search or incoming params, override
  // the static layers center so MapRecenter pans to the right place.
  const layers = {
    ...MAP_LAYERS,
    pfzZones: realPfzZones?.length ? realPfzZones : MAP_LAYERS.pfzZones,
    boundary: realBoundary?.length ? realBoundary : MAP_LAYERS.boundary,
    fishingRoutes: safeRouteData || MAP_LAYERS.fishingRoutes,
    ...(mapCenter ? { center: mapCenter } : {}),
  };


  // Show fallback banner when GPS isn't available
  const showFallbackBanner =
    geoStatus === "denied" || geoStatus === "unavailable";

  return (
    <div className={styles.page}>
      <Topbar
        title={t("nav.map")}
        subtitle={t("map.subtitle")}
        right={
          <div className={styles.searchWrapper}>
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
                {searchLoading && (
                  <div className={styles.searchEmpty}>Searching…</div>
                )}
                {!searchLoading && searchResults.length === 0 && searchQuery.trim() && (
                  <div className={styles.searchEmpty}>No results found</div>
                )}
                {!searchLoading &&
                  searchResults.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      className={styles.searchItem}
                      onMouseDown={() => handleSearchSelect(r)}
                    >
                      {r.label}
                    </button>
                  ))}
              </div>
            )}
          </div>
        }
      />

      {/* {showFallbackBanner && (
        <div className={styles.fallbackBanner}>
          📍 Showing Chennai (default) — enable location for your area
        </div>
      )} */}

      <div className={styles.toolbar}>
        {LAYER_TOGGLES.map(({ key, labelKey, swatch }) => (
          <button
            key={key}
            type="button"
            className={`${styles.layerChip} ${visibility[key] ? styles.active : ""}`}
            onClick={() => toggleLayer(key)}
          >
            <span className={styles.swatch} style={{ background: swatch }} />
            {t(labelKey)}
          </button>
        ))}
      </div>

      <div className={styles.mapWrap}>
        <MapView
          mapData={mapData}
          layers={layers}
          visibility={visibility}
          interactive
          gpsCenter={gpsCenter}
        />
      </div>

      <div className={styles.footer}>
        <div className={styles.legend}>
          {LAYER_TOGGLES.map(({ key, labelKey, swatch }) => (
            <span key={key} className={styles.legendItem}>
              <span className={styles.swatch} style={{ background: swatch }} />
              {t(labelKey)}
            </span>
          ))}
        </div>

        <div className={styles.infoPanel}>
          <div className={styles.infoHeader}>
            <h2>{t("map.locationInfo")}</h2>
            {geo && (
              <span className={styles.coord}>
                {geo.current_position.lat.toFixed(2)}°N,{" "}
                {geo.current_position.lon.toFixed(2)}°E
              </span>
            )}
          </div>
          <div className={styles.infoGrid}>
            <InfoTile
              label={t("map.zoneStatus")}
              value={
                geo
                  ? t(ZONE_STATUS_KEYS[geo.zone_status] ?? geo.zone_status)
                  : t("map.withinSafeZone")
              }
            />
            <InfoTile
              label={t("map.distanceImbl")}
              value={geo ? `${geo.distance_to_imbl_nm} nm` : "--"}
            />
            <InfoTile
              label={t("map.withinImbl")}
              value={
                geo
                  ? geo.zone_status === "crossed"
                    ? t("common.no")
                    : t("common.yes")
                  : t("common.yes")
              }
            />
            <InfoTile
              label={t("stat.seaCondition")}
              value={
                dashboardSnapshot.risk
                  ? t(
                      SEA_CONDITION_KEY[dashboardSnapshot.risk.verdict] ??
                        "seaCondition.moderate",
                    )
                  : "--"
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MapExplorerPage() {
  return (
    <Suspense fallback={null}>
      <MapExplorerInner />
    </Suspense>
  );
}

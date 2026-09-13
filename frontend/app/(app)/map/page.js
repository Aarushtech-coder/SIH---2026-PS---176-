"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import dynamic from "next/dynamic";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchBoundary } from "@/lib/api";
import { Topbar } from "@/components/shell/Topbar";
import { LocationSearch } from "@/components/shell/LocationSearch";
import { useOrca } from "@/lib/store";
import { useLocale } from "@/lib/i18n/LocaleContext";
import { MAP_LAYERS } from "@/lib/mockData";
import styles from "./page.module.css";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

// hazard-zone toggle removed -- no real backend source exists for it
// (confirmed: no hazard-zone data anywhere in orchestration/), so it was
// just a fixed illustrative marker, not real data.
const LAYER_TOGGLES = [
  { key: "pfz", labelKey: "layer.pfzZones", swatch: "#16a34a" },
  { key: "routes", labelKey: "layer.fishingRoutes", swatch: "#2a6fdb" },
  { key: "boundary", labelKey: "layer.boundaries", swatch: "#5b6b83" },
];

const ZONE_STATUS_KEYS = {
  safe: "zoneStatus.safe",
  approaching: "zoneStatus.approaching",
  crossed: "zoneStatus.crossed",
  inland: "Zone Status: Inland / Land",
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
    safeRoute,
    fetchSafeRouteFor,
  } = useOrca();
  const { t } = useLocale();
  const searchParams = useSearchParams();
  const router = useRouter();

  // ── Layer visibility ──────────────────────────────────────────────────────
  const [visibility, setVisibility] = useState({
    pfz: true, routes: true, boundary: true,
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

  const activeLoc = manualLocation || geoLocation;
  const gpsCenter = activeLoc
    ? { lat: activeLoc.latitude, lon: activeLoc.longitude }
    : null;

  // Eagerly fetches the real safe route whenever the location changes -- no
  // override passed, so it resolves via store.js's own manualLocation >
  // geoLocation > default chain, the same one Chat uses, instead of only
  // firing when manualLocation/geoLocation happen to already be set.
  useEffect(() => {
    fetchSafeRouteFor();
  }, [manualLocation, geoLocation, fetchSafeRouteFor]);
  // ── Map center override (set by search or incoming ?lat/?lon param) ───────
  const [mapCenter, setMapCenter] = useState(null); // {lat, lon} or null

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
          <LocationSearch
            onSelect={(result) => setMapCenter({ lat: result.lat, lon: result.lon })}
          />
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
          safeRoute={safeRoute}
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

"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
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

const SEA_CONDITION_KEY = { safe: "seaCondition.calm", caution: "seaCondition.moderate", unsafe: "seaCondition.rough" };

export default function MapExplorerPage() {
  const { mapData, geoLocation, runQuery, loading, dashboardSnapshot, refreshDashboardSnapshot } = useOrca();
  const { t } = useLocale();

  useEffect(() => {
    if (dashboardSnapshot.status === "idle") refreshDashboardSnapshot();
  }, [dashboardSnapshot.status, refreshDashboardSnapshot]);
  const [visibility, setVisibility] = useState({
    pfz: true,
    hazard: true,
    routes: true,
    boundary: true,
  });

  // Demo location override — lets us show the pipeline working with real
  // coastal data during a demo, even when the device's real GPS is inland
  // (e.g. testing from an office/venue far from the sea). null = use real GPS.
  const DEMO_LOCATIONS = {
    goa: { label: "Goa", lat: 15.5, lon: 73.5 },
    chennai: { label: "Chennai", lat: 13.08, lon: 80.27 },
    mumbai: { label: "Mumbai", lat: 18.94, lon: 72.84 },
  };
  const [demoLocation, setDemoLocation] = useState(null);

  // If the user opens Map Explorer directly (without asking a question in
  // Chat first), mapData is still null. Auto-run a geofence check using the
  // device's GPS so this page always shows live data, not stale placeholders.
  useEffect(() => {
    if (!mapData && !loading && geoLocation) {
      runQuery("What is my current maritime zone status?");
    }
  }, [mapData, loading, geoLocation, runQuery]);

  const [pendingPoint, setPendingPoint] = useState(null);

  // Click-to-inspect: fires the same kind of geospatial query the page
  // auto-runs on load, but for whatever point the user clicked instead of
  // their GPS position. runQuery already supports an explicit coords
  // override for exactly this. Also refreshes the Dashboard's overview
  // tiles for that same point, so weather/risk/sea-temp there reflect the
  // pinned region too, not just this page's own info panel.
  function handleMapClick(lat, lon) {
    if (loading) return;
    setPendingPoint({ lat, lon });
    const coords = { latitude: lat, longitude: lon };
    Promise.all([
      runQuery(t("map.clickQuery"), coords),
      refreshDashboardSnapshot(coords),
    ]).finally(() => setPendingPoint(null));
  }

  const geo = mapData?.current_position ? mapData : null;

  // Convert store's {latitude, longitude} shape to MapView's {lat, lon} shape.
  const gpsCenter = geoLocation
    ? { lat: geoLocation.latitude, lon: geoLocation.longitude }
    : null;

  function toggleLayer(key) {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className={styles.page}>
      <Topbar
        title={t("nav.map")}
        subtitle={t("map.subtitle")}
        right={
          <div className={styles.searchBox}>
            <IconSearch size={15} />
            <input placeholder={t("map.searchPlaceholder")} />
          </div>
        }
      />

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
        <span className={styles.clickHint}>{t("map.clickHint")}</span>
      </div>

      <div className={styles.mapWrap}>
        <MapView
          mapData={mapData}
          layers={MAP_LAYERS}
          visibility={visibility}
          interactive
          gpsCenter={gpsCenter}
          onLocationClick={handleMapClick}
          pendingPoint={pendingPoint}
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
                  ? t(SEA_CONDITION_KEY[dashboardSnapshot.risk.verdict] ?? "seaCondition.moderate")
                  : "--"
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}

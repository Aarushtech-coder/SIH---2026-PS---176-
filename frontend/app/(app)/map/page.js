"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Topbar } from "@/components/shell/Topbar";
import { useOrca } from "@/lib/store";
import { MAP_LAYERS, OVERVIEW } from "@/lib/mockData";
import { IconSearch } from "@/components/icons/Icons";
import styles from "./page.module.css";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

const LAYER_TOGGLES = [
  { key: "pfz", label: "PFZ Zones", swatch: "#16a34a" },
  { key: "hazard", label: "Hazard Zones", swatch: "#dc2626" },
  { key: "routes", label: "Fishing Routes", swatch: "#2a6fdb" },
  { key: "boundary", label: "Boundaries", swatch: "#5b6b83" },
];

function InfoTile({ label, value }) {
  return (
    <div className={styles.infoTile}>
      <div className={styles.infoLabel}>{label}</div>
      <div className={styles.infoValue}>{value}</div>
    </div>
  );
}

function capitalize(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

export default function MapExplorerPage() {
  const { mapData } = useOrca();
  const [visibility, setVisibility] = useState({ pfz: true, hazard: true, routes: true, boundary: true });

  const geo = mapData?.current_position ? mapData : null;

  function toggleLayer(key) {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className={styles.page}>
      <Topbar
        title="Map Explorer"
        subtitle="Explore marine data, zones and weather on the map"
        right={
          <div className={styles.searchBox}>
            <IconSearch size={15} />
            <input placeholder="Search location..." />
          </div>
        }
      />

      <div className={styles.toolbar}>
        {LAYER_TOGGLES.map(({ key, label, swatch }) => (
          <button
            key={key}
            type="button"
            className={`${styles.layerChip} ${visibility[key] ? styles.active : ""}`}
            onClick={() => toggleLayer(key)}
          >
            <span className={styles.swatch} style={{ background: swatch }} />
            {label}
          </button>
        ))}
      </div>

      <div className={styles.mapWrap}>
        <MapView mapData={mapData} layers={MAP_LAYERS} visibility={visibility} interactive />
      </div>

      <div className={styles.footer}>
        <div className={styles.legend}>
          {LAYER_TOGGLES.map(({ key, label, swatch }) => (
            <span key={key} className={styles.legendItem}>
              <span className={styles.swatch} style={{ background: swatch }} />
              {label}
            </span>
          ))}
        </div>

        <div className={styles.infoPanel}>
          <div className={styles.infoHeader}>
            <h2>Location Info</h2>
            {geo && (
              <span className={styles.coord}>
                {geo.current_position.lat.toFixed(2)}°N, {geo.current_position.lon.toFixed(2)}°E
              </span>
            )}
          </div>
          <div className={styles.infoGrid}>
            <InfoTile label="Zone Status" value={geo ? capitalize(geo.zone_status) : "Within safe zone"} />
            <InfoTile label="Distance to IMBL" value={geo ? `${geo.distance_to_imbl_nm} nm` : "--"} />
            <InfoTile label="Within IMBL" value={geo ? (geo.zone_status === "crossed" ? "No" : "Yes") : "Yes"} />
            <InfoTile label="Sea Condition" value={OVERVIEW.seaCondition} />
          </div>
        </div>
      </div>
    </div>
  );
}

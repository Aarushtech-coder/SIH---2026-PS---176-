"use client";

import { useCallback } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import styles from "./MapPreviewCard.module.css";
import { MAP_LAYERS } from "@/lib/mockData";
import { IconChevronRight, IconMap } from "@/components/icons/Icons";
import { useLocale } from "@/lib/i18n/LocaleContext";
import { useOrca } from "@/lib/store";

const MapView = dynamic(() => import("./MapView"), { ssr: false });

const PREVIEW_VISIBILITY = { pfz: true, routes: true, boundary: false };

// Resolves the current map center so the preview overlay click can carry the
// same position over to Map Explorer via query params.
function resolveCenter(mapData, manualLocation, geoLocation) {
  if (mapData?.center) return mapData.center;
  if (manualLocation) return { lat: manualLocation.latitude, lon: manualLocation.longitude };
  if (geoLocation) return { lat: geoLocation.latitude, lon: geoLocation.longitude };
  return { lat: 13.0827, lon: 80.2707 }; // Chennai fallback
}

export default function MapPreviewCard({ mapData }) {
  const { t } = useLocale();
  const { geoLocation, manualLocation, safeRoute } = useOrca();
  const router = useRouter();

  const activeLoc = manualLocation || geoLocation;
  const gpsCenter = activeLoc
    ? { lat: activeLoc.latitude, lon: activeLoc.longitude }
    : null;

  // On click, navigate to /map with the current center coords so the full
  // Map Explorer opens at the same location the preview was showing.
  const handlePreviewClick = useCallback(() => {
    const center = resolveCenter(mapData, manualLocation, geoLocation);
    router.push(`/map?lat=${center.lat.toFixed(5)}&lon=${center.lon.toFixed(5)}`);
  }, [mapData, manualLocation, geoLocation, router]);

  return (
    <div className={styles.card}>
      <div className={styles.mapBox}>
        <MapView
          mapData={mapData}
          layers={MAP_LAYERS}
          visibility={PREVIEW_VISIBILITY}
          interactive={false}
          gpsCenter={gpsCenter}
          onPreviewClick={handlePreviewClick}
          safeRoute={safeRoute}
        />
      </div>
      <div className={styles.footer}>
        <span className={styles.label}>
          <IconMap size={15} />
          {t("map.previewLabel")}
        </span>
        <span className={styles.cta}>
          {t("map.viewFull")}
          <IconChevronRight size={14} />
        </span>
      </div>
    </div>
  );
}

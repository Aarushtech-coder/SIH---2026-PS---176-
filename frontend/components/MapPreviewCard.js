"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import styles from "./MapPreviewCard.module.css";
import { MAP_LAYERS } from "@/lib/mockData";
import { IconChevronRight, IconMap } from "@/components/icons/Icons";
import { useLocale } from "@/lib/i18n/LocaleContext";
import { useOrca } from "@/lib/store";

const MapView = dynamic(() => import("./MapView"), { ssr: false });

const PREVIEW_VISIBILITY = { pfz: true, hazard: true, routes: false, boundary: false };

export default function MapPreviewCard({ mapData }) {
  const { t } = useLocale();
  const { geoLocation } = useOrca();

  const gpsCenter = geoLocation
    ? { lat: geoLocation.latitude, lon: geoLocation.longitude }
    : null;

  return (
    <Link href="/map" className={styles.card}>
      <div className={styles.mapBox}>
        <MapView mapData={mapData} layers={MAP_LAYERS} visibility={PREVIEW_VISIBILITY} interactive={false} gpsCenter={gpsCenter} />
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
    </Link>
  );
}

"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import styles from "./MapPreviewCard.module.css";
import { MAP_LAYERS } from "@/lib/mockData";
import { IconChevronRight, IconMap } from "@/components/icons/Icons";

const MapView = dynamic(() => import("./MapView"), { ssr: false });

const PREVIEW_VISIBILITY = { pfz: true, hazard: true, routes: false, boundary: false };

export default function MapPreviewCard({ mapData }) {
  return (
    <Link href="/map" className={styles.card}>
      <div className={styles.mapBox}>
        <MapView mapData={mapData} layers={MAP_LAYERS} visibility={PREVIEW_VISIBILITY} interactive={false} />
      </div>
      <div className={styles.footer}>
        <span className={styles.label}>
          <IconMap size={15} />
          Map Explorer
        </span>
        <span className={styles.cta}>
          View full map
          <IconChevronRight size={14} />
        </span>
      </div>
    </Link>
  );
}

"use client";

import styles from "./Topbar.module.css";
import { IconPin, IconSun, IconMenu } from "@/components/icons/Icons";
import { useOrca } from "@/lib/store";
import { useLocationLabel } from "@/lib/useLocationLabel";
import { useMobileNav } from "./MobileNavContext";

export function Topbar({ title, subtitle, right }) {
  const { toggle } = useMobileNav();

  return (
    <header className={styles.topbar}>
      <div className={styles.titleRow}>
        <button
          type="button"
          className={styles.menuButton}
          onClick={toggle}
          aria-label="Toggle navigation"
        >
          <IconMenu size={20} />
        </button>
        <div>
          <h1 className={styles.title}>{title}</h1>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
      </div>
      {right && <div className={styles.right}>{right}</div>}
    </header>
  );
}

export function LocationChip() {
  const { dashboardSnapshot } = useOrca();
  const { label: locationLabel } = useLocationLabel();

  // Sea surface temperature -- the only real temperature the backend
  // provides (there's no air-temperature field anywhere in the contract).
  const sst = dashboardSnapshot.ocean?.sst_celsius;

  return (
    <div className={styles.locationChip}>
      <IconPin size={15} />
      {locationLabel}
      {typeof sst === "number" && (
        <>
          <span className={styles.divider} />
          <IconSun size={15} />
          {sst.toFixed(1)}°C SST
        </>
      )}
    </div>
  );
}

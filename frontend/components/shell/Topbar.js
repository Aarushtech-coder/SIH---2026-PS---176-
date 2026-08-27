import styles from "./Topbar.module.css";
import { IconPin, IconSun } from "@/components/icons/Icons";
import { useOrca } from "@/lib/store";

export function Topbar({ title, subtitle, right }) {
  return (
    <header className={styles.topbar}>
      <div>
        <h1 className={styles.title}>{title}</h1>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
      {right && <div className={styles.right}>{right}</div>}
    </header>
  );
}

export function LocationChip() {
  const { geoLocation, geoStatus, dashboardSnapshot } = useOrca();

  const locationLabel =
    geoStatus === "granted" && geoLocation
      ? `${geoLocation.latitude.toFixed(4)}°, ${geoLocation.longitude.toFixed(4)}°`
      : "Chennai, India";

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

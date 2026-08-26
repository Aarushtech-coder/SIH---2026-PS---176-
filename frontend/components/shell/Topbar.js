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
  const { geoLocation, geoStatus } = useOrca();

  const locationLabel =
    geoStatus === "granted" && geoLocation
      ? `${geoLocation.latitude.toFixed(4)}°, ${geoLocation.longitude.toFixed(4)}°`
      : "Chennai, India";

  return (
    <div className={styles.locationChip}>
      <IconPin size={15} />
      {locationLabel}
      <span className={styles.divider} />
      <IconSun size={15} />
      31°C
    </div>
  );
}

import styles from "./Topbar.module.css";
import { IconPin, IconSun } from "@/components/icons/Icons";

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
  return (
    <div className={styles.locationChip}>
      <IconPin size={15} />
      Chennai, India
      <span className={styles.divider} />
      <IconSun size={15} />
      31°C
    </div>
  );
}

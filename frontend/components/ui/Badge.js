import styles from "./Badge.module.css";
import { IconCheck, IconAlert } from "@/components/icons/Icons";

const VERDICT_CONFIG = {
  safe: { label: "Safe", tone: "good", Icon: IconCheck },
  caution: { label: "Caution", tone: "warning", Icon: IconAlert },
  unsafe: { label: "Unsafe", tone: "critical", Icon: IconAlert },
  approaching: { label: "Approaching", tone: "warning", Icon: IconAlert },
  crossed: { label: "Crossed", tone: "critical", Icon: IconAlert },
};

// Status badges always pair color with an icon + label -- never color alone.
export function VerdictBadge({ verdict, className = "" }) {
  const config = VERDICT_CONFIG[verdict];
  if (!config) return null;
  const { label, tone, Icon } = config;

  return (
    <span className={`${styles.badge} ${styles[tone]} ${className}`}>
      <Icon size={13} strokeWidth={2.25} />
      {label}
    </span>
  );
}

export function Badge({ tone = "neutral", children, className = "" }) {
  return <span className={`${styles.badge} ${styles[tone]} ${className}`}>{children}</span>;
}

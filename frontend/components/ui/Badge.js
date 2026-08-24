"use client";

import styles from "./Badge.module.css";
import { IconCheck, IconAlert } from "@/components/icons/Icons";
import { useLocale } from "@/lib/i18n/LocaleContext";

const VERDICT_CONFIG = {
  safe: { key: "verdict.safe", tone: "good", Icon: IconCheck },
  caution: { key: "verdict.caution", tone: "warning", Icon: IconAlert },
  unsafe: { key: "verdict.unsafe", tone: "critical", Icon: IconAlert },
  approaching: { key: "verdict.approaching", tone: "warning", Icon: IconAlert },
  crossed: { key: "verdict.crossed", tone: "critical", Icon: IconAlert },
};

// Status badges always pair color with an icon + label -- never color alone.
export function VerdictBadge({ verdict, className = "" }) {
  const { t } = useLocale();
  const config = VERDICT_CONFIG[verdict];
  if (!config) return null;
  const { key, tone, Icon } = config;

  return (
    <span className={`${styles.badge} ${styles[tone]} ${className}`}>
      <Icon size={13} strokeWidth={2.25} />
      {t(key)}
    </span>
  );
}

export function Badge({ tone = "neutral", children, className = "" }) {
  return <span className={`${styles.badge} ${styles[tone]} ${className}`}>{children}</span>;
}

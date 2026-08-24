"use client";

import Link from "next/link";
import { Topbar, LocationChip } from "@/components/shell/Topbar";
import Panel from "@/components/ui/Panel";
import StatCard from "@/components/ui/StatCard";
import { Badge, VerdictBadge } from "@/components/ui/Badge";
import { useOrca } from "@/lib/store";
import { useLocale } from "@/lib/i18n/LocaleContext";
import { OVERVIEW, ALERTS, DATA_SOURCES } from "@/lib/mockData";
import { timeAgo } from "@/lib/format";
import {
  IconWave,
  IconWind,
  IconFish,
  IconShield,
  IconAlert,
  IconChevronRight,
  IconMap,
  IconChat,
} from "@/components/icons/Icons";
import styles from "./page.module.css";

const SUGGESTION_KEYS = ["suggestion.safe", "suggestion.nearestZone", "suggestion.weatherChennai"];

const QUICK_ACTIONS = [
  { labelKey: "action.findPfz", qKey: "suggestion.nearestZone", Icon: IconFish },
  { labelKey: "action.checkSafety", qKey: "suggestion.safe", Icon: IconShield },
  { labelKey: "action.openMap", href: "/map", Icon: IconMap },
  { labelKey: "action.openChat", href: "/chat", Icon: IconChat },
];

const INTENT_KEYS = {
  nearest_pfz: "intent.nearest_pfz",
  safe_to_sail: "intent.safe_to_sail",
  geofence_check: "intent.geofence_check",
  weather_tide: "intent.weather_tide",
};

function greetingKey() {
  const h = new Date().getHours();
  if (h < 12) return "greeting.morning";
  if (h < 17) return "greeting.afternoon";
  return "greeting.evening";
}

export default function DashboardPage() {
  const { savedQueries } = useOrca();
  const { t } = useLocale();

  return (
    <>
      <Topbar
        title={t("nav.dashboard")}
        subtitle={`${t(greetingKey())}, ${t("brand.user")}`}
        right={<LocationChip />}
      />

      <div className={styles.content}>
        <Panel
          title={t("dashboard.overviewTitle")}
          action={<span>{t("dashboard.updated")} {timeAgo(OVERVIEW.lastUpdated, t)}</span>}
        >
          <div className={styles.statGrid}>
            <StatCard icon={IconWave} label={t("stat.seaCondition")} value={OVERVIEW.seaCondition} tone="accent" />
            <StatCard icon={IconWave} label={t("stat.waveHeight")} value={OVERVIEW.waveHeightRange} tone="accent" />
            <StatCard
              icon={IconWind}
              label={t("stat.wind")}
              value={`${OVERVIEW.windSpeedKmh} km/h`}
              sub={OVERVIEW.windDirection}
              tone="accent"
            />
            <StatCard
              icon={IconFish}
              label={t("stat.fishingZone")}
              value={`${OVERVIEW.nearestPfzDistanceKm} km`}
              sub={t("stat.nearestPfz")}
              tone="good"
            />
            <StatCard icon={IconShield} label={t("stat.riskLevel")} value="Moderate" tone="warning" />
          </div>
        </Panel>

        {ALERTS.length > 0 && (
          <div className={styles.alertBanner}>
            <IconAlert size={17} />
            <span>{ALERTS[0].message}</span>
          </div>
        )}

        <Panel title={t("dashboard.askTitle")} subtitle={t("dashboard.askSubtitle")}>
          <div className={styles.suggestionRow}>
            {SUGGESTION_KEYS.map((key) => (
              <Link key={key} href={`/chat?q=${encodeURIComponent(t(key))}`} className={styles.suggestionChip}>
                {t(key)}
              </Link>
            ))}
          </div>
          <Link href="/chat" className={styles.askInput}>
            <span>{t("dashboard.typeQuestion")}</span>
            <IconChevronRight size={16} />
          </Link>
        </Panel>

        <div className={styles.twoCol}>
          <Panel title={t("dashboard.recentQueries")} action={<Link href="/saved">{t("common.viewAll")}</Link>}>
            {savedQueries.length === 0 ? (
              <p className={styles.emptyText}>{t("dashboard.noQueries")}</p>
            ) : (
              <ul className={styles.queryList}>
                {savedQueries.slice(0, 4).map((q) => (
                  <li key={q.id}>
                    <Link href={`/chat?q=${encodeURIComponent(q.text)}`} className={styles.queryRow}>
                      <div className={styles.queryMain}>
                        <div className={styles.queryText}>{q.text}</div>
                        <div className={styles.queryTime}>{timeAgo(q.timestamp, t)}</div>
                      </div>
                      {q.verdict ? <VerdictBadge verdict={q.verdict} /> : <Badge>{t(INTENT_KEYS[q.intent] ?? q.intent)}</Badge>}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title={t("dashboard.quickActions")}>
            <div className={styles.actionGrid}>
              {QUICK_ACTIONS.map(({ labelKey, qKey, href, Icon }) => (
                <Link
                  key={labelKey}
                  href={href ?? `/chat?q=${encodeURIComponent(t(qKey))}`}
                  className={styles.actionTile}
                >
                  <Icon size={18} />
                  {t(labelKey)}
                </Link>
              ))}
            </div>
          </Panel>
        </div>

        <Panel title={t("dashboard.dataSources")}>
          <div className={styles.sourceRow}>
            {DATA_SOURCES.map((s) => (
              <div key={s.id} className={styles.sourceChip}>
                <span className={styles.sourceLabel}>{s.label}</span>
                <span className={styles.sourceDesc}>{s.desc}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  );
}

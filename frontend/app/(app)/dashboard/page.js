"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Topbar, LocationChip } from "@/components/shell/Topbar";
import Panel from "@/components/ui/Panel";
import StatCard from "@/components/ui/StatCard";
import { Badge, VerdictBadge } from "@/components/ui/Badge";
import { useOrca } from "@/lib/store";
import { useLocale } from "@/lib/i18n/LocaleContext";
import { useMounted } from "@/lib/useMounted";
import { DATA_SOURCES } from "@/lib/mockData";
import { timeAgo, degToCompass } from "@/lib/format";
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

const VERDICT_TONE = { safe: "good", caution: "warning", unsafe: "critical" };
const SEA_CONDITION_KEY = { safe: "seaCondition.calm", caution: "seaCondition.moderate", unsafe: "seaCondition.rough" };

function greetingKey() {
  const h = new Date().getHours();
  if (h < 12) return "greeting.morning";
  if (h < 17) return "greeting.afternoon";
  return "greeting.evening";
}

export default function DashboardPage() {
  const { savedQueries, dashboardSnapshot, refreshDashboardSnapshot } = useOrca();
  const { t } = useLocale();
  const mounted = useMounted();

  useEffect(() => {
    if (dashboardSnapshot.status === "idle") refreshDashboardSnapshot();
  }, [dashboardSnapshot.status, refreshDashboardSnapshot]);

  const { status, weather, risk, ocean, nearestPfzKm, fetchedAt, usedDefaultLocation } = dashboardSnapshot;
  const isLoading = status === "idle" || status === "loading";
  const dash = "--";

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
          action={
            <span>
              {status === "ready" && mounted
                ? `${t("dashboard.updated")} ${timeAgo(fetchedAt, t)}`
                : isLoading
                  ? t("chat.transcribing")
                  : ""}
            </span>
          }
        >
          {status === "error" ? (
            <div className={styles.loadError}>
              <span>{t("dashboard.loadError")}</span>
              <button type="button" onClick={refreshDashboardSnapshot} className={styles.retryButton}>
                {t("dashboard.retry")}
              </button>
            </div>
          ) : (
            <div className={styles.statGrid}>
              <StatCard
                icon={IconWave}
                label={t("stat.seaCondition")}
                value={risk ? t(SEA_CONDITION_KEY[risk.verdict] ?? "seaCondition.moderate") : dash}
                tone="accent"
              />
              <StatCard
                icon={IconWave}
                label={t("stat.waveHeight")}
                value={weather ? `${weather.wave_height_m} m` : dash}
                tone="accent"
              />
              <StatCard
                icon={IconWind}
                label={t("stat.wind")}
                value={weather ? `${Math.round(weather.wind_speed_kmh)} km/h` : dash}
                sub={weather ? degToCompass(weather.wind_direction_deg) : null}
                tone="accent"
              />
              <StatCard
                icon={IconFish}
                label={t("stat.fishingZone")}
                value={nearestPfzKm != null ? `${Math.round(nearestPfzKm)} km` : dash}
                sub={t("stat.nearestPfz")}
                tone="good"
              />
              <StatCard
                icon={IconShield}
                label={t("stat.riskLevel")}
                value={risk ? t(`verdict.${risk.verdict}`) : dash}
                tone={risk ? (VERDICT_TONE[risk.verdict] ?? "accent") : "accent"}
              />
              <StatCard
                icon={IconWave}
                label={t("stat.seaTemp")}
                value={typeof ocean?.sst_celsius === "number" ? `${ocean.sst_celsius.toFixed(1)}°C` : dash}
                tone="accent"
              />
            </div>
          )}
          {usedDefaultLocation && status === "ready" && (
            <p className={styles.locationNote}>{t("dashboard.usingDefaultLocation")}</p>
          )}
        </Panel>

        {weather?.cyclone_alert && (
          <div className={styles.alertBanner}>
            <IconAlert size={17} />
            <span>{t("dashboard.cycloneAlert", { level: weather.cyclone_alert })}</span>
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
                        <div className={styles.queryTime}>{mounted ? timeAgo(q.timestamp, t) : ""}</div>
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

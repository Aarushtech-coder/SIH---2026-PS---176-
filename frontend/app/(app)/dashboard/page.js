"use client";

import Link from "next/link";
import { Topbar, LocationChip } from "@/components/shell/Topbar";
import Panel from "@/components/ui/Panel";
import StatCard from "@/components/ui/StatCard";
import { Badge, VerdictBadge } from "@/components/ui/Badge";
import { useOrca } from "@/lib/store";
import { OVERVIEW, ALERTS, DATA_SOURCES } from "@/lib/mockData";
import { timeAgo, INTENT_LABELS } from "@/lib/format";
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

const SUGGESTIONS = [
  "Is it safe to go to sea tomorrow?",
  "Where's the nearest fishing zone?",
  "Weather near Chennai",
];

const QUICK_ACTIONS = [
  { label: "Find Nearest PFZ", q: "Where's the nearest fishing zone?", Icon: IconFish },
  { label: "Check Safety", q: "Is it safe to go to sea tomorrow?", Icon: IconShield },
  { label: "Open Map Explorer", href: "/map", Icon: IconMap },
  { label: "Open Chat Assistant", href: "/chat", Icon: IconChat },
];

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function DashboardPage() {
  const { savedQueries } = useOrca();

  return (
    <>
      <Topbar title="Dashboard" subtitle={`${greeting()}, Fisherman`} right={<LocationChip />} />

      <div className={styles.content}>
        <Panel title="Today's Marine Overview" action={<span>Updated {timeAgo(OVERVIEW.lastUpdated)}</span>}>
          <div className={styles.statGrid}>
            <StatCard icon={IconWave} label="Sea Condition" value={OVERVIEW.seaCondition} tone="accent" />
            <StatCard icon={IconWave} label="Wave Height" value={OVERVIEW.waveHeightRange} tone="accent" />
            <StatCard icon={IconWind} label="Wind" value={`${OVERVIEW.windSpeedKmh} km/h`} sub={OVERVIEW.windDirection} tone="accent" />
            <StatCard icon={IconFish} label="Fishing Zone" value={`${OVERVIEW.nearestPfzDistanceKm} km`} sub="Nearest PFZ" tone="good" />
            <StatCard icon={IconShield} label="Risk Level" value="Moderate" tone="warning" />
          </div>
        </Panel>

        {ALERTS.length > 0 && (
          <div className={styles.alertBanner}>
            <IconAlert size={17} />
            <span>{ALERTS[0].message}</span>
          </div>
        )}

        <Panel title="Ask ORCA" subtitle="Your marine assistant is here to help">
          <div className={styles.suggestionRow}>
            {SUGGESTIONS.map((q) => (
              <Link key={q} href={`/chat?q=${encodeURIComponent(q)}`} className={styles.suggestionChip}>
                {q}
              </Link>
            ))}
          </div>
          <Link href="/chat" className={styles.askInput}>
            <span>Type your question...</span>
            <IconChevronRight size={16} />
          </Link>
        </Panel>

        <div className={styles.twoCol}>
          <Panel title="Recent Queries" action={<Link href="/saved">View All</Link>}>
            {savedQueries.length === 0 ? (
              <p className={styles.emptyText}>No queries yet -- ask ORCA a question to get started.</p>
            ) : (
              <ul className={styles.queryList}>
                {savedQueries.slice(0, 4).map((q) => (
                  <li key={q.id}>
                    <Link href={`/chat?q=${encodeURIComponent(q.text)}`} className={styles.queryRow}>
                      <div className={styles.queryMain}>
                        <div className={styles.queryText}>{q.text}</div>
                        <div className={styles.queryTime}>{timeAgo(q.timestamp)}</div>
                      </div>
                      {q.verdict ? <VerdictBadge verdict={q.verdict} /> : <Badge>{INTENT_LABELS[q.intent] ?? q.intent}</Badge>}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Quick Actions">
            <div className={styles.actionGrid}>
              {QUICK_ACTIONS.map(({ label, q, href, Icon }) => (
                <Link key={label} href={href ?? `/chat?q=${encodeURIComponent(q)}`} className={styles.actionTile}>
                  <Icon size={18} />
                  {label}
                </Link>
              ))}
            </div>
          </Panel>
        </div>

        <Panel title="Data Sources">
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

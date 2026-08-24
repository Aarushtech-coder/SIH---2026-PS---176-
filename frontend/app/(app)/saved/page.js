"use client";

import Link from "next/link";
import { Topbar } from "@/components/shell/Topbar";
import { Badge, VerdictBadge } from "@/components/ui/Badge";
import { useOrca } from "@/lib/store";
import { useLocale } from "@/lib/i18n/LocaleContext";
import { IconTrash, IconBookmark } from "@/components/icons/Icons";
import styles from "./page.module.css";

const INTENT_KEYS = {
  nearest_pfz: "intent.nearest_pfz",
  safe_to_sail: "intent.safe_to_sail",
  geofence_check: "intent.geofence_check",
  weather_tide: "intent.weather_tide",
};

export default function SavedQueriesPage() {
  const { savedQueries, clearSavedQueries, removeSavedQuery } = useOrca();
  const { t } = useLocale();

  return (
    <>
      <Topbar
        title={t("nav.saved")}
        subtitle={t("saved.subtitle")}
        right={
          savedQueries.length > 0 && (
            <button type="button" className={styles.clearButton} onClick={clearSavedQueries}>
              {t("saved.clearAll")}
            </button>
          )
        }
      />

      <div className={styles.content}>
        {savedQueries.length === 0 ? (
          <div className={styles.empty}>
            <IconBookmark size={26} />
            <p>{t("saved.emptyTitle")}</p>
            <span>{t("saved.emptyHint")}</span>
            <Link href="/chat" className={styles.emptyCta}>
              {t("saved.askQuestion")}
            </Link>
          </div>
        ) : (
          <ul className={styles.list}>
            {savedQueries.map((q) => (
              <li key={q.id} className={styles.row}>
                <Link href={`/chat?q=${encodeURIComponent(q.text)}`} className={styles.rowLink}>
                  <div className={styles.rowMain}>
                    <div className={styles.rowText}>{q.text}</div>
                    <div className={styles.rowTime}>{new Date(q.timestamp).toLocaleString()}</div>
                  </div>
                  <div className={styles.rowBadges}>
                    <Badge>{t(INTENT_KEYS[q.intent] ?? q.intent)}</Badge>
                    {q.verdict && <VerdictBadge verdict={q.verdict} />}
                  </div>
                </Link>
                <button
                  type="button"
                  className={styles.deleteButton}
                  aria-label="Delete saved query"
                  onClick={() => removeSavedQuery(q.id)}
                >
                  <IconTrash size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

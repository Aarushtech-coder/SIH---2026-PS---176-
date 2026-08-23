"use client";

import Link from "next/link";
import { Topbar } from "@/components/shell/Topbar";
import { Badge, VerdictBadge } from "@/components/ui/Badge";
import { useOrca } from "@/lib/store";
import { INTENT_LABELS } from "@/lib/format";
import { IconTrash, IconBookmark } from "@/components/icons/Icons";
import styles from "./page.module.css";

export default function SavedQueriesPage() {
  const { savedQueries, clearSavedQueries, removeSavedQuery } = useOrca();

  return (
    <>
      <Topbar
        title="Saved Queries"
        subtitle="Your question history with ORCA"
        right={
          savedQueries.length > 0 && (
            <button type="button" className={styles.clearButton} onClick={clearSavedQueries}>
              Clear all
            </button>
          )
        }
      />

      <div className={styles.content}>
        {savedQueries.length === 0 ? (
          <div className={styles.empty}>
            <IconBookmark size={26} />
            <p>No saved queries yet</p>
            <span>Questions you ask ORCA will show up here so you can revisit them.</span>
            <Link href="/chat" className={styles.emptyCta}>
              Ask a question
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
                    <Badge>{INTENT_LABELS[q.intent] ?? q.intent}</Badge>
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

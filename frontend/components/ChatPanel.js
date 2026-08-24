"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./ChatPanel.module.css";
import AnswerCard from "./AnswerCard";
import { IconSend, IconMic } from "@/components/icons/Icons";
import { useLocale } from "@/lib/i18n/LocaleContext";

const SUGGESTION_KEYS = ["suggestion.safe", "suggestion.nearestZone", "suggestion.boundary"];

export default function ChatPanel({ messages, onSend, loading }) {
  const { t } = useLocale();
  const [input, setInput] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  function submit(e) {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;
    onSend(q);
    setInput("");
  }

  return (
    <section className={styles.panel}>
      <div className={styles.messages} ref={listRef}>
        {messages.length === 0 && (
          <div className={styles.empty}>
            <p className={styles.emptyTitle}>{t("chat.subtitle")}</p>
            <p className={styles.emptyHint}>{t("chat.emptyHint")}</p>
            <div className={styles.suggestions}>
              {SUGGESTION_KEYS.map((key) => (
                <button key={key} type="button" onClick={() => onSend(t(key))} disabled={loading}>
                  {t(key)}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className={`${styles.bubble} ${styles.user}`}>
              <p>{m.text}</p>
            </div>
          ) : (
            <div key={m.id} className={`${styles.bubble} ${styles.assistant}`}>
              <AnswerCard turnState={m.turnState} />
            </div>
          )
        )}

        {loading && (
          <div className={`${styles.bubble} ${styles.assistant} ${styles.thinking}`}>
            <span className={styles.dot} />
            <span className={styles.dot} />
            <span className={styles.dot} />
          </div>
        )}
      </div>

      <form className={styles.inputRow} onSubmit={submit}>
        <button type="button" className={styles.iconButton} aria-label="Voice input" disabled>
          <IconMic size={18} />
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t("chat.placeholder")}
          disabled={loading}
        />
        <button type="submit" className={styles.sendButton} disabled={loading || !input.trim()}>
          <IconSend size={17} />
        </button>
      </form>
    </section>
  );
}

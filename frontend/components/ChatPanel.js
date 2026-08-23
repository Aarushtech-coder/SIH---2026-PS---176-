"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./ChatPanel.module.css";
import AnswerCard from "./AnswerCard";
import { IconSend, IconMic } from "@/components/icons/Icons";

const SUGGESTIONS = [
  "Is it safe to go to sea tomorrow?",
  "Where's the nearest fishing zone?",
  "Am I close to the maritime boundary?",
];

export default function ChatPanel({ messages, onSend, loading }) {
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
            <p className={styles.emptyTitle}>Ask ORCA about conditions at sea</p>
            <p className={styles.emptyHint}>Fishing zones, sailing safety, weather, or boundary status.</p>
            <div className={styles.suggestions}>
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" onClick={() => onSend(s)} disabled={loading}>
                  {s}
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
          placeholder="Ask ORCA..."
          disabled={loading}
        />
        <button type="submit" className={styles.sendButton} disabled={loading || !input.trim()}>
          <IconSend size={17} />
        </button>
      </form>
    </section>
  );
}

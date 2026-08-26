"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./ChatPanel.module.css";
import AnswerCard from "./AnswerCard";
import { IconSend, IconMic, IconAlert } from "@/components/icons/Icons";
import { useLocale } from "@/lib/i18n/LocaleContext";
import { useLocalStorage } from "@/lib/useLocalStorage";
import { useMounted } from "@/lib/useMounted";

const SUGGESTION_KEYS = ["suggestion.safe", "suggestion.nearestZone", "suggestion.boundary"];

const VOICE_SUPPORTED =
  typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia && !!window.MediaRecorder;

export default function ChatPanel({ messages, onSend, onSendVoice, loading }) {
  const { t } = useLocale();
  const [settings] = useLocalStorage("orca.settings", { voiceInput: true });
  const [input, setInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [micError, setMicError] = useState(null);
  const mounted = useMounted();
  const listRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

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

  async function startRecording() {
    setMicError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        onSendVoice(blob);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      setMicError(t("chat.micDenied"));
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  function handleMicClick() {
    if (loading) return;
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  // Optimistic rendering: assume voice is enabled during SSR and hydration.
  // This prevents the mic button from "popping in" late. If the user disabled it
  // or the browser doesn't support it, it will gracefully disappear after mount.
  const voiceEnabled = mounted ? (settings.voiceInput !== false && VOICE_SUPPORTED) : true;


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

        {messages.map((m) => {
          if (m.role === "error") {
            return (
              <div key={m.id} className={`${styles.bubble} ${styles.error}`}>
                <IconAlert size={15} />
                <span>{m.text || t("chat.requestFailed")}</span>
              </div>
            );
          }
          if (m.role === "user") {
            return (
              <div key={m.id} className={`${styles.bubble} ${styles.user}`}>
                <p>{m.pending ? t("chat.transcribing") : m.text}</p>
              </div>
            );
          }
          return (
            <div key={m.id} className={`${styles.bubble} ${styles.assistant}`}>
              <AnswerCard turnState={m.turnState} />
            </div>
          );
        })}

        {loading && (
          <div className={`${styles.bubble} ${styles.assistant} ${styles.thinking}`}>
            <span className={styles.dot} />
            <span className={styles.dot} />
            <span className={styles.dot} />
          </div>
        )}
      </div>

      {isRecording && (
        <div className={styles.recordingBar}>
          <span className={styles.recordingDot} />
          {t("chat.listening")}
        </div>
      )}
      {micError && <div className={styles.micErrorBar}>{micError}</div>}

      <form className={styles.inputRow} onSubmit={submit}>
        {voiceEnabled && (
          <button
            type="button"
            className={`${styles.iconButton} ${isRecording ? styles.recording : ""}`}
            aria-label={t("chat.listening")}
            onClick={handleMicClick}
            disabled={loading}
          >
            <IconMic size={18} />
          </button>
        )}
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

"use client";

import { Suspense, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Topbar } from "@/components/shell/Topbar";
import ChatPanel from "@/components/ChatPanel";
import AgentTracePanel from "@/components/AgentTracePanel";
import MapPreviewCard from "@/components/MapPreviewCard";
import { useOrca } from "@/lib/store";
import { useLocale } from "@/lib/i18n/LocaleContext";
import styles from "./page.module.css";

function ChatPageInner() {
  const { messages, trace, pipeline, mapData, loading, runQuery, runVoiceQuery } = useOrca();
  const { t } = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const handledParam = useRef(null);

  useEffect(() => {
    const q = searchParams.get("q");
    if (q && handledParam.current !== q) {
      handledParam.current = q;
      runQuery(q);
      router.replace("/chat");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  return (
    <>
      <Topbar title={t("nav.chat")} subtitle={t("chat.subtitle")} />
      <div className={styles.content}>
        <ChatPanel messages={messages} onSend={runQuery} onSendVoice={runVoiceQuery} loading={loading} />
        <div className={styles.side}>
          <AgentTracePanel pipeline={pipeline} trace={trace} loading={loading} />
          <MapPreviewCard mapData={mapData} />
        </div>
      </div>
    </>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatPageInner />
    </Suspense>
  );
}

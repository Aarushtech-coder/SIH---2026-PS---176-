"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { sendQuery, sendVoiceQuery } from "./api";
import { useLocalStorage } from "./useLocalStorage";

const OrcaContext = createContext(null);

function extractVerdict(turnState) {
  return turnState.agent_outputs?.risk_agent?.data?.verdict ?? null;
}

// Session state (chat thread, live trace, last map result) plus saved-query
// history lives here so it survives client-side navigation between
// /dashboard, /chat, /map, /saved -- they all read the same conversation.
export function OrcaProvider({ children }) {
  const [messages, setMessages] = useState([]);
  const [trace, setTrace] = useState([]);
  const [pipeline, setPipeline] = useState([]);
  const [mapData, setMapData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [savedQueries, setSavedQueries] = useLocalStorage("orca.savedQueries", []);

  const finishTurn = useCallback(
    (turnState, queryText) => {
      setMessages((prev) => [...prev, { id: `${Date.now()}-a`, role: "assistant", turnState }]);
      setMapData(turnState.map_data);

      setSavedQueries((prev) =>
        [
          {
            id: turnState.turn_id,
            text: queryText,
            intent: turnState.intent,
            verdict: extractVerdict(turnState),
            timestamp: new Date().toISOString(),
          },
          ...prev,
        ].slice(0, 50)
      );
    },
    [setSavedQueries]
  );

  const failTurn = useCallback((err) => {
    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-e`, role: "error", text: err?.message || "" },
    ]);
  }, []);

  const runQuery = useCallback(
    async (text) => {
      const query = text.trim();
      if (!query) return;

      setMessages((prev) => [...prev, { id: `${Date.now()}-u`, role: "user", text: query }]);
      setTrace([]);
      setPipeline([]);
      setLoading(true);

      try {
        const turnState = await sendQuery(query, {
          onPlan: (agents) => setPipeline(agents),
          onTrace: (entry) => setTrace((prev) => [...prev, entry]),
        });
        finishTurn(turnState, query);
      } catch (err) {
        failTurn(err);
      } finally {
        setLoading(false);
      }
    },
    [finishTurn, failTurn]
  );

  // Records->transcribe flow: the user's message bubble starts "pending"
  // (we don't know the query text yet) and is filled in with the backend's
  // transcribed_text once the response lands.
  const runVoiceQuery = useCallback(
    async (audioBlob) => {
      const userMsgId = `${Date.now()}-u`;
      setMessages((prev) => [...prev, { id: userMsgId, role: "user", text: null, pending: true }]);
      setTrace([]);
      setPipeline([]);
      setLoading(true);

      try {
        const turnState = await sendVoiceQuery(audioBlob, {
          onPlan: (agents) => setPipeline(agents),
          onTrace: (entry) => setTrace((prev) => [...prev, entry]),
        });

        const transcribed = turnState.transcribed_text || turnState.raw_query || "";
        setMessages((prev) => prev.map((m) => (m.id === userMsgId ? { ...m, text: transcribed, pending: false } : m)));
        finishTurn(turnState, transcribed);
      } catch (err) {
        setMessages((prev) => prev.filter((m) => m.id !== userMsgId));
        failTurn(err);
      } finally {
        setLoading(false);
      }
    },
    [finishTurn, failTurn]
  );

  const clearSavedQueries = useCallback(() => setSavedQueries([]), [setSavedQueries]);

  const removeSavedQuery = useCallback(
    (id) => setSavedQueries((prev) => prev.filter((q) => q.id !== id)),
    [setSavedQueries]
  );

  const value = {
    messages,
    trace,
    pipeline,
    mapData,
    loading,
    runQuery,
    runVoiceQuery,
    savedQueries,
    clearSavedQueries,
    removeSavedQuery,
  };

  return <OrcaContext.Provider value={value}>{children}</OrcaContext.Provider>;
}

export function useOrca() {
  const ctx = useContext(OrcaContext);
  if (!ctx) throw new Error("useOrca must be used within OrcaProvider");
  return ctx;
}

"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { sendQuery } from "./api";
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

        setMessages((prev) => [...prev, { id: `${Date.now()}-a`, role: "assistant", turnState }]);
        setMapData(turnState.map_data);

        setSavedQueries((prev) =>
          [
            {
              id: turnState.turn_id,
              text: query,
              intent: turnState.intent,
              verdict: extractVerdict(turnState),
              timestamp: new Date().toISOString(),
            },
            ...prev,
          ].slice(0, 50)
        );
      } finally {
        setLoading(false);
      }
    },
    [setSavedQueries]
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

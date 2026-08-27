"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import { sendQuery, sendVoiceQuery } from "./api";
import { useLocalStorage } from "./useLocalStorage";
import { useGeolocation } from "./useGeolocation";
import { haversineKm } from "./format";

const OrcaContext = createContext(null);

// Default fallback location (Chennai) -- used only when the browser hasn't
// granted GPS access, same default already used elsewhere in the app
// (LocationChip, MAP_LAYERS). The dashboard flags in its UI when this
// fallback is in use rather than presenting it as the user's real position.
const DEFAULT_LOCATION = { latitude: 13.0827, longitude: 80.2707 };

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
  const [savedQueries, setSavedQueries] = useLocalStorage(
    "orca.savedQueries",
    [],
  );
  const [dashboardSnapshot, setDashboardSnapshot] = useState({
    status: "idle", // idle | loading | ready | error
    weather: null,
    risk: null,
    nearestPfzKm: null,
    fetchedAt: null,
    usedDefaultLocation: false,
  });

  // GPS — single read per session; exposed so any component can consume it.
  const {
    latitude,
    longitude,
    status: geoStatus,
    retry: retryGeo,
  } = useGeolocation();
  const geoLocation = useMemo(
    () => (geoStatus === "granted" ? { latitude, longitude } : null),
    [geoStatus, latitude, longitude],
  );

  const finishTurn = useCallback(
    (turnState, queryText) => {
      setMessages((prev) => [
        ...prev,
        { id: `${Date.now()}-a`, role: "assistant", turnState },
      ]);
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
        ].slice(0, 50),
      );
    },
    [setSavedQueries],
  );

  const failTurn = useCallback((err) => {
    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-e`, role: "error", text: err?.message || "" },
    ]);
  }, []);

  const runQuery = useCallback(
    async (text, coordsOverride) => {
      const query = text.trim();
      if (!query) return;

      const coords = coordsOverride || geoLocation;

      setMessages((prev) => [
        ...prev,
        { id: `${Date.now()}-u`, role: "user", text: query },
      ]);
      setTrace([]);
      setPipeline([]);
      setLoading(true);

      try {
        const turnState = await sendQuery(query, coords, {
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
    [finishTurn, failTurn, geoLocation],
  );

  // Records->transcribe flow: the user's message bubble starts "pending"
  // (we don't know the query text yet) and is filled in with the backend's
  // transcribed_text once the response lands.
  const runVoiceQuery = useCallback(
    async (audioBlob) => {
      const userMsgId = `${Date.now()}-u`;
      setMessages((prev) => [
        ...prev,
        { id: userMsgId, role: "user", text: null, pending: true },
      ]);
      setTrace([]);
      setPipeline([]);
      setLoading(true);

      try {
        const turnState = await sendVoiceQuery(audioBlob, {
          onPlan: (agents) => setPipeline(agents),
          onTrace: (entry) => setTrace((prev) => [...prev, entry]),
        });

        const transcribed =
          turnState.transcribed_text || turnState.raw_query || "";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === userMsgId
              ? { ...m, text: transcribed, pending: false }
              : m,
          ),
        );
        finishTurn(turnState, transcribed);
      } catch (err) {
        setMessages((prev) => prev.filter((m) => m.id !== userMsgId));
        failTurn(err);
      } finally {
        setLoading(false);
      }
    },
    [finishTurn, failTurn],
  );

  // Silent background fetch for the Dashboard's overview tiles -- unlike
  // runQuery, this never touches messages/savedQueries, so it doesn't show
  // up as a fake chat turn just because the dashboard loaded.
  const refreshDashboardSnapshot = useCallback(async () => {
    const usingDefault = !geoLocation;
    const coords = geoLocation || DEFAULT_LOCATION;

    setDashboardSnapshot((prev) => ({ ...prev, status: "loading" }));

    try {
      const [safeState, pfzState] = await Promise.all([
        sendQuery("What are the current wind and wave conditions, and is it safe to sail?", coords),
        sendQuery("Where is the nearest fishing zone?", coords),
      ]);

      const weather = safeState.agent_outputs?.weather_agent?.data ?? null;
      const risk = safeState.agent_outputs?.risk_agent?.data ?? null;
      const pfzZones = pfzState.agent_outputs?.marine_data_agent?.data?.pfz_zones ?? [];

      // marine_data_agent's own distance_from_coast_km is currently a
      // documented Phase-1 sentinel (-1.0, not implemented upstream yet) --
      // zone lat/lon are real, so compute the actual distance from here
      // instead of trusting that field.
      const distances = pfzZones
        .filter((z) => typeof z.latitude === "number" && typeof z.longitude === "number")
        .map((z) => haversineKm(coords.latitude, coords.longitude, z.latitude, z.longitude));

      setDashboardSnapshot({
        status: "ready",
        weather,
        risk,
        nearestPfzKm: distances.length ? Math.min(...distances) : null,
        fetchedAt: new Date().toISOString(),
        usedDefaultLocation: usingDefault,
      });
    } catch (err) {
      setDashboardSnapshot((prev) => ({ ...prev, status: "error", error: err?.message || "" }));
    }
  }, [geoLocation]);

  const clearSavedQueries = useCallback(
    () => setSavedQueries([]),
    [setSavedQueries],
  );

  const removeSavedQuery = useCallback(
    (id) => setSavedQueries((prev) => prev.filter((q) => q.id !== id)),
    [setSavedQueries],
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
    dashboardSnapshot,
    refreshDashboardSnapshot,
    // GPS state
    geoLocation,
    geoStatus,
    retryGeo,
  };

  return <OrcaContext.Provider value={value}>{children}</OrcaContext.Provider>;
}

export function useOrca() {
  const ctx = useContext(OrcaContext);
  if (!ctx) throw new Error("useOrca must be used within OrcaProvider");
  return ctx;
}

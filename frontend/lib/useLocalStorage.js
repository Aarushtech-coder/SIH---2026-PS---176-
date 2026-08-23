"use client";

import { useCallback, useSyncExternalStore } from "react";

function readRaw(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function subscribe(key, callback) {
  const listener = (e) => {
    if (!e.key || e.key === key) callback();
  };
  window.addEventListener("storage", listener);
  return () => window.removeEventListener("storage", listener);
}

// Reads/writes JSON to localStorage via useSyncExternalStore, so the client
// starts from `initialValue` (matching SSR) and syncs to the stored value
// right after hydration -- no manual effect+setState hydration dance.
export function useLocalStorage(key, initialValue) {
  const getSnapshot = useCallback(() => readRaw(key), [key]);
  const getServerSnapshot = useCallback(() => null, []);
  const subscribeKey = useCallback((callback) => subscribe(key, callback), [key]);

  const raw = useSyncExternalStore(subscribeKey, getSnapshot, getServerSnapshot);
  const value = raw !== null ? JSON.parse(raw) : initialValue;

  const setValue = useCallback(
    (updater) => {
      const currentRaw = readRaw(key);
      const current = currentRaw !== null ? JSON.parse(currentRaw) : initialValue;
      const next = typeof updater === "function" ? updater(current) : updater;

      try {
        window.localStorage.setItem(key, JSON.stringify(next));
      } catch {
        // storage full/blocked -- in-memory value below still updates for this tab
      }
      // Native "storage" events only fire in *other* tabs; notify this one too.
      window.dispatchEvent(new StorageEvent("storage", { key }));
    },
    [key, initialValue]
  );

  return [value, setValue];
}

// lib/useGeolocation.js
// Single-read GPS hook using useSyncExternalStore to avoid useEffect+setState
// patterns that trigger the react-compiler lint rule. Never throws.
"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * @typedef {"idle"|"requesting"|"granted"|"denied"|"unavailable"} GeoStatus
 * @typedef {{ latitude: number|null, longitude: number|null, status: GeoStatus, tick: number }} GeoSnapshot
 */

// Module-level mutable store — one instance shared across all consumers.
// This avoids useEffect entirely: state lives outside React.
/** @type {GeoSnapshot} */
let snapshot = { latitude: null, longitude: null, status: "idle", tick: 0 };
/** @type {Set<() => void>} */
const listeners = new Set();
let pendingRequest = false;

function notify() {
  for (const fn of listeners) fn();
}

function requestPosition() {
  if (pendingRequest) return;
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    snapshot = { ...snapshot, status: "unavailable" };
    notify();
    return;
  }
  pendingRequest = true;
  snapshot = { ...snapshot, status: "requesting" };
  notify();

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      pendingRequest = false;
      snapshot = {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        status: "granted",
        tick: snapshot.tick,
      };
      notify();
    },
    (err) => {
      pendingRequest = false;
      // 1 = PERMISSION_DENIED, 2 = POSITION_UNAVAILABLE, 3 = TIMEOUT
      snapshot = {
        latitude: null,
        longitude: null,
        status: err.code === 1 ? "denied" : "unavailable",
        tick: snapshot.tick,
      };
      notify();
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
  );
}

// Subscribe to the external store.
function subscribe(callback) {
  listeners.add(callback);
  // Kick off the first request when the first subscriber arrives.
  requestPosition();
  return () => listeners.delete(callback);
}

function getSnapshot() {
  return snapshot;
}

// Server snapshot — safe, static, never throws.
function getServerSnapshot() {
  return { latitude: null, longitude: null, status: "idle", tick: 0 };
}

/**
 * @returns {{ latitude: number|null, longitude: number|null, status: GeoStatus, retry: () => void }}
 */
export function useGeolocation() {
  const snap = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const retry = useCallback(() => {
    if (pendingRequest) return;
    snapshot = { ...snapshot, tick: snapshot.tick + 1 };
    pendingRequest = false;
    requestPosition();
  }, []);

  return {
    latitude: snap.latitude,
    longitude: snap.longitude,
    status: snap.status,
    retry,
  };
}

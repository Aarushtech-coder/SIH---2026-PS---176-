"use client";

import { useSyncExternalStore } from "react";

function subscribe() {
  // Mounted-ness never changes after the first client render, so there's
  // nothing to subscribe to -- this is a no-op unsubscribe.
  return () => {};
}

// True only after the client has hydrated, false during SSR and the first
// client render (which must match SSR output). Use this instead of the
// useState(false) + useEffect(() => setState(true)) pattern -- that one
// calls setState synchronously inside an effect, which is a real anti-
// pattern (cascading renders), not just a lint nag.
export function useMounted() {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false
  );
}

// t: the useLocale() translation function, so relative times render in the
// current UI language instead of always English.
export function timeAgo(isoString, t) {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const minutes = Math.round(diffMs / 60000);

  if (minutes < 1) return t("time.justNow");
  if (minutes < 60) return t("time.minAgo", { n: minutes });

  const hours = Math.round(minutes / 60);
  if (hours < 24) return t("time.hoursAgo", { n: hours });

  const days = Math.round(hours / 24);
  if (days === 1) return t("time.yesterday");
  if (days < 7) return t("time.daysAgo", { n: days });

  return new Date(isoString).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const COMPASS_POINTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

export function degToCompass(deg) {
  if (deg == null || Number.isNaN(deg)) return null;
  return COMPASS_POINTS[Math.round(((deg % 360) + 360) % 360 / 45) % 8];
}

// Great-circle distance in km. marine_data_agent's own distance_from_coast_km
// field is currently a documented Phase-1 sentinel (-1.0, "not available yet"
// upstream) -- zone lat/lon are real though, so this computes the actual
// distance from the caller's position instead of trusting the sentinel.
export function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

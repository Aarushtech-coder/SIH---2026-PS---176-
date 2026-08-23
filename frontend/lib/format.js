export function timeAgo(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const minutes = Math.round(diffMs / 60000);

  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.round(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;

  return new Date(isoString).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export const INTENT_LABELS = {
  nearest_pfz: "PFZ",
  safe_to_sail: "Safety",
  geofence_check: "Boundary",
  weather_tide: "Weather",
};

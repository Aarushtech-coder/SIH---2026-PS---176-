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

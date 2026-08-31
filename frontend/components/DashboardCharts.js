"use client";

import { useLocale } from "@/lib/i18n/LocaleContext";
import { haversineKm } from "@/lib/format";
import Panel from "./ui/Panel";
import styles from "./DashboardCharts.module.css";

// A single "value vs. safety thresholds" bar. tone follows the same
// safe/caution/unsafe vocabulary already used for the risk verdict badge
// elsewhere on the dashboard, so color + word always travel together
// (never color alone).
function ThresholdBar({ label, value, unit, caution, unsafe, valueLabel, t }) {
  let tone = "safe";
  if (unsafe != null && value >= unsafe) tone = "unsafe";
  else if (value >= caution) tone = "caution";

  // Scale to whatever's largest -- the live value, or the unsafe threshold
  // when we have one, or a bit past caution otherwise (wave height has no
  // "unsafe" figure in the API's thresholds_used, only caution).
  const scaleMax = Math.max(value, unsafe ?? caution * 1.5, caution) * 1.15;
  const pct = (v) => Math.min(100, (v / scaleMax) * 100);

  return (
    <div className={styles.thresholdRow}>
      <div className={styles.thresholdHead}>
        <span className={styles.thresholdLabel}>{label}</span>
        <span className={`${styles.thresholdValue} ${styles[tone]}`}>
          {valueLabel} · {t(`verdict.${tone}`)}
        </span>
      </div>
      <div className={styles.track}>
        <div className={`${styles.fill} ${styles[tone]}`} style={{ width: `${pct(value)}%` }} />
        <div
          className={styles.tick}
          style={{ left: `${pct(caution)}%` }}
          title={`${t("verdict.caution")}: ${caution}${unit}`}
        />
        {unsafe != null && (
          <div
            className={`${styles.tick} ${styles.tickUnsafe}`}
            style={{ left: `${pct(unsafe)}%` }}
            title={`${t("verdict.unsafe")}: ${unsafe}${unit}`}
          />
        )}
      </div>
      <div className={styles.thresholdFoot}>
        <span>
          {t("verdict.caution")}: {caution}
          {unit}
        </span>
        {unsafe != null && (
          <span>
            {t("verdict.unsafe")}: {unsafe}
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}

function RiskThresholdsChart({ weather, thresholds, t }) {
  const hasWind = weather?.wind_speed_kmh != null && thresholds?.max_safe_wind_speed_kmh != null;
  // wave_height_m has no "unsafe" figure in thresholds_used -- only caution --
  // so its bar shows a caution tick only, rather than guessing an unsafe
  // number the API doesn't actually give us.
  const hasWave = weather?.wave_height_m != null && thresholds?.max_safe_wave_height_m != null;

  if (!hasWind && !hasWave) {
    return <p className={styles.emptyNote}>{t("chart.noThresholds")}</p>;
  }

  return (
    <div className={styles.thresholdList}>
      {hasWind && (
        <ThresholdBar
          label={t("stat.wind")}
          value={weather.wind_speed_kmh}
          unit=" km/h"
          caution={thresholds.max_safe_wind_speed_kmh}
          unsafe={thresholds.unsafe_wind_speed_kmh}
          valueLabel={`${Math.round(weather.wind_speed_kmh)} km/h`}
          t={t}
        />
      )}
      {hasWave && (
        <ThresholdBar
          label={t("stat.waveHeight")}
          value={weather.wave_height_m}
          unit=" m"
          caution={thresholds.max_safe_wave_height_m}
          unsafe={null}
          valueLabel={`${weather.wave_height_m.toFixed(2)} m`}
          t={t}
        />
      )}
    </div>
  );
}

// Real per-zone distances, computed the same way the Dashboard's own
// "Nearest PFZ" stat and Map Explorer's PFZ layer already do (haversine from
// the current dashboard location to each real zone's lat/lon) -- not a new
// data source, just a different view of data already flowing through.
function PfzDistanceChart({ pfzZones, location, t }) {
  const distances = (pfzZones || [])
    .filter((z) => typeof z.latitude === "number" && typeof z.longitude === "number")
    .map((z) => ({
      id: z.zone_id,
      km: haversineKm(location.latitude, location.longitude, z.latitude, z.longitude),
    }))
    .sort((a, b) => a.km - b.km)
    .slice(0, 5);

  if (!distances.length) {
    return <p className={styles.emptyNote}>{t("chart.noZones")}</p>;
  }

  const maxKm = Math.max(...distances.map((d) => d.km)) * 1.15;

  return (
    <div className={styles.barList}>
      {distances.map((d) => (
        <div key={d.id} className={styles.barRow}>
          <span className={styles.barLabel} title={d.id}>
            {d.id}
          </span>
          <div className={styles.barTrack}>
            <div className={`${styles.barFill} ${styles.pfzFill}`} style={{ width: `${(d.km / maxKm) * 100}%` }} />
          </div>
          <span className={styles.barValue}>{d.km.toFixed(1)} km</span>
        </div>
      ))}
    </div>
  );
}

// wave_height_m and swell_height_m are both real fields straight from
// weather_agent, both in meters -- directly comparable on one axis, unlike
// wind (km/h) which stays in its own chart above.
function SeaStateChart({ weather, t }) {
  const wave = weather?.wave_height_m;
  const swell = weather?.swell_height_m;

  if (wave == null && swell == null) {
    return <p className={styles.emptyNote}>{t("chart.noSeaState")}</p>;
  }

  const max = Math.max(wave || 0, swell || 0, 0.1) * 1.2;
  const rows = [
    { key: "wave", label: t("stat.waveHeight"), value: wave, cls: styles.waveFill, dotCls: styles.waveDot },
    { key: "swell", label: t("chart.swellHeight"), value: swell, cls: styles.swellFill, dotCls: styles.swellDot },
  ].filter((r) => r.value != null);

  return (
    <>
      <div className={styles.legend}>
        {rows.map((r) => (
          <span key={r.key} className={styles.legendItem}>
            <span className={`${styles.dot} ${r.dotCls}`} />
            {r.label}
          </span>
        ))}
      </div>
      <div className={styles.barList}>
        {rows.map((r) => (
          <div key={r.key} className={styles.barRow}>
            <span className={styles.barLabel}>{r.label}</span>
            <div className={styles.barTrack}>
              <div className={`${styles.barFill} ${r.cls}`} style={{ width: `${(r.value / max) * 100}%` }} />
            </div>
            <span className={styles.barValue}>{r.value.toFixed(2)} m</span>
          </div>
        ))}
      </div>
    </>
  );
}

// Sits directly below the Dashboard's stat grid. Reads the exact same
// dashboardSnapshot the stats above it already use, so it updates for the
// same location (GPS, map search, or a pin) automatically -- no separate
// fetch, no new backend work.
export default function DashboardCharts({ dashboardSnapshot }) {
  const { t } = useLocale();
  const { status, weather, risk, location, pfzZones } = dashboardSnapshot;

  return (
    <Panel title={t("chart.title")} subtitle={t("chart.subtitle")}>
      {status !== "ready" ? (
        <p className={styles.emptyNote}>{t("chart.loading")}</p>
      ) : (
        <div className={styles.grid}>
          <div className={styles.chartCard}>
            <h3 className={styles.chartTitle}>{t("chart.riskThresholds")}</h3>
            <RiskThresholdsChart weather={weather} thresholds={risk?.thresholds_used} t={t} />
          </div>

          <div className={styles.chartCard}>
            <h3 className={styles.chartTitle}>{t("chart.pfzDistances")}</h3>
            <PfzDistanceChart pfzZones={pfzZones} location={location} t={t} />
          </div>

          <div className={styles.chartCard}>
            <h3 className={styles.chartTitle}>{t("chart.seaState")}</h3>
            <SeaStateChart weather={weather} t={t} />
          </div>
        </div>
      )}
    </Panel>
  );
}

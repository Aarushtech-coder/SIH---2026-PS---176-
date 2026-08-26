"use client";

import { Topbar } from "@/components/shell/Topbar";
import Panel from "@/components/ui/Panel";
import Toggle from "@/components/ui/Toggle";
import LanguageSwitcher from "@/components/shell/LanguageSwitcher";
import { useLocalStorage } from "@/lib/useLocalStorage";
import { useOrca } from "@/lib/store";
import { useLocale } from "@/lib/i18n/LocaleContext";
import styles from "./page.module.css";

const DEFAULT_SETTINGS = {
  units: "km",
  defaultLocation: "Chennai, India",
  notifications: true,
  notificationSound: true,
  voiceInput: true,
  refreshInterval: "30",
  showDataSource: true,
};

function Row({ label, description, control }) {
  return (
    <div className={styles.row}>
      <div className={styles.rowText}>
        <div className={styles.rowLabel}>{label}</div>
        {description && <div className={styles.rowDesc}>{description}</div>}
      </div>
      <div className={styles.rowControl}>{control}</div>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useLocalStorage("orca.settings", DEFAULT_SETTINGS);
  const { clearSavedQueries, geoStatus, retryGeo } = useOrca();
  const { t } = useLocale();

  function set(key, value) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  function resetAll() {
    setSettings(DEFAULT_SETTINGS);
    clearSavedQueries();
  }

  function locationStatusText() {
    if (geoStatus === "granted") return t("settings.locationGranted");
    if (geoStatus === "denied") return t("settings.locationDenied");
    if (geoStatus === "requesting") return t("settings.locationRequesting");
    return t("settings.locationUnavailable");
  }

  return (
    <>
      <Topbar title={t("nav.settings")} subtitle={t("settings.subtitle")} />

      <div className={styles.content}>
        <Panel title={t("settings.general")}>
          <Row label={t("settings.language")} description={t("settings.languageDesc")} control={<LanguageSwitcher className={styles.select} />} />
          <Row
            label={t("settings.units")}
            description={t("settings.unitsDesc")}
            control={
              <select value={settings.units} onChange={(e) => set("units", e.target.value)} className={styles.select}>
                <option value="km">{t("settings.km")}</option>
                <option value="nm">{t("settings.nm")}</option>
              </select>
            }
          />
          <Row
            label={t("settings.defaultLocation")}
            description={t("settings.defaultLocationDesc")}
            control={
              <input
                className={styles.textInput}
                value={settings.defaultLocation}
                onChange={(e) => set("defaultLocation", e.target.value)}
              />
            }
          />
          {/* GPS location status — non-blocking, collapses gracefully */}
          <Row
            label={t("settings.location")}
            description={locationStatusText()}
            control={
              geoStatus === "denied" ? (
                <button type="button" className={styles.resetButton} onClick={retryGeo}>
                  {t("settings.locationRetry")}
                </button>
              ) : null
            }
          />
        </Panel>

        <Panel title={t("settings.notifications")}>
          <Row
            label={t("settings.alertPreferences")}
            description={t("settings.alertPreferencesDesc")}
            control={<Toggle checked={settings.notifications} onChange={(v) => set("notifications", v)} label={t("settings.alertPreferences")} />}
          />
          <Row
            label={t("settings.notificationSound")}
            description={t("settings.notificationSoundDesc")}
            control={
              <Toggle
                checked={settings.notificationSound}
                onChange={(v) => set("notificationSound", v)}
                label={t("settings.notificationSound")}
              />
            }
          />
        </Panel>

        <Panel title={t("settings.voiceAudio")}>
          <Row
            label={t("settings.enableMic")}
            description={t("settings.enableMicDesc")}
            control={<Toggle checked={settings.voiceInput} onChange={(v) => set("voiceInput", v)} label={t("settings.enableMic")} />}
          />
        </Panel>

        <Panel title={t("settings.dataDisplay")}>
          <Row
            label={t("settings.refreshInterval")}
            description={t("settings.refreshIntervalDesc")}
            control={
              <select
                value={settings.refreshInterval}
                onChange={(e) => set("refreshInterval", e.target.value)}
                className={styles.select}
              >
                <option value="15">{t("settings.min15")}</option>
                <option value="30">{t("settings.min30")}</option>
                <option value="60">{t("settings.min60")}</option>
              </select>
            }
          />
          <Row
            label={t("settings.showDataSource")}
            description={t("settings.showDataSourceDesc")}
            control={
              <Toggle checked={settings.showDataSource} onChange={(v) => set("showDataSource", v)} label={t("settings.showDataSource")} />
            }
          />
        </Panel>

        <Panel title={t("settings.about")}>
          <Row label={t("settings.version")} description={t("brand.tagline")} control={<span className={styles.version}>v1.0.0</span>} />
          <Row
            label={t("settings.resetAll")}
            description={t("settings.resetAllDesc")}
            control={
              <button type="button" className={styles.resetButton} onClick={resetAll}>
                {t("settings.reset")}
              </button>
            }
          />
        </Panel>
      </div>
    </>
  );
}

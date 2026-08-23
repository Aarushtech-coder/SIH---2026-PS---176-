"use client";

import { Topbar } from "@/components/shell/Topbar";
import Panel from "@/components/ui/Panel";
import Toggle from "@/components/ui/Toggle";
import { useLocalStorage } from "@/lib/useLocalStorage";
import { useOrca } from "@/lib/store";
import styles from "./page.module.css";

const DEFAULT_SETTINGS = {
  units: "km",
  defaultLocation: "Chennai, India",
  notifications: true,
  notificationSound: true,
  voiceInput: false,
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
  const { clearSavedQueries } = useOrca();

  function set(key, value) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  function resetAll() {
    setSettings(DEFAULT_SETTINGS);
    clearSavedQueries();
  }

  return (
    <>
      <Topbar title="Settings" subtitle="Customize your preferences and app settings" />

      <div className={styles.content}>
        <Panel title="General">
          <Row
            label="Units"
            description="Distance unit used across the app"
            control={
              <select value={settings.units} onChange={(e) => set("units", e.target.value)} className={styles.select}>
                <option value="km">Kilometres</option>
                <option value="nm">Nautical miles</option>
              </select>
            }
          />
          <Row
            label="Default location"
            description="Used for the dashboard overview and map centre"
            control={
              <input
                className={styles.textInput}
                value={settings.defaultLocation}
                onChange={(e) => set("defaultLocation", e.target.value)}
              />
            }
          />
        </Panel>

        <Panel title="Notifications">
          <Row
            label="Alert preferences"
            description="Get notified about weather and safety alerts"
            control={<Toggle checked={settings.notifications} onChange={(v) => set("notifications", v)} label="Alert preferences" />}
          />
          <Row
            label="Notification sound"
            description="Play a sound for new alerts"
            control={<Toggle checked={settings.notificationSound} onChange={(v) => set("notificationSound", v)} label="Notification sound" />}
          />
        </Panel>

        <Panel title="Voice & audio">
          <Row
            label="Enable microphone"
            description="Allow voice input in Chat Assistant"
            control={<Toggle checked={settings.voiceInput} onChange={(v) => set("voiceInput", v)} label="Enable microphone" />}
          />
        </Panel>

        <Panel title="Data & display">
          <Row
            label="Data refresh interval"
            description="How often marine data is refreshed"
            control={
              <select
                value={settings.refreshInterval}
                onChange={(e) => set("refreshInterval", e.target.value)}
                className={styles.select}
              >
                <option value="15">15 minutes</option>
                <option value="30">30 minutes</option>
                <option value="60">60 minutes</option>
              </select>
            }
          />
          <Row
            label="Show data source"
            description="Show which agency a response's data came from"
            control={<Toggle checked={settings.showDataSource} onChange={(v) => set("showDataSource", v)} label="Show data source" />}
          />
        </Panel>

        <Panel title="About ORCA">
          <Row label="Version" description="Marine Intelligence Assistant" control={<span className={styles.version}>v1.0.0</span>} />
          <Row
            label="Reset all settings"
            description="Restore defaults and clear saved query history"
            control={
              <button type="button" className={styles.resetButton} onClick={resetAll}>
                Reset
              </button>
            }
          />
        </Panel>
      </div>
    </>
  );
}

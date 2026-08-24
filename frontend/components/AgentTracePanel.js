"use client";

import styles from "./AgentTracePanel.module.css";
import { IconCheck, IconSpinner } from "@/components/icons/Icons";
import { useLocale } from "@/lib/i18n/LocaleContext";

const AGENT_KEYS = {
  planner: "agent.planner",
  weather_agent: "agent.weather_agent",
  marine_data_agent: "agent.marine_data_agent",
  ocean_analytics_agent: "agent.ocean_analytics_agent",
  risk_agent: "agent.risk_agent",
  geospatial_agent: "agent.geospatial_agent",
  synthesizer: "agent.synthesizer",
};

const PENDING_KEYS = {
  planner: "pending.planner",
  weather_agent: "pending.weather_agent",
  marine_data_agent: "pending.marine_data_agent",
  ocean_analytics_agent: "pending.ocean_analytics_agent",
  risk_agent: "pending.risk_agent",
  geospatial_agent: "pending.geospatial_agent",
  synthesizer: "pending.synthesizer",
};

// Renders the planned agent pipeline for the current turn, deriving each
// step's status from how many trace entries have landed so far -- so the
// list fills in live as the (simulated) multi-agent run progresses.
export default function AgentTracePanel({ pipeline, trace, loading }) {
  const { t } = useLocale();
  const hasRun = pipeline.length > 0;

  return (
    <section className={styles.panel}>
      <h2>
        {t("trace.title")} {hasRun && loading && <span className={styles.live}>{t("trace.live")}</span>}
      </h2>

      {!hasRun ? (
        <p className={styles.empty}>{t("trace.empty")}</p>
      ) : (
        <ol className={styles.steps}>
          {pipeline.map((agent, i) => {
            const entry = trace[i];
            const status = entry ? "done" : i === trace.length && loading ? "running" : "pending";

            return (
              <li key={`${agent}-${i}`} className={`${styles.step} ${styles[status]}`}>
                <span className={styles.statusIcon}>
                  {status === "done" && <IconCheck size={13} strokeWidth={2.5} />}
                  {status === "running" && <IconSpinner size={13} />}
                </span>
                <div className={styles.stepBody}>
                  <span className={styles.agentName}>{t(AGENT_KEYS[agent] ?? agent)}</span>
                  <p className={styles.summary}>
                    {entry ? entry.output_summary : status === "running" ? t("trace.working") : t(PENDING_KEYS[agent])}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

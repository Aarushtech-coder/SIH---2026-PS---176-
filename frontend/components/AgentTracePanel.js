import styles from "./AgentTracePanel.module.css";
import { IconCheck, IconSpinner } from "@/components/icons/Icons";

const AGENT_LABELS = {
  planner: "Planner Agent",
  weather_agent: "Weather Agent",
  marine_data_agent: "Marine Data Agent",
  ocean_analytics_agent: "Ocean Analytics Agent",
  risk_agent: "Risk Assessment Agent",
  geospatial_agent: "Geospatial Agent",
  synthesizer: "Synthesizer Agent",
};

const PENDING_HINTS = {
  planner: "Waiting to classify query",
  weather_agent: "Waiting to fetch forecast",
  marine_data_agent: "Waiting to fetch PFZ advisory",
  ocean_analytics_agent: "Waiting to fetch ocean data",
  risk_agent: "Waiting to assess risk",
  geospatial_agent: "Waiting to check boundary",
  synthesizer: "Waiting to compose final answer",
};

// Renders the planned agent pipeline for the current turn, deriving each
// step's status from how many trace entries have landed so far -- so the
// list fills in live as the (simulated) multi-agent run progresses.
export default function AgentTracePanel({ pipeline, trace, loading }) {
  const hasRun = pipeline.length > 0;

  return (
    <section className={styles.panel}>
      <h2>Agent Activity {hasRun && loading && <span className={styles.live}>Live</span>}</h2>

      {!hasRun ? (
        <p className={styles.empty}>Ask a question to watch the multi-agent pipeline run here.</p>
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
                  <span className={styles.agentName}>{AGENT_LABELS[agent] ?? agent}</span>
                  <p className={styles.summary}>
                    {entry ? entry.output_summary : status === "running" ? "Working..." : PENDING_HINTS[agent]}
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

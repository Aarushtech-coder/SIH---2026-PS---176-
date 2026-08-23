import styles from "./AnswerCard.module.css";
import { VerdictBadge } from "@/components/ui/Badge";

export default function AnswerCard({ turnState }) {
  const risk = turnState.agent_outputs?.risk_agent?.data;

  return (
    <div className={styles.card}>
      {risk?.verdict && <VerdictBadge verdict={risk.verdict} />}

      <p className={styles.answer}>{turnState.final_answer}</p>

      {risk?.reasons?.length > 0 && (
        <ul className={styles.reasons}>
          {risk.reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}

      {turnState.disclaimer && <p className={styles.disclaimer}>{turnState.disclaimer}</p>}

      {turnState.citations?.length > 0 && (
        <div className={styles.citations}>
          {turnState.citations.map((c) => (
            <span key={c} className={styles.citation}>
              {c.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

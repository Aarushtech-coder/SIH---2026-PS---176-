import styles from "./StatCard.module.css";

export default function StatCard({ icon: Icon, label, value, sub, tone = "accent" }) {
  return (
    <div className={styles.card}>
      <div className={`${styles.iconWrap} ${styles[tone]}`}>
        <Icon size={17} strokeWidth={2} />
      </div>
      <div className={styles.body}>
        <div className={styles.label}>{label}</div>
        <div className={styles.value}>{value}</div>
        {sub && <div className={styles.sub}>{sub}</div>}
      </div>
    </div>
  );
}

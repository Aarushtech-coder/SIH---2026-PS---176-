import styles from "./Panel.module.css";

export default function Panel({ title, subtitle, action, children, className = "" }) {
  return (
    <section className={`${styles.panel} ${className}`}>
      {(title || action) && (
        <div className={styles.header}>
          <div>
            {title && <h2 className={styles.title}>{title}</h2>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {action && <div className={styles.action}>{action}</div>}
        </div>
      )}
      <div className={styles.body}>{children}</div>
    </section>
  );
}

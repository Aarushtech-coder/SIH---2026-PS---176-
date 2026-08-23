import { OrcaProvider } from "@/lib/store";
import Sidebar from "@/components/shell/Sidebar";
import styles from "./layout.module.css";

export default function AppLayout({ children }) {
  return (
    <OrcaProvider>
      <div className={styles.shell}>
        <Sidebar />
        <main className={styles.main}>{children}</main>
      </div>
    </OrcaProvider>
  );
}

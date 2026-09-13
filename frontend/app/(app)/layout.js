import { OrcaProvider } from "@/lib/store";
import { LocaleProvider } from "@/lib/i18n/LocaleContext";
import { MobileNavProvider } from "@/components/shell/MobileNavContext";
import Sidebar from "@/components/shell/Sidebar";
import styles from "./layout.module.css";

export default function AppLayout({ children }) {
  return (
    <LocaleProvider>
      <OrcaProvider>
        <MobileNavProvider>
          <div className={styles.shell}>
            <Sidebar />
            <main className={styles.main}>{children}</main>
          </div>
        </MobileNavProvider>
      </OrcaProvider>
    </LocaleProvider>
  );
}

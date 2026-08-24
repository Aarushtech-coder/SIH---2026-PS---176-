"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Sidebar.module.css";
import LanguageSwitcher from "./LanguageSwitcher";
import { useLocale } from "@/lib/i18n/LocaleContext";
import {
  IconLogo,
  IconDashboard,
  IconChat,
  IconMap,
  IconBookmark,
  IconSettings,
} from "@/components/icons/Icons";

const NAV_ITEMS = [
  { href: "/dashboard", key: "nav.dashboard", Icon: IconDashboard },
  { href: "/chat", key: "nav.chat", Icon: IconChat },
  { href: "/map", key: "nav.map", Icon: IconMap },
  { href: "/saved", key: "nav.saved", Icon: IconBookmark },
  { href: "/settings", key: "nav.settings", Icon: IconSettings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { t } = useLocale();

  return (
    <nav className={styles.sidebar}>
      <div className={styles.brand}>
        <IconLogo size={30} />
        <div>
          <div className={styles.brandName}>ORCA</div>
          <div className={styles.brandTag}>{t("brand.tagline")}</div>
        </div>
      </div>

      <ul className={styles.nav}>
        {NAV_ITEMS.map(({ href, key, Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <li key={href}>
              <Link href={href} className={`${styles.navItem} ${active ? styles.active : ""}`}>
                <Icon size={18} strokeWidth={active ? 2 : 1.75} />
                {t(key)}
              </Link>
            </li>
          );
        })}
      </ul>

      <div className={styles.spacer} />

      <LanguageSwitcher className={styles.languageSwitcher} />

      <div className={styles.userChip}>
        <div className={styles.avatar}>F</div>
        <div className={styles.userInfo}>
          <div className={styles.userName}>{t("brand.user")}</div>
          <div className={styles.userLocation}>Chennai, India</div>
        </div>
      </div>
    </nav>
  );
}

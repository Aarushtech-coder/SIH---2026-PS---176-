"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Sidebar.module.css";
import {
  IconLogo,
  IconDashboard,
  IconChat,
  IconMap,
  IconBookmark,
  IconSettings,
} from "@/components/icons/Icons";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", Icon: IconDashboard },
  { href: "/chat", label: "Chat Assistant", Icon: IconChat },
  { href: "/map", label: "Map Explorer", Icon: IconMap },
  { href: "/saved", label: "Saved Queries", Icon: IconBookmark },
  { href: "/settings", label: "Settings", Icon: IconSettings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className={styles.sidebar}>
      <div className={styles.brand}>
        <IconLogo size={30} />
        <div>
          <div className={styles.brandName}>ORCA</div>
          <div className={styles.brandTag}>Marine Intelligence</div>
        </div>
      </div>

      <ul className={styles.nav}>
        {NAV_ITEMS.map(({ href, label, Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <li key={href}>
              <Link href={href} className={`${styles.navItem} ${active ? styles.active : ""}`}>
                <Icon size={18} strokeWidth={active ? 2 : 1.75} />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>

      <div className={styles.spacer} />

      <div className={styles.userChip}>
        <div className={styles.avatar}>F</div>
        <div className={styles.userInfo}>
          <div className={styles.userName}>Fisherman</div>
          <div className={styles.userLocation}>Chennai, India</div>
        </div>
      </div>
    </nav>
  );
}

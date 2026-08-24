"use client";

import { useLocale } from "@/lib/i18n/LocaleContext";
import styles from "./LanguageSwitcher.module.css";

export default function LanguageSwitcher({ className = "" }) {
  const { locale, setLocale, locales } = useLocale();

  return (
    <select
      className={`${styles.select} ${className}`}
      value={locale}
      onChange={(e) => setLocale(e.target.value)}
      aria-label="Language"
    >
      {locales.map((l) => (
        <option key={l.code} value={l.code}>
          {l.nativeLabel}
        </option>
      ))}
    </select>
  );
}

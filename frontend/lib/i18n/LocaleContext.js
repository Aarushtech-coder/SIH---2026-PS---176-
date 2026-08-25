"use client";

import { createContext, useCallback, useContext, useMemo } from "react";
import { LOCALES, TRANSLATIONS } from "./translations";
import { useLocalStorage } from "@/lib/useLocalStorage";

const LocaleContext = createContext(null);

export function LocaleProvider({ children }) {
  const [locale, setLocale] = useLocalStorage("orca.locale", "en");

  const t = useCallback(
    (key, params) => {
      const dict = TRANSLATIONS[locale] ?? TRANSLATIONS.en;
      let text = dict[key] ?? TRANSLATIONS.en[key] ?? key;
      if (params) {
        for (const [param, value] of Object.entries(params)) {
          text = text.replaceAll(`{${param}}`, value);
        }
      }
      return text;
    },
    [locale]
  );

  const value = useMemo(() => ({ locale, setLocale, t, locales: LOCALES }), [locale, setLocale, t]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}

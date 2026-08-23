// Minimal stroke-based icon set (24x24, currentColor) so the app doesn't
// depend on an icon package. Consistent viewBox/strokeWidth = visual system.

function Svg({ children, size = 20, strokeWidth = 1.75, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {children}
    </svg>
  );
}

export function IconDashboard(props) {
  return (
    <Svg {...props}>
      <rect x="3.5" y="3.5" width="7.5" height="7.5" rx="1.5" />
      <rect x="13" y="3.5" width="7.5" height="4.5" rx="1.5" />
      <rect x="13" y="10.5" width="7.5" height="10" rx="1.5" />
      <rect x="3.5" y="13.5" width="7.5" height="7" rx="1.5" />
    </Svg>
  );
}

export function IconChat(props) {
  return (
    <Svg {...props}>
      <path d="M4 5.5h16v11H9.5L5 20.5v-4H4z" />
    </Svg>
  );
}

export function IconMap(props) {
  return (
    <Svg {...props}>
      <path d="M9 4.5 4 6.5v13l5-2 6 2 5-2v-13l-5 2-6-2Z" />
      <path d="M9 4.5v13M15 6.5v13" />
    </Svg>
  );
}

export function IconBookmark(props) {
  return (
    <Svg {...props}>
      <path d="M6 4h12v16l-6-4-6 4Z" />
    </Svg>
  );
}

export function IconSettings(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 13.5a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V19.5a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87A1.7 1.7 0 0 0 3 12.53H2.9a2 2 0 1 1 0-4H3a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34H9a1.7 1.7 0 0 0 1.03-1.56V.9a2 2 0 1 1 4 0v.09A1.7 1.7 0 0 0 15.06 2a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.09c.2.67.75 1.19 1.44 1.36H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51 1.35Z" />
    </Svg>
  );
}

export function IconSend(props) {
  return (
    <Svg {...props}>
      <path d="M4.5 12 20 4.5 15 19.5l-3.5-6.5L4.5 12Z" />
      <path d="M11.5 13 15 19.5" />
    </Svg>
  );
}

export function IconMic(props) {
  return (
    <Svg {...props}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0" />
      <path d="M12 17.5v3M9 20.5h6" />
    </Svg>
  );
}

export function IconSearch(props) {
  return (
    <Svg {...props}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m19.5 19.5-4.3-4.3" />
    </Svg>
  );
}

export function IconLayers(props) {
  return (
    <Svg {...props}>
      <path d="m12 3 8.5 4.5L12 12 3.5 7.5 12 3Z" />
      <path d="m3.5 12 8.5 4.5L20.5 12" />
      <path d="m3.5 16.5 8.5 4.5 8.5-4.5" />
    </Svg>
  );
}

export function IconAlert(props) {
  return (
    <Svg {...props}>
      <path d="M12 3.5 21.5 20h-19L12 3.5Z" />
      <path d="M12 10v4.5M12 17.2v.1" />
    </Svg>
  );
}

export function IconChevronRight(props) {
  return (
    <Svg {...props}>
      <path d="m9 5 7 7-7 7" />
    </Svg>
  );
}

export function IconPin(props) {
  return (
    <Svg {...props}>
      <path d="M12 21.5s7-6.6 7-12A7 7 0 0 0 5 9.5c0 5.4 7 12 7 12Z" />
      <circle cx="12" cy="9.5" r="2.4" />
    </Svg>
  );
}

export function IconWind(props) {
  return (
    <Svg {...props}>
      <path d="M3.5 8h10.75a2.375 2.375 0 1 0-2.375-2.375" />
      <path d="M3.5 12.5h14.75a2.375 2.375 0 1 1-2.375 2.375" />
      <path d="M3.5 17h8.25a2.125 2.125 0 1 1-2.125 2.125" />
    </Svg>
  );
}

export function IconWave(props) {
  return (
    <Svg {...props}>
      <path d="M2.5 9.5c1.5-2 3.5-2 5 0s3.5 2 5 0 3.5-2 5 0 3.5 2 4.5 0" />
      <path d="M2.5 15.5c1.5-2 3.5-2 5 0s3.5 2 5 0 3.5-2 5 0 3.5 2 4.5 0" />
    </Svg>
  );
}

export function IconFish(props) {
  return (
    <Svg {...props}>
      <path d="M3 12c3-4.5 7.5-6.5 12-4.5 2 .9 3.7 2.5 5 4.5-1.3 2-3 3.6-5 4.5-4.5 2-9 0-12-4.5Z" />
      <path d="M15 9.5 18 6M15 14.5l3 3.5" />
      <circle cx="7.3" cy="12" r=".9" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function IconShield(props) {
  return (
    <Svg {...props}>
      <path d="M12 3.5 19 6v6c0 4.5-3 7.5-7 8.5-4-1-7-4-7-8.5V6l7-2.5Z" />
    </Svg>
  );
}

export function IconSun(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
    </Svg>
  );
}

export function IconCheck(props) {
  return (
    <Svg {...props}>
      <path d="m4.5 12.5 5 5 10-11" />
    </Svg>
  );
}

export function IconClock(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3.2 2" />
    </Svg>
  );
}

export function IconTrash(props) {
  return (
    <Svg {...props}>
      <path d="M4.5 7h15M9.5 7V5a1.5 1.5 0 0 1 1.5-1.5h2A1.5 1.5 0 0 1 14.5 5v2M6.5 7l.8 12.2A1.5 1.5 0 0 0 8.8 20.5h6.4a1.5 1.5 0 0 0 1.5-1.3L17.5 7" />
    </Svg>
  );
}

export function IconCopy(props) {
  return (
    <Svg {...props}>
      <rect x="8.5" y="8.5" width="11.5" height="11.5" rx="1.75" />
      <path d="M15.5 8.5V6A1.5 1.5 0 0 0 14 4.5H5.5A1.5 1.5 0 0 0 4 6v8.5A1.5 1.5 0 0 0 5.5 16H8" />
    </Svg>
  );
}

export function IconCompass(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m14.8 9.2-1.9 4.7-4.7 1.9 1.9-4.7 4.7-1.9Z" />
    </Svg>
  );
}

export function IconHelp(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.5 9.3a2.5 2.5 0 1 1 3.7 2.2c-.8.5-1.2 1-1.2 1.9v.3" />
      <path d="M12 17.2v.1" />
    </Svg>
  );
}

export function IconSpinner({ size = 20, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      style={{ animation: "orca-spin 0.8s linear infinite" }}
      {...props}
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.2" strokeWidth="2.5" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export function IconLogo({ size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="12" fill="var(--accent)" />
      <path
        d="M5.5 13.5c1.8-3.6 4.3-5.5 6.8-5.5 2.2 0 4.2 1.5 5.7 3.8-1.5 2.3-3.5 3.7-5.7 3.7-2.5 0-5-1.9-6.8-4Z"
        fill="white"
        opacity="0.95"
      />
      <circle cx="9.2" cy="12" r="0.9" fill="var(--accent)" />
    </svg>
  );
}

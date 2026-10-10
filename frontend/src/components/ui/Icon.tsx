/**
 * The app's small line-icon set, drawn for KASHT on a 24px grid (no icon library: docs/PIVOT.md rule 4).
 * Icons are decorative by default (aria-hidden): every status and action they sit beside also says it in words.
 */
const PATHS = {
  home: <path d="M4 11 12 4l8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z" />,
  why: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.6 9.4a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.6" />
      <path d="M12 16.8v.2" />
    </>
  ),
  pin: (
    <>
      <path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z" />
      <circle cx="12" cy="10" r="2.4" />
    </>
  ),
  sprout: (
    <>
      <path d="M12 20v-8" />
      <path d="M12 12c0-3.5-2.5-6-6.5-6 0 3.5 2.5 6 6.5 6z" />
      <path d="M12 14c0-3.2 2.3-5.5 6-5.5 0 3.2-2.3 5.5-6 5.5z" />
    </>
  ),
  trend: (
    <>
      <path d="M4 19h16" />
      <path d="M5 15l4-4 3 3 6-6" />
      <path d="M15 8h3v3" />
    </>
  ),
  receipt: (
    <>
      <path d="M6 3.5h12v17l-2.4-1.5-2.4 1.5-2.4-1.5-2.4 1.5L6 20.5z" />
      <path d="M9 8.5h6M9 12h6M9 15.5h3.5" />
    </>
  ),
  chat: <path d="M5 5.5h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-8l-4.5 3.5v-3.5H5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1z" />,
  user: (
    <>
      <circle cx="12" cy="8.5" r="3.6" />
      <path d="M5 20c.8-3.6 3.6-5.5 7-5.5s6.2 1.9 7 5.5" />
    </>
  ),
  more: (
    <>
      <circle cx="6" cy="12" r="1.3" />
      <circle cx="12" cy="12" r="1.3" />
      <circle cx="18" cy="12" r="1.3" />
    </>
  ),
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  checkCircle: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.3 12.3l2.6 2.6 4.9-5.2" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  alert: (
    <>
      <path d="M12 4.2 21 19.5H3z" />
      <path d="M12 10v4.2M12 16.8v.2" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5.5M12 7.8v.2" />
    </>
  ),
  error: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.2 9.2l5.6 5.6M14.8 9.2l-5.6 5.6" />
    </>
  ),
  repeat: (
    <>
      <path d="M5 9.5h11.5L13.5 6.5" />
      <path d="M19 14.5H7.5l3 3" />
    </>
  ),
  calculator: (
    <>
      <rect x="5.5" y="3.5" width="13" height="17" rx="1.5" />
      <path d="M8.5 7.5h7M9 12h.01M12 12h.01M15 12h.01M9 15.5h.01M12 15.5h.01M15 15.5h.01" />
    </>
  ),
  chevron: <path d="M7 10l5 5 5-5" />,
  external: (
    <>
      <path d="M14 5h5v5" />
      <path d="M19 5l-8 8" />
      <path d="M17 13.5V19H5V7h5.5" />
    </>
  ),
  wheat: (
    <>
      <path d="M12 21V9" />
      <path d="M12 13c-2.2 0-3.8-1.5-4-3.8 2.2 0 3.8 1.5 4 3.8zM12 13c2.2 0 3.8-1.5 4-3.8-2.2 0-3.8 1.5-4 3.8z" />
      <path d="M12 17c-2.2 0-3.8-1.5-4-3.8 2.2 0 3.8 1.5 4 3.8zM12 17c2.2 0 3.8-1.5 4-3.8-2.2 0-3.8 1.5-4 3.8z" />
      <path d="M12 9c-1.3-.8-1.8-2.3-1.2-4.2 1.3.8 1.8 2.3 1.2 4.2zM12 9c1.3-.8 1.8-2.3 1.2-4.2-1.3.8-1.8 2.3-1.2 4.2z" />
    </>
  ),
  close: <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />,
} as const

export type IconName = keyof typeof PATHS

export function Icon({ name, className = 'size-5', label }: { name: IconName; className?: string; label?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`shrink-0 ${className}`}
      aria-hidden={label ? undefined : true}
      role={label ? 'img' : undefined}
      aria-label={label}
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  )
}

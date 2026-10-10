import { ChevronDown, Info } from 'lucide-react'
import type { ReactNode } from 'react'

/** An expandable panel ("What FarmSight cannot know"): a native <details>, so it works without script. */
export function Disclosure({ title, children, open = false }: { title: string; children: ReactNode; open?: boolean }) {
  return (
    <details className="card group" open={open}>
      <summary className="flex min-h-12 cursor-pointer list-none items-center gap-3 px-5 py-3 font-semibold">
        <Info aria-hidden className="size-5 shrink-0 text-slate" />
        <span className="flex-1">{title}</span>
        <ChevronDown aria-hidden className="size-5 shrink-0 transition-transform group-open:rotate-180" />
      </summary>
      <div className="px-5 pb-5 text-sm text-slate">{children}</div>
    </details>
  )
}

/** A quiet note: an icon and a sentence on a soft background. Tone picks caution or plain information. */
export function Note({ children, tone = 'info' }: { children: ReactNode; tone?: 'info' | 'caution' }) {
  const look = tone === 'caution' ? 'bg-wheat-soft text-wheat-deep' : 'bg-slate-soft text-slate'
  return (
    <p className={`flex items-start gap-2 rounded-[var(--radius-control)] px-4 py-3 text-sm ${look}`}>
      <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
      <span>{children}</span>
    </p>
  )
}

/** An on/off switch with its label (alert settings). */
export function Toggle({
  label,
  checked,
  onChange,
  disabled = false,
}: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="flex min-h-14 w-full items-center justify-between gap-3 rounded-[var(--radius-control)] border border-line bg-paper px-4 py-2 text-start disabled:opacity-60"
    >
      <span>{label}</span>
      <span
        aria-hidden
        className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${checked ? 'bg-field' : 'bg-slate'}`}
      >
        <span
          className={`absolute top-1 size-5 rounded-full bg-paper transition-all ${checked ? 'start-6' : 'start-1'}`}
        />
      </span>
    </button>
  )
}

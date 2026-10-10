/**
 * Visual primitives for the reference design: paper cards, buttons, status badges, callouts, form fields,
 * skeletons and empty states. Visual only: they hold no data and no behaviour of their own, so a screen keeps
 * every behaviour it had and just looks the part.
 */
import type { ReactNode } from 'react'

import { Icon, type IconName } from './Icon'
import { STATUS, type StatusKind } from './styles'

/** A card heading: a calm, large title with an optional icon and a muted line under it. */
export function CardTitle({ icon, children, sub, as: Tag = 'h2' }: {
  icon?: IconName
  children: ReactNode
  sub?: ReactNode
  as?: 'h2' | 'h3'
}) {
  return (
    <div className="space-y-1">
      <Tag className="flex items-center gap-2 text-xl font-bold text-ink">
        {icon && <Icon name={icon} className="size-6 text-field" />}
        <span>{children}</span>
      </Tag>
      {sub && <p className="text-sm text-slate">{sub}</p>}
    </div>
  )
}

/** A small pill: an icon and the status in words. */
export function Badge({ kind, children }: { kind: StatusKind; children: ReactNode }) {
  const s = STATUS[kind]
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-0.5 text-sm font-semibold ${s.className}`}>
      {s.icon && <Icon name={s.icon} className="size-4" />}
      <span>{children}</span>
    </span>
  )
}

// ---------------------------------------------------------------- callouts

export type CalloutTone = 'caution' | 'info' | 'error' | 'positive'

const CALLOUT: Record<CalloutTone, { icon: IconName; className: string }> = {
  caution: { icon: 'alert', className: 'border-wheat/60 bg-wheat-soft text-wheat-deep' },
  info: { icon: 'info', className: 'border-transparent bg-mist text-slate' },
  error: { icon: 'error', className: 'border-madder/30 bg-madder-soft text-madder' },
  positive: { icon: 'checkCircle', className: 'border-field/25 bg-field-soft text-field' },
}

/** A message panel with an icon: caution (limits, old data), information, or an error. */
export function Callout({ tone, children, role, icon }: {
  tone: CalloutTone
  children: ReactNode
  role?: 'alert' | 'status'
  icon?: IconName
}) {
  const c = CALLOUT[tone]
  return (
    <div role={role} className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${c.className}`}>
      <Icon name={icon ?? c.icon} className="mt-1 size-5" />
      <div className="min-w-0 flex-1 space-y-1">{children}</div>
    </div>
  )
}

// ---------------------------------------------------------------- loading and empty

/** Grey bars where content will appear; the caller adds the spoken "loading" text. */
export function SkeletonLines({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3" aria-hidden>
      <div className="skeleton h-6 w-2/5 rounded-lg" />
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className={`skeleton h-4 rounded-lg ${i === lines - 1 ? 'w-3/5' : 'w-full'}`} />
      ))}
    </div>
  )
}

/** A calm empty state: an icon, what is missing, and (optionally) the one thing to do next. */
export function EmptyState({ icon = 'info', title, children }: { icon?: IconName; title: ReactNode; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-line bg-paper px-5 py-8 text-center">
      <Icon name={icon} className="size-7 text-slate" />
      <p className="font-semibold text-ink">{title}</p>
      {children && <div className="text-sm text-slate">{children}</div>}
    </div>
  )
}

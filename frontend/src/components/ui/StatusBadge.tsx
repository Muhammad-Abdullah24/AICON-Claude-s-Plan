import { AlertTriangle, Calculator, CheckCircle2, Clock, FileText, XCircle, type LucideIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import type { BadgeKind } from '../../lib/status'

const LOOK: Record<BadgeKind, { icon: LucideIcon; className: string }> = {
  fresh: { icon: CheckCircle2, className: 'bg-field-soft text-field' },
  limited: { icon: AlertTriangle, className: 'bg-wheat-soft text-wheat-deep' },
  stale: { icon: Clock, className: 'bg-wheat-soft text-wheat-deep' },
  frozen: { icon: AlertTriangle, className: 'bg-wheat-soft text-wheat-deep' },
  samePrice: { icon: AlertTriangle, className: 'bg-wheat-soft text-wheat-deep' },
  fewDays: { icon: AlertTriangle, className: 'bg-wheat-soft text-wheat-deep' },
  estimate: { icon: Calculator, className: 'bg-slate-soft text-slate' },
  illustrative: { icon: FileText, className: 'bg-slate-soft text-slate' },
  error: { icon: XCircle, className: 'bg-madder-soft text-madder' },
}

/** A status as an icon and a word, never colour alone. */
export function StatusBadge({ kind }: { kind: BadgeKind }) {
  const { t } = useTranslation()
  const { icon: Icon, className } = LOOK[kind]
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold ${className}`}
      data-badge={kind}
    >
      <Icon aria-hidden className="size-4 shrink-0" strokeWidth={2} />
      {t(`badge.${kind}`)}
    </span>
  )
}

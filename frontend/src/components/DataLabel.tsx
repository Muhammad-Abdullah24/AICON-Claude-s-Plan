import { useTranslation } from 'react-i18next'

import type { Lang } from '../i18n'
import { formatDate } from '../lib/format'

/**
 * States where a number came from, next to the number (PLAN.md 6.4 and 11.3):
 * synthetic or real, wholesale or retail proxy, unit, and the data date.
 */
export function DataLabel({
  isSynthetic,
  priceType,
  asOf,
}: {
  isSynthetic: boolean
  priceType?: 'wholesale' | 'retail'
  asOf?: string
}) {
  const { t, i18n } = useTranslation()
  const parts = [
    priceType && t(`data.${priceType}`),
    t('data.per40kg'),
    asOf && t('data.basedOn', { date: formatDate(asOf, i18n.language as Lang) }),
  ].filter(Boolean)

  return (
    <p className="flex flex-wrap items-center gap-x-2 text-xs text-slate">
      <span
        className={`rounded px-1.5 font-semibold ${isSynthetic ? 'tape' : 'bg-field text-paper'}`}
      >
        {isSynthetic ? t('data.synthetic') : t('data.real')}
      </span>
      {parts.join(' · ')}
    </p>
  )
}

import { useTranslation } from 'react-i18next'

import type { Lang } from '../i18n'
import { formatDate } from '../lib/format'

/**
 * States where a number came from, next to the number: real or synthetic, the AMIS source, the unit, and
 * the date of the price. An old price shows its date in amber; a price AMIS has repeated for weeks says so.
 */
export function DataLabel({
  isSynthetic,
  asOf,
  stale = false,
  unchangedSince,
}: {
  isSynthetic: boolean
  asOf?: string
  stale?: boolean
  unchangedSince?: string | null
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  return (
    <div className="space-y-0.5 text-xs text-slate">
      <p className="flex flex-wrap items-center gap-x-2">
        <span className={`rounded px-1.5 font-semibold ${isSynthetic ? 'tape' : 'bg-field text-paper'}`}>
          {isSynthetic ? t('data.synthetic') : t('data.real')}
        </span>
        <span>{t('data.source')}</span>
        <span>· {t('data.per40kg')}</span>
      </p>
      {asOf && (
        <p className={stale ? 'font-semibold text-wheat-deep' : undefined}>
          {stale
            ? t('data.stale', { date: formatDate(asOf, lang) })
            : t('data.asOf', { date: formatDate(asOf, lang) })}
        </p>
      )}
      {unchangedSince && (
        <p className="font-semibold text-wheat-deep">{t('data.unchanged', { date: formatDate(unchangedSince, lang) })}</p>
      )}
    </div>
  )
}

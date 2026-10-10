import { useTranslation } from 'react-i18next'

import type { Lang } from '../i18n'
import { formatDate } from '../lib/format'
import { Badge } from './ui/primitives'

/**
 * States where a number came from, next to the number: real or synthetic, the AMIS source, the unit, and
 * the date of the price. An old price shows its date with an "old" badge; a price AMIS has repeated for weeks
 * gets a "repeated" badge. Each badge has an icon and words, so the warning never rests on colour.
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
    <div className="space-y-2 border-t border-line pt-3 text-sm text-slate">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <Badge kind={isSynthetic ? 'synthetic' : 'fresh'}>{isSynthetic ? t('data.synthetic') : t('data.real')}</Badge>
        <span>{t('data.source')}</span>
        <span>· {t('data.per40kg')}</span>
      </p>
      {asOf &&
        (stale ? (
          <Badge kind="stale">{t('data.stale', { date: formatDate(asOf, lang) })}</Badge>
        ) : (
          <p>{t('data.asOf', { date: formatDate(asOf, lang) })}</p>
        ))}
      {unchangedSince && (
        <p>
          <Badge kind="frozen">{t('data.unchanged', { date: formatDate(unchangedSince, lang) })}</Badge>
        </p>
      )}
    </div>
  )
}

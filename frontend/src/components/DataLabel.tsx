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
  // One short line: real or synthetic, and the price date (amber when old). The source and unit sit behind the badge.
  return (
    <p className="flex flex-wrap items-center gap-2 text-sm text-slate" title={`${t('data.source')} · ${t('data.per40kg')}`}>
      <Badge kind={isSynthetic ? 'synthetic' : 'fresh'}>{isSynthetic ? t('data.synthetic') : t('data.real')}</Badge>
      {asOf &&
        (stale || unchangedSince ? (
          <Badge kind="stale">{formatDate(asOf, lang)}</Badge>
        ) : (
          <span>AMIS · {formatDate(asOf, lang)}</span>
        ))}
    </p>
  )
}

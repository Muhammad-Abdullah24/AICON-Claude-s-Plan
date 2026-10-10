import { useTranslation } from 'react-i18next'

import type { Lang } from '../i18n'
import { formatDate } from '../lib/format'
import { replayDate } from '../lib/replay'
import { Icon } from './ui/Icon'

/** Says plainly, on every screen, that the app is replaying a past week (the demo's backup weeks). */
export function ReplayBanner() {
  const { t, i18n } = useTranslation()
  if (!replayDate) return null
  return (
    <div role="status" className="border-b border-wheat bg-wheat-soft px-4 py-2.5 text-sm text-ink lg:px-8">
      <p className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <span className="flex items-start gap-2">
          <Icon name="clock" className="mt-1 size-5 text-wheat-deep" />
          <span>{t('status.replay', { date: formatDate(replayDate, i18n.language as Lang) })}</span>
        </span>
        {/* A full page load, so the replay date is cleared everywhere at once. */}
        <a href="/?as_of=" className="inline-flex min-h-11 items-center font-semibold text-field underline">
          {t('status.replayExit')}
        </a>
      </p>
    </div>
  )
}

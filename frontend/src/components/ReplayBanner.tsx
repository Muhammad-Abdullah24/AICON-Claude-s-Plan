import { useTranslation } from 'react-i18next'

import type { Lang } from '../i18n'
import { formatDate } from '../lib/format'
import { replayDate } from '../lib/replay'

/** Says plainly, on every screen, that the app is replaying a past week (the demo's backup weeks). */
export function ReplayBanner() {
  const { t, i18n } = useTranslation()
  if (!replayDate) return null
  return (
    <div role="status" className="bg-wheat px-4 py-2 text-sm text-ink">
      <p className="mx-auto flex max-w-xl flex-wrap items-baseline justify-between gap-x-3">
        <span>{t('status.replay', { date: formatDate(replayDate, i18n.language as Lang) })}</span>
        {/* A full page load, so the replay date is cleared everywhere at once. */}
        <a href="/?as_of=" className="font-semibold underline">
          {t('status.replayExit')}
        </a>
      </p>
    </div>
  )
}

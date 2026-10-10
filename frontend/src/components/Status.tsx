import { useTranslation } from 'react-i18next'

import { ApiError } from '../api/client'
import { Icon } from './ui/Icon'
import { SkeletonLines } from './ui/primitives'
import { buttonClass } from './ui/styles'

/** A quiet skeleton where the answer will appear, with the loading message for screen readers and sighted users. */
export function Loading() {
  const { t } = useTranslation()
  return (
    <div className="space-y-4 py-4" role="status">
      <SkeletonLines />
      <p className="text-sm text-slate">{t('status.loading')}</p>
    </div>
  )
}

/** Says what went wrong and offers the one action that can fix it. */
export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation()
  const status = error instanceof ApiError ? error.status : 0
  // Only a network or server failure is worth retrying; 404 and 422 will fail the same way again.
  const kind = status === 404 ? 'notFound' : status === 422 ? 'invalid' : 'error'
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-madder/30 bg-madder-soft p-4" role="alert">
      <Icon name="error" className="mt-1 size-6 text-madder" />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="font-bold text-madder">{t(`status.${kind}`)}</p>
        {kind === 'error' && <p className="text-sm text-ink">{t('status.errorHint')}</p>}
        {onRetry && kind === 'error' && (
          <button type="button" onClick={onRetry} className={buttonClass('outline', 'mt-2')}>
            {t('status.retry')}
          </button>
        )}
      </div>
    </div>
  )
}

/** A screen that crashed while drawing (not a network problem): says so, and offers a reload. */
export function ScreenError({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation()
  return (
    <div className="rounded-xl border-2 border-madder/40 bg-paper p-4" role="alert">
      <p className="font-bold text-madder">{t('status.screenError')}</p>
      <button type="button" onClick={onRetry} className="mt-3 min-h-12 rounded-xl border-2 border-ink px-4 py-2">
        {t('status.retry')}
      </button>
    </div>
  )
}

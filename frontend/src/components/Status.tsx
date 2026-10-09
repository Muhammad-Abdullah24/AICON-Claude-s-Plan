import { useTranslation } from 'react-i18next'

import { ApiError } from '../api/client'

export function Loading() {
  const { t } = useTranslation()
  return (
    <p className="py-10 text-center text-slate" role="status">
      {t('status.loading')}
    </p>
  )
}

/** Says what went wrong and offers the one action that can fix it. */
export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation()
  const status = error instanceof ApiError ? error.status : 0
  // Only a network or server failure is worth retrying; 404 and 422 will fail the same way again.
  const kind = status === 404 ? 'notFound' : status === 422 ? 'invalid' : 'error'
  return (
    <div className="rounded-xl border-2 border-madder/40 bg-paper p-4" role="alert">
      <p className="font-bold text-madder">{t(`status.${kind}`)}</p>
      {kind === 'error' && <p className="text-sm text-slate">{t('status.errorHint')}</p>}
      {onRetry && kind === 'error' && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded-lg bg-ink px-4 py-1.5 text-sm text-cotton"
        >
          {t('status.retry')}
        </button>
      )}
    </div>
  )
}

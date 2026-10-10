import { AlertCircle, Loader2, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { ApiError } from '../api/client'

/** Loading with context: a line saying what is coming, over a skeleton of the card that will appear. */
export function Loading({ label }: { label?: string }) {
  const { t } = useTranslation()
  return (
    <div className="card space-y-3 p-5" role="status" aria-live="polite">
      <p className="flex items-center gap-2 text-sm text-slate">
        <Loader2 aria-hidden className="size-4 animate-spin" />
        {label ?? t('status.loading')}
      </p>
      <div aria-hidden className="space-y-2">
        <div className="h-4 w-1/3 animate-pulse rounded bg-line" />
        <div className="h-9 w-1/2 animate-pulse rounded bg-line" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-line" />
      </div>
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
    <div className="rounded-[var(--radius-card)] border border-madder/40 bg-madder-soft p-4" role="alert">
      <p className="flex items-center gap-2 font-semibold text-madder">
        <AlertCircle aria-hidden className="size-5 shrink-0" />
        {t(`status.${kind}`)}
      </p>
      {kind === 'error' && <p className="mt-1 text-sm text-slate">{t('status.errorHint')}</p>}
      {onRetry && kind === 'error' && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 min-h-11 rounded-[var(--radius-control)] bg-ink px-4 text-sm text-paper"
        >
          {t('status.retry')}
        </button>
      )}
    </div>
  )
}

/** A first-use state: what this place is for and the one thing to do next. */
export function EmptyState({ icon: Icon, title, body, action }: {
  icon: LucideIcon
  title: string
  body: string
  action?: ReactNode
}) {
  return (
    <div className="card flex flex-col items-center gap-3 p-6 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-field-soft text-field">
        <Icon aria-hidden className="size-6" />
      </span>
      <p className="text-lg font-semibold">{title}</p>
      <p className="text-sm text-slate">{body}</p>
      {action}
    </div>
  )
}

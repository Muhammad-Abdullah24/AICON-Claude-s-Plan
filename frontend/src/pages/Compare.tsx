import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import { useAppState } from '../appState'
import { DataLabel } from '../components/DataLabel'
import { SelectionBar } from '../components/SelectionBar'
import { ErrorBox, Loading } from '../components/Status'
import type { Lang } from '../i18n'
import { formatDate, formatRs } from '../lib/format'
import { useAsync } from '../lib/useAsync'

/** Mandis ranked by net price after (estimated) transport from the farmer's mandi (UC-04). */
export function Compare() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { selection, quantity, mandiName } = useAppState()
  const [state, reload] = useAsync(
    (signal) => api.compare({ ...selection, quantity_maund: quantity }, signal),
    `${selection.crop}|${selection.mandi}|${quantity}`,
  )

  return (
    <div className="space-y-5">
      <SelectionBar />
      <section className="space-y-3">
        <h2 className="text-xl font-bold">{t('compare.title')}</h2>
        {state.status === 'loading' && <Loading />}
        {state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
        {state.status === 'ok' &&
          state.data.rows.map((r, i) => (
            <article
              key={r.mandi}
              className={`rounded-2xl bg-paper p-4 shadow-sm ${i === 0 && r.has_data ? 'border-2 border-field' : ''}`}
            >
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="text-lg font-bold">
                  {mandiName(r.mandi)}
                  {i === 0 && r.has_data && (
                    <span className="ms-2 rounded bg-field px-2 text-sm text-paper">{t('compare.best')}</span>
                  )}
                </h3>
                {r.has_data && r.net_price != null ? (
                  <span className="figures text-2xl">{formatRs(r.net_price)}</span>
                ) : (
                  <span className="text-slate">{t('compare.noData')}</span>
                )}
              </div>
              {r.has_data && (
                <dl className="mt-1 grid grid-cols-[1fr_auto] gap-x-3 text-sm text-slate">
                  <dt>{t('compare.price')}</dt>
                  <dd className="figures">{formatRs(r.price ?? 0)}</dd>
                  <dt>{t('compare.transport')}</dt>
                  <dd className="figures">−{formatRs(r.transport_cost ?? 0)}</dd>
                  {r.gain_vs_preferred != null && r.mandi !== selection.mandi && (
                    <>
                      <dt>{t('compare.gainFor', { qty: quantity })}</dt>
                      <dd className={`figures ${r.gain_vs_preferred >= 0 ? 'text-field' : 'text-madder'}`}>
                        {r.gain_vs_preferred >= 0 ? '+' : '−'}
                        {formatRs(Math.abs(r.gain_vs_preferred))}
                      </dd>
                    </>
                  )}
                </dl>
              )}
              {r.prices_as_of && (
                <p className={`mt-1 text-xs ${r.is_stale ? 'font-semibold text-wheat-deep' : 'text-slate'}`}>
                  {t('compare.priceOf', { date: formatDate(r.prices_as_of, lang) })}
                </p>
              )}
            </article>
          ))}
        {state.status === 'ok' && <DataLabel isSynthetic={state.data.is_synthetic} />}
      </section>
    </div>
  )
}

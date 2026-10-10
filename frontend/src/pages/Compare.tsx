import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import { useAppState } from '../appState'
import { HelpTip } from '../components/HelpTip'
import { DataLabel } from '../components/DataLabel'
import { SelectionBar } from '../components/SelectionBar'
import { ErrorBox, Loading } from '../components/Status'
import { Icon } from '../components/ui/Icon'
import { Badge } from '../components/ui/primitives'
import { cardClass } from '../components/ui/styles'
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
    <div className="space-y-6">
      <SelectionBar />
      <section className="space-y-4">
        <h2 className="text-2xl font-bold">
          {t('compare.title')}
          <HelpTip text={t('help.compare')} />
        </h2>
        {state.status === 'loading' && <Loading />}
        {state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
        {state.status === 'ok' &&
          (() => {
            const bestMandi = state.data.rows.find((x) => x.has_data && !x.is_stale)?.mandi
            return state.data.rows.map((r) => (
            <article
              key={r.mandi}
              className={cardClass(r.mandi === bestMandi ? 'highlight' : 'surface', 'space-y-4')}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="flex items-center gap-2 text-xl font-bold">
                  <Icon name="pin" className="size-5 text-field" />
                  {mandiName(r.mandi)}
                </h3>
                {r.mandi === bestMandi && <Badge kind="fresh">{t('compare.best')}</Badge>}
              </div>
              {r.has_data && r.net_price != null ? (
                <p className="figures text-3xl font-semibold text-ink">{formatRs(r.net_price)}</p>
              ) : (
                <Badge kind="limited">{t('compare.noData')}</Badge>
              )}
              {r.has_data && (
                <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 border-t border-line pt-3 text-sm text-slate">
                  <dt>{t('compare.price')}</dt>
                  <dd className="figures text-base text-ink">{formatRs(r.price ?? 0)}</dd>
                  <dt>{t('compare.transport')}</dt>
                  <dd className="figures text-base text-ink">−{formatRs(r.transport_cost ?? 0)}</dd>
                  {r.gain_vs_preferred != null && r.mandi !== selection.mandi && (
                    <>
                      <dt>{t('compare.gainFor', { qty: quantity })}</dt>
                      <dd className={`figures text-base font-semibold ${r.gain_vs_preferred >= 0 ? 'text-field' : 'text-madder'}`}>
                        {r.gain_vs_preferred >= 0 ? '+' : '−'}
                        {formatRs(Math.abs(r.gain_vs_preferred))}
                      </dd>
                    </>
                  )}
                </dl>
              )}
              {r.prices_as_of &&
                (r.is_stale ? (
                  <Badge kind="stale">{t('compare.priceOf', { date: formatDate(r.prices_as_of, lang) })}</Badge>
                ) : (
                  <p className="text-sm text-slate">{t('compare.priceOf', { date: formatDate(r.prices_as_of, lang) })}</p>
                ))}
            </article>
            ))
          })()}
        {state.status === 'ok' && <DataLabel isSynthetic={state.data.is_synthetic} />}
      </section>
    </div>
  )
}

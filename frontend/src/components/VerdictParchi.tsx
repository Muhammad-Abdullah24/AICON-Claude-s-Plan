import { useTranslation } from 'react-i18next'

import type { AdviceResponse, Verdict } from '../api/client'
import { formatRs } from '../lib/format'
import { useAppState } from '../appState'
import { DataLabel } from './DataLabel'

/** Each verdict gets its own colour band at the top of the slip. */
const BAND: Record<Verdict, string> = {
  sell_now: 'bg-ink',
  sell_elsewhere: 'bg-wheat',
  store: 'bg-field',
  split: 'bg-[linear-gradient(90deg,var(--color-field)_50%,var(--color-ink)_50%)]',
}

/**
 * The verdict as a parchi: the slip an arhti hands a farmer. Every number on
 * it comes from the API; the component only lays it out.
 */
export function VerdictParchi({ advice, quantity }: { advice: AdviceResponse; quantity: number }) {
  const { t } = useTranslation()
  const { mandiName } = useAppState()
  const gain = advice.rupee_difference
  const alt = advice.alternative_mandi

  return (
    <article className="parchi rounded-b-2xl px-5 pb-5" aria-live="polite">
      <div className={`-mx-5 mb-3 h-1.5 ${BAND[advice.verdict]}`} aria-hidden />
      <p className="text-sm text-slate">{t('verdict.advice')}</p>
      <h2 className="font-urdu text-3xl leading-[2] font-bold">{advice.verdict_text}</h2>
      {advice.best_week > 0 && (
        <p className="text-base text-slate">{t('verdict.bestWeek', { count: advice.best_week })}</p>
      )}

      {gain > 0 && (
        <div className="tear mt-3 flex items-baseline justify-between gap-3 pt-3">
          <span className="text-sm text-slate">
            {advice.verdict === 'split' ? t('verdict.gainSplit') : t('verdict.gainFor', { qty: quantity })}
          </span>
          <span className="figures text-3xl font-medium text-field">+{formatRs(gain)}</span>
        </div>
      )}

      {advice.alerts.length > 0 && (
        <div className="mt-3 rounded-lg bg-madder/10 p-3">
          <p className="text-sm font-bold text-madder">{t('verdict.alert')}</p>
          <ul className="text-sm">
            {advice.alerts.map((a, i) => (
              <li key={i} lang="en" dir="auto">
                {a.source_url ? (
                  <a href={a.source_url} target="_blank" rel="noreferrer" className="underline">
                    {a.headline}
                  </a>
                ) : (
                  a.headline
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="tear mt-3 pt-2">
        <p className="text-sm font-bold">{t('verdict.why')}</p>
        <ul className="list-disc ps-5">
          {advice.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </div>

      <p className="mt-2 text-sm">
        <span className="font-bold text-madder">{t('verdict.risk')}: </span>
        {advice.risk_line}
      </p>

      {alt && (
        <p className="mt-1 flex justify-between gap-3 text-sm text-slate">
          <span>{t('verdict.altMandi', { mandi: mandiName(alt.mandi) })}</span>
          <span className="figures">{formatRs(alt.net_price)}</span>
        </p>
      )}

      {advice.assumptions.length > 0 && (
        <details className="mt-2 text-sm text-slate">
          <summary className="cursor-pointer">{t('verdict.assumptions')}</summary>
          <ul className="mt-1">
            {advice.assumptions.map((a) => (
              <li key={a.name} className="flex justify-between gap-3">
                <span lang="en" dir="ltr">{a.name}</span>
                <span>
                  <span className="figures">{a.value}</span>{' '}
                  ({a.source === 'farmer' ? t('verdict.assumptionFarmer') : t('verdict.assumptionDefault')})
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}

      <div className="tear mt-3 space-y-1 pt-2">
        <p className="text-sm font-bold">{t('verdict.disclaimer')}</p>
        <DataLabel isSynthetic={advice.is_synthetic} asOf={advice.as_of} />
      </div>
    </article>
  )
}

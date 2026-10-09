import { useTranslation } from 'react-i18next'

import type { AdviceResponse, Signal } from '../api/client'
import { useAppState } from '../appState'
import { formatRs } from '../lib/format'
import { DataLabel } from './DataLabel'

/** Blueprint signal colours: SELL green, WAIT amber; always with an icon and a word. */
const STYLE: Record<Signal, { band: string; text: string; icon: string }> = {
  SELL: { band: 'bg-field', text: 'text-field', icon: '✓' },
  WAIT: { band: 'bg-wheat', text: 'text-wheat-deep', icon: '⏳' },
}

/**
 * The SELL / WAIT answer as a parchi: the slip an arhti hands a farmer. Every number comes from the API;
 * the component only lays it out.
 */
export function SignalCard({ advice }: { advice: AdviceResponse }) {
  const { t } = useTranslation()
  const { meta } = useAppState()
  const s = STYLE[advice.signal]
  const weeks = meta.horizon_weeks
  const gain = advice.rupee_impact

  return (
    <article className="parchi rounded-b-2xl px-5 pb-5" aria-live="polite">
      <div className={`-mx-5 mb-3 h-2 ${s.band}`} aria-hidden />
      <h2 className={`font-urdu text-4xl leading-[2] font-bold ${s.text}`}>
        <span aria-hidden className="me-2">
          {s.icon}
        </span>
        {t(`signal.${advice.signal}`)}
      </h2>

      <dl className="tear mt-3 grid grid-cols-[1fr_auto] items-baseline gap-x-3 gap-y-1 pt-3">
        <dt className="text-sm text-slate">{t('signal.today')}</dt>
        <dd className="figures text-2xl font-medium">{formatRs(advice.current_price)}</dd>
        <dt className="text-sm text-slate">{t('signal.inWeeks', { weeks })}</dt>
        <dd className="figures text-2xl font-medium">{formatRs(advice.predicted_price)}</dd>
      </dl>
      <p className="text-sm text-slate">
        {t('signal.range', { low: formatRs(advice.range.low), high: formatRs(advice.range.high) })}
      </p>

      <div className="tear mt-3 pt-3">
        <p className="text-sm text-slate">{t('signal.impactFor', { weeks, qty: advice.quantity_maund })}</p>
        <p className={`figures text-3xl font-medium ${gain >= 0 ? 'text-field' : 'text-madder'}`}>
          {gain >= 0 ? '+' : '−'}
          {formatRs(Math.abs(gain))}
        </p>
        <p className="text-sm text-slate">{t('signal.afterInterest', { interest: formatRs(advice.interest_cost) })}</p>
      </div>

      <p className="tear mt-3 pt-2 text-sm">
        <span className="font-bold">{t('signal.confidence')} </span>
        {t(`signal.confidenceLevels.${advice.confidence}`)}
      </p>
      {advice.model.startsWith('baseline') && <p className="mt-1 text-xs text-slate">{t('signal.baseline')}</p>}

      <div className="mt-3 space-y-1">
        <p className="text-sm font-bold">{t('signal.disclaimer')}</p>
        <DataLabel
          isSynthetic={advice.is_synthetic}
          asOf={advice.prices_as_of}
          stale={advice.is_stale}
          unchangedSince={advice.price_unchanged_since}
        />
      </div>
    </article>
  )
}

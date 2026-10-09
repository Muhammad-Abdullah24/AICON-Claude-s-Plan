import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import type { Lang } from '../i18n'
import { formatDate, formatRs } from '../lib/format'
import { alternativeVerdict, assumptions, showNextSteps, side, tone, type OfferResult as Result } from '../lib/offer'
import { DataLabel } from './DataLabel'

const TONE_CLASS = { below: 'text-madder', within: 'text-ink', above: 'text-field', limited: 'text-wheat-deep' }

function signed(value: number): string {
  return `${value < 0 ? '−' : value > 0 ? '+' : ''}${formatRs(Math.abs(value))}`
}

/**
 * The offer against recent AMIS reference prices, in the order a farmer needs it: the offer, the reported
 * price and range with their source and date, the total for their quantity, how far the reference can be
 * trusted, other mandis after transport, then what is not included. Lays out API numbers only.
 */
export function OfferResult({ result: r, mandiName }: { result: Result; mandiName: (id: string) => string }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const tn = tone(r)
  const dir = side(r.difference_vs_reference_per_maund)
  const perMaund = formatRs(Math.abs(r.difference_vs_reference_per_maund))
  const strong = r.reference_strength === 'STRONG'

  return (
    <div aria-live="polite" className="space-y-3" data-testid="offer-result">
      <h3 className={`text-xl font-bold ${TONE_CLASS[tn]}`} data-status={r.result_status}>
        {t(`offer.status.${tn}`)}
      </h3>

      <dl className="grid grid-cols-[1fr_auto] items-baseline gap-x-3 gap-y-1">
        <dt className="text-sm text-slate">{t('offer.buyerOffer')}</dt>
        <dd className="figures text-2xl font-medium">{formatRs(r.buyer_offer_price)}</dd>
        <dt className="text-sm text-slate">{t('offer.referencePrice')}</dt>
        <dd className="figures text-2xl font-medium">{formatRs(r.reference_price)}</dd>
        <dt className="text-sm text-slate">{t('offer.referenceRange')}</dt>
        <dd className="figures">
          {formatRs(r.reference_range_low)} – {formatRs(r.reference_range_high)}
        </dd>
      </dl>
      <p className="text-xs text-slate">{t('offer.grossBasis')}</p>
      <p className="text-xs text-slate">
        {t('offer.reportedDays', { days: r.reference_days, window: r.window_days })}
      </p>
      <DataLabel
        isSynthetic={r.is_synthetic}
        asOf={r.reference_price_as_of}
        stale={r.is_stale}
        unchangedSince={r.price_unchanged_since}
      />

      <div className="tear space-y-1 pt-3">
        <p>{t(`offer.vsReference.${dir}`, { diff: perMaund })}</p>
        <p className="text-sm text-slate">{t('offer.totalFor', { qty: r.quantity_maund })}</p>
        <p
          className={`figures text-3xl font-medium ${r.total_difference_vs_reference < 0 ? 'text-madder' : 'text-field'}`}
          data-testid="offer-total"
        >
          {signed(r.total_difference_vs_reference)}
        </p>
        {strong && r.total_difference_vs_range !== 0 && (
          <p className="text-sm text-slate">
            {t('offer.totalVsRange', { total: signed(r.total_difference_vs_range) })}
          </p>
        )}
      </div>

      {!strong && (
        <p className="rounded-xl bg-wheat-soft p-3 text-sm font-semibold text-wheat-deep" data-testid="offer-limited">
          {t(`offer.limited.${r.reference_strength}`, {
            days: r.reference_days,
            window: r.window_days,
            date: formatDate(r.price_unchanged_since ?? r.reference_price_as_of, lang),
          })}{' '}
          {t(`offer.limitedOffer.${dir}`, { diff: perMaund })}
        </p>
      )}

      {r.estimated_commission && (
        <p className="text-sm">
          {t('offer.commission', {
            pct: r.estimated_commission.pct,
            perMaund: formatRs(r.estimated_commission.per_maund),
            total: formatRs(r.estimated_commission.total),
          })}
        </p>
      )}

      {showNextSteps(r) && (
        <section className="space-y-1 rounded-xl bg-cotton p-3" data-testid="offer-next-steps">
          <h4 className="text-sm font-bold">{t('offer.nextSteps.title')}</h4>
          <ul className="list-disc space-y-1 ps-5 text-sm">
            {(['askReason', 'compare', 'reference', 'constraints'] as const).map((k) => (
              <li key={k}>{t(`offer.nextSteps.${k}`)}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-2">
        <h4 className="text-sm font-bold">{t('offer.alternatives.title')}</h4>
        {r.alternative_mandis.map((a) => {
          const v = alternativeVerdict(a)
          return (
            <div key={a.mandi} className="rounded-xl border border-line p-3 text-sm" data-verdict={v}>
              <p className="font-bold">
                {mandiName(a.mandi)}: {t(`offer.alternatives.${v}`)}
              </p>
              {a.has_data && a.net_after_transport != null && (
                <>
                  <p className="figures text-slate">
                    {t('offer.alternatives.line', {
                      price: formatRs(a.reference_price ?? 0),
                      transport: formatRs(a.transport_cost ?? 0),
                      net: formatRs(a.net_after_transport),
                    })}
                  </p>
                  <p className="text-slate">
                    {t('offer.alternatives.vsOffer', {
                      qty: r.quantity_maund,
                      total: signed(a.difference_vs_offer_total ?? 0),
                    })}
                  </p>
                  {a.prices_as_of && (
                    <p className={`text-xs ${a.is_stale ? 'font-semibold text-wheat-deep' : 'text-slate'}`}>
                      {t(a.is_stale ? 'data.stale' : 'data.asOf', { date: formatDate(a.prices_as_of, lang) })}
                    </p>
                  )}
                </>
              )}
            </div>
          )
        })}
        <p className="text-xs text-slate">{t('offer.alternatives.verify')}</p>
        <Link to="/compare" className="inline-block rounded-xl bg-ink px-4 py-2 text-cotton hover:opacity-90">
          {t('offer.alternatives.open')}
        </Link>
      </section>

      <section className="space-y-1 text-xs text-slate">
        <h4 className="font-bold">{t('offer.assumptions.title')}</h4>
        <ul className="list-disc space-y-0.5 ps-5">
          {assumptions(r).map((c) => (
            <li key={c}>{t(`offer.assumptions.${c}`)}</li>
          ))}
        </ul>
        <p>{t('offer.referenceOnly')}</p>
      </section>
    </div>
  )
}

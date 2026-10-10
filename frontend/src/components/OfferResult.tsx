import { AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, Clock, MapPin, Phone } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import type { Lang } from '../i18n'
import { formatDate, formatRs } from '../lib/format'
import { assumptions, showNextSteps, side, tone, type OfferResult as Result } from '../lib/offer'
import { referenceBadge } from '../lib/status'
import { DataLabel } from './DataLabel'
import { ButtonLink } from './ui/Button'
import { Disclosure, Note } from './ui/Disclosure'
import { StatusBadge } from './ui/StatusBadge'

const TONE_CLASS = { below: 'text-madder', within: 'text-ink', above: 'text-field', limited: 'text-wheat-deep' }
const TONE_ICON = { below: ArrowDown, within: CheckCircle2, above: ArrowUp, limited: AlertTriangle }

function signed(value: number): string {
  return `${value < 0 ? '−' : value > 0 ? '+' : ''}${formatRs(Math.abs(value))}`
}

/** "Rs 3,514 → Rs 3,820": the buyer's offer against the reported reference, read left to right in both languages. */
function OfferToReference({ r }: { r: Result }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-1">
      <p className="figures text-3xl lg:text-4xl" dir="ltr">
        {formatRs(r.buyer_offer_price)} <span className="text-slate">→</span> {formatRs(r.reference_price)}
      </p>
      <p className="text-sm text-slate">
        {t('offer.offerToRef', { qty: r.quantity_maund, total: signed(r.total_difference_vs_reference) })}
      </p>
    </div>
  )
}

/** Grade, buyer terms, trucks, credit and buyer availability: the things no price report can know. */
export function CannotKnow({ open = false }: { open?: boolean }) {
  const { t } = useTranslation()
  return (
    <Disclosure title={t('cannotKnow.title')} open={open}>
      <p className="mb-2">{t('cannotKnow.intro')}</p>
      <ul className="list-disc space-y-1 ps-5">
        {(['grade', 'terms', 'truck', 'credit', 'buyer'] as const).map((k) => (
          <li key={k}>{t(`cannotKnow.${k}`)}</li>
        ))}
      </ul>
    </Disclosure>
  )
}

function Assumptions({ r }: { r: Result }) {
  const { t } = useTranslation()
  return (
    <section className="space-y-1 text-xs text-slate">
      <h4 className="font-semibold">{t('offer.assumptions.title')}</h4>
      <ul className="list-disc space-y-0.5 ps-5">
        {assumptions(r).map((c) => (
          <li key={c}>{t(`offer.assumptions.${c}`)}</li>
        ))}
      </ul>
      <p>{t('offer.referenceOnly')}</p>
    </section>
  )
}

function Commission({ r }: { r: Result }) {
  const { t } = useTranslation()
  if (!r.estimated_commission) return null
  return (
    <div className="space-y-1 text-sm">
      <StatusBadge kind="estimate" />
      <p>
        {t('offer.commission', {
          pct: r.estimated_commission.pct,
          perMaund: formatRs(r.estimated_commission.per_maund),
          total: formatRs(r.estimated_commission.total),
        })}
      </p>
    </div>
  )
}

function NextSteps() {
  const { t } = useTranslation()
  return (
    <section className="space-y-1 rounded-[var(--radius-control)] bg-field-soft p-4" data-testid="offer-next-steps">
      <h4 className="font-semibold">{t('offer.nextSteps.title')}</h4>
      <ul className="list-disc space-y-1 ps-5 text-sm">
        {(['askReason', 'compare', 'reference', 'constraints'] as const).map((k) => (
          <li key={k}>{t(`offer.nextSteps.${k}`)}</li>
        ))}
      </ul>
    </section>
  )
}

function Total({ r }: { r: Result }) {
  const negative = r.total_difference_vs_reference < 0
  return (
    <p className={`figures text-3xl ${negative ? 'text-madder' : 'text-field'}`} data-testid="offer-total">
      {signed(r.total_difference_vs_reference)}
    </p>
  )
}

/** A strong reference: below / within / above the recent reported reference, with the numbers behind it. */
function StandardResult({ r }: { r: Result }) {
  const { t } = useTranslation()
  const tn = tone(r)
  const Icon = TONE_ICON[tn]
  const dir = side(r.difference_vs_reference_per_maund)
  return (
    <article className="card space-y-4 p-5 lg:p-6" data-testid="offer-result" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className={`flex items-center gap-2 text-xl font-bold ${TONE_CLASS[tn]}`} data-status={r.result_status}>
          <Icon aria-hidden className="size-6 shrink-0" />
          {t(`offer.status.${tn}`)}
        </h3>
        <StatusBadge kind={referenceBadge(r)} />
      </div>
      <OfferToReference r={r} />
      <dl className="grid grid-cols-[1fr_auto] items-baseline gap-x-3 gap-y-1.5 border-t border-line pt-3">
        <dt className="text-sm text-slate">{t('offer.buyerOffer')}</dt>
        <dd className="figures text-lg">{formatRs(r.buyer_offer_price)}</dd>
        <dt className="text-sm text-slate">{t('offer.referencePrice')}</dt>
        <dd className="figures text-lg">{formatRs(r.reference_price)}</dd>
        <dt className="text-sm text-slate">{t('offer.referenceRange')}</dt>
        <dd className="figures">
          {formatRs(r.reference_range_low)} – {formatRs(r.reference_range_high)}
        </dd>
      </dl>
      <p className="text-xs text-slate">
        {t('offer.reportedDays', { days: r.reference_days, window: r.window_days })} {t('offer.grossBasis')}
      </p>
      <DataLabel
        isSynthetic={r.is_synthetic}
        asOf={r.reference_price_as_of}
        stale={r.is_stale}
        unchangedSince={r.price_unchanged_since}
      />
      <div className="space-y-1 border-t border-line pt-3">
        <p>{t(`offer.vsReference.${dir}`, { diff: formatRs(Math.abs(r.difference_vs_reference_per_maund)) })}</p>
        <p className="text-sm text-slate">{t('offer.totalFor', { qty: r.quantity_maund })}</p>
        <Total r={r} />
        {r.total_difference_vs_range !== 0 && (
          <p className="text-sm text-slate">{t('offer.totalVsRange', { total: signed(r.total_difference_vs_range) })}</p>
        )}
      </div>
      <Commission r={r} />
      {showNextSteps(r) && <NextSteps />}
      <div className="flex flex-wrap items-center gap-3">
        <ButtonLink to="/compare">
          <MapPin aria-hidden className="size-5" />
          {t('offer.compareCta')}
        </ButtonLink>
        <ButtonLink to="/why" variant="text">
          {t('offer.detailsCta')}
        </ButtonLink>
      </div>
      <Assumptions r={r} />
    </article>
  )
}

/**
 * A weak reference (stale, frozen, one repeated price, too few reported days): "reference data is limited"
 * leads, every number stays visible, and the next steps are ones that do not lean on the weak reference.
 */
function LimitedResult({ r, cropName, mandiName }: { r: Result; cropName: string; mandiName: string }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const dir = side(r.difference_vs_reference_per_maund)
  const Icon = r.reference_strength === 'LIMITED_STALE' ? Clock : AlertTriangle
  const reason = t(`offer.limited.${r.reference_strength}`, {
    days: r.reference_days,
    window: r.window_days,
    date: formatDate(r.price_unchanged_since ?? r.reference_price_as_of, lang),
  })
  return (
    <article className="space-y-4" data-testid="offer-result" aria-live="polite">
      <h3 className="text-2xl font-bold" data-status={r.result_status}>
        {t('offer.status.limited')}
      </h3>
      <div
        className="space-y-3 rounded-[var(--radius-card)] border border-wheat/50 bg-wheat-soft p-5 lg:p-6"
        data-testid="offer-limited"
      >
        <p className="flex items-start gap-2 text-lg font-semibold text-wheat-deep">
          <Icon aria-hidden className="mt-1 size-6 shrink-0" />
          {reason}
        </p>
        <p className="text-sm">
          {cropName} · {mandiName} · {t('offer.availableReference')}
        </p>
        <OfferToReference r={r} />
        <dl className="grid grid-cols-[1fr_auto] items-baseline gap-x-3 gap-y-1">
          <dt className="text-sm">{t('offer.buyerOffer')}</dt>
          <dd className="figures">{formatRs(r.buyer_offer_price)}</dd>
          <dt className="text-sm">{t('offer.referencePrice')}</dt>
          <dd className="figures">{formatRs(r.reference_price)}</dd>
        </dl>
        <p className="text-sm">{t('offer.totalFor', { qty: r.quantity_maund })}</p>
        <Total r={r} />
        <DataLabel
          isSynthetic={r.is_synthetic}
          asOf={r.reference_price_as_of}
          stale={r.is_stale}
          unchangedSince={r.price_unchanged_since}
        />
        <StatusBadge kind={referenceBadge(r)} />
        <p className="font-semibold text-wheat-deep">
          {t(`offer.limitedOffer.${dir}`, { diff: formatRs(Math.abs(r.difference_vs_reference_per_maund)) })}
        </p>
        <p className="text-sm text-wheat-deep">{t('offer.limitedExplain')}</p>
      </div>
      <Note>{t('offer.reportedDays', { days: r.reference_days, window: r.window_days })}</Note>
      <Commission r={r} />
      <section className="card space-y-3 p-5">
        <h4 className="text-lg font-semibold">{t('offer.whatYouCanDo.title')}</h4>
        <p className="text-sm text-slate">{t('offer.whatYouCanDo.body')}</p>
        <div className="flex flex-col gap-2">
          <ButtonLink to="/compare" wide>
            <MapPin aria-hidden className="size-5" />
            {t('offer.whatYouCanDo.tryMandi')}
          </ButtonLink>
          <ButtonLink to="/why" variant="secondary" wide>
            <Clock aria-hidden className="size-5" />
            {t('offer.whatYouCanDo.latestDates')}
          </ButtonLink>
          <p className="flex items-center justify-center gap-2 py-2 text-center text-field">
            <Phone aria-hidden className="size-5 shrink-0" />
            {t('offer.whatYouCanDo.askMandi')}
          </p>
        </div>
      </section>
      <Note tone="caution">{t('offer.checkYourself')}</Note>
      {showNextSteps(r) && <NextSteps />}
      <CannotKnow />
      <Assumptions r={r} />
    </article>
  )
}

/** The offer against recent AMIS reference prices. Lays out API numbers only; it computes nothing. */
export function OfferResult({
  result: r,
  mandiName,
  cropName,
}: {
  result: Result
  mandiName: (id: string) => string
  cropName?: (id: string) => string
}) {
  return r.reference_strength === 'STRONG' ? (
    <StandardResult r={r} />
  ) : (
    <LimitedResult r={r} mandiName={mandiName(r.mandi)} cropName={cropName ? cropName(r.crop) : r.crop} />
  )
}

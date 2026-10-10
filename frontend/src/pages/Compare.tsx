import { AlertTriangle, Info, MapPin } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { api, type CompareRow } from '../api/client'
import { useAppState } from '../appState'
import { ErrorBox, Loading } from '../components/Status'
import { ButtonLink } from '../components/ui/Button'
import { StatusBadge } from '../components/ui/StatusBadge'
import type { Lang } from '../i18n'
import { formatDate, formatRs } from '../lib/format'
import { alternativeVerdict, type OfferAlternative } from '../lib/offer'
import { isStrong, referenceBadge } from '../lib/status'
import { useAsync } from '../lib/useAsync'

function signed(value: number): string {
  return `${value < 0 ? '−' : value > 0 ? '+' : ''}${formatRs(Math.abs(value))}`
}

/** One mandi: reported reference − estimated transport = estimated net, and what that means for the farmer. */
function MandiCard({
  mandi,
  price,
  transport,
  net,
  total,
  totalLabel,
  asOf,
  badge,
  verdict,
  own,
  limitedNote,
}: {
  mandi: string
  price?: number | null
  transport?: number | null
  net?: number | null
  total?: number | null
  totalLabel: string
  asOf?: string | null
  badge: ReturnType<typeof referenceBadge> | null
  verdict?: string | null
  own: boolean
  limitedNote?: string | null
}) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { mandiName } = useAppState()
  return (
    <article className="card space-y-3 p-5" data-testid="mandi-card">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-lg font-bold">
          <MapPin aria-hidden className="size-5 text-field" />
          {mandiName(mandi)}
          {own && <span className="text-sm font-normal text-slate">({t('compare.yourMandi')})</span>}
        </h3>
        {badge && <StatusBadge kind={badge} />}
      </div>
      {net == null ? (
        <p className="text-slate">{t('compare.noData')}</p>
      ) : (
        <>
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <dt className="text-sm text-slate">{t('compare.reportedPerMaund')}</dt>
              <dd className="figures text-xl">{formatRs(price ?? 0)}</dd>
            </div>
            <div>
              <dt className="text-sm text-slate">{t('compare.transportPerMaund')}</dt>
              <dd className="figures text-xl">− {formatRs(transport ?? 0)}</dd>
            </div>
            <div>
              <dt className="text-sm text-slate">{t('compare.netPerMaund')}</dt>
              <dd className="figures text-xl">{formatRs(net)}</dd>
            </div>
          </dl>
          {total != null && (
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-t border-line pt-3">
              <span className="text-sm">{totalLabel}</span>
              <span className={`figures text-2xl ${total < 0 ? 'text-madder' : 'text-field'}`}>{signed(total)}</span>
            </div>
          )}
          {verdict && <p className="text-sm font-semibold">{verdict}</p>}
          {asOf && (
            <p className="text-xs text-slate">
              {t('data.sourceShort')} · {formatDate(asOf, lang)}
            </p>
          )}
          <p className="text-xs text-slate">{limitedNote ?? t('compare.transportNote')}</p>
        </>
      )}
    </article>
  )
}

function HowCalculated({ example }: { example?: string }) {
  const { t } = useTranslation()
  return (
    <section className="card space-y-3 p-5" aria-labelledby="calc-title">
      <h2 id="calc-title" className="text-lg font-bold">{t('compare.calc.title')}</h2>
      <p className="text-sm">{t('compare.calc.net')}</p>
      <p className="text-sm">{t('compare.calc.difference')}</p>
      {example && <p className="figures text-sm text-slate" dir="ltr">{example}</p>}
      <p className="text-xs text-slate">{t('compare.calc.notIncluded')}</p>
    </section>
  )
}

/** Mandis after estimated transport: against the farmer's latest offer when there is one, else by net price. */
export function Compare() {
  const { t } = useTranslation()
  const { selection, quantity, cropName, mandiName, lastCheck } = useAppState()
  const withOffer = lastCheck && lastCheck.crop === selection.crop && lastCheck.mandi === selection.mandi ? lastCheck : null
  const qty = withOffer ? withOffer.quantity : quantity
  const [state, reload] = useAsync(
    (signal) => api.compare({ ...selection, quantity_maund: qty }, signal),
    `${selection.crop}|${selection.mandi}|${qty}`,
  )
  const limitedNote = (strength: string | null | undefined, stale?: boolean | null) =>
    strength && strength !== 'STRONG' ? t(`compare.limitedNote.${strength}`) : stale ? t('compare.limitedNote.LIMITED_STALE') : null

  const offerRows = withOffer?.result.alternative_mandis ?? []
  const own = offerRows.find((a) => a.is_own_mandi)
  const example =
    withOffer && own?.net_after_transport != null
      ? `${mandiName(own.mandi)}: (${Math.round(own.net_after_transport)} − ${Math.round(withOffer.offer)}) × ${withOffer.quantity}`
      : undefined
  const anyWeak = withOffer
    ? offerRows.some((a) => a.has_data && a.reference_strength !== 'STRONG')
    : state.status === 'ok' && state.data.rows.some((r) => r.has_data && !isStrong(r))

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold lg:text-3xl">{t('compare.title')}</h1>
        <p className="text-slate">
          {withOffer
            ? t('compare.contextOffer', { crop: cropName(selection.crop), qty, offer: formatRs(withOffer.offer) })
            : t('compare.context', { crop: cropName(selection.crop), qty })}
        </p>
      </header>
      <p className="flex items-start gap-2 rounded-[var(--radius-card)] border border-wheat/50 bg-wheat-soft p-4 text-wheat-deep"
        role="note" data-testid="compare-caution">
        <AlertTriangle aria-hidden className="mt-0.5 size-5 shrink-0" />
        <span>
          {t('compare.caution')} {anyWeak ? t('compare.cautionWeak') : ''}
        </span>
      </p>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="space-y-4" aria-label={t('compare.title')}>
          <p className="text-sm font-semibold text-slate">{t(withOffer ? 'compare.orderOffer' : 'compare.orderNet')}</p>
          {withOffer &&
            offerRows.map((a: OfferAlternative) => {
              const v = alternativeVerdict(a)
              return (
                <MandiCard
                  key={a.mandi}
                  mandi={a.mandi}
                  own={a.is_own_mandi}
                  price={a.reference_price}
                  transport={a.transport_cost}
                  net={a.has_data ? (a.net_after_transport ?? null) : null}
                  total={a.difference_vs_offer_total}
                  totalLabel={t('compare.vsOffer', { qty })}
                  asOf={a.prices_as_of}
                  badge={a.has_data ? referenceBadge(a) : null}
                  verdict={a.has_data ? t(`offer.alternatives.${v}`) : null}
                  limitedNote={limitedNote(a.reference_strength, a.is_stale)}
                />
              )
            })}
          {!withOffer && state.status === 'loading' && <Loading />}
          {!withOffer && state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
          {!withOffer &&
            state.status === 'ok' &&
            state.data.rows.map((r: CompareRow) => (
              <MandiCard
                key={r.mandi}
                mandi={r.mandi}
                own={r.mandi === selection.mandi}
                price={r.price}
                transport={r.transport_cost}
                net={r.has_data ? (r.net_price ?? null) : null}
                total={r.mandi === selection.mandi ? null : r.gain_vs_preferred}
                totalLabel={t('compare.gainFor', { qty })}
                asOf={r.prices_as_of}
                badge={r.has_data ? referenceBadge(r) : null}
                verdict={r.is_best ? t('compare.bestStrong') : null}
                limitedNote={limitedNote(r.reference_strength, r.is_stale)}
              />
            ))}
        </section>
        <aside className="space-y-4">
          <HowCalculated example={example} />
          <ButtonLink to="/" variant="secondary" wide>
            {t(withOffer ? 'compare.changeOffer' : 'compare.addOffer')}
          </ButtonLink>
          <p className="flex items-start gap-2 rounded-[var(--radius-control)] bg-slate-soft p-3 text-xs text-slate">
            <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
            {t('compare.footnote')}
          </p>
        </aside>
      </div>
    </div>
  )
}

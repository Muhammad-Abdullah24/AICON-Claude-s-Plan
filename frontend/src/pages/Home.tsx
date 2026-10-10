import { History, Sprout } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { api, type ReferenceResponse } from '../api/client'
import { useAppState } from '../appState'
import { DataLabel } from '../components/DataLabel'
import { OfferCheck } from '../components/OfferCheck'
import { EmptyState, ErrorBox, Loading } from '../components/Status'
import { ButtonLink } from '../components/ui/Button'
import { StatusBadge } from '../components/ui/StatusBadge'
import type { Lang } from '../i18n'
import { formatDate, formatRs } from '../lib/format'
import { referenceBadge } from '../lib/status'
import { useAsync } from '../lib/useAsync'

/** The latest AMIS reference at the selected mandi, before any offer (GET /api/reference). */
function ReferenceCard({ r }: { r: ReferenceResponse }) {
  const { t } = useTranslation()
  const { cropName, mandiName } = useAppState()
  return (
    <section className="card space-y-2 p-5" aria-labelledby="ref-title" data-testid="reference-card">
      <h2 id="ref-title" className="text-lg font-bold">{t('home.reference.title')}</h2>
      <p className="text-sm text-slate">
        {cropName(r.crop)} · {mandiName(r.mandi)}
      </p>
      <p className="figures text-4xl">{formatRs(r.reference_price)}</p>
      <p className="text-sm text-slate">{t('home.reference.perMaund')}</p>
      <DataLabel isSynthetic={r.is_synthetic} asOf={r.reference_price_as_of} stale={r.is_stale}
        unchangedSince={r.price_unchanged_since} />
      <StatusBadge kind={referenceBadge(r)} />
    </section>
  )
}

/** How far the reference can be leaned on, in words, from the API's strength and reported days. */
function FreshnessCard({ r }: { r: ReferenceResponse }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const strong = r.reference_strength === 'STRONG'
  return (
    <section
      className={`space-y-2 rounded-[var(--radius-card)] border p-5 ${strong ? 'border-line bg-paper' : 'border-wheat/50 bg-wheat-soft'}`}
      aria-labelledby="fresh-title"
    >
      <h2 id="fresh-title" className="text-lg font-bold">{t('home.freshness.title')}</h2>
      <StatusBadge kind={referenceBadge(r)} />
      <p className="text-sm">{t('offer.reportedDays', { days: r.reference_days, window: r.window_days })}</p>
      {!strong && (
        <p className="text-sm">
          {t(`offer.limited.${r.reference_strength}`, {
            days: r.reference_days,
            window: r.window_days,
            date: formatDate(r.price_unchanged_since ?? r.reference_price_as_of, lang),
          })}
        </p>
      )}
      <p className={`text-sm font-semibold ${strong ? 'text-field' : 'text-wheat-deep'}`}>
        {t(`home.freshness.${strong ? 'strong' : 'limited'}`)}
      </p>
    </section>
  )
}

function HowItHelps() {
  const { t } = useTranslation()
  return (
    <section className="card space-y-3 p-5" aria-labelledby="how-title">
      <h2 id="how-title" className="text-lg font-bold">{t('home.how.title')}</h2>
      <ol className="space-y-2">
        {(['offer', 'reference', 'transport', 'decide'] as const).map((k, i) => (
          <li key={k} className="flex items-center gap-3">
            <span className="figures flex size-8 shrink-0 items-center justify-center rounded-full bg-field-soft text-sm text-field">
              {i + 1}
            </span>
            {t(`home.how.${k}`)}
          </li>
        ))}
      </ol>
    </section>
  )
}

/** The latest check of this browser session when the form now shows something else, or a first-use state. */
function LastCheck() {
  const { t } = useTranslation()
  const { lastCheck, selection, quantity, cropName, mandiName } = useAppState()
  if (!lastCheck) {
    return (
      <EmptyState icon={History} title={t('home.last.emptyTitle')} body={t('home.last.emptyBody')} />
    )
  }
  if (lastCheck.crop === selection.crop && lastCheck.mandi === selection.mandi && lastCheck.quantity === quantity) {
    return null // the result is already on screen under the form
  }
  const r = lastCheck.result
  return (
    <section className="card space-y-2 p-5" aria-labelledby="last-title">
      <h2 id="last-title" className="text-lg font-bold">{t('home.last.title')}</h2>
      <p className="text-xs text-slate">{t('home.last.sessionOnly')}</p>
      <StatusBadge kind={referenceBadge(r)} />
      <p className="figures text-2xl" dir="ltr">
        {formatRs(r.buyer_offer_price)} → {formatRs(r.reference_price)}
      </p>
      <p className="text-sm text-slate">
        {cropName(lastCheck.crop)} · {mandiName(lastCheck.mandi)} · {t('offer.totalFor', { qty: r.quantity_maund })}:{' '}
        <span className="figures">{formatRs(r.total_difference_vs_reference)}</span>
      </p>
    </section>
  )
}

/** Market outlook stays reachable but secondary: a small card linking to the outlook page. */
function OutlookTeaser({ r }: { r: ReferenceResponse | null }) {
  const { t } = useTranslation()
  return (
    <section className="flex flex-col items-start gap-2 rounded-[var(--radius-card)] border border-line bg-cotton p-5"
      data-testid="market-outlook">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <Sprout aria-hidden className="size-5 text-field" />
        {t('outlook.title')}
      </h2>
      <p className="text-sm text-slate">{t('outlook.context')}</p>
      {r && <StatusBadge kind={referenceBadge(r)} />}
      <ButtonLink to="/outlook" variant="text">
        {t('home.outlookLink')}
      </ButtonLink>
    </section>
  )
}

/**
 * Home: "got a buyer's offer? check it before you sell". The offer check is the page; the market reference,
 * its freshness and how FarmSight helps sit beside it on a desktop; the market outlook is a link, not the answer.
 */
export function Home() {
  const { t } = useTranslation()
  const { selection } = useAppState()
  const [ref, reload] = useAsync((signal) => api.reference(selection, signal), `${selection.crop}|${selection.mandi}`)
  const r = ref.status === 'ok' ? ref.data : null

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold lg:text-3xl">{t('home.title')}</h1>
        <p className="text-slate">{t('home.subtitle')}</p>
        <p className="text-sm text-field">{t('home.trust')}</p>
      </header>
      <div className="grid items-start gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
        <div className="space-y-6 lg:order-2">
          <OfferCheck />
          <LastCheck />
          <OutlookTeaser r={r} />
        </div>
        <aside className="space-y-4 lg:order-1" aria-label={t('home.reference.title')}>
          {ref.status === 'loading' && <Loading label={t('home.reference.loading')} />}
          {ref.status === 'error' && <ErrorBox error={ref.error} onRetry={reload} />}
          {r && <ReferenceCard r={r} />}
          {r && <FreshnessCard r={r} />}
          <HowItHelps />
        </aside>
      </div>
    </div>
  )
}

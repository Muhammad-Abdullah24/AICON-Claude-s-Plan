import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { api, type LenderId, type LoanOption, type LoanPlanResponse } from '../api/client'
import { useAppState } from '../appState'
import { ChipGroup } from '../components/ChipGroup'
import { ErrorBox, Loading } from '../components/Status'
import type { Lang } from '../i18n'
import { formatRs, parseTypedNumber } from '../lib/format'
import { replayDate } from '../lib/replay'
import { useAsync } from '../lib/useAsync'

// The loan planner works out wheat only for now: the official cash-cost table is wheat's (docs/PIVOT.md 3.4, D1).
const CROP = 'wheat'
const PLANNED: LenderId[] = ['arhti', 'bank', 'zarkhez_e']
const INPUT =
  'figures min-h-12 w-40 rounded-xl border-2 border-line bg-paper px-3 py-2 text-lg focus:border-ink focus:outline-none'

/** How much to borrow, from whom (cheapest first), and what over-borrowing costs at harvest (docs/PIVOT.md L3). */
export function Loan() {
  const { t } = useTranslation()
  const { farmer } = useAppState()
  const [acresTyped, setAcresTyped] = useState(String(Math.min(farmer?.land_area_acres ?? 5, 12.5)))
  const [savings, setSavings] = useState('')
  const [age, setAge] = useState('')
  const [planned, setPlanned] = useState('400000')
  const [lender, setLender] = useState<LenderId>('arhti')

  const acres = parseTypedNumber(acresTyped)
  const valid = acres !== null && acres > 0
  const savingsRs = parseTypedNumber(savings) ?? 0
  const ageN = parseTypedNumber(age)
  const plannedRs = planned === '' ? null : parseTypedNumber(planned)
  const key = `${acres}|${savingsRs}|${ageN}|${plannedRs}|${lender}`
  const [state, reload] = useAsync(
    (signal) =>
      valid
        ? api.loanPlan(
            {
              crop: CROP,
              acres: acres,
              savings_rs: savingsRs,
              age: ageN !== null && ageN >= 14 && ageN <= 120 ? Math.round(ageN) : null,
              planned_borrow_rs: plannedRs,
              planned_lender: plannedRs ? lender : null,
            },
            signal,
          )
        : Promise.reject(new Error('invalid')),
    key,
  )

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold">{t('loan.title')}</h2>
        <p className="text-sm text-slate">{t('loan.intro')}</p>
      </div>
      {/* One line until tapped, so the answer stays on the first screen (same pattern as SelectionBar and Grow). */}
      <details className="group rounded-2xl bg-paper shadow-sm">
        <summary
          onClick={(e) => !valid && e.preventDefault()}
          className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 py-2 [&::-webkit-details-marker]:hidden"
        >
          <span className="font-bold">
            {valid ? acres : '–'} {t('grow.acres')}
            {plannedRs ? ` · ${formatRs(plannedRs)} ${t(`loan.lender.${lender}`)}` : ''}
          </span>
          <span className="shrink-0 rounded-full border-2 border-line px-3 text-sm text-slate group-open:hidden">
            {t('select.change')}
          </span>
          <span className="hidden shrink-0 rounded-full border-2 border-line px-3 text-sm text-slate group-open:inline">
            {t('select.done')}
          </span>
        </summary>
        <div className="space-y-4 px-4 pb-4">
          <label className="block text-sm text-slate">
            {t('loan.acres')}
            <input
              inputMode="decimal"
              value={acresTyped}
              onChange={(e) => setAcresTyped(e.target.value)}
              aria-invalid={!valid}
              className={`${INPUT} mt-1 block`}
            />
          </label>
          {!valid && <p className="text-sm text-madder">{t('grow.landInvalid')}</p>}
          <label className="block text-sm text-slate">
            {t('loan.savings')}
            <input
              inputMode="numeric"
              value={savings}
              onChange={(e) => setSavings(e.target.value)}
              placeholder="0"
              className={`${INPUT} mt-1 block`}
            />
          </label>
          <label className="block text-sm text-slate">
            {t('loan.age')}
            <input
              inputMode="numeric"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className={`${INPUT} mt-1 block w-24`}
            />
          </label>
          <label className="block text-sm text-slate">
            {t('loan.planned')}
            <input
              inputMode="numeric"
              value={planned}
              onChange={(e) => setPlanned(e.target.value)}
              className={`${INPUT} mt-1 block`}
            />
          </label>
          <ChipGroup
            label={t('loan.plannedFrom')}
            value={lender}
            onChange={(v) => setLender(v as LenderId)}
            options={PLANNED.map((l) => ({
              value: l,
              label: t(`loan.lender.${l}`),
            }))}
          />
        </div>
      </details>

      {valid && state.status === 'loading' && <Loading />}
      {valid && state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
      {valid && state.status === 'ok' && <Plan plan={state.data} />}
    </div>
  )
}

function Plan({ plan }: { plan: LoanPlanResponse }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const byId = new Map(plan.options.map((o) => [o.id, o]))
  const label = (o: LoanOption | undefined, id: string) => (o ? (lang === 'en' ? o.name_en : o.name_ur) : id)

  return (
    <section className="parchi space-y-4 rounded-2xl p-4">
      {/* The farmer's own plan, compared: the answer comes first */}
      {plan.plan_comparison === 'COMPARED' && plan.planned_borrow_rs != null && (
        <div className="space-y-2">
          <h3 className="text-lg font-bold">{t('loan.yourPlan')}</h3>
          <p className="text-base">
            {t('loan.yourPlanLine', {
              amount: formatRs(plan.planned_borrow_rs),
              lender: plan.planned_lender ? t(`loan.lender.${plan.planned_lender}`) : '',
              interest: formatRs(plan.planned_interest_rs ?? 0),
              months: plan.months_to_harvest,
            })}
          </p>
          {(plan.extra_cost_rs ?? 0) > 0 && (
            <p className="rounded-xl bg-madder px-3 py-3 text-lg font-bold text-paper">
              {t('loan.extraCost', {
                amount: formatRs(plan.extra_cost_rs ?? 0),
              })}
            </p>
          )}
          {(plan.saving_rs ?? 0) > 0 && (
            <p className="rounded-xl bg-field/15 px-3 py-2 text-base text-field">
              {t('loan.planCheaper', {
                amount: formatRs(plan.saving_rs ?? 0),
              })}
            </p>
          )}
          {(plan.over_borrow_rs ?? 0) > 0 && (
            <p className="rounded-lg bg-wheat/20 px-3 py-2 text-sm text-wheat-deep">
              {t('loan.overBorrow', {
                amount: formatRs(plan.over_borrow_rs ?? 0),
              })}
            </p>
          )}
        </div>
      )}

      {/* 1. What the crop needs */}
      <div className={plan.plan_comparison === 'COMPARED' ? 'tear pt-3' : undefined}>
        <p className="text-sm text-slate">{t('loan.needs', { acres: plan.acres })}</p>
        <p className="figures text-3xl font-bold">{formatRs(plan.input_need_rs)}</p>
        <details className="mt-1">
          <summary className="flex min-h-12 cursor-pointer items-center text-sm text-slate">
            {t('loan.perAcre')}
          </summary>
          <ul className="space-y-1 text-sm">
            {plan.input_items.map((i) => (
              <li key={i.item} className="flex justify-between gap-3">
                <span>{lang === 'en' ? i.name_en : i.name_ur}</span>
                <span className="figures">{formatRs(i.rs_per_acre)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-1 text-xs text-slate">{t('loan.costSource')}</p>
        </details>
        {plan.harvest_cost_rs > 0 && (
          <p className="text-sm text-slate">{t('loan.harvestApart', { amount: formatRs(plan.harvest_cost_rs) })}</p>
        )}
        {plan.savings_rs > 0 && (
          <p className="text-sm">{t('loan.borrowOnly', { amount: formatRs(plan.borrow_needed_rs) })}</p>
        )}
      </div>

      {/* 2. Cheapest money first */}
      <div className="tear space-y-2 pt-3">
        <h3 className="text-lg font-bold">{t('loan.ladder')}</h3>
        {plan.ladder.length === 0 && <p className="text-sm">{t('loan.nothingToBorrow')}</p>}
        {plan.ladder.map((s, n) => {
          const o = byId.get(s.id)
          return (
            <div key={s.id} className="space-y-0.5 border-s-4 border-field ps-3">
              <p className="flex items-baseline justify-between gap-3">
                <span className="font-bold">
                  <span className="figures me-1 text-slate">{n + 1}</span>
                  {label(o, s.id)}
                </span>
                <span className="figures text-lg">{formatRs(s.amount_rs)}</span>
              </p>
              <p className="text-sm text-slate">
                {o && o.annual_rate_pct === 0
                  ? t('loan.free')
                  : t('loan.rate', {
                      rate: o?.annual_rate_pct,
                      interest: formatRs(s.interest_rs),
                    })}
              </p>
              {o && <p className="text-xs text-slate">{lang === 'en' ? o.conditions_en : o.conditions_ur}</p>}
              {o && (
                <a
                  href={o.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex min-h-12 items-center text-xs text-ink underline"
                >
                  {o.verified ? t('loan.verified') : t('loan.unverified')}
                </a>
              )}
            </div>
          )
        })}
        {plan.uncovered_rs > 0 && (
          <p className="rounded-lg bg-madder/10 px-3 py-2 text-sm text-madder">
            {t('loan.uncovered', { amount: formatRs(plan.uncovered_rs) })}
          </p>
        )}
        <p className="flex items-baseline justify-between gap-3 border-t-2 border-line pt-2">
          <span className="text-sm">{t('loan.harvestDue', { months: plan.months_to_harvest })}</span>
          <span className="figures text-xl font-bold">{formatRs(plan.harvest_due_rs)}</span>
        </p>
      </div>

      {/* 4. Options this farmer can't use, with the reason */}
      {plan.options.some((o) => !o.eligible) && (
        <div className="space-y-1">
          <p className="text-sm font-bold text-slate">{t('loan.notEligible')}</p>
          {plan.options
            .filter((o) => !o.eligible)
            .map((o) => (
              <p key={o.id} className="text-sm text-slate">
                {label(o, o.id)}: {lang === 'en' ? o.why_not_en : o.why_not_ur}
              </p>
            ))}
        </div>
      )}

      {plan.warnings.includes('NOT_SMALL_FARMER') && (
        <p className="rounded-lg bg-wheat/20 px-3 py-2 text-sm text-wheat-deep">{t('loan.notSmall')}</p>
      )}

      <SaveLoans plan={plan} />

      <p className="text-xs text-slate">{t('loan.estimate')}</p>
      <p className="text-xs text-slate">
        <span className={`me-2 rounded px-1.5 font-semibold ${plan.is_synthetic ? 'tape' : 'bg-field text-paper'}`}>
          {plan.is_synthetic ? t('data.synthetic') : t('data.real')}
        </span>
        {t('loan.sources')}
      </p>
    </section>
  )
}

/** Logged in: keep the recommended loans in the farmer's list, due at harvest, so the wait plan counts them. */
function SaveLoans({ plan }: { plan: LoanPlanResponse }) {
  const { t } = useTranslation()
  const { farmer } = useAppState()
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved'>('idle')
  const [error, setError] = useState<unknown>(null)
  if (plan.ladder.length === 0) return null
  if (!farmer) {
    return (
      <p className="text-sm text-slate">
        <Link to="/profile" className="inline-flex min-h-12 items-center underline">
          {t('loan.loginToSave')}
        </Link>
      </p>
    )
  }

  function save() {
    const due = new Date(replayDate ?? new Date().toISOString().slice(0, 10))
    due.setMonth(due.getMonth() + plan.months_to_harvest)
    const due_date = due.toISOString().slice(0, 10)
    const rate = (id: string) => plan.options.find((o) => o.id === id)?.annual_rate_pct ?? 0
    setStatus('saving')
    setError(null)
    Promise.all(
      plan.ladder.map((s) =>
        api.addLoan({
          lender: s.id,
          amount_rs: s.amount_rs,
          annual_rate_pct: rate(s.id),
          due_date,
        }),
      ),
    ).then(
      () => setStatus('saved'),
      (e) => {
        setError(e)
        setStatus('idle')
      },
    )
  }

  return (
    <div className="space-y-2">
      {status === 'saved' ? (
        <p className="text-base text-field">
          {t('loan.saved')}{' '}
          <Link to="/profile" className="underline">
            {t('loan.seeList')}
          </Link>
        </p>
      ) : (
        <button
          type="button"
          onClick={save}
          disabled={status === 'saving'}
          className="min-h-12 w-full rounded-xl bg-ink px-4 py-2 text-lg font-bold text-cotton disabled:opacity-60"
        >
          {t('loan.save')}
        </button>
      )}
      {error !== null && <ErrorBox error={error} />}
    </div>
  )
}

import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Money, type Storage, type WaitExit, type WaitPlanResponse } from '../api/client'
import { useAppState } from '../appState'
import { formatRs, parseTypedNumber } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { ChipGroup } from './ChipGroup'
import { DataLabel } from './DataLabel'
import { ErrorBox, Loading } from './Status'

const MONEY: Money[] = ['own', 'bank', 'arhti']
const STORAGE: Storage[] = ['godown', 'bags']
const VERDICT_STYLE: Record<string, string> = {
  SELL_ALL: 'text-field',
  SPLIT: 'text-wheat-deep',
  HOLD_ALL: 'text-ink',
}

/** "Can you afford to wait?" — the pivot's core answer (docs/PIVOT.md F1). Collects the farmer's cash need, money
 * and store, then shows how much to sell now, how much to hold, each way out in rupees, and how often holding paid. */
export function WaitPlan() {
  const { t } = useTranslation()
  const { selection, quantity } = useAppState()
  const [cash, setCash] = useState('')
  const [months, setMonths] = useState(4)
  const [money, setMoney] = useState<Money>('own')
  const [storage, setStorage] = useState<Storage>('godown')
  const [offer, setOffer] = useState('')
  const [household, setHousehold] = useState('')
  const [income, setIncome] = useState('')

  const cashRs = parseTypedNumber(cash) ?? 0
  const offerRs = offer === '' ? null : parseTypedNumber(offer)
  const householdRs = parseTypedNumber(household) ?? 0
  const incomeRs = parseTypedNumber(income) ?? 0
  const key = `${selection.crop}|${selection.mandi}|${quantity}|${cashRs}|${months}|${money}|${storage}|${offerRs}|${householdRs}|${incomeRs}`
  const [state, reload] = useAsync(
    (signal) =>
      api.waitPlan(
        {
          ...selection,
          quantity_maund: quantity,
          cash_need_rs: cashRs,
          wait_months: months,
          money,
          storage,
          offer: offerRs,
          household_spend_rs_month: householdRs,
          other_income_rs_month: incomeRs,
        },
        signal,
      ),
    key,
  )

  const input = 'figures min-h-12 w-40 rounded-xl border-2 border-line bg-paper px-3 py-2 text-lg focus:border-ink focus:outline-none'
  return (
    <section className="space-y-4 rounded-2xl bg-paper p-4 shadow-sm">
      <div>
        <h2 className="text-xl font-bold">{t('wait.title')}</h2>
        <p className="text-sm text-slate">{t('wait.intro')}</p>
      </div>

      <label className="block text-sm text-slate">
        {t('wait.cashNeed')}
        <input inputMode="numeric" value={cash} onChange={(e) => setCash(e.target.value)} className={`${input} mt-1 block`} />
      </label>

      {/* Leave "cash now" empty and the app works it out: loans due before the sale + household spending
          not covered by other income (milk, labour) while waiting (docs/PIVOT.md 3.4). */}
      <details className="rounded-xl border-2 border-line px-3">
        <summary className="flex min-h-12 cursor-pointer items-center text-sm text-slate">{t('wait.more')}</summary>
        <div className="space-y-3 pb-3">
          <label className="block text-sm text-slate">
            {t('wait.household')}
            <input inputMode="numeric" value={household} onChange={(e) => setHousehold(e.target.value)} className={`${input} mt-1 block`} />
          </label>
          <label className="block text-sm text-slate">
            {t('wait.otherIncome')}
            <input inputMode="numeric" value={income} onChange={(e) => setIncome(e.target.value)} className={`${input} mt-1 block`} />
          </label>
        </div>
      </details>

      <ChipGroup
        label={t('wait.waitMonths')}
        value={String(months)}
        onChange={(v) => setMonths(Number(v))}
        options={[2, 3, 4, 5, 6].map((m) => ({ value: String(m), label: t('wait.monthsN', { n: m }) }))}
      />
      <ChipGroup
        label={t('wait.money')}
        value={money}
        onChange={(v) => setMoney(v as Money)}
        options={MONEY.map((m) => ({ value: m, label: t(`wait.money${m[0].toUpperCase()}${m.slice(1)}`) }))}
      />
      <ChipGroup
        label={t('wait.storage')}
        value={storage}
        onChange={(v) => setStorage(v as Storage)}
        options={STORAGE.map((s) => ({ value: s, label: t(`wait.storage${s[0].toUpperCase()}${s.slice(1)}`) }))}
      />
      <label className="block text-sm text-slate">
        {t('wait.offer')}
        <input inputMode="decimal" value={offer} onChange={(e) => setOffer(e.target.value)} className={`${input} mt-1 block`} />
      </label>

      {state.status === 'loading' && <Loading />}
      {state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
      {state.status === 'ok' && <Answer plan={state.data} />}
    </section>
  )
}

function Answer({ plan }: { plan: WaitPlanResponse }) {
  const { t } = useTranslation()
  return (
    <div className="tear space-y-3 pt-3">
      <h3 className={`text-2xl font-bold ${VERDICT_STYLE[plan.verdict] ?? ''}`}>
        {t(`wait.verdict.${plan.verdict}`)}
      </h3>
      {plan.cash_need_rs > 0 && (
        <p className="text-sm text-slate">
          {t('wait.cashUsed', { amount: formatRs(plan.cash_need_rs) })}
          {plan.loans_due_rs > 0 && <span className="block">{t('wait.fromLoans', { amount: formatRs(plan.loans_due_rs) })}</span>}
        </p>
      )}
      {plan.verdict === 'SPLIT' && (
        <p className="text-base">
          {t('wait.sellNow', { maund: plan.sell_now_maund })} · {t('wait.hold', { maund: plan.hold_maund })}
        </p>
      )}

      <div className="space-y-2">
        <p className="text-sm font-bold text-slate">{t('wait.ways', { qty: plan.quantity_maund })}</p>
        {plan.exits.map((e) => (
          <ExitRow key={e.kind} exit={e} />
        ))}
      </div>

      {plan.history && (
        <p className="text-sm">
          {t('wait.historyPaid', { wins: plan.history.wins, n: plan.history.n })}
        </p>
      )}
      {/* Selling everything while "hold" shows a bigger total reads as a contradiction: say why (E1). */}
      {plan.verdict === 'SELL_ALL' && plan.history && (
        <p className="text-sm">
          {plan.history.median_net_per_maund > 0
            ? t('wait.whySellSmall', {
                gain: formatRs(plan.history.median_net_per_maund),
                worst: formatRs(Math.abs(plan.history.worst_p10_net_per_maund)),
              })
            : t('wait.whySellLoss', { loss: formatRs(Math.abs(plan.history.median_net_per_maund)) })}
        </p>
      )}
      <p className="text-xs text-slate">{t('wait.confidence', { level: t(`signal.confidenceLevels.${plan.confidence}`) })}</p>

      {plan.warnings.map((w) => (
        <Warning key={w} code={w} check={plan.news_check} />
      ))}

      <p className="text-xs text-slate">{t('wait.estimate')}</p>
      <DataLabel isSynthetic={plan.is_synthetic} asOf={plan.prices_as_of} stale={plan.is_stale} />
    </div>
  )
}

function ExitRow({ exit: e }: { exit: WaitExit }) {
  const { t } = useTranslation()
  const { mandiName } = useAppState()
  const where = e.kind === 'SELL_NOW' && e.mandi ? ` ${t('wait.atMandi', { mandi: mandiName(e.mandi) })}` : ''
  return (
    <div className="flex items-baseline justify-between gap-3 border-s-2 border-line ps-3">
      <span className="text-sm">
        {t(`wait.exit.${e.kind}`)}
        {where}
      </span>
      <span className="text-end">
        <span className="figures font-medium">{formatRs(e.total_rs)}</span>
        {e.kind === 'HOLD' && e.worst_total_rs != null && (
          <span className="block text-xs text-slate">{t('wait.holdWorst', { amount: formatRs(e.worst_total_rs) })}</span>
        )}
        {e.kind === 'HOLD' && e.cost_rs != null && (
          <span className="block text-xs text-slate">{t('wait.holdCost', { amount: formatRs(e.cost_rs) })}</span>
        )}
      </span>
    </div>
  )
}

function Warning({ code, check }: { code: string; check: WaitPlanResponse['news_check'] }) {
  const { t } = useTranslation()
  const opts =
    code === 'NEWS_PRICE_CONFLICT' && check
      ? { source: check.news_source, price: formatRs(check.news_price), date: check.news_date }
      : {}
  return <p className="rounded-lg bg-wheat/20 px-3 py-2 text-sm text-wheat-deep">{t(`wait.warn.${code}`, opts)}</p>
}

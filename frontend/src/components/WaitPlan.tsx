import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Money, type Storage, type WaitExit, type WaitPlanResponse } from '../api/client'
import { useAppState } from '../appState'
import { formatRs, parseTypedNumber } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { ChipGroup } from './ChipGroup'
import { DataLabel } from './DataLabel'
import { HelpTip } from './HelpTip'
import { ErrorBox, Loading } from './Status'
import { Icon } from './ui/Icon'
import { Badge, Callout, CardTitle } from './ui/primitives'
import { cardClass, inputClass, labelClass } from './ui/styles'

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

  const input = `${inputClass} figures mt-2 block w-full max-w-xs text-lg font-semibold`
  return (
    <section className={cardClass('surface', 'space-y-5')}>
      <CardTitle icon="clock" sub={t('wait.intro')}>
        {t('wait.title')}
      </CardTitle>

      {state.status === 'loading' && <Loading />}
      {state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
      {state.status === 'ok' && <Answer plan={state.data} />}
      {/* The farmer's situation, folded under the answer so the answer stays on the first screen. Open by default
          until a cash need is typed, so a first-time farmer sees what to fill in. */}
      <details className="group rounded-2xl border border-line bg-paper px-4" open={cash === ''}>
        <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 font-semibold text-field [&::-webkit-details-marker]:hidden">
          <span>{t('wait.yourSituation')}</span>
          <Icon name="chevron" className="size-5 transition-transform group-open:rotate-180" />
        </summary>
        <div className="space-y-5 pb-4">
          <label className={labelClass}>
            {t('wait.cashNeed')}
            <HelpTip text={t('help.cashNeed')} />
            <input inputMode="numeric" value={cash} onChange={(e) => setCash(e.target.value)} className={input} />
          </label>

          {/* Leave "cash now" empty and the app works it out: loans due before the sale + household spending
            not covered by other income (milk, labour) while waiting (docs/PIVOT.md 3.4). */}
          <details className="group rounded-xl border border-line bg-cotton px-4">
            <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-field [&::-webkit-details-marker]:hidden">
              <span>{t('wait.more')}</span>
              <Icon name="chevron" className="size-5 transition-transform group-open:rotate-180" />
            </summary>
            <div className="space-y-4 pb-4">
              <label className={labelClass}>
                {t('wait.household')}
                <input
                  inputMode="numeric"
                  value={household}
                  onChange={(e) => setHousehold(e.target.value)}
                  className={input}
                />
              </label>
              <label className={labelClass}>
                {t('wait.otherIncome')}
                <input
                  inputMode="numeric"
                  value={income}
                  onChange={(e) => setIncome(e.target.value)}
                  className={input}
                />
              </label>
            </div>
          </details>

          <ChipGroup
            label={t('wait.waitMonths')}
            help={t('help.months')}
            value={String(months)}
            onChange={(v) => setMonths(Number(v))}
            options={[2, 3, 4, 5, 6].map((m) => ({ value: String(m), label: t('wait.monthsN', { n: m }) }))}
          />
          <ChipGroup
            label={t('wait.money')}
            help={t('help.money')}
            value={money}
            onChange={(v) => setMoney(v as Money)}
            options={MONEY.map((m) => ({ value: m, label: t(`wait.money${m[0].toUpperCase()}${m.slice(1)}`) }))}
          />
          <ChipGroup
            label={t('wait.storage')}
            help={t('help.storage')}
            value={storage}
            onChange={(v) => setStorage(v as Storage)}
            options={STORAGE.map((s) => ({ value: s, label: t(`wait.storage${s[0].toUpperCase()}${s.slice(1)}`) }))}
          />
          <label className={labelClass}>
            {t('wait.offer')}
            <HelpTip text={t('help.offer')} />
            <input inputMode="decimal" value={offer} onChange={(e) => setOffer(e.target.value)} className={input} />
          </label>
        </div>
      </details>
    </section>
  )
}

function Answer({ plan }: { plan: WaitPlanResponse }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-4 rounded-2xl border border-line bg-cotton p-4 sm:p-5" aria-live="polite">
      <h3 className={`text-2xl font-bold ${VERDICT_STYLE[plan.verdict] ?? ''}`}>{t(`wait.verdict.${plan.verdict}`)}</h3>
      {plan.cash_need_rs > 0 && (
        <p className="text-sm text-slate">
          {t('wait.cashUsed', { amount: formatRs(plan.cash_need_rs) })}
          {plan.loans_due_rs > 0 && (
            <span className="block">{t('wait.fromLoans', { amount: formatRs(plan.loans_due_rs) })}</span>
          )}
        </p>
      )}
      {plan.verdict === 'SPLIT' && (
        <p className="text-base">
          {t('wait.sellNow', { maund: plan.sell_now_maund })} · {t('wait.hold', { maund: plan.hold_maund })}
        </p>
      )}

      <div className="space-y-2">
        <p className="text-sm font-semibold text-slate">{t('wait.ways', { qty: plan.quantity_maund })}</p>
        <div className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper">
          {plan.exits.map((e) => (
            <ExitRow key={e.kind} exit={e} />
          ))}
        </div>
      </div>

      {plan.history && (
        <p className="text-sm">
          {t('wait.historyPaid', { wins: plan.history.wins, n: plan.history.n })}
          <HelpTip text={t('help.history')} />
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
      <p className="text-sm text-slate">
        {t('wait.confidence', { level: t(`signal.confidenceLevels.${plan.confidence}`) })}
      </p>

      {plan.warnings.map((w) => (
        <Warning key={w} code={w} check={plan.news_check} />
      ))}

      <p>
        <Badge kind="estimate">{t('wait.estimate')}</Badge>
      </p>
      <DataLabel isSynthetic={plan.is_synthetic} asOf={plan.prices_as_of} stale={plan.is_stale} />
    </div>
  )
}

function ExitRow({ exit: e }: { exit: WaitExit }) {
  const { t } = useTranslation()
  const { mandiName } = useAppState()
  const where = e.kind === 'SELL_NOW' && e.mandi ? ` ${t('wait.atMandi', { mandi: mandiName(e.mandi) })}` : ''
  return (
    <div className="flex items-baseline justify-between gap-3 px-4 py-3">
      <span className="text-sm text-ink">
        {t(`wait.exit.${e.kind}`)}
        {where}
      </span>
      <span className="text-end">
        <span className="figures text-lg font-semibold">{formatRs(e.total_rs)}</span>
        {e.kind === 'HOLD' && e.worst_total_rs != null && (
          <span className="block text-sm text-slate">
            {t('wait.holdWorst', { amount: formatRs(e.worst_total_rs) })}
          </span>
        )}
        {e.kind === 'HOLD' && e.cost_rs != null && (
          <span className="block text-sm text-slate">{t('wait.holdCost', { amount: formatRs(e.cost_rs) })}</span>
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
  return (
    <Callout tone="caution">
      <p className="font-semibold">{t(`wait.warn.${code}`, opts)}</p>
    </Callout>
  )
}

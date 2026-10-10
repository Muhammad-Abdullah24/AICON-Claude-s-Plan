import { useTranslation } from 'react-i18next'

import { api, type Money, type Storage, type WaitExit, type WaitPlanResponse } from '../api/client'
import { useAppState } from '../appState'
import { formatRs } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { HelpTip } from './HelpTip'
import { ErrorBox, Loading } from './Status'
import { Callout, CardTitle } from './ui/primitives'
import { cardClass } from './ui/styles'

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
  // No questions on Home: the answer uses sensible defaults (own money, proper store, 4 months). A logged-in
  // farmer's cash need still comes from their loan list on the server.
  const cashRs = 0
  const months = 4
  const money: Money = 'own'
  const storage: Storage = 'godown'
  const offerRs = null
  const householdRs = 0
  const incomeRs = 0
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

  return (
    <section className={cardClass('surface', 'space-y-5')}>
      <CardTitle icon="clock">{t('wait.title')}</CardTitle>

      {state.status === 'loading' && <Loading />}
      {state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
      {state.status === 'ok' && <Answer plan={state.data} />}
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

      {(plan.weeks ?? []).length > 0 && <Weeks plan={plan} />}

      <div className="space-y-2">
        <p className="text-sm font-semibold text-slate">{t('wait.ways', { qty: plan.quantity_maund })}</p>
        <div className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper">
          {/* "Sell all" means holding does not pay here: its row would only add a confusing number. */}
          {(plan.exits ?? [])
            .filter((e) => !(plan.verdict === 'SELL_ALL' && e.kind === 'HOLD'))
            .map((e) => (
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
      {(plan.warnings ?? [])
        .filter((w) => w === 'CASH_NEED_EXCEEDS_CROP')
        .map((w) => (
          <Warning key={w} code={w} check={plan.news_check} />
        ))}
    </div>
  )
}

/** Sell in harvest week or 1..4 weeks later: each week's expected price and what it leaves after interest and
 * storage loss, from past seasons' AMIS weekly prices. The best week is marked. */
function Weeks({ plan }: { plan: WaitPlanResponse }) {
  const { t } = useTranslation()
  const best = plan.best_week
  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold text-slate">{t('wait.weeksTitle', { qty: plan.quantity_maund })}</p>
      <ol className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper">
        {(plan.weeks ?? []).map((w) => (
          <li
            key={w.week}
            className={`flex items-center justify-between gap-3 px-4 py-3 ${w.week === best ? 'bg-field-soft' : ''}`}
          >
            <span className="flex flex-col">
              <span className="font-semibold">
                {w.week === 0 ? t('wait.weekHarvest') : t('wait.weekN', { n: w.week })}
                {w.week === best && (
                  <span className="ms-2 rounded-full bg-field px-2 text-sm text-paper">{t('wait.best')}</span>
                )}
              </span>
              <span className="figures text-sm text-slate">{formatRs(w.price)}</span>
            </span>
            <span className="text-end">
              <span className="figures block font-semibold">{formatRs(w.total_rs)}</span>
              {w.week > 0 && (
                <span className={`figures block text-sm ${w.gain_rs >= 0 ? 'text-field' : 'text-madder'}`}>
                  {w.gain_rs >= 0 ? '+' : '−'}
                  {formatRs(Math.abs(w.gain_rs))}
                </span>
              )}
            </span>
          </li>
        ))}
      </ol>
      <p className="text-sm text-slate">{t('wait.weeksFrom', { n: plan.weeks_n_years })}</p>
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

import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type LenderId } from '../api/client'
import type { Lang } from '../i18n'
import { formatDate, formatRs, parseTypedNumber } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { ChipGroup } from './ChipGroup'
import { ErrorBox, Loading } from './Status'

const LENDERS: LenderId[] = ['kissan_card', 'pm_youth', 'akhuwat', 'zarkhez_e', 'bank', 'arhti']
const INPUT = 'figures min-h-12 w-40 rounded-xl border-2 border-line bg-paper px-3 py-2 text-lg focus:border-ink focus:outline-none'

/**
 * The farmer's loans (docs/PIVOT.md 3.4). The wait plan counts every loan due before the later sale as cash
 * needed now, so keeping this list is what makes "can you afford to wait?" answer for this farmer.
 */
export function LoanList() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const [version, setVersion] = useState(0)
  const [loans, reload] = useAsync((signal) => api.loans(signal), `loans#${version}`)
  // Default rates come from the loan options data (the server's), never typed into the front end.
  const [opts] = useAsync((signal) => api.loanPlan({ crop: 'wheat', acres: 1 }, signal), 'loan-options')
  const rateOf = (id: string) => (opts.status === 'ok' ? opts.data.options.find((o) => o.id === id)?.annual_rate_pct : undefined)

  const [lender, setLender] = useState<LenderId>('arhti')
  const [amount, setAmount] = useState('')
  const [rate, setRate] = useState('')
  const [due, setDue] = useState('')
  const [error, setError] = useState<unknown>(null)

  const amountRs = parseTypedNumber(amount)
  const rateTyped = rate === '' ? rateOf(lender) : parseTypedNumber(rate)
  const ok = amountRs !== null && amountRs > 0 && rateTyped != null && rateTyped >= 0 && due !== ''

  function add(e: FormEvent) {
    e.preventDefault()
    if (!ok) return
    setError(null)
    api.addLoan({ lender, amount_rs: amountRs, annual_rate_pct: rateTyped, due_date: due }).then(() => {
      setAmount('')
      setRate('')
      setVersion((v) => v + 1)
    }, setError)
  }

  function remove(id: string) {
    api.deleteLoan(id).then(() => setVersion((v) => v + 1), setError)
  }

  const name = (id: string) => (LENDERS.includes(id as LenderId) ? t(`loan.lender.${id}`) : id)

  return (
    <section className="space-y-3 rounded-2xl bg-paper p-4 shadow-sm">
      <div>
        <h2 className="text-xl font-bold">{t('loan.listTitle')}</h2>
        <p className="text-sm text-slate">{t('loan.listIntro')}</p>
      </div>

      {loans.status === 'loading' && <Loading />}
      {loans.status === 'error' && <ErrorBox error={loans.error} onRetry={reload} />}
      {loans.status === 'ok' && loans.data.length === 0 && <p className="text-sm text-slate">{t('loan.listEmpty')}</p>}
      {loans.status === 'ok' && loans.data.length > 0 && (
        <ul className="space-y-2">
          {loans.data.map((l) => (
            <li key={l.id} className="flex items-center justify-between gap-3 border-s-2 border-line ps-3">
              <span>
                <span className="block font-bold">{name(l.lender)}</span>
                <span className="block text-sm text-slate">
                  {t('loan.listLine', { rate: l.annual_rate_pct, date: formatDate(l.due_date, lang) })}
                </span>
              </span>
              <span className="flex items-center gap-2">
                <span className="figures">{formatRs(l.amount_rs)}</span>
                <button type="button" onClick={() => remove(l.id)} aria-label={t('loan.remove')}
                  className="min-h-12 min-w-12 rounded-xl border-2 border-line text-madder">
                  ✕
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={add} className="tear space-y-3 pt-3">
        <h3 className="font-bold">{t('loan.add')}</h3>
        <ChipGroup label={t('loan.from')} value={lender} onChange={(v) => setLender(v as LenderId)}
          options={LENDERS.map((l) => ({ value: l, label: name(l) }))} />
        <label className="block text-sm text-slate">
          {t('loan.amount')}
          <input inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} className={`${INPUT} mt-1 block`} />
        </label>
        <label className="block text-sm text-slate">
          {t('wait.rate')}
          <input inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)}
            placeholder={rateOf(lender) != null ? String(rateOf(lender)) : ''} className={`${INPUT} mt-1 block w-24`} />
        </label>
        <label className="block text-sm text-slate">
          {t('loan.due')}
          <input type="date" value={due} onChange={(e) => setDue(e.target.value)} className={`${INPUT} mt-1 block w-48`} />
        </label>
        <button type="submit" disabled={!ok} className="min-h-12 rounded-xl bg-ink px-4 py-2 font-bold text-cotton disabled:opacity-50">
          {t('loan.addButton')}
        </button>
        {error !== null && <ErrorBox error={error} />}
      </form>
    </section>
  )
}

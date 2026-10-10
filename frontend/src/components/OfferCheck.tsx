import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type OfferCheckResponse } from '../api/client'
import { useAppState } from '../appState'
import { formatRs, parseTypedNumber } from '../lib/format'
import { ErrorBox } from './Status'

/** "Buyer offered Rs ___": compared with what AMIS reported at this mandi in the last 14 days (UC-07). */
export function OfferCheck() {
  const { t } = useTranslation()
  const { selection, quantity } = useAppState()
  const [typed, setTyped] = useState('')
  const [result, setResult] = useState<OfferCheckResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const offer = parseTypedNumber(typed)

  function submit(e: FormEvent) {
    e.preventDefault()
    if (offer === null || offer <= 0) return
    setError(null)
    api.offerCheck({ ...selection, offer_price: offer, quantity_maund: quantity }).then(setResult, setError)
  }

  const colour = result?.verdict === 'below' ? 'text-madder' : result?.verdict === 'above' ? 'text-field' : 'text-ink'
  return (
    <form onSubmit={submit} className="space-y-2 rounded-2xl bg-paper p-4 shadow-sm" noValidate>
      <label htmlFor="offer" className="block text-sm font-bold">
        {t('offer.title')}
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <input
          id="offer"
          inputMode="decimal"
          placeholder={t('offer.placeholder')}
          value={typed}
          onChange={(e) => {
            setTyped(e.target.value)
            setResult(null)
          }}
          className="figures w-40 rounded-xl border-2 border-line bg-paper px-3 py-2 text-lg focus:border-ink focus:outline-none"
        />
        <button
          type="submit"
          disabled={offer === null || offer <= 0}
          className="min-h-12 rounded-xl bg-ink px-4 py-2 text-cotton disabled:opacity-50"
        >
          {t('offer.check')}
        </button>
      </div>
      {result && (
        <div aria-live="polite" className="space-y-1">
          <p className={`text-lg font-bold ${colour}`}>
            {result.verdict === 'fair'
              ? t('offer.fair')
              : t(`offer.${result.verdict}`, { diff: formatRs(Math.abs(result.difference_per_maund)) })}
          </p>
          <p className="text-sm text-slate">
            {t('offer.fairRange', { days: result.window_days, low: formatRs(result.fair_low), high: formatRs(result.fair_high) })}
          </p>
          {result.verdict !== 'fair' && (
            <p className="text-sm text-slate">
              {t('offer.total', { qty: quantity, total: formatRs(result.difference_total) })}
            </p>
          )}
        </div>
      )}
      {error !== null && <ErrorBox error={error} />}
    </form>
  )
}

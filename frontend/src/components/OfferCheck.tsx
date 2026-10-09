import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type OfferCheckResponse } from '../api/client'
import { useAppState } from '../appState'
import { parseTypedNumber } from '../lib/format'
import { OfferResult } from './OfferResult'
import { SelectionBar } from './SelectionBar'
import { ErrorBox } from './Status'

/**
 * "Check a buyer offer" (UC-07), the main thing FarmSight does: crop, mandi and quantity (shared with every
 * screen), the buyer's price per maund, then the API's comparison with recent AMIS reference prices.
 */
export function OfferCheck() {
  const { t } = useTranslation()
  const { selection, quantity, mandiName } = useAppState()
  const [typed, setTyped] = useState('')
  // The result is kept with the question it answers, so changing crop, mandi or quantity hides an old answer.
  const [answer, setAnswer] = useState<{ key: string; result: OfferCheckResponse } | null>(null)
  const [error, setError] = useState<unknown>(null)
  const offer = parseTypedNumber(typed)
  const key = `${selection.crop}|${selection.mandi}|${quantity}|${offer}`

  function submit(e: FormEvent) {
    e.preventDefault()
    if (offer === null || offer <= 0) return
    setError(null)
    api
      .offerCheck({ ...selection, offer_price: offer, quantity_maund: quantity })
      .then((result) => setAnswer({ key, result }), setError)
  }

  return (
    <section className="space-y-3" aria-labelledby="offer-title">
      <div>
        <h2 id="offer-title" className="text-2xl font-bold">
          {t('offer.title')}
        </h2>
        <p className="text-sm text-slate">{t('offer.intro')}</p>
      </div>
      <SelectionBar withQuantity />
      <form onSubmit={submit} className="space-y-3 rounded-2xl bg-paper p-4 shadow-sm" noValidate>
        <label htmlFor="offer" className="block font-bold">
          {t('offer.label')}
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <input
            id="offer"
            inputMode="decimal"
            placeholder={t('offer.placeholder')}
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            className="figures w-44 rounded-xl border-2 border-line bg-paper px-3 py-3 text-xl focus:border-ink focus:outline-none"
          />
          <button
            type="submit"
            disabled={offer === null || offer <= 0}
            className="min-h-12 rounded-xl bg-ink px-5 py-3 text-lg font-bold text-cotton disabled:opacity-50"
          >
            {t('offer.check')}
          </button>
        </div>
        {answer && answer.key === key && <OfferResult result={answer.result} mandiName={mandiName} />}
        {error !== null && <ErrorBox error={error} />}
      </form>
    </section>
  )
}

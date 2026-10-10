import { ArrowLeft, Scale } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api, QUANTITY_MAX } from '../api/client'
import { useAppState } from '../appState'
import { formatNumber, formatRs, parseTypedNumber } from '../lib/format'
import { replayDate } from '../lib/replay'
import { ChipGroup } from './ChipGroup'
import { OfferResult } from './OfferResult'
import { ErrorBox, Loading } from './Status'
import { Button } from './ui/Button'
import { NumberField } from './ui/NumberField'

// The demo's example offer (docs/DEMO.md): it only fills the form, it is never shown as a real price.
const EXAMPLE = { crop: 'wheat', mandi: 'bahawalpur', quantity: 100, offer: 3514 }

/**
 * "Check a buyer's offer", FarmSight's main job: crop, mandi, quantity and the buyer's price per maund, then the
 * API's comparison with recent AMIS reference prices. The latest check is kept for this browser session.
 */
export function OfferCheck() {
  const { t } = useTranslation()
  const { meta, selection, setCrop, setMandi, mandisFor, name, quantity, setQuantity, mandiName, cropName,
    lastCheck, setLastCheck } = useAppState()
  const matches = (c: typeof lastCheck) =>
    c !== null && c.crop === selection.crop && c.mandi === selection.mandi && c.quantity === quantity
  const [typed, setTyped] = useState(() => (matches(lastCheck) ? String(lastCheck!.offer) : ''))
  const [qtyText, setQtyText] = useState({ forQty: quantity, text: String(quantity) })
  const [state, setState] = useState<'idle' | 'loading' | { error: unknown }>('idle')
  const [showErrors, setShowErrors] = useState(false)

  const qtyTyped = qtyText.forQty === quantity ? qtyText.text : String(quantity)
  const qty = parseTypedNumber(qtyTyped)
  const qtyError =
    qty === null || qty <= 0
      ? t('select.quantityInvalid')
      : qty > QUANTITY_MAX
        ? t('select.quantityTooLarge', { max: formatNumber(QUANTITY_MAX) })
        : null
  const offer = parseTypedNumber(typed)
  const offerError = offer === null || offer <= 0 ? t('offer.errors.offer') : offer > 1_000_000 ? t('offer.errors.tooLarge') : null
  const shown = matches(lastCheck) && lastCheck!.offer === offer ? lastCheck : null

  function submit(e: FormEvent) {
    e.preventDefault()
    setShowErrors(true)
    if (offerError || qtyError || offer === null) return
    setState('loading')
    api.offerCheck({ ...selection, offer_price: offer, quantity_maund: quantity }).then(
      (result) => {
        setLastCheck({ ...selection, quantity, offer, asOf: replayDate, result })
        setState('idle')
      },
      (error: unknown) => setState({ error }),
    )
  }

  function useExample() {
    setCrop(EXAMPLE.crop)
    setMandi(EXAMPLE.mandi)
    setQuantity(EXAMPLE.quantity)
    setQtyText({ forQty: EXAMPLE.quantity, text: String(EXAMPLE.quantity) })
    setTyped(String(EXAMPLE.offer))
  }

  return (
    <div className="space-y-5">
      <form onSubmit={submit} className="card space-y-5 p-5 lg:p-6" noValidate aria-labelledby="offer-title">
        <h2 id="offer-title" className="flex items-center gap-2 text-xl font-bold">
          <Scale aria-hidden className="size-6 text-field" />
          {t('offer.title')}
        </h2>
        <ChipGroup
          label={t('offer.form.crop')}
          options={meta.crops.map((c) => ({ value: c.id, label: name(c) }))}
          value={selection.crop}
          onChange={setCrop}
        />
        <ChipGroup
          label={t('offer.form.mandi')}
          options={mandisFor(selection.crop).map((m) => ({ value: m.id, label: name(m) }))}
          value={selection.mandi}
          onChange={setMandi}
        />
        <div className="grid gap-5 lg:grid-cols-2">
          <NumberField
            id="qty"
            label={t('offer.form.quantity')}
            unit={t('select.maund')}
            value={qtyTyped}
            onChange={(text) => {
              const n = parseTypedNumber(text)
              const valid = n !== null && n > 0 && n <= QUANTITY_MAX
              if (valid) setQuantity(n)
              setQtyText({ forQty: valid ? n : quantity, text })
            }}
            helper={t('offer.form.maundIs40kg')}
            error={qtyError}
          />
          <NumberField
            id="offer"
            label={t('offer.label')}
            prefix="Rs"
            unit={t('offer.form.perMaund')}
            value={typed}
            onChange={setTyped}
            placeholder={t('offer.placeholder')}
            error={showErrors ? offerError : null}
          />
        </div>
        <Button type="submit" wide disabled={state === 'loading'}>
          {t('offer.check')}
          <ArrowLeft aria-hidden className="size-5 ltr:rotate-180" />
        </Button>
        <button type="button" onClick={useExample} className="text-sm text-slate underline-offset-4 hover:underline">
          {t('offer.form.example', { offer: formatRs(EXAMPLE.offer), qty: EXAMPLE.quantity })}
        </button>
      </form>
      {state === 'loading' && <Loading label={t('offer.loading')} />}
      {typeof state === 'object' && <ErrorBox error={state.error} />}
      {shown && state !== 'loading' && <OfferResult result={shown.result} mandiName={mandiName} cropName={cropName} />}
    </div>
  )
}

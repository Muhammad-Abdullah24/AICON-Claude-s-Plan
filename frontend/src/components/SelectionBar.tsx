import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { QUANTITY_MAX } from '../api/client'
import { useAppState } from '../appState'
import { formatNumber, parseTypedNumber } from '../lib/format'
import { ChipGroup } from './ChipGroup'

/**
 * Crop and mandi as large chips, and optionally the farmer's quantity. Shared by every screen.
 *
 * Collapsed to one line ("Wheat · Bahawalpur · 100 maund — Change") so the answer stays on the first screen
 * of a phone (blueprint section 11, "Answer first"); tapping the line opens the chips. A native <details>
 * element, so it works with a keyboard and a screen reader without extra code.
 */
export function SelectionBar({ withQuantity = false }: { withQuantity?: boolean }) {
  const { t } = useTranslation()
  const { meta, selection, setCrop, setMandi, mandisFor, name, quantity, setQuantity } = useAppState()
  // What the farmer typed, remembered with the quantity it belongs to: when the quantity changes elsewhere
  // (another crop, a login), the box shows the new one without an effect.
  const [draft, setDraft] = useState({ forQty: quantity, text: String(quantity) })
  const typed = draft.forQty === quantity ? draft.text : String(quantity)

  const qty = parseTypedNumber(typed)
  const problem = qty === null || qty <= 0 ? 'empty' : qty > QUANTITY_MAX ? 'tooLarge' : null

  const crop = meta.crops.find((c) => c.id === selection.crop)
  const mandi = meta.mandis.find((m) => m.id === selection.mandi)
  const summary = [name(crop), name(mandi), withQuantity ? `${formatNumber(quantity)} ${t('select.maund')}` : null]
    .filter(Boolean)
    .join(' · ')

  return (
    <details className="group rounded-2xl bg-paper shadow-sm">
      {/* The browser opens and closes it. An error can only appear while typing in the open panel, so the one
          case to stop is closing it then: that tap is cancelled, and the error is never hidden. */}
      <summary
        onClick={(e) => problem !== null && e.preventDefault()}
        className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 py-2 [&::-webkit-details-marker]:hidden"
      >
        <span className="font-bold">{summary}</span>
        <span className="shrink-0 rounded-full border-2 border-line px-3 text-sm text-slate group-open:hidden">
          {t('select.change')}
        </span>
        <span className="hidden shrink-0 rounded-full border-2 border-line px-3 text-sm text-slate group-open:inline">
          {t('select.done')}
        </span>
      </summary>
      <div className="space-y-4 px-4 pb-4">
        <ChipGroup
          label={t('select.crop')}
          options={meta.crops.map((c) => ({ value: c.id, label: name(c) }))}
          value={selection.crop}
          onChange={setCrop}
        />
        <ChipGroup
          label={t('select.mandi')}
          options={mandisFor(selection.crop).map((m) => ({ value: m.id, label: name(m) }))}
          value={selection.mandi}
          onChange={setMandi}
        />
        {withQuantity && (
          <div>
            <label htmlFor="qty" className="mb-1 block text-sm text-slate">
              {t('select.quantity')}
            </label>
            <div className="flex items-center gap-2">
              <input
                id="qty"
                inputMode="decimal"
                value={typed}
                onChange={(e) => {
                  const n = parseTypedNumber(e.target.value)
                  const valid = n !== null && n > 0 && n <= QUANTITY_MAX
                  if (valid) setQuantity(n)
                  setDraft({ forQty: valid ? n : quantity, text: e.target.value })
                }}
                aria-invalid={problem !== null}
                aria-describedby={problem ? 'qty-error' : undefined}
                className="figures w-32 rounded-xl border-2 border-line bg-paper px-3 py-2 text-xl focus:border-ink focus:outline-none"
              />
              <span className="text-base">{t('select.maund')}</span>
            </div>
            {problem && (
              <p id="qty-error" className="mt-1 text-sm text-madder">
                {problem === 'tooLarge'
                  ? t('select.quantityTooLarge', { max: formatNumber(QUANTITY_MAX) })
                  : t('select.quantityInvalid')}
              </p>
            )}
          </div>
        )}
      </div>
    </details>
  )
}

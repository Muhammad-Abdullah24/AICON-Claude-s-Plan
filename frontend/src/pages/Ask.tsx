import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api, QUANTITY_MAX, type AdviceRequest, type AdviceResponse, type Storage } from '../api/client'
import { ChipGroup } from '../components/ChipGroup'
import { ErrorBox } from '../components/Status'
import { VerdictParchi } from '../components/VerdictParchi'
import i18next, { type Lang } from '../i18n'
import { formatNumber, parseTypedNumber } from '../lib/format'
import { useAppState } from '../appState'

const STORAGE: Storage[] = ['none', 'home', 'cold_store', 'warehouse']

type Result =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; advice: AdviceResponse; quantity: number }
  | { status: 'error'; error: unknown }

export function Ask() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { meta, selection, setCrop, setMandi, mandisFor, name } = useAppState()
  const [quantity, setQuantity] = useState('100')
  const [storage, setStorage] = useState<Storage>('home')
  const [result, setResult] = useState<Result>({ status: 'idle' })
  const lastRequest = useRef<AdviceRequest | null>(null)
  const inflight = useRef<AbortController | null>(null)

  const qty = parseTypedNumber(quantity)
  const qtyProblem = qty === null || qty <= 0 ? 'empty' : qty > QUANTITY_MAX ? 'tooLarge' : null
  const qtyValid = qtyProblem === null

  // Stable: uses only refs and a state setter.
  const run = useCallback((req: AdviceRequest) => {
    inflight.current?.abort()
    const ctrl = new AbortController()
    inflight.current = ctrl
    lastRequest.current = req
    setResult({ status: 'loading' })
    api.advice(req, ctrl.signal).then(
      (advice) => setResult({ status: 'ok', advice, quantity: req.quantity_maund }),
      (error: unknown) => {
        if (!ctrl.signal.aborted) setResult({ status: 'error', error })
      },
    )
  }, [])

  // Any change to the inputs makes the shown advice stale, so the handlers clear it.
  function changed<T>(set: (v: T) => void) {
    return (v: T) => {
      inflight.current?.abort()
      lastRequest.current = null
      setResult({ status: 'idle' })
      set(v)
    }
  }

  // The advice text is written by the server in one language: refetch it when the language changes.
  // This effect only manages the listener. It must not cancel requests: its cleanup also runs when
  // React re-subscribes, and cancelling there killed the refetch it had just started.
  useEffect(() => {
    const onChange = (next: string) => {
      const last = lastRequest.current
      if (last && last.lang !== next) run({ ...last, lang: next as Lang })
    }
    i18next.on('languageChanged', onChange)
    return () => i18next.off('languageChanged', onChange)
  }, [run])

  // Cancel any request still in flight when the screen closes.
  useEffect(() => () => inflight.current?.abort(), [])

  function submit(e: FormEvent) {
    e.preventDefault()
    if (qty === null || !qtyValid) return
    run({ crop: selection.crop, mandi: selection.mandi, quantity_maund: qty, storage, lang })
  }

  return (
    <div className="space-y-5">
      <form onSubmit={submit} className="space-y-4 rounded-2xl bg-paper p-4 shadow-sm" noValidate>
        <ChipGroup
          label={t('ask.crop')}
          options={meta.crops.map((c) => ({ value: c.id, label: name(c) }))}
          value={selection.crop}
          onChange={changed(setCrop)}
        />
        <ChipGroup
          label={t('ask.mandi')}
          options={mandisFor(selection.crop).map((m) => ({ value: m.id, label: name(m) }))}
          value={selection.mandi}
          onChange={changed(setMandi)}
        />
        <div>
          <label htmlFor="qty" className="mb-1 block text-sm text-slate">
            {t('ask.quantity')}
          </label>
          <div className="flex items-center gap-2">
            <input
              id="qty"
              inputMode="decimal"
              value={quantity}
              onChange={(e) => changed(setQuantity)(e.target.value)}
              aria-invalid={!qtyValid}
              aria-describedby={qtyValid ? undefined : 'qty-error'}
              className="figures w-32 rounded-xl border-2 border-line bg-paper px-3 py-2 text-xl focus:border-ink focus:outline-none"
            />
            <span className="text-base">{t('ask.maund')}</span>
          </div>
          {qtyProblem && (
            <p id="qty-error" className="mt-1 text-sm text-madder">
              {qtyProblem === 'tooLarge'
                ? t('ask.quantityTooLarge', { max: formatNumber(QUANTITY_MAX) })
                : t('ask.quantityInvalid')}
            </p>
          )}
        </div>
        <ChipGroup
          label={t('ask.storage')}
          options={STORAGE.map((s) => ({ value: s, label: t(`ask.storageOptions.${s}`) }))}
          value={storage}
          onChange={changed((v: string) => setStorage(v as Storage))}
        />
        <button
          type="submit"
          disabled={!qtyValid || result.status === 'loading'}
          className="w-full rounded-xl bg-wheat px-4 py-3 text-lg font-bold text-ink transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {result.status === 'loading' ? t('ask.submitting') : t('ask.submit')}
        </button>
      </form>

      {result.status === 'ok' && <VerdictParchi advice={result.advice} quantity={result.quantity} />}
      {result.status === 'error' && (
        <ErrorBox error={result.error} onRetry={() => lastRequest.current && run(lastRequest.current)} />
      )}
    </div>
  )
}

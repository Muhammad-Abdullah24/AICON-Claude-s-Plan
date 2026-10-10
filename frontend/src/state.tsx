/**
 * App-wide state: the meta (crops, mandis, series, data labels) loaded once from the API, the farmer's
 * current crop, mandi and quantity, and the logged-in farmer (if any). Shared by every screen.
 *
 * Crops and mandis come only from /api/meta, never from code.
 */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { api, getToken, setToken, type Farmer, type Meta, type NamedItem } from './api/client'
import { type AppState, AppStateContext, type Selection } from './appState'
import type { Lang } from './i18n'

const DEMO_DEFAULT: Selection = { crop: 'wheat', mandi: 'bahawalpur' }
const EXAMPLE_QUANTITY = 100

function firstSelection(meta: Meta, farmer: Farmer | null): Selection {
  const has = (s: Selection) => meta.series.some((x) => x.crop === s.crop && x.mandi === s.mandi)
  const own = farmer?.crops.map((c) => ({ crop: c.crop, mandi: c.preferred_mandi })).find(has)
  if (own) return own
  if (has(DEMO_DEFAULT)) return DEMO_DEFAULT
  return { crop: meta.series[0].crop, mandi: meta.series[0].mandi }
}

export function AppStateProvider({ meta, children }: { meta: Meta; children: ReactNode }) {
  const { i18n } = useTranslation()
  const lang = i18n.language as Lang
  const [farmer, setFarmerState] = useState<Farmer | null>(null)
  const [selection, setSelection] = useState<Selection>(() => firstSelection(meta, null))
  const [quantityOverride, setQuantityOverride] = useState<number | null>(null)

  // A saved login is restored once; an expired or unknown token simply leaves the farmer a guest.
  useEffect(() => {
    if (!getToken()) return
    const ctrl = new AbortController()
    api.me(ctrl.signal).then(
      (f) => {
        setFarmerState(f)
        setSelection(firstSelection(meta, f))
      },
      () => {
        if (!ctrl.signal.aborted) setToken(null)
      },
    )
    return () => ctrl.abort()
  }, [meta])

  const mandisFor = useCallback(
    (crop: string) => {
      const ids = new Set<string>(meta.series.filter((s) => s.crop === crop).map((s) => s.mandi))
      return meta.mandis.filter((m) => ids.has(m.id))
    },
    [meta],
  )

  // Changing crop keeps the mandi if that pair exists, otherwise picks the first valid one.
  const setCrop = useCallback(
    (crop: string) => {
      setQuantityOverride(null)
      setSelection((s) => {
        const valid = mandisFor(crop)
        return { crop, mandi: valid.some((m) => m.id === s.mandi) ? s.mandi : valid[0].id }
      })
    },
    [mandisFor],
  )
  const setMandi = useCallback((mandi: string) => setSelection((s) => ({ ...s, mandi })), [])

  const signIn = useCallback(
    (token: string, f: Farmer) => {
      setToken(token)
      setFarmerState(f)
      setQuantityOverride(null)
      setSelection(firstSelection(meta, f))
      if (f.language !== i18n.language) void i18n.changeLanguage(f.language)
    },
    [meta, i18n],
  )
  const signOut = useCallback(() => {
    setToken(null)
    setFarmerState(null)
    setQuantityOverride(null)
  }, [])

  const value = useMemo<AppState>(() => {
    const name = (item: NamedItem | undefined) => (item ? (lang === 'en' ? item.name_en : item.name_ur) : '')
    const profileQty = farmer?.crops.find((c) => c.crop === selection.crop)?.harvest_quantity_maund
    return {
      meta,
      selection,
      setCrop,
      setMandi,
      mandisFor,
      series: (crop, mandi) => meta.series.find((s) => s.crop === crop && s.mandi === mandi),
      quantity: quantityOverride ?? profileQty ?? EXAMPLE_QUANTITY,
      setQuantity: setQuantityOverride,
      farmer,
      signIn,
      signOut,
      setFarmer: setFarmerState,
      name,
      cropName: (id) => name(meta.crops.find((c) => c.id === id)),
      mandiName: (id) => name(meta.mandis.find((m) => m.id === id)),
    }
  }, [meta, selection, setCrop, setMandi, mandisFor, quantityOverride, farmer, signIn, signOut, lang])

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
}

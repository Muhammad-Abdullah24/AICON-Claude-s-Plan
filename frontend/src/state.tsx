/**
 * App-wide state: the meta (crops, mandis, data labels) loaded once from the
 * API, and the farmer's current crop and mandi, shared by every screen.
 *
 * Crops and mandis come only from /api/meta, never from code (PLAN.md 11.3).
 */
import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import type { Meta, NamedItem } from './api/client'
import { type AppState, AppStateContext, type Selection } from './appState'
import type { Lang } from './i18n'

export function AppStateProvider({ meta, children }: { meta: Meta; children: ReactNode }) {
  const { i18n } = useTranslation()
  const lang = i18n.language as Lang

  const mandisFor = useCallback(
    (crop: string) => {
      const ids = new Set(meta.series.filter((s) => s.crop === crop).map((s) => s.mandi))
      return meta.mandis.filter((m) => ids.has(m.id))
    },
    [meta],
  )

  const [selection, setSelection] = useState<Selection>(() => ({
    crop: meta.series[0].crop,
    mandi: meta.series[0].mandi,
  }))

  // Changing crop keeps the mandi if that pair exists, otherwise picks the first valid one.
  const setCrop = useCallback(
    (crop: string) =>
      setSelection((s) => {
        const valid = mandisFor(crop)
        return { crop, mandi: valid.some((m) => m.id === s.mandi) ? s.mandi : valid[0].id }
      }),
    [mandisFor],
  )
  const setMandi = useCallback((mandi: string) => setSelection((s) => ({ ...s, mandi })), [])

  const value = useMemo<AppState>(() => {
    const name = (item: NamedItem | undefined) => (item ? (lang === 'en' ? item.name_en : item.name_ur) : '')
    return {
      meta,
      selection,
      setCrop,
      setMandi,
      mandisFor,
      name,
      cropName: (id) => name(meta.crops.find((c) => c.id === id)),
      mandiName: (id) => name(meta.mandis.find((m) => m.id === id)),
    }
  }, [meta, selection, setCrop, setMandi, mandisFor, lang])

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
}

import { createContext, useContext } from 'react'

import type { Farmer, Meta, NamedItem, OfferCheckResponse, SeriesInfo } from './api/client'

export interface Selection {
  crop: string
  mandi: string
}

/** The farmer's latest offer check, kept for this browser session only (sessionStorage), never sent anywhere. */
export interface LastCheck {
  crop: string
  mandi: string
  quantity: number
  offer: number
  asOf: string | null // the replay date it was made under, so a replay never shows a live check
  result: OfferCheckResponse
}

export interface AppState {
  meta: Meta
  selection: Selection
  setCrop: (crop: string) => void
  setMandi: (mandi: string) => void
  mandisFor: (crop: string) => NamedItem[]
  series: (crop: string, mandi: string) => SeriesInfo | undefined
  /** The farmer's quantity for the selected crop, else 100 (the blueprint's example). */
  quantity: number
  setQuantity: (q: number) => void
  farmer: Farmer | null
  signIn: (token: string, farmer: Farmer) => void
  signOut: () => void
  setFarmer: (farmer: Farmer) => void
  lastCheck: LastCheck | null
  setLastCheck: (c: LastCheck) => void
  name: (item: NamedItem | undefined) => string
  cropName: (id: string) => string
  mandiName: (id: string) => string
}

export const AppStateContext = createContext<AppState | null>(null)

export function useAppState(): AppState {
  const v = useContext(AppStateContext)
  if (!v) throw new Error('useAppState must be used inside AppStateProvider')
  return v
}

import { createContext, useContext } from 'react'

import type { Meta, NamedItem } from './api/client'

export interface Selection {
  crop: string
  mandi: string
}

export interface AppState {
  meta: Meta
  selection: Selection
  setCrop: (crop: string) => void
  setMandi: (mandi: string) => void
  mandisFor: (crop: string) => NamedItem[]
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

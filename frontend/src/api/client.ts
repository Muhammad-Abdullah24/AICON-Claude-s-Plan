/**
 * The only place the front end talks to the backend (docs/BLUEPRINT.md section 12).
 *
 * Every type comes from schema.d.ts, which is generated from the backend's Pydantic models
 * (npm run gen:api). Never write an API type by hand: if the backend changes a field, regenerate and
 * TypeScript shows every place to fix.
 */
import { replayDate } from '../lib/replay'
import spec from './openapi.json'
import type { components } from './schema'

type S = components['schemas']
export type Meta = S['Meta']
export type NamedItem = S['NamedItem']
export type CropInfo = S['CropInfo']
export type SeriesInfo = S['SeriesInfo']
export type ForecastResponse = S['ForecastResponse']
export type ExplainResponse = S['ExplainResponse']
export type Reason = S['Reason']
export type HistoryResponse = S['HistoryResponse']
export type AdviceResponse = S['AdviceResponse']
export type CompareResponse = S['CompareResponse']
export type CompareRow = S['CompareRow']
export type OfferCheckResponse = S['OfferCheckResponse']
export type MarginResponse = S['MarginResponse']
export type CropPlanResponse = S['CropPlanResponse']
export type CropPlanItem = S['CropPlanItem']
export type WeatherResponse = S['WeatherResponse']
export type Farmer = S['Farmer']
export type FarmerIn = S['FarmerIn']
export type FarmerUpdate = S['FarmerUpdate']
export type TokenResponse = S['TokenResponse']
export type ChatResponse = S['ChatResponse']
export type CropId = ForecastResponse['crop']
export type MandiId = S['ForecastResponse']['mandi']
export type Signal = AdviceResponse['signal']
export type DirectionCall = S['DirectionCall']
export type WaitPlanResponse = S['WaitPlanResponse']
export type WaitExit = S['WaitExit']
export type HoldHistory = S['HoldHistory']
export type HoldSeason = S['HoldSeason']
export type NewsResponse = S['NewsResponse']
export type NewsItem = S['NewsItem']
export type NewsPriceCheck = S['NewsPriceCheck']
export type PolicyResponse = S['PolicyResponse']
export type PolicyEvent = S['PolicyEvent']
export type Money = WaitPlanResponse['money']
export type Storage = WaitPlanResponse['storage']

/** Input limits, read from the backend's schema so the two can never disagree. */
export const QUANTITY_MAX: number = spec.components.schemas.OfferCheckRequest.properties.quantity_maund.maximum
export const QUESTION_MAX: number = spec.components.schemas.ChatRequest.properties.question.maxLength

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const TOKEN_KEY = 'farmsight.token'

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null // storage blocked: the farmer simply stays a guest
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // not fatal
  }
}

/**
 * A saved login the server rejects (expired, or signed with a secret from before a restart) is dropped and the
 * request is sent again as a guest, so an old token never breaks the public screens.
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    return await send<T>(path, init, getToken())
  } catch (e) {
    if (!(e instanceof ApiError && e.status === 401 && getToken())) throw e
    setToken(null)
    return send<T>(path, init, null)
  }
}

async function send<T>(path: string, init: RequestInit | undefined, token: string | null): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    throw new ApiError(0, 'network')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // body was not JSON; keep the status text
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

function query(params: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v != null && v !== '') q.set(k, String(v))
  const s = q.toString()
  return s ? `?${s}` : ''
}

type Pair = { crop: string; mandi: string }
/** Price endpoints carry the replay date (lib/replay.ts) when the demo is replaying a past week. */
const priced = (params: Record<string, string | number | null | undefined>) => query({ ...params, as_of: replayDate })
const post = (body: unknown) => ({ method: 'POST', body: JSON.stringify(body) })

export const api = {
  meta: (signal?: AbortSignal) => request<Meta>('/api/meta', { signal }),
  forecast: (p: Pair, signal?: AbortSignal) => request<ForecastResponse>(`/api/forecast${priced(p)}`, { signal }),
  explain: (p: Pair, signal?: AbortSignal) => request<ExplainResponse>(`/api/explain${priced(p)}`, { signal }),
  history: (p: Pair, signal?: AbortSignal) => request<HistoryResponse>(`/api/history${priced(p)}`, { signal }),
  advice: (p: Pair & { quantity_maund?: number }, signal?: AbortSignal) =>
    request<AdviceResponse>(`/api/advice${priced(p)}`, { signal }),
  compare: (p: Pair & { quantity_maund?: number }, signal?: AbortSignal) =>
    request<CompareResponse>(`/api/compare-mandis${priced(p)}`, { signal }),
  cropPlan: (p: { mandi?: string; land_area_acres?: number }, signal?: AbortSignal) =>
    request<CropPlanResponse>(`/api/crop-plan${priced(p)}`, { signal }),
  waitPlan: (
    p: Pair & {
      quantity_maund?: number
      cash_need_rs?: number
      wait_months?: number
      money?: Money
      annual_rate?: number | null
      storage?: Storage
      offer?: number | null
    },
    signal?: AbortSignal,
  ) => request<WaitPlanResponse>(`/api/wait-plan${priced(p)}`, { signal }),
  // News is today's, never replayed (like weather), so it does not carry the replay date.
  news: (p: { crop?: string; mandi?: string }, signal?: AbortSignal) =>
    request<NewsResponse>(`/api/news${query(p)}`, { signal }),
  policy: (crop: string, signal?: AbortSignal) =>
    request<PolicyResponse>(`/api/policy${priced({ crop })}`, { signal }),
  offerCheck: (body: { crop: string; mandi: string; offer_price: number; quantity_maund: number }) =>
    request<OfferCheckResponse>(`/api/offer-check${priced({})}`, post(body)),
  margin: (p: { crop: string; price: number; arhti_pct?: number | null }, signal?: AbortSignal) =>
    request<MarginResponse>(`/api/margin${query(p)}`, { signal }),
  weather: (mandi: string, signal?: AbortSignal) =>
    request<WeatherResponse>(`/api/weather${query({ mandi })}`, { signal }),
  chat: (body: { question: string; crop?: string; mandi?: string; quantity_maund?: number }) =>
    request<ChatResponse>('/api/chat', post(body)),
  login: (phone: string) => request<TokenResponse>('/api/auth/login', post({ phone })),
  register: (body: FarmerIn) => request<TokenResponse>('/api/farmers', post(body)),
  me: (signal?: AbortSignal) => request<Farmer>('/api/farmers/me', { signal }),
  updateMe: (body: FarmerUpdate) => request<Farmer>('/api/farmers/me', { method: 'PUT', body: JSON.stringify(body) }),
}

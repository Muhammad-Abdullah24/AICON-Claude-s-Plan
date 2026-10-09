/**
 * The only place the front end talks to the backend.
 *
 * Every type comes from schema.d.ts, which is generated from the backend's
 * Pydantic models (npm run gen:api). Never write an API type by hand: if the
 * backend changes a field, regenerate and TypeScript shows every place to fix.
 */
import spec from './openapi.json'
import type { components } from './schema'

type S = components['schemas']
export type Meta = S['Meta']
export type ForecastResponse = S['ForecastResponse']
export type AdviceRequest = S['AdviceRequest']
export type AdviceResponse = S['AdviceResponse']
export type AlertsResponse = S['AlertsResponse']
export type ReplayResponse = S['ReplayResponse']
export type BacktestArtifact = S['BacktestArtifact']
export type Verdict = AdviceResponse['verdict']
export type Storage = AdviceRequest['storage']
export type NamedItem = S['NamedItem']

/** Input limits, read from the backend's schema so the two can never disagree. */
export const QUANTITY_MAX: number = spec.components.schemas.AdviceRequest.properties.quantity_maund.maximum

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}) },
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

function query(params: Record<string, string | null | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v != null && v !== '') q.set(k, v)
  const s = q.toString()
  return s ? `?${s}` : ''
}

export const api = {
  meta: (signal?: AbortSignal) => request<Meta>('/api/meta', { signal }),

  forecast: (p: { crop: string; mandi: string; as_of?: string | null }, signal?: AbortSignal) =>
    request<ForecastResponse>(`/api/forecast${query(p)}`, { signal }),

  advice: (body: AdviceRequest, signal?: AbortSignal) =>
    request<AdviceResponse>('/api/advice', { method: 'POST', body: JSON.stringify(body), signal }),

  alerts: (p: { crop: string; mandi?: string | null; as_of?: string | null }, signal?: AbortSignal) =>
    request<AlertsResponse>(`/api/alerts${query(p)}`, { signal }),

  replay: (caseId: string, lang: 'ur' | 'en', signal?: AbortSignal) =>
    request<ReplayResponse>(`/api/replay/${encodeURIComponent(caseId)}${query({ lang })}`, { signal }),

  backtest: (signal?: AbortSignal) => request<BacktestArtifact>('/api/backtest', { signal }),
}

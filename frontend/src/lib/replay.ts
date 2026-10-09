/**
 * Replay mode for the demo's backup weeks: open the app with `?as_of=2025-03-24` and every price screen shows what
 * the app would have said that day (the API's time-machine rule: no price after that date). It lasts for the browser
 * tab, so it survives moving between screens; `?as_of=` with no date goes back to today.
 */
const KEY = 'farmsight.asOf'
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

export function readReplayDate(search: string, storage: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>): string | null {
  const params = new URLSearchParams(search)
  if (params.has('as_of')) {
    const v = params.get('as_of') ?? ''
    if (ISO_DATE.test(v)) {
      storage.setItem(KEY, v)
      return v
    }
    storage.removeItem(KEY)
    return null
  }
  const saved = storage.getItem(KEY)
  return saved && ISO_DATE.test(saved) ? saved : null
}

function initial(): string | null {
  try {
    return readReplayDate(window.location.search, sessionStorage)
  } catch {
    return null // no window (tests) or storage blocked: today's prices
  }
}

export const replayDate: string | null = initial()

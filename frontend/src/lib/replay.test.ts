import { describe, expect, it } from 'vitest'

import { readReplayDate } from './replay'

function memory() {
  const m = new Map<string, string>()
  return {
    getItem: (k: string) => m.get(k) ?? null,
    setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k),
  }
}

describe('replay date', () => {
  it('starts from ?as_of and keeps it while moving between screens', () => {
    const s = memory()
    expect(readReplayDate('?as_of=2025-03-24', s)).toBe('2025-03-24')
    expect(readReplayDate('', s)).toBe('2025-03-24')
  })

  it('an empty or malformed as_of goes back to today', () => {
    const s = memory()
    readReplayDate('?as_of=2025-03-24', s)
    expect(readReplayDate('?as_of=', s)).toBeNull()
    expect(readReplayDate('', s)).toBeNull()
    expect(readReplayDate('?as_of=24-03-2025', s)).toBeNull()
  })
})

import { describe, expect, it } from 'vitest'

import { inSeason, monthsIn } from './months'

describe('seasons', () => {
  it('lists the months of a season', () => {
    expect(monthsIn([4, 6])).toEqual([4, 5, 6])
    expect(monthsIn([10, 12])).toEqual([10, 11, 12])
  })

  it('wraps over the new year', () => {
    expect(monthsIn([11, 3])).toEqual([11, 12, 1, 2, 3])
    expect(inSeason(1, [11, 3])).toBe(true)
    expect(inSeason(6, [11, 3])).toBe(false)
  })
})

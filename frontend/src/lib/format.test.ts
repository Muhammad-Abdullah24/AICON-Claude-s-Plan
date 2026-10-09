import { describe, expect, it } from 'vitest'

import { addWeeks, formatRs, parseDate } from './format'

describe('format', () => {
  it('formats rupees with Western digits and separators', () => {
    expect(formatRs(4250)).toBe('Rs 4,250')
    expect(formatRs(1234567.6)).toBe('Rs 1,234,568')
    expect(formatRs(-1200)).toBe('Rs -1,200')
  })

  it('parses ISO dates as calendar dates without a timezone shift', () => {
    const d = parseDate('2026-10-04')
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 9, 4])
  })

  it('adds weeks across month and year boundaries', () => {
    expect(addWeeks('2026-10-04', 1)).toBe('2026-10-11')
    expect(addWeeks('2026-12-27', 1)).toBe('2027-01-03')
    expect(addWeeks('2024-02-25', 1)).toBe('2024-03-03')
  })
})

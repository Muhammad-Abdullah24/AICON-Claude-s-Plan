/** Months 1-12 in a season [start, end]; a season may wrap over the new year (e.g. sowing 10 to 12, or 11 to 3). */
export function monthsIn([start, end]: readonly [number, number]): number[] {
  const out: number[] = []
  let m = start
  for (let i = 0; i < 12; i++) {
    out.push(m)
    if (m === end) break
    m = (m % 12) + 1
  }
  return out
}

export function inSeason(month: number, span: readonly [number, number]): boolean {
  return monthsIn(span).includes(month)
}

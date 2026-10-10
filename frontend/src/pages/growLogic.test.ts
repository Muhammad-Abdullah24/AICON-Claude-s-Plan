import { describe, expect, it } from 'vitest'

import type { CropPlanItem, CropPlanResponse } from '../api/client'
import en from '../locales/en.json'
import ur from '../locales/ur.json'
import { isolate, noteLine, notRankedKeys, policyLine, seasonSections, seasonStatusLine } from './growLogic'

type Ctx = CropPlanResponse['support_price_context']

function item(crop: CropPlanItem['crop'], season: CropPlanItem['season'], rank: number | null,
              issues: CropPlanItem['evidence_issues'] = [], notes: CropPlanItem['notes'] = []): CropPlanItem {
  return {
    crop, season, rank, evidence_issues: issues, notes, is_stale: issues.includes('STALE_PRICE'), is_frozen: false,
    latest_price: 100, latest_price_date: '2026-10-09', harvest_price_estimate: 110, harvest_price_low: 90,
    harvest_price_high: 130, months_ahead: 6, yield_maund_per_acre: 30, cost_per_acre: 1000, profit_per_acre: 2300,
    expected_profit: 23000, risk_level: 'MEDIUM', spread_pct: 40, n_years: 9, sowing_months: [6, 7],
    harvest_months: [10, 11], best_sell_month: null, best_sell_gain_pct: null, sell_at_harvest: false,
    sell_window_months: [], profit_per_acre_low: 1000, profit_per_acre_high: 3000,
  }
}

const RICE_NOTE = { id: 'RICE_WATER_BAHAWALPUR', source: 'Dawn', source_date: '2025-01-05', url: 'https://x' } as const

describe('What to Grow (F4)', () => {
  it('a stale crop shows no rank and says why (1)', () => {
    expect(notRankedKeys(item('cotton', 'KHARIF', 1))).toBeNull()
    expect(notRankedKeys(item('super_basmati', 'KHARIF', null, ['STALE_PRICE']))).toEqual(['grow.issues.STALE_PRICE'])
  })

  it('all stale, or too few comparable crops: the season says so instead of naming a winner (2, 4)', () => {
    const line = seasonStatusLine({ season: 'KHARIF', status: 'NOT_ENOUGH_CURRENT_EVIDENCE', n_crops: 2, n_comparable: 0 })
    expect(line).toEqual({ key: 'grow.seasonStatus.NOT_ENOUGH_CURRENT_EVIDENCE', params: { n: 2, comparable: 0 } })
    expect(en.grow.seasonStatus.NOT_ENOUGH_CURRENT_EVIDENCE).toMatch(/none is put first/)
  })

  it('crops are shown under their own season, never mixed (3)', () => {
    const plan = {
      seasons: [
        { season: 'RABI', status: 'TOO_FEW_CROPS', n_crops: 1, n_comparable: 1 },
        { season: 'KHARIF', status: 'RANKED', n_crops: 2, n_comparable: 2 },
      ] as CropPlanResponse['seasons'],
      items: [item('wheat', 'RABI', null), item('cotton', 'KHARIF', 1), item('irri', 'KHARIF', 2)],
    }
    const sections = seasonSections(plan)
    expect(sections.map((s) => [s.season, s.items.map((i) => i.crop)])).toEqual([
      ['RABI', ['wheat']],
      ['KHARIF', ['cotton', 'irri']],
    ])
    expect(sections[0].items[0].rank).toBeNull()
  })

  it('the rice water note renders only from the API note, with its source and the crop months (5)', () => {
    const months = (m: number) => en.months[String(m) as keyof typeof en.months]
    const line = noteLine(RICE_NOTE, item('irri', 'KHARIF', 2, [], [RICE_NOTE]), months, (d) => d)
    expect(line.key).toBe('grow.notes.RICE_WATER_BAHAWALPUR')
    expect(line.params.source).toBe(isolate('Dawn'))
    expect(line.params.sow).toBe(isolate(`${months(6)}–${months(7)}`))
    expect(item('cotton', 'KHARIF', 1).notes).toEqual([])   // no note unless the API scoped one to this crop
    for (const text of [en.grow.notes.RICE_WATER_BAHAWALPUR, ur.grow.notes.RICE_WATER_BAHAWALPUR]) {
      expect(text).toContain('{{source}}')
    }
    expect(en.grow.notes.RICE_WATER_BAHAWALPUR).toMatch(/not advice against rice/)
  })

  it('the wheat policy context is labelled as policy, not a price, and says when it is old or missing (6)', () => {
    const event = { date: '2026-01-21', tag: 'SUPPORT_PRICE', text_ur: 'اردو', text_en: 'Rs 3,500 indicative',
      source: 'Dunya News', url: 'https://x' } as const
    const old: Ctx = { state: 'OUTDATED', event, age_days: 109, max_age_days: 60 }
    expect(policyLine(old, 'en', (d) => d)).toEqual({
      key: 'grow.policy.OUTDATED',
      params: { text: isolate('Rs 3,500 indicative'), source: isolate('Dunya News'), date: isolate('2026-01-21') },
    })
    expect(policyLine({ ...old, state: 'CURRENT' }, 'ur', (d) => d).params.text).toBe(isolate('اردو'))
    expect(policyLine({ state: 'UNAVAILABLE', event: null, age_days: null, max_age_days: 60 }, 'en', (d) => d).key)
      .toBe('grow.policy.UNAVAILABLE')
    expect(en.grow.policy.limit).toMatch(/not a mandi price/)
    expect(en.grow.policy.limit).toMatch(/not a price you are guaranteed/)
    expect(ur.grow.policy.limit).toMatch(/منڈی کا ریٹ نہیں/)
    expect(ur.grow.policy.limit).toMatch(/گارنٹی/)
    expect(en.grow.policy.OUTDATED).toMatch(/may have changed/)
  })

  it('no "AI says grow X" language in the grow block', () => {
    const all = JSON.stringify(en.grow).toLowerCase()
    for (const banned of ['ai says', 'you should grow', 'best crop', 'recommended crop', 'guaranteed profit']) {
      expect(all).not.toContain(banned)
    }
  })
})

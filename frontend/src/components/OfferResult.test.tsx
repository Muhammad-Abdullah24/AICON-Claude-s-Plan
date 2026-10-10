/**
 * The offer check on Home: it comes first, its labels are neutral, a weak reference is never shown as a
 * strong verdict, and no "fair price" or "guaranteed" wording appears. Rendered to HTML on Node with
 * react-dom/server (no browser needed; effects and API calls do not run).
 */
import i18next from 'i18next'
import { renderToStaticMarkup } from 'react-dom/server'
import { I18nextProvider } from 'react-i18next'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import type { Meta } from '../api/client'
import { type AppState, AppStateContext } from '../appState'
import en from '../locales/en.json'
import ur from '../locales/ur.json'
import { Home } from '../pages/Home'
import { alternativeVerdict, assumptions, FORBIDDEN_WORDS, type OfferResult as Result, showNextSteps, side, tone } from '../lib/offer'
import { OfferResult } from './OfferResult'

function i18n(lng: 'en' | 'ur') {
  const inst = i18next.createInstance()
  void inst.init({ resources: { en: { translation: en }, ur: { translation: ur } }, lng, initAsync: false,
    interpolation: { escapeValue: false } })
  return inst
}

const NAMES: Record<string, string> = { bahawalpur: 'Bahawalpur', vehari: 'Vehari', rahim_yar_khan: 'Rahim Yar Khan' }
const mandiName = (id: string) => NAMES[id] ?? id

/** The real API answer for wheat at Bahawalpur on 10 Oct 2026, offer Rs 3,514 on 100 maund. */
function wheatBahawalpur(over: Partial<Result> = {}): Result {
  return {
    data_source: 'amis', is_synthetic: false, crop: 'wheat', mandi: 'bahawalpur', unit: '40kg',
    buyer_offer_price: 3514, offer_price_basis: 'GROSS_QUOTED', quantity_maund: 100,
    reference_price: 3820, reference_price_as_of: '2026-10-09', reference_range_low: 3820, reference_range_high: 3820,
    reference_days: 12, window_days: 14, is_stale: false, price_unchanged_since: null,
    reference_strength: 'LIMITED_SAME_PRICE', range_position: 'BELOW_REFERENCE_RANGE',
    result_status: 'REFERENCE_DATA_LIMITED', difference_vs_reference_per_maund: -306,
    total_difference_vs_reference: -30600, difference_vs_range_per_maund: -306, total_difference_vs_range: -30600,
    estimated_transport_cost: 0, estimated_commission: null,
    alternative_mandis: [
      { mandi: 'vehari', has_data: true, is_own_mandi: false, reference_price: 3475.2, prices_as_of: '2026-07-17', is_stale: true,
        price_unchanged_since: null, reference_days: 1, transport_cost: 165.1, net_after_transport: 3310.1,
        difference_vs_offer_per_maund: -203.9, difference_vs_offer_total: -20390, reference_strength: 'LIMITED_STALE',
        better_after_transport: null, higher_quote_not_better: false },
      { mandi: 'rahim_yar_khan', has_data: true, is_own_mandi: false, reference_price: 3475.2, prices_as_of: '2026-10-02', is_stale: false,
        price_unchanged_since: null, reference_days: 11, transport_cost: 291.2, net_after_transport: 3184,
        difference_vs_offer_per_maund: -330, difference_vs_offer_total: -33000,
        reference_strength: 'LIMITED_SAME_PRICE', better_after_transport: null, higher_quote_not_better: false },
    ],
    limitations: ['SAME_PRICE_ALL_WINDOW', 'COMMISSION_NOT_INCLUDED', 'TRANSPORT_IS_ESTIMATE',
      'QUALITY_GRADE_NOT_INCLUDED', 'BUYER_TERMS_NOT_INCLUDED'],
    offer_price: 3514, fair_low: 3820, fair_high: 3820, verdict: 'below', difference_per_maund: -306,
    difference_total: -30600, prices_as_of: '2026-10-09',
    ...over,
  }
}

const STRONG: Partial<Result> = { reference_strength: 'STRONG', reference_range_low: 3700, reference_range_high: 3900,
  limitations: ['COMMISSION_NOT_INCLUDED', 'QUALITY_GRADE_NOT_INCLUDED', 'BUYER_TERMS_NOT_INCLUDED'] }

function render(r: Result, lng: 'en' | 'ur' = 'en'): string {
  return renderToStaticMarkup(
    <I18nextProvider i18n={i18n(lng)}>
      <MemoryRouter>
        <OfferResult result={r} mandiName={mandiName} />
      </MemoryRouter>
    </I18nextProvider>,
  )
}

/** Visible text only (tags and the invisible number-isolation marks removed). */
function text(html: string): string {
  return html
    .replace(/<[^>]+>/g, ' ')
    .replace(/&#x27;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/[\u2066-\u2069]/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/\s+/g, ' ')
}

function headline(html: string): string | undefined {
  return html.match(/data-status="([A-Z_]+)"/)?.[1]
}

describe('display helpers', () => {
  it('map the API status and flags without judging anything themselves', () => {
    expect(tone(wheatBahawalpur())).toBe('limited')
    expect(side(-306)).toBe('below')
    expect(side(0)).toBe('equal')
    expect(assumptions(wheatBahawalpur())).toEqual(['COMMISSION_NOT_INCLUDED', 'TRANSPORT_IS_ESTIMATE',
      'QUALITY_GRADE_NOT_INCLUDED', 'BUYER_TERMS_NOT_INCLUDED'])
    expect(showNextSteps(wheatBahawalpur())).toBe(true)
    const [vehari] = wheatBahawalpur().alternative_mandis
    expect(alternativeVerdict(vehari)).toBe('unknown')
    expect(alternativeVerdict({ ...vehari, better_after_transport: true })).toBe('better')
    expect(alternativeVerdict({ ...vehari, better_after_transport: false, higher_quote_not_better: true })).toBe(
      'higherNotBetter',
    )
    expect(alternativeVerdict({ mandi: 'vehari', has_data: false, is_own_mandi: false })).toBe('noData')
  })
})

describe('offer result', () => {
  it.each([
    ['BELOW_REFERENCE_RANGE', 'Below the recent reference range'],
    ['WITHIN_REFERENCE_RANGE', 'Within the recent reference range'],
    ['ABOVE_REFERENCE_RANGE', 'Above the recent reference range'],
  ] as const)('a strong reference shows %s as a neutral label', (status, label) => {
    const html = render(wheatBahawalpur({ ...STRONG, result_status: status, range_position: status }))
    expect(headline(html)).toBe(status)
    expect(text(html)).toContain(label)
    expect(html).not.toContain('data-testid="offer-limited"')
  })

  it('wheat at Bahawalpur (one repeated price) shows the total but no strong verdict', () => {
    const html = render(wheatBahawalpur())
    const t = text(html)
    expect(headline(html)).toBe('REFERENCE_DATA_LIMITED')
    expect(t).toContain('Reference data is limited')
    expect(t).not.toContain('Below the recent reference range')
    expect(t).toContain('AMIS reported the same reference price on all 12 reported days.')
    expect(t).toContain(
      'The offer is Rs 306 below that reported reference, but FarmSight cannot treat this as a reliable market range.',
    )
    expect(t).toContain('−Rs 30,600')             // the total for the farmer's 100 maund is still shown
    expect(t).toContain('Buyer\'s offer Rs 3,514')
    expect(t).toContain('Latest reported mandi price Rs 3,820')
    expect(t).not.toContain('Compared with the nearest edge')   // no range claim on a weak reference
  })

  it('a limited result leads with the limit, then the numbers, then safe next steps', () => {
    const t = text(render(wheatBahawalpur()))
    const order = ['Reference data is limited', 'AMIS reported the same', 'Buyer\'s offer', 'Latest reported mandi price',
      'Difference on your 100 maund', 'Source: AMIS', 'Prices as of', 'What can you do now?',
      'What FarmSight cannot know', 'Not included, and assumptions']
    const at = order.map((s) => t.indexOf(s))
    expect(at.every((i) => i >= 0)).toBe(true)
    expect([...at].sort((a, b) => a - b)).toEqual(at)
  })

  it('a stale reference shows the old-price warning and is limited', () => {
    const t = text(render(wheatBahawalpur({ reference_strength: 'LIMITED_STALE', is_stale: true,
      reference_price_as_of: '2026-07-17', limitations: ['STALE_REFERENCE', 'QUALITY_GRADE_NOT_INCLUDED'] })))
    expect(t).toContain('Old price: last reported on 17 July 2026')
    expect(t).toContain('The latest reported price is from 17 July 2026, more than 8 weeks ago.')
    expect(t).toContain('Reference data is limited')
  })

  it('next steps for an offer below the reported prices are suggestions, not instructions', () => {
    const t = text(render(wheatBahawalpur()))
    expect(t).toContain('Ask the buyer how the price was set')
    expect(t).toContain('FarmSight cannot remove that constraint')
    expect(text(render(wheatBahawalpur({ ...STRONG, range_position: 'ABOVE_REFERENCE_RANGE',
      result_status: 'ABOVE_REFERENCE_RANGE' })))).not.toContain('Before you decide')
  })

  it('transport and commission are labelled estimates; the cannot-know panel is there', () => {
    const html = render(wheatBahawalpur({ estimated_commission: { pct: 2, per_maund: 70.28, total: 7028,
      source: 'farmer' } }))
    const t = text(html)
    expect(t).toContain('Transport costs are estimates from road distance, not quotes.')
    expect(t).toContain('Commission at the rate you entered (2%)')
    expect(t).toContain('not used in the comparison above')
    expect(html).toContain('data-badge="estimate"')
    for (const s of ['Crop quality, grade and moisture', "The buyer's terms", 'Whether a truck is available',
      'Credit you owe, or an urgent need for cash', 'Whether a buyer is really there']) expect(t).toContain(s)
  })

  it.each(['en', 'ur'] as const)('in %s every string resolves and no forbidden wording appears', (lng) => {
    for (const r of [wheatBahawalpur(), wheatBahawalpur({ ...STRONG, result_status: 'WITHIN_REFERENCE_RANGE',
      range_position: 'WITHIN_REFERENCE_RANGE' })]) {
      const t = text(render(r, lng))
      expect(t).not.toMatch(/\boffer\.[a-zA-Z]/)   // a missing translation would show its key
      for (const w of FORBIDDEN_WORDS) expect(t).not.toMatch(w)
    }
  })
})

describe('wording', () => {
  it('no fair, true or guaranteed price, and no accusations, anywhere in the offer or outlook strings', () => {
    for (const locale of [en, ur]) {
      const all = JSON.stringify({ offer: locale.offer, outlook: locale.outlook, app: locale.app, nav: locale.nav })
      for (const w of FORBIDDEN_WORDS) expect(all).not.toMatch(w)
      expect(all).not.toMatch(/\b(reject|accept)\b/i)
    }
    expect(JSON.stringify(ur)).not.toContain('مناسب حد')   // the old Urdu "fair range"
  })
})

describe('Home', () => {
  const meta = {
    crops: [{ id: 'wheat', name_en: 'Wheat', name_ur: 'گندم' }],
    mandis: [{ id: 'bahawalpur', name_en: 'Bahawalpur', name_ur: 'بہاولپور' }],
    series: [{ crop: 'wheat', mandi: 'bahawalpur' }],
  } as unknown as Meta
  const state = {
    meta, selection: { crop: 'wheat', mandi: 'bahawalpur' }, quantity: 100, farmer: null,
    setCrop: () => {}, setMandi: () => {}, setQuantity: () => {}, signIn: () => {}, signOut: () => {},
    setFarmer: () => {}, mandisFor: () => meta.mandis, series: () => undefined,
    name: (i: { name_en: string } | undefined) => i?.name_en ?? '', cropName: () => 'Wheat', mandiName,
    lastCheck: null, setLastCheck: () => {},
  } as unknown as AppState

  it('puts "Check a buyer\'s offer" first and the market outlook after it', () => {
    const html = renderToStaticMarkup(
      <I18nextProvider i18n={i18n('en')}>
        <AppStateContext.Provider value={state}>
          <MemoryRouter>
            <Home />
          </MemoryRouter>
        </AppStateContext.Provider>
      </I18nextProvider>,
    )
    const t = text(html)
    expect(t.trim().indexOf("Got a buyer's offer? Check it before you sell.")).toBe(0)
    expect(t.indexOf("Check a buyer's offer")).toBeLessThan(t.indexOf('Market outlook'))
    expect(t).toContain('Check my offer')
    expect(t).toContain('The buyer offered (Rs per maund, 40 kg)')
    expect(t).toContain('1 maund = 40 kg')
    expect(html).toContain('id="offer"')
    expect(t).toContain('No offer checked yet')            // first use: a clear empty state
    expect(t).not.toContain('What you should do')
  })
})

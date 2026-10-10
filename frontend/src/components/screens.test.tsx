/**
 * The redesigned screens: status badges from real fields only, every limited-data state, stale and frozen
 * warnings, real-versus-illustrative labels, the responsive shell, and the WhatsApp/SMS page rendering the API's
 * text as it is. Rendered to HTML on Node with react-dom/server (effects and API calls do not run).
 */
import i18next from 'i18next'
import type { ReactNode } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { I18nextProvider } from 'react-i18next'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import type { ChannelPreview, Meta, OfferCheckResponse } from '../api/client'
import { type AppState, AppStateContext, type LastCheck } from '../appState'
import en from '../locales/en.json'
import ur from '../locales/ur.json'
import { FORBIDDEN_WORDS } from '../lib/offer'
import { referenceBadge } from '../lib/status'
import { Channels, PreviewBody } from '../pages/Channels'
import { Compare } from '../pages/Compare'
import { DataLabel } from './DataLabel'
import { OfferResult } from './OfferResult'
import { AppShell } from './shell/AppShell'
import { StatusBadge } from './ui/StatusBadge'

function i18n(lng: 'en' | 'ur') {
  const inst = i18next.createInstance()
  void inst.init({ resources: { en: { translation: en }, ur: { translation: ur } }, lng, initAsync: false,
    interpolation: { escapeValue: false } })
  return inst
}

const NAMES: Record<string, string> = { bahawalpur: 'Bahawalpur', vehari: 'Vehari', rahim_yar_khan: 'Rahim Yar Khan' }
const mandiName = (id: string) => NAMES[id] ?? id
const meta = {
  crops: [{ id: 'wheat', name_en: 'Wheat', name_ur: 'گندم' }],
  mandis: Object.entries(NAMES).map(([id, n]) => ({ id, name_en: n, name_ur: n })),
  series: [{ crop: 'wheat', mandi: 'bahawalpur' }], prices_as_of: '2026-10-09', is_synthetic: false,
} as unknown as Meta

function stateWith(over: Partial<AppState> = {}): AppState {
  return {
    meta, selection: { crop: 'wheat', mandi: 'bahawalpur' }, quantity: 100, farmer: null, lastCheck: null,
    setLastCheck: () => {}, setCrop: () => {}, setMandi: () => {}, setQuantity: () => {}, signIn: () => {},
    signOut: () => {}, setFarmer: () => {}, mandisFor: () => meta.mandis, series: () => undefined,
    name: (i: { name_en: string } | undefined) => i?.name_en ?? '', cropName: () => 'Wheat', mandiName,
    ...over,
  } as unknown as AppState
}

function render(node: ReactNode, lng: 'en' | 'ur' = 'en', state: AppState = stateWith(), path = '/'): string {
  return renderToStaticMarkup(
    <I18nextProvider i18n={i18n(lng)}>
      <AppStateContext.Provider value={state}>
        <MemoryRouter initialEntries={[path]}>{node}</MemoryRouter>
      </AppStateContext.Provider>
    </I18nextProvider>,
  )
}

function text(html: string): string {
  return html
    .replace(/<[^>]+>/g, ' ')
    .replace(/&#x27;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/[⁦-⁩]/g, '')
    .replace(/ /g, ' ')
    .replace(/\s+/g, ' ')
}

/** The real wheat / Bahawalpur offer-check answer of 10 Oct 2026 (Rs 3,514 on 100 maund). */
function offer(over: Partial<OfferCheckResponse> = {}): OfferCheckResponse {
  return {
    data_source: 'amis', is_synthetic: false, crop: 'wheat', mandi: 'bahawalpur', unit: '40kg',
    buyer_offer_price: 3514, offer_price_basis: 'GROSS_QUOTED', quantity_maund: 100, reference_price: 3820,
    reference_price_as_of: '2026-10-09', reference_range_low: 3820, reference_range_high: 3820, reference_days: 12,
    window_days: 14, is_stale: false, price_unchanged_since: null, reference_strength: 'LIMITED_SAME_PRICE',
    range_position: 'BELOW_REFERENCE_RANGE', result_status: 'REFERENCE_DATA_LIMITED',
    difference_vs_reference_per_maund: -306, total_difference_vs_reference: -30600,
    difference_vs_range_per_maund: -306, total_difference_vs_range: -30600, estimated_transport_cost: 0,
    estimated_commission: null,
    alternative_mandis: [
      { mandi: 'bahawalpur', has_data: true, is_own_mandi: true, reference_price: 3820, prices_as_of: '2026-10-09',
        is_stale: false, price_unchanged_since: null, reference_days: 12, transport_cost: 0, net_after_transport: 3820,
        difference_vs_offer_per_maund: 306, difference_vs_offer_total: 30600, reference_strength: 'LIMITED_SAME_PRICE',
        better_after_transport: null, higher_quote_not_better: false },
      { mandi: 'vehari', has_data: true, is_own_mandi: false, reference_price: 3475.2, prices_as_of: '2026-07-17',
        is_stale: true, price_unchanged_since: null, reference_days: 1, transport_cost: 165.1,
        net_after_transport: 3310.1, difference_vs_offer_per_maund: -203.9, difference_vs_offer_total: -20390,
        reference_strength: 'LIMITED_STALE', better_after_transport: null, higher_quote_not_better: false },
      { mandi: 'rahim_yar_khan', has_data: false, is_own_mandi: false },
    ],
    limitations: ['SAME_PRICE_ALL_WINDOW', 'COMMISSION_NOT_INCLUDED', 'TRANSPORT_IS_ESTIMATE',
      'QUALITY_GRADE_NOT_INCLUDED', 'BUYER_TERMS_NOT_INCLUDED'],
    offer_price: 3514, fair_low: 3820, fair_high: 3820, verdict: 'below', difference_per_maund: -306,
    difference_total: -30600, prices_as_of: '2026-10-09',
    ...over,
  }
}

const check = (over: Partial<OfferCheckResponse> = {}): LastCheck => ({
  crop: 'wheat', mandi: 'bahawalpur', quantity: 100, offer: 3514, asOf: null, result: offer(over),
})

// ---------------------------------------------------------------- status badges

describe('status badges', () => {
  it.each([
    ['STRONG', 'fresh', 'Recent report'],
    ['LIMITED_STALE', 'stale', 'Old report'],
    ['LIMITED_FROZEN', 'frozen', 'Price not updated'],
    ['LIMITED_FEW_DAYS', 'fewDays', 'Few reports'],
    ['LIMITED_SAME_PRICE', 'samePrice', 'Same price reported'],
  ] as const)('%s maps to the %s badge, with an icon and a word', (strength, kind, word) => {
    expect(referenceBadge({ reference_strength: strength })).toBe(kind)
    const html = render(<StatusBadge kind={kind} />)
    expect(html).toContain(`data-badge="${kind}"`)
    expect(html).toContain('<svg')                     // never colour alone
    expect(text(html)).toContain(word)
  })

  it('without a strength, only the stale and frozen flags decide', () => {
    expect(referenceBadge({ is_stale: true })).toBe('stale')
    expect(referenceBadge({ price_unchanged_since: '2026-06-01' })).toBe('frozen')
    expect(referenceBadge({})).toBe('fresh')
  })
})

// ---------------------------------------------------------------- limited-data states

describe('limited reference states', () => {
  it.each([
    ['LIMITED_STALE', { is_stale: true, reference_price_as_of: '2026-07-17' }, 'Old price: last reported on 17 July 2026'],
    ['LIMITED_FROZEN', { price_unchanged_since: '2026-06-01' }, 'AMIS has shown the same price since 1 June 2026'],
    ['LIMITED_FEW_DAYS', { reference_days: 2 }, 'AMIS reported a price on only 2 of the last 14 days.'],
    ['LIMITED_SAME_PRICE', {}, 'AMIS reported the same reference price on all 12 reported days.'],
  ] as const)('%s leads with "Reference data is limited" and keeps the numbers', (strength, over, warning) => {
    const html = render(<OfferResult result={offer({ reference_strength: strength, ...over })} mandiName={mandiName} />)
    const t = text(html)
    expect(html).toContain('data-status="REFERENCE_DATA_LIMITED"')
    expect(t).toContain('Reference data is limited')
    expect(t).toContain(warning)
    expect(t).toContain('−Rs 30,600')
    expect(t).toContain('What can you do now?')
    expect(t).toContain('What FarmSight cannot know')
    expect(t).not.toMatch(/(Below|Within|Above) the recent reference range/)
  })

  it('a strong reference shows a neutral verdict and no limited card', () => {
    const html = render(<OfferResult result={offer({ reference_strength: 'STRONG', result_status: 'BELOW_REFERENCE_RANGE' })}
      mandiName={mandiName} />)
    expect(text(html)).toContain('Below the recent reference range')
    expect(html).not.toContain('data-testid="offer-limited"')
    expect(html).toContain('data-badge="fresh"')
  })
})

// ---------------------------------------------------------------- real versus illustrative

describe('data labels', () => {
  it('real data is labelled real, synthetic data is labelled synthetic, illustrative is never used for real data', () => {
    expect(text(render(<DataLabel isSynthetic={false} asOf="2026-10-09" />))).toContain('Real data')
    expect(text(render(<DataLabel isSynthetic asOf="2026-10-09" />))).toContain('Synthetic data')
    expect(render(<OfferResult result={offer()} mandiName={mandiName} />)).not.toContain('data-badge="illustrative"')
  })

  it('stale and frozen warnings are visible next to the price', () => {
    expect(text(render(<DataLabel isSynthetic={false} asOf="2026-07-17" stale />))).toContain('Old price')
    expect(text(render(<DataLabel isSynthetic={false} asOf="2026-10-09" unchangedSince="2026-06-01" />))).toContain(
      'AMIS has shown the same price since',
    )
  })
})

// ---------------------------------------------------------------- compare

describe('compare with the latest offer', () => {
  it('lists the own mandi first, labels weak references, and calls no weak mandi best', () => {
    const t = text(render(<Compare />, 'en', stateWith({ lastCheck: check() })))
    expect(t).toContain('buyer\'s offer Rs 3,514 per maund')
    expect(t).toContain('This is not necessarily the best mandi.')
    expect(t.indexOf('Bahawalpur (your mandi)')).toBeLessThan(t.indexOf('Vehari'))
    expect(t).toContain('Same price reported')
    expect(t).toContain('This price is old')
    expect(t).not.toContain('Highest estimated net price')
    expect(t).toContain('How is this calculated?')
    expect(t).toContain('Bahawalpur: (3820 − 3514) × 100')
    expect(t).toContain('No price data')
  })
})

// ---------------------------------------------------------------- the shell

describe('app shell', () => {
  it('renders the desktop sidebar and the mobile bottom bar, each hidden on the other size', () => {
    const html = render(<AppShell>content</AppShell>)
    expect(html).toMatch(/<aside[^>]*class="[^"]*hidden[^"]*lg:flex/)
    expect(html).toMatch(/<nav[^>]*class="[^"]*fixed[^"]*lg:hidden/)
    const t = text(html)
    for (const label of ['Check an offer', 'Compare mandis', 'Market outlook', 'Why / data details', 'WhatsApp / SMS',
      'Profile & alerts', 'Offer', 'Compare', 'Outlook', 'Profile']) expect(t).toContain(label)
  })

  it('shows the real data date, never a fixed demo label', () => {
    const t = text(render(<AppShell>x</AppShell>, 'en', stateWith({ meta: { ...meta, prices_as_of: '2025-03-24' } })))
    expect(t).toContain('AMIS prices up to 24 March 2025')
    expect(t).not.toContain('Demo workspace')
    expect(t).not.toContain('9 Oct 2026')
  })
})

// ---------------------------------------------------------------- WhatsApp / SMS page

describe('channels page', () => {
  const preview: ChannelPreview = {
    whatsapp_menu: 'MENU-FROM-API\n1  first', sms_menu: 'SMS-MENU-FROM-API', menu_choices: ['offer'],
    whatsapp_offer: 'WA-OFFER', whatsapp_offer_buttons: ['b'], sms_offer: 'SMS-OFFER-FROM-API', sms_offer_parts: 2,
    prices_as_of: '2026-10-09',
    status: { whatsapp_configured: false, sms_provider_configured: false, voice_notes_enabled: false },
  }

  it('shows the API text as it is and says SMS and voice are not live', () => {
    const html = render(<PreviewBody p={preview} />)
    const t = text(html)
    expect(html).toContain('MENU-FROM-API\n1  first')            // verbatim, line breaks kept
    expect(t).toContain('SMS-OFFER-FROM-API')
    expect(t).toContain('2 SMS part(s)')
    expect(t).toContain('SMS is not live yet: no SMS provider is connected.')
    expect(t).toContain('Voice notes are not available yet.')
    expect(t).toContain('WhatsApp is not connected on this server yet')
  })

  it('only claims what the status flags say', () => {
    const live = { ...preview, status: { whatsapp_configured: true, sms_provider_configured: true, voice_notes_enabled: true } }
    const t = text(render(<PreviewBody p={live} />))
    expect(t).toContain('This server is connected to WhatsApp.')
    expect(t).toContain('An SMS provider is connected.')
  })

  it('without an offer shows the SMS menu and asks for an offer first', () => {
    const t = text(render(<PreviewBody p={{ ...preview, sms_offer: null, sms_offer_parts: null }} />))
    expect(t).toContain('SMS-MENU-FROM-API')
    expect(t).toContain('Check an offer on the home screen')
  })

  it('loads from the API (no copied menu in the page)', () => {
    const t = text(render(<Channels />))
    expect(t).not.toContain('Check a buyer offer')   // nothing rendered until the API answers
  })
})

// ---------------------------------------------------------------- wording, everywhere

describe('user-facing wording', () => {
  function values(obj: object): string[] {
    return Object.values(obj).flatMap((v) => (v && typeof v === 'object' ? values(v) : [String(v)]))
  }

  it('no fair/true/guaranteed price, scam or exploitation wording in any English or Urdu string', () => {
    for (const s of [...values(en), ...values(ur)]) for (const w of FORBIDDEN_WORDS) expect(s, s).not.toMatch(w)
  })

  it('the Urdu strings never call the reference a fair price', () => {
    for (const s of values(ur)) expect(s).not.toMatch(/مناسب (حد|قیمت)|منصفانہ/)
  })
})

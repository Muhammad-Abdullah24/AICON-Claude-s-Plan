/**
 * Guards for the visual layer: status is never colour alone, tap targets stay large, and the reskinned navigation
 * still reaches every route the app defines (and no other).
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import { BOTTOM, MORE_ITEMS, MORE_PATH, NAV } from '../shell/nav'
import { buttonClass, cardClass, STATUS, type StatusKind } from './styles'

describe('visual primitives', () => {
  it('every data status carries an icon, so its meaning never rests on colour', () => {
    const needsIcon: StatusKind[] = ['fresh', 'limited', 'stale', 'frozen', 'estimate', 'synthetic']
    for (const kind of needsIcon) expect(STATUS[kind].icon, kind).not.toBeNull()
    // The cautions that matter most look different from each other by icon, not only by tint.
    const icons = new Set((['limited', 'stale', 'frozen'] as const).map((k) => STATUS[k].icon))
    expect(icons.size).toBe(3)
  })

  it('every button variant is at least 48px tall (NFR-05)', () => {
    for (const v of ['primary', 'outline', 'quiet'] as const) expect(buttonClass(v)).toContain('min-h-12')
  })

  it('a card never gets two competing border widths', () => {
    for (const tone of ['surface', 'highlight', 'quiet', 'caution', 'info', 'error', 'positive'] as const) {
      const widths = cardClass(tone).split(/\s+/).filter((c) => /^border(-\d)?$/.test(c))
      expect(widths, tone).toHaveLength(1)
    }
  })
})

describe('navigation', () => {
  it('reaches exactly the routes App.tsx defines, each once', () => {
    const app = readFileSync(join(import.meta.dirname, '..', '..', 'App.tsx'), 'utf8')
    const routes = [...app.matchAll(/<Route path="([^"*]+)"/g)].map((m) => m[1])
    // Every screen, plus the phone's "More" page that lists the screens not in the bottom bar.
    expect([...NAV.map((n) => n.to), MORE_PATH].sort()).toEqual([...routes].sort())
    expect(new Set(NAV.map((n) => n.to)).size).toBe(NAV.length)
  })

  it('every screen is in the bottom bar or on the "More" page', () => {
    const reachable = [...BOTTOM, ...MORE_ITEMS.map((n) => n.to)]
    expect(reachable.sort()).toEqual(NAV.map((n) => n.to).sort())
    expect(MORE_ITEMS.map((n) => n.key)).toEqual(['history', 'chat', 'profile'])
  })
})

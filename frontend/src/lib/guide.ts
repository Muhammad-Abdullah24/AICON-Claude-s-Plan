/** The first-visit guide (components/Guide.tsx) listens for this event; the header's "?" sends it. */
export const OPEN_GUIDE_EVENT = 'kasht:open-guide'

export function openGuide() {
  window.dispatchEvent(new Event(OPEN_GUIDE_EVENT))
}

import type { IconName } from '../ui/Icon'

export interface NavItem {
  to: string
  key: string
  icon: IconName
}

/** The app's eight existing screens, in their existing order. The shell only changes how they are reached. */
export const NAV: NavItem[] = [
  { to: '/', key: 'home', icon: 'home' },
  { to: '/loan', key: 'loan', icon: 'wallet' },
  { to: '/why', key: 'why', icon: 'why' },
  { to: '/compare', key: 'compare', icon: 'pin' },
  { to: '/grow', key: 'grow', icon: 'sprout' },
  { to: '/history', key: 'history', icon: 'trend' },
  { to: '/margin', key: 'margin', icon: 'receipt' },
  { to: '/chat', key: 'chat', icon: 'chat' },
  { to: '/profile', key: 'profile', icon: 'user' },
]

/** The phone's bottom bar (besides "More"); every other screen is listed on the "More" page, so none is lost. */
// The loan planner is a core screen, so it is in the bar; "Why" is one tap away from the Home answer.
export const BOTTOM: string[] = ['/', '/loan', '/compare', '/grow']

/** The "More" page: a list of the screens that are not in the phone's bottom bar. Navigation only. */
export const MORE_PATH = '/more'
export const MORE_ITEMS = NAV.filter((n) => !BOTTOM.includes(n.to))

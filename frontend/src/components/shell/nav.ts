import { FileSearch, MapPin, MessageSquare, Scale, Sprout, User, type LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  key: string             // nav.<key> (full label) and navShort.<key> (bottom bar)
  icon: LucideIcon
  primary: boolean        // in the mobile bottom bar (four places a farmer goes most)
}

/** One list for the desktop sidebar and the mobile bottom bar, so they never disagree. */
export const NAV: NavItem[] = [
  { to: '/', key: 'home', icon: Scale, primary: true },
  { to: '/compare', key: 'compare', icon: MapPin, primary: true },
  { to: '/outlook', key: 'outlook', icon: Sprout, primary: true },
  { to: '/why', key: 'why', icon: FileSearch, primary: false },
  { to: '/channels', key: 'channels', icon: MessageSquare, primary: false },
  { to: '/profile', key: 'profile', icon: User, primary: true },
]

/** Screens kept from before, reached from "More" (sidebar, and the outlook page on a phone). */
export const MORE = [
  { to: '/grow', key: 'grow' },
  { to: '/history', key: 'history' },
  { to: '/margin', key: 'margin' },
  { to: '/chat', key: 'chat' },
]

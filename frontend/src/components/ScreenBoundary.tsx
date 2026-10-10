import { Component, type ReactNode } from 'react'

import { ScreenError } from './Status'

/**
 * A screen that throws while rendering shows the usual error box with "try again" instead of a blank page. On demo
 * day a half-finished deploy (new web app, old API) blanked What to Grow; this keeps the rest of the app usable.
 * App gives it the page path as its key, so moving to another screen clears the error.
 */
export class ScreenBoundary extends Component<{ children: ReactNode }, { error: unknown }> {
  state = { error: null as unknown }

  static getDerivedStateFromError(error: unknown) {
    return { error }
  }

  render() {
    if (this.state.error !== null) {
      return <ScreenError onRetry={() => window.location.reload()} />
    }
    return this.props.children
  }
}

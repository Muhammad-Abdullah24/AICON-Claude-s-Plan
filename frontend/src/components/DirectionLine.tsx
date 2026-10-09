import { useTranslation } from 'react-i18next'

import type { DirectionCall } from '../api/client'

/**
 * Owner B's model's "likely up / likely down" call (wheat only, docs/MODEL_CARD.md). No price number: the model's
 * prices did not beat the baseline, only its direction did, so that is all it is allowed to say.
 */
export function DirectionLine({ direction }: { direction?: DirectionCall | null }) {
  const { t } = useTranslation()
  if (!direction) return null
  return (
    <p className="text-sm">
      <span aria-hidden className={`me-1 ${direction.call === 'UP' ? 'text-field' : 'text-madder'}`}>
        {direction.call === 'UP' ? '⬆' : '⬇'}
      </span>
      {t(`direction.${direction.call}`)}
      {direction.validation_accuracy_pct != null && (
        <span className="text-slate"> {t('direction.accuracy', { pct: Math.round(direction.validation_accuracy_pct) })}</span>
      )}
    </p>
  )
}

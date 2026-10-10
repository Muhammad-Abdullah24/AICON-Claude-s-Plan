import { useTranslation } from 'react-i18next'

import { api, type NewsItem, type PolicyEvent } from '../api/client'
import type { Lang } from '../i18n'
import { formatDate, formatRs } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import { Icon } from './ui/Icon'
import { Badge, Callout } from './ui/primitives'
import { cardClass } from './ui/styles'

/**
 * Market news and the policy timeline (docs/PIVOT.md F3). News never changes the advice (rule 8); it only informs.
 * A price conflict (news price far from AMIS) is shown first, then a few headlines, then government-policy events.
 * Every item carries its source, date and a link, so the farmer can check it.
 */
export function NewsBanner({ crop, mandi }: { crop: string; mandi: string }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const [news] = useAsync((signal) => api.news({ crop, mandi }, signal), `news|${crop}|${mandi}`)
  const [policy] = useAsync((signal) => api.policy(crop, signal), `policy|${crop}`)

  if (news.status !== 'ok') return null
  const { items, price_check: check, is_snapshot } = news.data
  const events = policy.status === 'ok' ? policy.data.events.slice(0, 3) : []
  if (items.length === 0 && events.length === 0 && !check) return null

  return (
    <section className={cardClass('surface', 'space-y-4')}>
      {check && (
        <Callout tone="caution" role="status">
          <p className="font-semibold">
            {t('news.conflict', {
              price: formatRs(check.news_price),
              amis: formatRs(check.amis_price),
              pct: Math.abs(Math.round(check.difference_pct)),
              source: check.news_source,
              date: formatDate(check.news_date, lang),
            })}
          </p>
        </Callout>
      )}

      {/* Headlines and policy are context, not the answer: one tappable line until the farmer wants them. */}
      <details className="group">
        <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 font-semibold text-field [&::-webkit-details-marker]:hidden">
          <span>{t('news.fold', { n: items.slice(0, 4).length + events.length })}</span>
          <Icon name="chevron" className="size-5 transition-transform group-open:rotate-180" />
        </summary>
        <div className="space-y-4 pt-2">
          {items.length > 0 && (
            <div className="space-y-3">
              <h2 className="flex flex-wrap items-center gap-2 text-lg font-bold">
                <Icon name="info" className="size-5 text-field" />
                {t('news.title')}
                {is_snapshot && <Badge kind="stale">{t('news.snapshot')}</Badge>}
              </h2>
              <ul className="divide-y divide-line">
                {items.slice(0, 4).map((it) => (
                  <Item key={it.url} item={it} lang={lang} />
                ))}
              </ul>
            </div>
          )}

          {events.length > 0 && (
            <div className="space-y-3 border-t border-line pt-4">
              <h2 className="flex items-center gap-2 text-lg font-bold">
                <Icon name="receipt" className="size-5 text-field" />
                {t('news.policy')}
              </h2>
              {events.map((e) => (
                <Policy key={e.url + e.date} event={e} lang={lang} />
              ))}
            </div>
          )}
        </div>
      </details>
    </section>
  )
}

function Tag({ tag }: { tag: string }) {
  const { t } = useTranslation()
  return <Badge kind="neutral">{t(`news.tag.${tag}`)}</Badge>
}

function Item({ item, lang }: { item: NewsItem; lang: Lang }) {
  const { t } = useTranslation()
  return (
    <li className="space-y-1 py-2.5 text-sm">
      <a
        href={item.url}
        target="_blank"
        rel="noreferrer"
        className="font-semibold text-ink underline decoration-line underline-offset-4 hover:decoration-field"
      >
        {lang === 'en' ? item.summary_en : item.summary_ur}
      </a>
      <p className="flex flex-wrap items-center gap-2 text-slate">
        <Tag tag={item.tag} /> {t('news.byline', { source: item.source, date: formatDate(item.published, lang) })}
      </p>
    </li>
  )
}

function Policy({ event, lang }: { event: PolicyEvent; lang: Lang }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-1 border-s-2 border-line ps-3 text-sm">
      <Tag tag={event.tag} />
      <p>
        <a
          href={event.url}
          target="_blank"
          rel="noreferrer"
          className="text-ink underline decoration-line underline-offset-4 hover:decoration-field"
        >
          {lang === 'en' ? event.text_en : event.text_ur}
        </a>
      </p>
      <p className="text-slate">{t('news.byline', { source: event.source, date: formatDate(event.date, lang) })}</p>
    </div>
  )
}

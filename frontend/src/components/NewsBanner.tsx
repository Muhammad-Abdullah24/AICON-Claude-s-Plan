import { useTranslation } from 'react-i18next'

import { api, type NewsItem, type PolicyEvent } from '../api/client'
import type { Lang } from '../i18n'
import { formatDate, formatRs } from '../lib/format'
import { useAsync } from '../lib/useAsync'

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
    <section className="space-y-3 rounded-2xl border border-line bg-paper p-4">
      {check && (
        <p className="rounded-lg bg-madder/10 px-3 py-2 text-sm font-medium text-madder">
          {t('news.conflict', {
            price: formatRs(check.news_price),
            amis: formatRs(check.amis_price),
            pct: Math.abs(Math.round(check.difference_pct)),
            source: check.news_source,
            date: formatDate(check.news_date, lang),
          })}
        </p>
      )}

      {items.length > 0 && (
        <div className="space-y-2">
          <h2 className="flex items-baseline gap-2 text-sm font-bold">
            {t('news.title')}
            {is_snapshot && <span className="text-xs font-normal text-slate">({t('news.snapshot')})</span>}
          </h2>
          {items.slice(0, 4).map((it) => (
            <Item key={it.url} item={it} lang={lang} />
          ))}
        </div>
      )}

      {events.length > 0 && (
        <div className="space-y-2 border-t border-line pt-2">
          <h2 className="text-sm font-bold">{t('news.policy')}</h2>
          {events.map((e) => (
            <Policy key={e.url + e.date} event={e} lang={lang} />
          ))}
        </div>
      )}
    </section>
  )
}

function Tag({ tag }: { tag: string }) {
  const { t } = useTranslation()
  return <span className="rounded bg-line px-1.5 text-xs text-slate">{t(`news.tag.${tag}`)}</span>
}

function Item({ item, lang }: { item: NewsItem; lang: Lang }) {
  const { t } = useTranslation()
  return (
    <div className="text-sm">
      <a href={item.url} target="_blank" rel="noreferrer" className="font-medium underline">
        {lang === 'en' ? item.summary_en : item.summary_ur}
      </a>
      <span className="ms-2 text-xs text-slate">
        <Tag tag={item.tag} /> {t('news.byline', { source: item.source, date: formatDate(item.published, lang) })}
      </span>
    </div>
  )
}

function Policy({ event, lang }: { event: PolicyEvent; lang: Lang }) {
  const { t } = useTranslation()
  return (
    <div className="text-sm">
      <Tag tag={event.tag} />{' '}
      <a href={event.url} target="_blank" rel="noreferrer" className="underline">
        {lang === 'en' ? event.text_en : event.text_ur}
      </a>
      <span className="ms-1 text-xs text-slate">· {t('news.byline', { source: event.source, date: formatDate(event.date, lang) })}</span>
    </div>
  )
}

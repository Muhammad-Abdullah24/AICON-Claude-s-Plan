import { CheckCircle2, ListOrdered, MessageSquare, Mic, Phone, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type ChannelPreview } from '../api/client'
import { useAppState } from '../appState'
import { ErrorBox, Loading } from '../components/Status'
import { Note } from '../components/ui/Disclosure'
import type { Lang } from '../i18n'
import { formatDate } from '../lib/format'
import { useAsync } from '../lib/useAsync'

/** A chat bubble. Text keeps its own line breaks, exactly as the channel sends it. */
function Bubble({ from, children, lang }: { from: 'farmer' | 'farmsight'; children: ReactNode; lang?: string }) {
  const farmer = from === 'farmer'
  return (
    <div className={`flex ${farmer ? 'justify-start' : 'justify-end'}`}>
      <div
        lang={lang}
        className={`max-w-[90%] rounded-[var(--radius-card)] px-4 py-3 text-sm whitespace-pre-line ${
          farmer ? 'figures bg-field-soft text-lg' : 'border border-line bg-paper'
        }`}
      >
        {!farmer && <p className="mb-1 text-xs font-bold text-field">FarmSight</p>}
        {children}
      </div>
    </div>
  )
}

function StatusLine({ ok, children }: { ok: boolean; children: ReactNode }) {
  const Icon = ok ? CheckCircle2 : XCircle
  return (
    <li className="flex items-start gap-2">
      <Icon aria-hidden className={`mt-0.5 size-5 shrink-0 ${ok ? 'text-field' : 'text-slate'}`} />
      <span>{children}</span>
    </li>
  )
}

/** The page body for a preview from the API (exported for tests). */
export function PreviewBody({ p }: { p: ChannelPreview }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const s = p.status
  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <section className="space-y-3" aria-labelledby="wa-title">
        <h2 id="wa-title" className="text-xl font-bold">{t('channels.whatsappTitle')}</h2>
        <div className="mx-auto max-w-sm rounded-[2rem] border-8 border-ink bg-cotton p-4 shadow-sm" data-testid="phone">
          <p className="flex items-center justify-between border-b border-line pb-2 font-semibold">
            <span lang="en">FarmSight · WhatsApp</span>
            <MessageSquare aria-hidden className="size-5" />
          </p>
          <p className="py-2 text-xs text-slate">{t('channels.realText')}</p>
          <div className="space-y-3">
            <Bubble from="farmer">0</Bubble>
            <Bubble from="farmsight" lang="ur">
              <span data-testid="wa-menu">{p.whatsapp_menu}</span>
            </Bubble>
          </div>
        </div>
      </section>
      <div className="space-y-4">
        <section className="card space-y-3 p-5" aria-labelledby="sms-title">
          <h2 id="sms-title" className="text-xl font-bold">{t(p.sms_offer ? 'channels.smsOfferTitle' : 'channels.smsMenuTitle')}</h2>
          <div className="rounded-[var(--radius-control)] border border-line bg-paper p-4 text-sm" lang="en" dir="ltr"
            data-testid="sms-text">
            <p className="mb-1 text-xs font-bold text-field">FarmSight</p>
            {p.sms_offer ?? p.sms_menu}
          </div>
          {p.sms_offer && p.sms_offer_parts != null && (
            <p className="text-xs text-slate">{t('channels.smsParts', { parts: p.sms_offer_parts })}</p>
          )}
          {p.prices_as_of && (
            <p className="text-xs text-slate">
              {t('data.sourceShort')} · {formatDate(p.prices_as_of, lang)} · {t('channels.notAPromise')}
            </p>
          )}
          {!p.sms_offer && <Note>{t('channels.checkOfferFirst')}</Note>}
        </section>
        <section className="space-y-3 rounded-[var(--radius-card)] border border-line bg-field-soft p-5"
          aria-labelledby="status-title">
          <h2 id="status-title" className="flex items-center gap-2 text-lg font-bold">
            <ListOrdered aria-hidden className="size-5 text-field" />
            {t('channels.statusTitle')}
          </h2>
          <ul className="space-y-2 text-sm" data-testid="channel-status">
            <StatusLine ok={true}>{t('channels.menuWorks')}</StatusLine>
            <StatusLine ok={s.whatsapp_configured}>
              {t(s.whatsapp_configured ? 'channels.waConnected' : 'channels.waNotConnected')}
            </StatusLine>
            <StatusLine ok={s.sms_provider_configured}>
              {t(s.sms_provider_configured ? 'channels.smsLive' : 'channels.smsNotLive')}
            </StatusLine>
            <StatusLine ok={s.voice_notes_enabled}>
              <span className="inline-flex items-center gap-1">
                <Mic aria-hidden className="size-4" />
                {t(s.voice_notes_enabled ? 'channels.voiceOn' : 'channels.voiceOff')}
              </span>
            </StatusLine>
          </ul>
          <p className="flex items-start gap-2 text-sm">
            <Phone aria-hidden className="mt-0.5 size-4 shrink-0" />
            {t('channels.freeText')}
          </p>
        </section>
      </div>
    </div>
  )
}

/**
 * FarmSight on WhatsApp and SMS: the numbered text menu and an offer reply, as the channel code renders them
 * (GET /api/channels/preview), with honest status: which channels this server has, and that voice is not on.
 */
export function Channels() {
  const { t } = useTranslation()
  const { selection, quantity, lastCheck } = useAppState()
  const check = lastCheck && lastCheck.crop === selection.crop && lastCheck.mandi === selection.mandi ? lastCheck : null
  const qty = check ? check.quantity : quantity
  const offer = check ? check.offer : null
  const [preview, reload] = useAsync(
    (signal) => api.channelsPreview({ ...selection, quantity_maund: qty, offer_price: offer }, signal),
    `${selection.crop}|${selection.mandi}|${qty}|${offer}`,
  )
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold lg:text-3xl">{t('channels.title')}</h1>
        <p className="text-slate">{t('channels.subtitle')}</p>
      </header>
      {preview.status === 'loading' && <Loading />}
      {preview.status === 'error' && <ErrorBox error={preview.error} onRetry={reload} />}
      {preview.status === 'ok' && <PreviewBody p={preview.data} />}
    </div>
  )
}

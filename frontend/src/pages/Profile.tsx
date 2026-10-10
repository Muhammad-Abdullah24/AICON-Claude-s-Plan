import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api, ApiError, type CropId, type MandiId } from '../api/client'
import { useAppState } from '../appState'
import { ChipGroup } from '../components/ChipGroup'
import { ErrorBox } from '../components/Status'
import { Note, Toggle } from '../components/ui/Disclosure'
import { parseTypedNumber } from '../lib/format'

const input = 'w-full rounded-xl border-2 border-line bg-paper px-3 py-2 focus:border-ink focus:outline-none'

/** Phone login (no OTP in the MVP; blueprint decision 10), registration, and the alerts switch. */
export function Profile() {
  const { t } = useTranslation()
  const { farmer } = useAppState()
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold lg:text-3xl">{t('profile.title')}</h1>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        {farmer ? <Signed /> : <Guest />}
        <AlertsCard />
      </div>
    </div>
  )
}

function Signed() {
  const { t } = useTranslation()
  const { farmer, setFarmer, signOut } = useAppState()
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<unknown>(null)
  if (!farmer) return null

  function toggleAlerts(enabled: boolean) {
    setSaved(false)
    api.updateMe({ alerts_enabled: enabled }).then((f) => {
      setFarmer(f)
      setSaved(true)
    }, setError)
  }

  return (
    <section className="card space-y-3 p-5">
      <p className="font-bold">{t('profile.loggedInAs', { name: farmer.name })}</p>
      <p className="figures text-sm text-slate">{farmer.phone}</p>
      <Toggle
        label={t(farmer.alerts_enabled ? 'profile.alertsOn' : 'profile.alertsOff')}
        checked={farmer.alerts_enabled}
        onChange={toggleAlerts}
      />
      {saved && <p className="text-sm text-field">{t('profile.saved')}</p>}
      {error !== null && <ErrorBox error={error} />}
      <button type="button" onClick={signOut} className="rounded-xl border-2 border-ink px-4 py-2">
        {t('profile.logout')}
      </button>
    </section>
  )
}

/** Price alerts: opt-in, at most one a week, information only. A guest is told what is needed. */
function AlertsCard() {
  const { t } = useTranslation()
  const { farmer } = useAppState()
  return (
    <section className="card space-y-3 p-5" aria-labelledby="alerts-title">
      <h2 id="alerts-title" className="text-lg font-bold">{t('profile.alertsTitle')}</h2>
      {!farmer && (
        <Toggle label={t('profile.alertsOff')} checked={false} onChange={() => {}} disabled />
      )}
      <p className="text-sm text-slate">{t(farmer ? 'profile.alertsHelp' : 'profile.alertsNeedProfile')}</p>
      <Note>{t('profile.alertsNotPromise')}</Note>
    </section>
  )
}

function Guest() {
  const { t, i18n } = useTranslation()
  const { meta, name, signIn, selection, quantity } = useAppState()
  const [phone, setPhone] = useState('')
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [reg, setReg] = useState({ name: '', phone: '', district: selection.mandi, land: '', arhti: '' })
  const [exists, setExists] = useState(false)

  function login(e: FormEvent) {
    e.preventDefault()
    setNotFound(false)
    setError(null)
    api.login(phone).then(
      (r) => signIn(r.token, r.farmer),
      (err: unknown) => (err instanceof ApiError && err.status === 404 ? setNotFound(true) : setError(err)),
    )
  }

  function register(e: FormEvent) {
    e.preventDefault()
    setExists(false)
    setError(null)
    api
      .register({
        name: reg.name,
        phone: reg.phone,
        language: i18n.language === 'en' ? 'en' : 'ur',
        alerts_enabled: false, // opt-in: turned on afterwards with the alerts switch on this page
        district: reg.district as MandiId,
        land_area_acres: parseTypedNumber(reg.land),
        arhti_commission_pct: reg.arhti === '' ? null : parseTypedNumber(reg.arhti),
        crops: [{ crop: selection.crop as CropId, preferred_mandi: selection.mandi as MandiId, harvest_quantity_maund: quantity }],
      })
      .then(
        (r) => signIn(r.token, r.farmer),
        (err: unknown) => (err instanceof ApiError && err.status === 409 ? setExists(true) : setError(err)),
      )
  }

  return (
    <>
      <p className="text-slate">{t('profile.guest')}</p>
      <form onSubmit={login} className="space-y-2 card p-5">
        <label htmlFor="login-phone" className="block font-bold">{t('profile.login')}</label>
        <input id="login-phone" inputMode="tel" dir="ltr" value={phone} onChange={(e) => setPhone(e.target.value)}
          placeholder="+92…" className={`${input} figures`} />
        <p className="text-xs text-slate">{t('profile.demoHint')}</p>
        {notFound && <p className="text-sm text-madder">{t('profile.notFound')}</p>}
        <button type="submit" disabled={phone.length < 7} className="rounded-xl bg-ink px-4 py-2 text-cotton disabled:opacity-50">
          {t('profile.loginButton')}
        </button>
      </form>

      <form onSubmit={register} className="space-y-3 card p-5">
        <p className="font-bold">{t('profile.register')}</p>
        <label className="block text-sm text-slate">{t('profile.name')}
          <input value={reg.name} onChange={(e) => setReg({ ...reg, name: e.target.value })} className={`${input} mt-1`} />
        </label>
        <label className="block text-sm text-slate">{t('profile.phone')}
          <input inputMode="tel" dir="ltr" value={reg.phone} onChange={(e) => setReg({ ...reg, phone: e.target.value })}
            placeholder="+92…" className={`${input} figures mt-1`} />
        </label>
        <ChipGroup label={t('profile.district')} options={meta.mandis.map((m) => ({ value: m.id, label: name(m) }))}
          value={reg.district} onChange={(v) => setReg({ ...reg, district: v })} />
        <label className="block text-sm text-slate">{t('profile.land')}
          <input inputMode="decimal" value={reg.land} onChange={(e) => setReg({ ...reg, land: e.target.value })} className={`${input} figures mt-1`} />
        </label>
        <label className="block text-sm text-slate">{t('profile.arhti')}
          <input inputMode="decimal" value={reg.arhti} onChange={(e) => setReg({ ...reg, arhti: e.target.value })} className={`${input} figures mt-1`} />
        </label>
        {exists && <p className="text-sm text-madder">{t('profile.exists')}</p>}
        <button type="submit" disabled={!reg.name || reg.phone.length < 7}
          className="rounded-xl bg-wheat px-4 py-2 font-bold text-ink disabled:opacity-50">
          {t('profile.create')}
        </button>
      </form>
      {error !== null && <ErrorBox error={error} />}
    </>
  )
}

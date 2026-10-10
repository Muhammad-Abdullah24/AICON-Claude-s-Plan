import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api, ApiError, type CropId, type MandiId } from '../api/client'
import { useAppState } from '../appState'
import { ChipGroup } from '../components/ChipGroup'
import { ErrorBox } from '../components/Status'
import { buttonClass, inputClass, labelClass } from '../components/ui/styles'
import { parseTypedNumber } from '../lib/format'

const input = `${inputClass} w-full`

/** Phone login (no OTP in the MVP; blueprint decision 10), registration, and the alerts switch. */
export function Profile() {
  const { t } = useTranslation()
  const { farmer } = useAppState()
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{t('profile.title')}</h2>
      {farmer ? <Signed /> : <Guest />}
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
    <section className="space-y-4 rounded-2xl border border-line bg-paper p-5 shadow-(--shadow-card) sm:p-6">
      <p className="font-bold">{t('profile.loggedInAs', { name: farmer.name })}</p>
      <p className="figures text-sm text-slate">{farmer.phone}</p>
      <label className="flex min-h-12 items-center gap-3 rounded-xl border border-line bg-cotton px-4">
        <input type="checkbox" checked={farmer.alerts_enabled} onChange={(e) => toggleAlerts(e.target.checked)} className="size-5 accent-field" />
        {t('profile.alerts')}
      </label>
      {saved && <p className="text-sm text-field">{t('profile.saved')}</p>}
      {error !== null && <ErrorBox error={error} />}
      <button type="button" onClick={signOut} className={buttonClass('outline')}>
        {t('profile.logout')}
      </button>
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
        alerts_enabled: true,
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
      <form onSubmit={login} className="space-y-3 rounded-2xl border border-line bg-paper p-5 shadow-(--shadow-card) sm:p-6">
        <label htmlFor="login-phone" className="block text-xl font-bold">{t('profile.login')}</label>
        <input id="login-phone" inputMode="tel" dir="ltr" value={phone} onChange={(e) => setPhone(e.target.value)}
          placeholder="+92…" className={`${input} figures`} />
        <p className="text-sm text-slate">{t('profile.demoHint')}</p>
        {notFound && <p className="text-sm text-madder">{t('profile.notFound')}</p>}
        <button type="submit" disabled={phone.length < 7} className={buttonClass('primary')}>
          {t('profile.loginButton')}
        </button>
      </form>

      <form onSubmit={register} className="space-y-4 rounded-2xl border border-line bg-paper p-5 shadow-(--shadow-card) sm:p-6">
        <p className="text-xl font-bold">{t('profile.register')}</p>
        <label className={labelClass}>{t('profile.name')}
          <input value={reg.name} onChange={(e) => setReg({ ...reg, name: e.target.value })} className={`${input} mt-1`} />
        </label>
        <label className={labelClass}>{t('profile.phone')}
          <input inputMode="tel" dir="ltr" value={reg.phone} onChange={(e) => setReg({ ...reg, phone: e.target.value })}
            placeholder="+92…" className={`${input} figures mt-1`} />
        </label>
        <ChipGroup label={t('profile.district')} options={meta.mandis.map((m) => ({ value: m.id, label: name(m) }))}
          value={reg.district} onChange={(v) => setReg({ ...reg, district: v })} />
        <label className={labelClass}>{t('profile.land')}
          <input inputMode="decimal" value={reg.land} onChange={(e) => setReg({ ...reg, land: e.target.value })} className={`${input} figures mt-1`} />
        </label>
        <label className={labelClass}>{t('profile.arhti')}
          <input inputMode="decimal" value={reg.arhti} onChange={(e) => setReg({ ...reg, arhti: e.target.value })} className={`${input} figures mt-1`} />
        </label>
        {exists && <p className="text-sm text-madder">{t('profile.exists')}</p>}
        <button type="submit" disabled={!reg.name || reg.phone.length < 7}
          className={buttonClass('outline')}>
          {t('profile.create')}
        </button>
      </form>
      {error !== null && <ErrorBox error={error} />}
    </>
  )
}

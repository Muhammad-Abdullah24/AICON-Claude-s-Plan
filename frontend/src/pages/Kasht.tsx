import { useEffect, useRef, useState } from 'react'

/**
 * KASHT — a WhatsApp-style voice-note demo of the FarmSight assistant (docs/PIVOT.md).
 *
 * A single chat with "KASHT". The farmer records a voice note (live, on stage); KASHT answers with a
 * pre-recorded voice note (the team's own voice, reading the scripted replies below). The replies play in a
 * fixed order and the whole conversation resets every time the page opens.
 *
 * This page is deliberately self-contained: no backend call, no API, no network. It is a pure front-end
 * playback of recorded audio, so it works on the deployed link and can never fail on stage. The reply audio
 * lives in public/kasht/reply-1.mp3 ... reply-3.mp3 (recorded by the team).
 */

type Turn = { q: string; a: string; dur: string }

// The three scripted turns asked on stage. `q` is what the farmer says (recorded live); `a` is KASHT's answer (pre-recorded
// mp3). Numbers are the real engine's output (wheat/Vehari/Bahawalpur, 10 Oct 2026 data).
const TURNS: Turn[] = [
  {
    q: 'السلام علیکم، میرے پاس ایک ایکڑ زمین ہے اور ایک ہفتے میں گندم کی فصل تیار ہو جائے گی۔ اگلے ہفتے کیا ریٹ مل سکتا ہے؟ میں فصل روک بھی سکتا ہوں۔ اور بتائیں کہ کہاں بیچوں؟ میں وہاڑی میں ہوں۔',
    a: 'وعلیکم السلام! وہاڑی میں گندم کا ریٹ اس وقت تقریباً Rs 3,475 فی من ہے، مگر یہ کچھ پرانا ہے۔ سب سے اہم بات: بہاولپور کی منڈی میں آج گندم Rs 3,820 فی من ہے — کرایہ نکال کر بھی آپ کو تقریباً Rs 3,655 فی من ملیں گے، یعنی ایک ایکڑ (31 من) پر وہاڑی کے مقابلے میں تقریباً Rs 5,500 زیادہ۔ اس لیے بہاولپور بیچنا بہتر ہے۔ اگر پیسوں کی فوری ضرورت نہیں اور گودام ہے تو روکنا بھی ٹھیک — پچھلے 7 میں سے 4 سال روکنے سے فائدہ ہوا۔ یہ اندازہ ہے، گارنٹی نہیں۔',
    dur: '0:43',
  },
  {
    q: 'میں تین ایکڑ پر گندم کاشت کرنے والا ہوں۔ میرے پاس پچاس ہزار روپے ہیں اور سوچ رہا تھا کہ آڑھتی سے چار لاکھ اُدھار لے لوں۔ بتائیں مجھے کتنا قرض چاہیے اور کہاں سے لوں؟',
    a: 'تین ایکڑ گندم کا اصل خرچ تقریباً Rs 2,52,000 ہے۔ آپ کے پاس پچاس ہزار ہیں، تو صرف Rs 2,02,000 قرض چاہیے — چار لاکھ نہیں! سب سے سستا طریقہ: کسان کارڈ سے Rs 90,000 بلا سود، اخوت سے Rs 50,000 بلا سود، اور بینک سے Rs 62,000 تقریباً Rs 5,100 سود پر۔ کٹائی پر کل واپسی تقریباً Rs 2,07,000۔ اگر آپ آڑھتی سے چار لاکھ لیتے تو اکیلے سود ہی Rs 1,32,000 بنتا — یعنی تقریباً Rs 1,27,000 زیادہ۔ اس لیے ضرورت سے زیادہ قرض مت لیں۔',
    dur: '0:32',
  },
  {
    q: 'میں بہاولپور میں ہوں، میرے پاس دو ایکڑ زمین ہے۔ اس سیزن میں کون سی فصل لگانا سب سے زیادہ فائدہ مند رہے گا؟',
    a: 'بہاولپور کے اعداد و شمار کے مطابق اس سیزن میں کپاس (پھٹی) سب سے زیادہ منافع بخش لگتی ہے — تقریباً Rs 76,484 فی ایکڑ، یعنی دو ایکڑ پر تقریباً Rs 1,52,000۔ اس کے بعد چاول (اری) ہے، مگر اس کا خطرہ زیادہ ہے اور بہاولپور میں نہری پانی کی کمی کا بھی خیال رکھیں۔ گندم اس وقت مشکل سے لاگت پوری کر رہی ہے۔ یہ اندازہ ہے، گارنٹی نہیں۔',
    dur: '0:35',
  },
]

type Msg = { side: 'me' | 'kasht'; audio: string | null; text: string; dur: string; time: string }

function clock(): string {
  return new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

/** One voice-note bubble: play/pause, a static waveform that fills as it plays, duration, time and ticks. */
function Voice({ m }: { m: Msg }) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [pct, setPct] = useState(0)
  const [showText, setShowText] = useState(false)
  const [bars] = useState<number[]>(() => Array.from({ length: 34 }, () => 25 + Math.round(Math.random() * 60)))

  function toggle() {
    const el = audioRef.current
    if (!el || !m.audio) return
    if (playing) {
      el.pause()
    } else {
      el.play().catch(() => setPlaying(false))
    }
  }

  const mine = m.side === 'me'
  return (
    <div className={`kasht-row ${mine ? 'me' : 'them'}`}>
      <div className={`kasht-bub ${mine ? 'bub-me' : 'bub-them'}`}>
        <div className="kasht-voice">
          {!mine && <div className="kasht-ava sm">🌾</div>}
          <button className="kasht-play" onClick={toggle} aria-label="play">
            {playing ? '❚❚' : '▶'}
          </button>
          <div className="kasht-wave" onClick={toggle}>
            {bars.map((h, i) => (
              <span key={i} style={{ height: `${h}%`, opacity: (i / bars.length) * 100 <= pct ? 1 : 0.35 }} />
            ))}
          </div>
          <span className="kasht-dur">{playing ? '…' : m.dur}</span>
        </div>
        <div className="kasht-meta">
          <button className="kasht-cc" onClick={() => setShowText((s) => !s)}>
            {showText ? 'متن چھپائیں' : 'متن دیکھیں'}
          </button>
          <span className="kasht-time">
            {m.time}
            {mine && <span className="kasht-tick"> ✓✓</span>}
          </span>
        </div>
        {showText && <p className="kasht-text">{m.text}</p>}
        {m.audio && (
          <audio
            ref={audioRef}
            src={m.audio}
            preload="none"
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => {
              setPlaying(false)
              setPct(0)
            }}
            onTimeUpdate={(e) => {
              const el = e.currentTarget
              if (el.duration) setPct((el.currentTime / el.duration) * 100)
            }}
          />
        )}
      </div>
    </div>
  )
}

export function Kasht() {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [step, setStep] = useState(0)
  const [recording, setRecording] = useState(false)
  const [secs, setSecs] = useState(0)
  const [waiting, setWaiting] = useState(false)
  const recRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const endRef = useRef<HTMLDivElement | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Opening the page is a full load (the entry is a plain link), so msgs/step start empty — a fresh conversation
  // every time. This effect only clears the recording timer on unmount.
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs, waiting])

  function send(audio: string | null) {
    if (step >= TURNS.length || waiting) return
    const turn = TURNS[step]
    setMsgs((m) => [...m, { side: 'me', audio, text: turn.q, dur: '0:0' + (6 + (step % 3)), time: clock() }])
    setWaiting(true)
    window.setTimeout(() => {
      setMsgs((m) => [
        ...m,
        { side: 'kasht', audio: `/kasht/reply-${step + 1}.mp3`, text: turn.a, dur: turn.dur, time: clock() },
      ])
      setWaiting(false)
      setStep((s) => s + 1)
    }, 1600)
  }

  async function startRec() {
    if (step >= TURNS.length || waiting) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream)
      chunksRef.current = []
      rec.ondataavailable = (e) => chunksRef.current.push(e.data)
      rec.onstop = () => {
        const url = chunksRef.current.length ? URL.createObjectURL(new Blob(chunksRef.current)) : null
        stream.getTracks().forEach((t) => t.stop())
        send(url)
      }
      recRef.current = rec
      rec.start()
      setRecording(true)
      setSecs(0)
      timerRef.current = setInterval(() => setSecs((s) => s + 1), 1000)
    } catch {
      // No mic / permission denied: still advance the scripted conversation (voice note without local audio).
      send(null)
    }
  }

  function stopRec() {
    if (timerRef.current) clearInterval(timerRef.current)
    setRecording(false)
    const rec = recRef.current
    if (rec && rec.state !== 'inactive') rec.stop()
    else send(null)
  }

  const done = step >= TURNS.length

  return (
    <div className="kasht-app" dir="rtl">
      <style>{CSS}</style>
      <header className="kasht-head">
        <a className="kasht-back" href="/" aria-label="back">
          ‹
        </a>
        <div className="kasht-ava">🌾</div>
        <div className="kasht-who">
          <b>KASHT</b>
          <span>{recording ? 'ریکارڈنگ…' : waiting ? 'ٹائپ کر رہا ہے…' : 'آن لائن'}</span>
        </div>
        <div className="kasht-icons">📞 ⋮</div>
      </header>

      <div className="kasht-log">
        <div className="kasht-day">آج</div>
        <div className="kasht-note">🔒 پیغامات محفوظ ہیں۔ KASHT آپ کی فصل کے لیے مشورہ دیتا ہے۔</div>
        {msgs.map((m, i) => (
          <Voice key={i} m={m} />
        ))}
        {waiting && (
          <div className="kasht-row them">
            <div className="kasht-bub bub-them kasht-typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
        {done && !waiting && <div className="kasht-done">✓ ڈیمو مکمل — دوبارہ شروع کرنے کے لیے صفحہ کھولیں</div>}
        <div ref={endRef} />
      </div>

      <div className="kasht-bar">
        {recording ? (
          <>
            <button className="kasht-cancel" onClick={stopRec} aria-label="stop">
              ⏹
            </button>
            <div className="kasht-recbar">
              <span className="kasht-dot" />
              {`0:${secs < 10 ? '0' : ''}${secs}`} — ریکارڈنگ، بھیجنے کے لیے دبائیں
            </div>
            <button className="kasht-mic live" onClick={stopRec} aria-label="send">
              ➤
            </button>
          </>
        ) : (
          <>
            <div className="kasht-input">{done ? 'گفتگو مکمل' : 'آواز ریکارڈ کرنے کے لیے مائیک دبائیں'}</div>
            <button className="kasht-mic" onClick={startRec} disabled={done || waiting} aria-label="record">
              🎤
            </button>
          </>
        )}
      </div>
    </div>
  )
}

const CSS = `
.kasht-app{position:fixed;inset:0;display:flex;flex-direction:column;background:#efe7de;
  font-family:'Segoe UI',system-ui,sans-serif;max-width:480px;margin:0 auto;box-shadow:0 0 24px rgba(0,0,0,.2)}
.kasht-head{background:#075e54;color:#fff;display:flex;align-items:center;gap:10px;padding:10px 12px}
.kasht-back{color:#fff;text-decoration:none;font-size:26px;line-height:1}
.kasht-ava{width:40px;height:40px;border-radius:50%;background:#128c7e;display:flex;align-items:center;
  justify-content:center;font-size:20px;flex:0 0 auto}
.kasht-ava.sm{width:26px;height:26px;font-size:14px}
.kasht-who{flex:1;line-height:1.2}.kasht-who b{font-size:16px}.kasht-who span{font-size:12px;opacity:.85;display:block}
.kasht-icons{opacity:.9;font-size:16px;letter-spacing:6px}
.kasht-log{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:7px;
  background-image:linear-gradient(rgba(239,231,222,.85),rgba(239,231,222,.85))}
.kasht-day{align-self:center;background:#fff;border-radius:8px;padding:3px 10px;font-size:12px;color:#555;
  box-shadow:0 1px .5px rgba(0,0,0,.1);margin-bottom:3px}
.kasht-note{align-self:center;background:#fdf6cc;border-radius:8px;padding:6px 12px;font-size:12px;color:#5c5636;
  text-align:center;max-width:92%}
.kasht-row{display:flex}.kasht-row.me{justify-content:flex-start}.kasht-row.them{justify-content:flex-end}
.kasht-bub{max-width:85%;padding:6px 8px 4px;border-radius:10px;box-shadow:0 1px .5px rgba(0,0,0,.13)}
.bub-me{background:#d9fdd3;border-top-right-radius:2px}
.bub-them{background:#fff;border-top-left-radius:2px}
.kasht-voice{display:flex;align-items:center;gap:8px;direction:ltr}
.kasht-play{width:34px;height:34px;border-radius:50%;border:none;background:#0a7d6e;color:#fff;font-size:13px;
  cursor:pointer;flex:0 0 auto;display:flex;align-items:center;justify-content:center}
.kasht-wave{flex:1;display:flex;align-items:center;gap:2px;height:30px;cursor:pointer;min-width:120px}
.kasht-wave span{flex:1;background:#0a7d6e;border-radius:2px;min-width:2px}
.kasht-dur{font-size:11px;color:#667;font-variant-numeric:tabular-nums;flex:0 0 auto}
.kasht-meta{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:2px}
.kasht-cc{background:none;border:none;color:#0a7d6e;font-size:11px;cursor:pointer;padding:0}
.kasht-time{font-size:10px;color:#8a8}.kasht-tick{color:#53bdeb}
.kasht-text{margin:5px 2px 0;font-size:14px;line-height:1.6;color:#222;border-top:1px solid #0001;padding-top:5px}
.kasht-typing{display:flex;gap:4px;padding:12px 14px}
.kasht-typing span{width:7px;height:7px;border-radius:50%;background:#aaa;animation:kb 1s infinite}
.kasht-typing span:nth-child(2){animation-delay:.2s}.kasht-typing span:nth-child(3){animation-delay:.4s}
@keyframes kb{0%,60%,100%{opacity:.3}30%{opacity:1}}
.kasht-done{align-self:center;background:#d9fdd3;border-radius:8px;padding:5px 12px;font-size:12px;color:#235}
.kasht-bar{display:flex;align-items:center;gap:8px;padding:8px;background:#efe7de}
.kasht-input{flex:1;background:#fff;border-radius:22px;padding:11px 16px;font-size:14px;color:#888}
.kasht-mic{width:48px;height:48px;border-radius:50%;border:none;background:#0a7d6e;color:#fff;font-size:20px;
  cursor:pointer;flex:0 0 auto}
.kasht-mic:disabled{opacity:.5;cursor:default}
.kasht-mic.live{background:#d33}
.kasht-recbar{flex:1;background:#fff;border-radius:22px;padding:11px 16px;font-size:13px;color:#444;
  display:flex;align-items:center;gap:8px;direction:rtl}
.kasht-dot{width:10px;height:10px;border-radius:50%;background:#d33;animation:kp 1s infinite}
@keyframes kp{50%{opacity:.3}}
.kasht-cancel{width:44px;height:44px;border-radius:50%;border:none;background:#eee;color:#444;font-size:16px;
  cursor:pointer;flex:0 0 auto}
`

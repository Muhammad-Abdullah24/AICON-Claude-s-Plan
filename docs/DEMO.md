# FarmSight demo runbook

Our slot: **Sunday 11 October 2026, 11:27–11:32, SEECS Lecture Hall.** Five minutes. Everyone speaks.

Every figure below is **real app output from 10 Oct 2026** (AMIS prices up to 9 Oct 2026) with Owner B's deployed
model and engine. The price forecast is the labelled baseline ("the price stays the same, with the range of past
4-week swings"): the XGBoost model did not beat it on prices (NFR-01, `docs/MODEL_CARD.md`). For **wheat**, the model's
**direction call** (likely up / likely down, no price) and its SHAP reasons are shown, because it called 72% of 2025's
big wheat moves right. **Re-run section 7 on the morning of the demo** and fix any number that moved (blueprint
decision 12). Never say a number on stage that the app does not show.

---

## 1. Before we walk in (by 10:30)

- [ ] Backend and front end running on the laptop (README "Start the app"), **and** the deployed link opened on a
      phone over mobile data (the free host sleeps; opening it wakes it, which takes up to a minute). Open the API's
      `/health` again at 11:15. Deploy steps: `docs/DEPLOY.md`.
- [ ] Logged in as the demo farmer on both: Profile → phone **+920000000001** (invented farmer "Ahmed", Bahawalpur,
      wheat 100 maund and cotton 60 maund, 12.5 acres). Language: Urdu.
- [ ] Gemini key set (`FS_LLM_API_KEY`): ask one chat question to check. If chat falls back to the template, that is
      still correct output; say "the template answer, same numbers".
- [ ] WhatsApp (needs A3 done): the demo phone has messaged the bot in the last 24 hours, so alerts arrive as free
      text. Run `POST /api/alerts/run?dry_run=true` with `X-Admin-Token` to see the alert before sending it.
- [ ] WhatsApp menu rehearsal (section 3a): send `0` from the demo phone and walk the menu once. Then send `0` again
      just before going on stage, so the phone shows the menu and no half-finished session is waiting (sessions last
      30 minutes).
- [ ] Backup tab open at `/?as_of=2025-03-24` (section 4), and the backup recording on the desktop. If we play it,
      we say it is a recording.
- [ ] Phone brightness up, notifications off, laptop on charger.

## 2. The five minutes (real output, 10 Oct 2026)

| Time | Screen | What we show and say |
|---|---|---|
| 0:00–0:30 | – | **Problem.** Farmers sell at harvest into a glut, at the nearest mandi, without knowing their margin. Wheat at Bahawalpur fell 29% in four weeks in spring 2024 (Rs 4,825 → 3,432 from 18 Mar 2024, AMIS; history, not a model result). |
| 0:30–1:15 | **Home** (wheat, Bahawalpur, 100 maund) | Card: **بیچ دیں (SELL)**. Today **Rs 3,820**, in 4 weeks Rs 3,820, likely **Rs 3,607 to Rs 4,071**. Waiting 4 weeks on 100 maund: **−Rs 4,848**, the interest cost of waiting (16.5% a year for 4 weeks). "How sure: somewhat sure". Then the model's line: **"likely to rise in the next 4 weeks (it called 72% of the big moves in 2025 right; not a price forecast)"**. Say: a rise is likely, but not enough to beat the interest and the 5% bar, so SELL. Label: "Real data · Source: AMIS Punjab · per 40 kg · prices as of 9 October 2026". Weather line: live from Open-Meteo. |
| 1:15–2:00 | **Why?** | SHAP reasons from the model, in Urdu with arrows: the time of year (about +Rs 18 per 40 kg), heat and weather (+Rs 12), rainfall (+Rs 12); and, honestly, "the price shown is a simple estimate". Open "details" for one second: the price chart with the 4-week range; weeks without an AMIS price are gaps, not invented lines. |
| 2:00–2:40 | **Compare mandis**, then the **offer check** on Home | Bahawalpur is best: Rs 3,820. Rahim Yar Khan Rs 3,475 minus Rs 291 transport = Rs 3,184 (**−Rs 63,600** on 100 maund). Vehari's last price is 17 Jul 2026, shown in amber as old. Offer check: a buyer offers **Rs 3,514** → "Rs 306 a maund below the fair range" (**−Rs 30,600** on 100 maund; fair range = the mandi's last 14 days). |
| 2:40–3:30 | **What to grow** (Bahawalpur, 12.5 acres, logged in as Ahmed) | Ranked by profit per acre: 1 Super Basmati **Rs 1,691,610** (**amber: prices only to 7 Apr 2026**), 2 cotton **Rs 956,049** (Rs 76,484 an acre; past years Rs 40,065 to Rs 126,840), 3 IRRI Rs 681,254, 4 wheat **Rs 56,211** (Rs 4,497 an acre; past years from a loss of Rs 30,934 to a profit of Rs 35,487). Every crop shows "price risk: high" (year-to-year swings are large). Month strip: sowing, harvest, best time to sell. Wheat, cotton, IRRI: "best to sell at harvest: holding usually does not beat the interest"; Super Basmati: December. Say: Super Basmati is first on paper but its price is six months old, which is why the app marks it. |
| 3:30–4:10 | **WhatsApp** on the phone | Type "گندم بہاولپور 100 من" → the same advice as the web, with buttons کیوں؟ / منڈیاں / الرٹ بند and the line "1 کیوں؟ · 2 منڈیاں · 3 الرٹ بند · 0 مینو". If typing Urdu is slow on stage, use the numbered menu instead (section 3a): `0`, `1`, `1`, `1`, `100`. Say: "a farmer who cannot type can do all of it with digits". Then show the alert (section 3). |
| 4:10–4:40 | **Chat** (Ask) | "گندم کا ریٹ اگلے ہفتے کتنا ہوگا؟" → Urdu answer that uses only the app's numbers (every number is checked; if Gemini adds one, the template answer is shown instead). Voice notes are not available (A10): a voice note gets "type it, or send 0 for the menu". Do not send one on stage. |
| 4:40–5:00 | – | **Close.** "The same information traders have, in the farmer's language." Limits, in one breath: AMIS mandi prices (some series stale or frozen, and we show it); the baseline is right within its range 81% of the time on 2025 data; our model must beat it or we ship the baseline. |

**Must work:** Home, Why, Compare, What to grow. If WhatsApp or chat fails, say so and move on: the web shows the
same numbers.

**Strongest proof (30 seconds, if time allows or a judge asks):** open `/?as_of=2025-03-24`, then `/?as_of=2025-08-04`
(section 4). The model called **DOWN** before the 2025 pre-harvest crash and **UP** before the summer rally, both
held-out weeks.

## 3. The alert on the phone

Alerts follow Owner B's rule (`ml.decision.alert_check`): a signal change, or a 4-week move bigger than the forecast
band allows, at most one a week. **Today nothing is due for Ahmed**: wheat rose 11% in 4 weeks, but the week it is
compared with sits in the frozen Rs 3,450 stretch, so the app refuses to call it news. That is a feature: say so.

For the demo, replay the April 2025 drop. Dry run first (shows the message, sends nothing):

```bash
curl -X POST "http://127.0.0.1:8000/api/alerts/run?as_of=2025-04-21&dry_run=true" -H "X-Admin-Token: $FS_ADMIN_TOKEN"
```

What it says (real output):

```
🔔 فارم سائٹ الرٹ

ریٹ 4 ہفتوں میں 20% گرا، جو عام اتار چڑھاؤ سے زیادہ ہے:
🟢 گندم، بہاولپور: بیچ دیں
آج: Rs 2,380 فی من (AMIS، 2025-04-21 تک)
4 ہفتے بعد اندازہ: Rs 2,380 (Rs 2,247 سے Rs 2,536)
100 من پر رکنے کا فرق: −Rs 3,021 (Rs 3,021 سود نکال کر)
اعتماد: درمیانہ
یہ اندازہ ہے، گارنٹی نہیں۔

الرٹ بند کرنے کے لیے 'بند' لکھیں۔
```

To send it for real, Ahmed's invented phone (+920000000001) will not work: register a team member's phone (verified on
the Meta test number, and it has messaged the bot in the last 24 hours) with wheat at Bahawalpur, turn alerts off
for Ahmed in Profile, then run the same command without `dry_run=true`. Once sent, the one-a-week limit applies to
that farmer: to repeat it, delete `var/farmsight.sqlite` and restart. Other replay dates that alert: 2025-09-01
(wheat +49%), 2026-04-13 (−22%, test split).

## 3a. WhatsApp numbered menu (the reliable path)

Every step lists its numbers, so nothing has to be remembered. Rehearse it on the demo phone (registered and verified
on the Meta test number):

| Send | Reply |
|---|---|
| `0` | Menu: 1 ریٹ اور مشورہ · 2 منڈیوں کا موازنہ · 3 مشورے کی وجہ · 4 الرٹ چالو · 5 الرٹ بند · 0 مینو |
| `1` | کون سی فصل؟ 1 گندم · 2 کپاس (پھٹی) · 3 چاول |
| `1` | کون سی منڈی؟ 1 بہاولپور · 2 وہاڑی · 3 رحیم یار خان |
| `1` | کتنے من؟ |
| `100` | The advice card, the same numbers as Home (re-check them in section 7) |
| `1` | Why: the same reasons as the Why screen |
| `2` | Compare mandis |

If a number gets "یہ نمبر کس سوال کا جواب ہے" (no session), the 30 minutes ran out: send `0` and start again.
Always start with `0`: outside a session a bare `3` keeps its old meaning and turns alerts **off**.

**SMS is not live.** No SMS vendor is chosen, so there is nothing to show on a basic phone. If asked: "SMS is built and
tested as an adapter with the same menu in Roman Urdu, two SMS at most; it goes live once we pick an SMS gateway". Do
not show it as working, and do not show voice notes.

## 4. Backup: replay a past week

If the live data looks odd on the day, open the app with **`?as_of=<date>`**. A yellow banner on every screen says
"Replaying <date>" and every price screen shows what the app would have said that day (no price after that date is
used). "Back to today" ends it. Weather and chat stay live, and the banner says so.

Use **held-out** weeks only (the model never trained on them; say "held-out week", not "unseen test"):

| Open | What happened next (AMIS, Bahawalpur wheat) | What the app says now (baseline) |
|---|---|---|
| `/?as_of=2025-03-24` | Fell from Rs 2,990 to Rs 2,380 four weeks later (pre-harvest crash, the year with no support price) | SELL, today Rs 2,990, range Rs 2,823 to Rs 3,186; waiting costs Rs 3,795 interest. Model: **likely to fall** (time of year −Rs 26, heat −Rs 10). **Selling was right.** The real price fell below the range: say so |
| `/?as_of=2025-08-04` | Rose from Rs 2,360 to Rs 3,170 four weeks later (rally after the summer low) | SELL, today Rs 2,360 (the baseline price cannot see a rally). Model: **likely to rise**. **Waiting was right**, and the direction call said so; the SELL card did not, because the model's prices are not trusted enough to drive the decision |
| `/?as_of=2026-03-16` | Fell 21.8% into the 2026 harvest | Test split: show only after the final test run (`ml.eval.gate --split test --final`) |

Avoid 2026-08-31 and 2026-09-07: Bahawalpur wheat was frozen at Rs 3,450 then (a reporting artifact).

What to Grow in replay uses the seasonal tables, which were built from every year including later ones. Say it is
"the pattern across years", not a prediction made that day.

## 5. If something fails live

| Failure | Switch to |
|---|---|
| Deployed site down or asleep | Local copy on the laptop |
| Venue Wi-Fi down | Phone hotspot, or the local copy (fonts are bundled; weather falls back to the offline file and says "cached") |
| WhatsApp reply or alert does not arrive | The same advice on the web, then the backup recording, and say it is a recording |
| Chat answers with the template | Fine: same numbers. Say "Gemini was unavailable, so the app used its template" |
| Live prices look odd | Replay a held-out week (section 4) |

## 6. Questions judges may ask

**"Wheat is Rs 5,300 in Punjab, why does the app say Rs 3,820?"** Rs 5,300 is an open-market rate reported by ARY
News (8 Oct 2026) with no mandi named. AMIS mandi prices across Punjab are Rs 3,475 to Rs 4,700 (median of 18
mandis Rs 4,450), and South Punjab is at the low end: Bahawalpur 3,820, Rahim Yar Khan 3,475. That gap is exactly
why "where to sell" matters. (Details: `docs/DATA_NOTES.md` section A7.)

**"It always says SELL."** Yes, by design for now: the SELL/WAIT card runs on the baseline price, which can never
clear the 5% bar for WAIT, and the interest cost of waiting is real. Prices rise 5% or more in 4 weeks only 14–19% of
weeks. Our XGBoost model did not predict prices better than the baseline on held-out 2025 data (5.64% vs 5.60%
error), so we do not let its prices drive the decision (NFR-01).

**"Then why does it say 'likely to rise' and SELL?"** The model is good at direction for wheat (72% of 2025's big moves
called right) but not at size. Likely up is not the same as up by more than 5% plus 4 weeks of interest. We show both,
honestly labelled.

**"How accurate is it?"** On 328 real 2025 weeks (held out): the baseline's average error is 5.60% (6.66% without
weeks where AMIS repeated the same price), and its range held the real price 81% of the time. The XGBoost model:
5.64% (not better, so not used for prices); direction of moves over 3%: 60% across crops, 72% for wheat. Wheat was
chosen after seeing validation, so the one-time 2026 test run confirms or rejects it. Sources: `ml/eval/report.md`,
`docs/MODEL_CARD.md`. A backtest, not a field trial.

**"Is the data real?"** Yes: AMIS Punjab daily mandi prices, Jan 2015 to Oct 2026, for these 3 mandis and 4 crop
options (no IRRI at Rahim Yar Khan). Old prices are shown in amber and lower the confidence; a price AMIS repeated for
4+ weeks says "price unchanged since". Costs come from the Agriculture Policy Institute; transport and rice milling
yield are estimates and labelled so.

**"Where does the LLM come in?"** Only to rephrase chat answers in Urdu. The "Why?" reasons are SHAP values from the
XGBoost model turned into fixed sentences, not LLM text. It never makes a number: every number in its
answer must already be in the farmer's advice, or the template answer is sent instead. Prompts are in
`docs/PROMPTS.md`. No phone or personal data goes to Gemini.

## 7. Regenerate these numbers

After the model lands (or on the morning of the demo), with the backend running:

```bash
curl "http://127.0.0.1:8000/api/advice?crop=wheat&mandi=bahawalpur&quantity_maund=100"
curl "http://127.0.0.1:8000/api/explain?crop=wheat&mandi=bahawalpur"
curl "http://127.0.0.1:8000/api/compare-mandis?crop=wheat&mandi=bahawalpur&quantity_maund=100"
curl "http://127.0.0.1:8000/api/crop-plan?mandi=bahawalpur&land_area_acres=12.5"
curl -X POST "http://127.0.0.1:8000/api/offer-check" -H "Content-Type: application/json" -d "{\"crop\":\"wheat\",\"mandi\":\"bahawalpur\",\"offer_price\":3514,\"quantity_maund\":100}"
curl "http://127.0.0.1:8000/api/advice?crop=wheat&mandi=bahawalpur&quantity_maund=100&as_of=2025-03-24"
curl "http://127.0.0.1:8000/api/advice?crop=wheat&mandi=bahawalpur&quantity_maund=100&as_of=2025-08-04"
```

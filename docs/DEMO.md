# FarmSight demo runbook

Our slot: **Sunday 11 October 2026, 11:27–11:32, SEECS Lecture Hall.** Five minutes. Everyone speaks.

Every figure below is **real app output from 10 Oct 2026** (AMIS prices up to 9 Oct 2026), before Owner B's trained
model. The forecast is still the labelled baseline: "the price stays the same, with the range of past 4-week swings".
**When Usman's model lands, re-run the commands at the bottom and replace every number in this file**
(blueprint decision 12). Never say a number on stage that the app does not show.

---

## 1. Before we walk in (by 10:30)

- [ ] Backend and front end running on the laptop (README "Start the app"), **and** the deployed link opened on a
      phone over mobile data (the free host sleeps; opening it wakes it, which takes up to a minute).
- [ ] Logged in as the demo farmer on both: Profile → phone **+920000000001** (invented farmer "Ahmed", Bahawalpur,
      wheat 100 maund and cotton 60 maund, 12.5 acres). Language: Urdu.
- [ ] Gemini key set (`FS_LLM_API_KEY`): ask one chat question to check. If chat falls back to the template, that is
      still correct output; say "the template answer, same numbers".
- [ ] WhatsApp (needs A3 done): the demo phone has messaged the bot in the last 24 hours, so alerts arrive as free
      text. Run `POST /api/alerts/run?dry_run=true` with `X-Admin-Token` to see the alert before sending it.
- [ ] Backup tab open at `/?as_of=2025-03-24` (section 4), and the backup recording on the desktop. If we play it,
      we say it is a recording.
- [ ] Phone brightness up, notifications off, laptop on charger.

## 2. The five minutes (real output, 10 Oct 2026)

| Time | Screen | What we show and say |
|---|---|---|
| 0:00–0:30 | – | **Problem.** Farmers sell at harvest into a glut, at the nearest mandi, without knowing their margin. Wheat at Bahawalpur fell 29% in four weeks in spring 2024 (Rs 4,825 → 3,432 from 18 Mar 2024, AMIS; history, not a model result). |
| 0:30–1:15 | **Home** (wheat, Bahawalpur, 100 maund) | Card: **بیچ دیں (SELL)**. Today **Rs 3,820**, in 4 weeks Rs 3,820, likely **Rs 3,607 to Rs 4,071**. Waiting 4 weeks on 100 maund: **−Rs 5,253**, which is the interest cost of waiting (1.375% a month). "How sure: somewhat sure". Label: "Real data · Source: AMIS Punjab · per 40 kg · prices as of 9 October 2026". Weather line: live from Open-Meteo. |
| 1:15–2:00 | **Why?** | Reasons in Urdu: the price rose 11% over the last 4 weeks; in October the price is usually 102% of its yearly trend; and, honestly, "this is a simple estimate". Once the model lands this becomes SHAP reasons. |
| 2:00–2:40 | **Compare mandis**, then the **offer check** on Home | Bahawalpur is best: Rs 3,820. Rahim Yar Khan Rs 3,475 minus Rs 291 transport = Rs 3,184 (**−Rs 63,600** on 100 maund). Vehari's last price is 17 Jul 2026, shown in amber as old. Offer check: a buyer offers **Rs 3,514** → "Rs 306 a maund below the fair range" (**−Rs 30,600** on 100 maund; fair range = the mandi's last 14 days). |
| 2:40–3:30 | **What to grow** (Bahawalpur, 12.5 acres) | Ranked by expected profit: 1 Super Basmati (**amber: prices only to 7 Apr 2026**, risk raised), 2 cotton **Rs 956,049** (Rs 76,484 an acre, medium risk), 3 IRRI, 4 wheat **Rs 56,211** (Rs 4,497 an acre). Month strip: sowing, harvest, best time to sell. For wheat and cotton: "best to sell at harvest: holding usually does not beat the interest". Say: Super Basmati is first on paper but its price is six months old, which is why the app marks it. |
| 3:30–4:10 | **WhatsApp** on the phone | Type "گندم بہاولپور 100 من" → the same advice as the web, with buttons کیوں؟ / منڈیاں / الرٹ بند. Then show the alert (section 3). |
| 4:10–4:40 | **Chat** (Ask) | "گندم کا ریٹ اگلے ہفتے کتنا ہوگا؟" → Urdu answer that uses only the app's numbers (every number is checked; if Gemini adds one, the template answer is shown instead). Voice notes are not built (A10): type the question. |
| 4:40–5:00 | – | **Close.** "The same information traders have, in the farmer's language." Limits, in one breath: AMIS mandi prices (some series stale or frozen, and we show it); the baseline is right within its range 81% of the time on 2025 data; our model must beat it or we ship the baseline. |

**Must work:** Home, Why, Compare, What to grow. If WhatsApp or chat fails, say so and move on: the web shows the
same numbers.

## 3. The alert on the phone

What `alerts.run` sends Ahmed today (first alert for each crop):

```
🔔 فارم سائٹ الرٹ

آپ کی فصل کا تازہ مشورہ:
🟢 گندم، بہاولپور: بیچ دیں
آج: Rs 3,820 فی من (AMIS، 2026-10-09 تک)
4 ہفتے بعد اندازہ: Rs 3,820 (Rs 3,607 سے Rs 4,071)
100 من پر رکنے کا فرق: −Rs 5,253 (Rs 5,253 سود نکال کر)
اعتماد: درمیانہ
یہ اندازہ ہے، گارنٹی نہیں۔

آپ کی فصل کا تازہ مشورہ:
🟢 کپاس (پھٹی)، بہاولپور: بیچ دیں
آج: Rs 9,200 فی من (AMIS، 2026-10-09 تک)
4 ہفتے بعد اندازہ: Rs 9,200 (Rs 8,115 سے Rs 10,376)
60 من پر رکنے کا فرق: −Rs 7,590 (Rs 7,590 سود نکال کر)
اعتماد: کم
یہ اندازہ ہے، گارنٹی نہیں۔

الرٹ بند کرنے کے لیے 'بند' لکھیں۔
```

Ahmed's real phone is not +920000000001. For the live alert, register a team member's phone (verified on the Meta
test number) with wheat at Bahawalpur, then run the check:

```bash
curl -X POST "http://127.0.0.1:8000/api/alerts/run" -H "X-Admin-Token: $FS_ADMIN_TOKEN"
```

At most one alert per farmer per week: to send again on the same day, use a fresh database (delete
`var/farmsight.sqlite` and restart) or another registered phone.

## 4. Backup: replay a past week

If the live data looks odd on the day, open the app with **`?as_of=<date>`**. A yellow banner on every screen says
"Replaying <date>" and every price screen shows what the app would have said that day (no price after that date is
used). "Back to today" ends it. Weather and chat stay live, and the banner says so.

Use **held-out** weeks only (the model never trained on them; say "held-out week", not "unseen test"):

| Open | What happened next (AMIS, Bahawalpur wheat) | What the app says now (baseline) |
|---|---|---|
| `/?as_of=2025-03-24` | Fell from Rs 2,990 to Rs 2,380 four weeks later (pre-harvest crash, the year with no support price) | SELL, today Rs 2,990, range Rs 2,823 to Rs 3,186; waiting costs Rs 4,111 interest. **Selling was right**, and the real price fell below the range: say so |
| `/?as_of=2025-08-04` | Rose from Rs 2,360 to Rs 3,170 four weeks later (rally after the summer low) | SELL, today Rs 2,360. **The baseline cannot see a rally; waiting was right.** This is the week the trained model has to get right |
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

**"It always says SELL."** With the baseline, yes: "the price stays the same" can never clear the 5% bar for WAIT,
and the interest cost of waiting is real. Prices rise 5% or more in 4 weeks only 14–19% of weeks. The model's job is
to find those weeks; until it beats the baseline on held-out data we do not ship it (NFR-01).

**"How accurate is it?"** On 328 real 2025 weeks (held out): the baseline's average error is 5.60% (6.66% without
weeks where AMIS repeated the same price), and its range held the real price 81% of the time. Source:
`ml/eval/report.md`. A backtest, not a field trial. Replace with the model's result when it lands.

**"Is the data real?"** Yes: AMIS Punjab daily mandi prices, Jan 2015 to Oct 2026, for these 3 mandis and 4 crop
options (no IRRI at Rahim Yar Khan). Old prices are shown in amber and lower the confidence; a price AMIS repeated for
4+ weeks says "price unchanged since". Costs come from the Agriculture Policy Institute; transport and rice milling
yield are estimates and labelled so.

**"Where does the LLM come in?"** Only to rephrase chat answers in Urdu. It never makes a number: every number in its
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

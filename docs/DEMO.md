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
| 0:00–0:30 | – | **Problem.** A buyer at the farm gate offers a price and wants an answer now. The farmer has no quick, independent reference in Urdu, and selling at harvest is when prices are weakest: wheat at Bahawalpur fell 29% in four weeks in spring 2024 (Rs 4,825 → 3,432 from 18 Mar 2024, AMIS; history, not a model result). FarmSight is one thing: **check a buyer's offer before you sell**. |
| 0:30–1:30 | **Home: check an offer** (cotton, Bahawalpur, 60 maund, buyer offers **Rs 8,500**) | **"Below the recent reference range"**. Latest reported mandi price **Rs 9,200** (AMIS, 9 Oct 2026); recent reference range **Rs 8,900 to Rs 9,240**, AMIS reported 12 of the last 14 days ("Recent report" badge). The offer is **Rs 700 a maund below** the latest price: **−Rs 42,000 on 60 maund** (−Rs 24,000 against the bottom of the range). Then the next steps: ask the buyer how the price was set and whether grade changed it; compare mandis; use this as an independent reference; and, honestly, "FarmSight cannot remove a credit, transport or cash constraint". Say: "a reference, not a fair price; grade and terms are not in it". |
| 1:30–2:10 | Same form: **wheat, Bahawalpur, 100 maund, Rs 3,514** | **"Reference data is limited"** in the wheat card: AMIS reported **the same price, Rs 3,820, on all 12 reported days**. The numbers stay (−Rs 306 a maund, **−Rs 30,600** on 100 maund) but FarmSight gives no verdict on the offer, and offers safe next steps instead (another mandi, the latest dates, ask the mandi) and "What FarmSight cannot know". Say: this is the honesty we built in. |
| 2:10–2:50 | **Compare mandis** (cotton, the Rs 8,500 offer) | Your mandi first: Bahawalpur Rs 9,200, transport Rs 0, **+Rs 42,000** against the offer on 60 maund. Vehari: Rs 7,500 reported, −Rs 165 transport = Rs 7,335, **not estimated better after transport** (−Rs 69,906). Rahim Yar Khan: higher net on paper (Rs 8,859) but **only 2 reports in 14 days**, so **"reference too weak to compare"**, never "best". The caution banner: "not necessarily the best mandi; check a buyer is there and arrange transport". |
| 2:50–3:40 | **WhatsApp** on the phone, then the **WhatsApp / SMS** page | Numbered menu: `0`, `1` (check an offer), `2` (cotton), `1` (Bahawalpur), `60`, `8500` → the same result as the web, in Urdu; `2` → the mandis against the offer. Free text works too: "گندم بہاولپور 100 من آفر 3514". On the web, open **WhatsApp / SMS**: the real menu and the real Roman Urdu SMS for the last check (2 SMS parts), rendered by the channel code. Say plainly: **SMS is a tested adapter, not live** (no SMS provider yet), and voice notes are off. |
| 3:40–4:20 | **Data details**, then **Market outlook** | Data details: the same strength labels, the reference price and date, "What FarmSight cannot know" (grade, buyer terms, trucks, credit or urgent cash, whether a buyer is there). Market outlook (secondary): we tested price forecasting; our XGBoost model did not beat the simple baseline on held-out data (5.64% vs 5.60% error), so the outlook is background, **not a reason to hold the crop**. For wheat it shows the model's direction call (72% of 2025's big moves right), labelled. |
| 4:20–5:00 | – | **Close.** "Before you sell, check once: an independent reference in the farmer's language." Limits, in one breath: AMIS reports can be old, frozen or repeated, and we say so; transport is an estimate; we cannot see grade, terms, credit or buyers; no field trial yet, so no income claims. |

**Must work:** Home (offer check), Compare, Data details. If WhatsApp fails, say so and move on: the web shows the
same numbers. Re-check every figure above with section 7 on the morning of the demo.

**If a judge asks for a past week (30 seconds):** open `/?as_of=2025-03-24` (section 4) and check an offer of Rs 2,750
for wheat at Bahawalpur, 100 maund: the reference that day was strong (Rs 2,990, range Rs 2,760 to Rs 2,990, 14 of 14
days), so the result is "below the recent reference range", −Rs 24,000 on 100 maund. Say: **this is what reference
information was available that day**, not money anyone saved: there was no real offer.

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
the Meta test number, and it has messaged the bot in the last 24 hours) with wheat at Bahawalpur, **turn its alerts
on** (Profile, or send `0` then `4` on WhatsApp: new farmers start with alerts off), turn alerts off for Ahmed in
Profile, then run the same command without `dry_run=true`. Once sent, the one-a-week limit applies to
that farmer: to repeat it, delete `var/farmsight.sqlite` and restart. Other replay dates that alert: 2025-09-01
(wheat +49%), 2026-04-13 (−22%, test split).

## 3a. WhatsApp numbered menu (the reliable path)

Every step lists its numbers, so nothing has to be remembered. Rehearse it on the demo phone (registered and verified
on the Meta test number):

| Send | Reply |
|---|---|
| `0` | Menu: 1 خریدار کی آفر چیک کریں · 2 منڈیوں کا موازنہ · 3 وجہ اور ڈیٹا کی تفصیل · 4 الرٹ شروع کریں · 5 الرٹ بند کریں · 0 مینو |
| `1` | کون سی فصل؟ 1 گندم · 2 کپاس (پھٹی) · 3 چاول |
| `2` | کون سی منڈی؟ 1 بہاولپور · 2 وہاڑی · 3 رحیم یار خان |
| `1` | کتنے من؟ |
| `60` | خریدار نے فی من کتنا دیا؟ |
| `8500` | The offer result, the same numbers as Home: "حالیہ حوالہ حد سے کم", Rs 8,500 vs Rs 9,200, 60 من پر −Rs 42,000 |
| `2` | Every mandi after estimated transport against the Rs 8,500 offer, Bahawalpur first |
| `1` | Why / data details |

If a number gets "یہ نمبر کس سوال کا جواب ہے" (no session), the 30 minutes ran out: send `0` and start again.
Always start with `0`: outside a session a bare `3` keeps its old meaning and turns alerts **off**.

**SMS is not live.** No SMS vendor is chosen, so there is nothing to show on a basic phone. If asked: "SMS is built and
tested as an adapter with the same menu in Roman Urdu, two SMS at most; it goes live once we pick an SMS gateway". Do
not show it as working, and do not show voice notes.

## 4. Backup: replay a past week ("what reference was available that day?")

If the live data looks odd on the day, open the app with **`?as_of=<date>`**. A banner on every screen says
"Replaying <date>" and every price screen shows what reference information was available that day (no price after
that date is used). "Back to today" ends it. Weather and chat stay live, and the banner says so. **Never present a
replay as money saved**: there was no real buyer's offer, so there is no counterfactual.

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

**"Is this offer unfair?"** FarmSight does not say that. It shows the recent reported reference, how strong it is, and
the difference for the farmer's quantity. It cannot see the crop's grade, the buyer's terms or any credit tie, so
proving an offer unfair would need field evidence we do not have.

**"Are you replacing arhtis?"** No. Commission agents often give credit, transport and quick settlement. FarmSight is a
calculation and negotiation aid for the farmer to use alongside them.

**"It always says SELL."** (Market outlook, now secondary.) Yes, by design for now: the SELL/WAIT card runs on the baseline price, which can never
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
curl -X POST "http://127.0.0.1:8000/api/offer-check" -H "Content-Type: application/json" -d "{\"crop\":\"cotton\",\"mandi\":\"bahawalpur\",\"offer_price\":8500,\"quantity_maund\":60}"
curl "http://127.0.0.1:8000/api/reference?crop=wheat&mandi=bahawalpur"
curl "http://127.0.0.1:8000/api/channels/preview?crop=cotton&mandi=bahawalpur&quantity_maund=60&offer_price=8500"
curl "http://127.0.0.1:8000/api/explain?crop=wheat&mandi=bahawalpur"
curl "http://127.0.0.1:8000/api/compare-mandis?crop=wheat&mandi=bahawalpur&quantity_maund=100"
curl "http://127.0.0.1:8000/api/crop-plan?mandi=bahawalpur&land_area_acres=12.5"
curl -X POST "http://127.0.0.1:8000/api/offer-check" -H "Content-Type: application/json" -d "{\"crop\":\"wheat\",\"mandi\":\"bahawalpur\",\"offer_price\":3514,\"quantity_maund\":100}"
curl "http://127.0.0.1:8000/api/advice?crop=wheat&mandi=bahawalpur&quantity_maund=100&as_of=2025-03-24"
curl "http://127.0.0.1:8000/api/advice?crop=wheat&mandi=bahawalpur&quantity_maund=100&as_of=2025-08-04"
```

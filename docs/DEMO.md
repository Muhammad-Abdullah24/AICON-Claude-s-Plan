# FarmSight demo runbook

Our slot: **Sunday 11 October 2026, 11:27–11:32, SEECS Lecture Hall.** Five minutes. Everyone speaks.

**The story (BLUEPRINT section 0, docs/PIVOT.md): small farmers don't lack prices; their loan forces them to sell at
the harvest low.** FarmSight plans the loan at sowing, so the farmer can afford to wait at harvest.

Every figure in section 2 is **real app output from 10 Oct 2026 (evening)**, with AMIS prices up to 9 Oct. **Re-run section 7 on demo morning** and fix any number that moved. Never say a number on stage
that the app doesn't show.

---

## 1. Before we walk in (by 10:30)

**Live:** web app **https://aicon-claude-s-plan-bay.vercel.app** (share this one) · API
https://farmsight-api-auat.onrender.com/health. Not `aicon-claude-s-plan.vercel.app`: that's an old copy in
Hamza's Vercel account. Open the API's `/health` first; the free plan sleeps and takes about a minute to wake.

- [ ] Backend and front end running on the laptop (README "Start the app"), **and** the deployed link opened on a
      phone over mobile data (the free host sleeps; opening it wakes it, which takes up to a minute). Open the API's
      `/health` again at 11:15. Deploy steps: `docs/DEPLOY.md`.
- [ ] Logged in as the demo farmer on both: Profile → phone **+920000000001** (invented farmer "Ahmed", Bahawalpur,
      wheat 100 maund and cotton 60 maund, 12.5 acres). Language: Urdu.
- [ ] Gemini key set (`FS_LLM_API_KEY`): ask one chat question to check. If chat falls back to the template, that is
      still correct output; say "the template answer, same numbers".
- [ ] WhatsApp (needs A3 done): the demo phone has messaged the bot in the last 24 hours, so alerts arrive as free
      text. Run `POST /api/alerts/run?dry_run=true` with `X-Admin-Token` to see the alert before sending it.
- [ ] Replay tab open at `/?as_of=2026-05-10` (Act 2), plus a backup tab at `/?as_of=2025-03-24` (section 4), and the backup recording on the desktop. If we play it,
      we say it is a recording.
- [ ] Phone brightness up, notifications off, laptop on charger.

## 2. The five minutes

| Time | Screen | What we show and say |
|---|---|---|
| 0:00–0:40 | – | **Problem, with sources.** 2026 harvest: Punjab wheat sold at **Rs 2,900–3,100** (Friday Times, ProPakistani). By October the open market was about **Rs 5,300** (ARY). Traders and big farmers who could wait gained. Small farmers couldn't: their loans fell due in April, and about **half of what a smallholder borrows "for the crop" goes to household needs** (Sindh study: 51.5% reached the farm). Mandi prices are already free (Telenor 7272, AMIS), and price information alone doesn't raise farmers' prices. **Money does:** harvest loans earned a 29% return in a Kenyan trial. |
| 0:40–1:40 | **قرض tab: loan planner** (Act 1: October, sowing now) | Ahmed, **5 acres** of wheat, age 30, plans to borrow **Rs 4,00,000 from his arhti**. Top of the answer, in red: **"that is Rs 1,32,000 more than the cheapest way"** (66% for 6 months), and **"you planned Rs 83,675 more than the crop needs: extra loan for the house still falls due at harvest"**, the over-borrowing the expert described. His wheat needs **Rs 3,16,325** in cash before the sale (Rs 63,265/acre: seed, fertiliser at 2026 prices, land preparation, irrigation, sprays; official API table, labelled "estimate"). Harvesting (about Rs 1,03,650) is shown apart: paid in April from the crop, not borrowed now. Cheapest first: **Kissan Card Rs 1,50,000 at 0%** (terms checked on the Punjab government page), then **PM Youth Rs 1,66,325 at 0%** (SBP scheme page; monthly instalments, said on screen). Tap **"keep these loans in my list"** (logged in) to show them in Profile, due at harvest. |
| 1:40–3:00 | **Home: wait plan**, replay **`/?as_of=2026-05-10`** (Act 2: harvest) | Wheat, Bahawalpur, 100 maund; type **1,00,000** in "cash you need now"; tap **5 months**. **Own money and a godown:** verdict **SPLIT: sell 29 maund now, hold 71**. Sell-now Rs 3,450 at Bahawalpur (best after transport; Vehari Rs 3,185, Rahim Yar Khan Rs 3,159). The arhti's offer of **Rs 2,900** is **Rs 55,000 less on 100 maund**. Holding: "waiting paid in **7 of 9** past seasons with your setup", typical +Rs 65/maund, a bad year −Rs 128. **Then switch to arhti money and bags at home:** verdict **SELL ALL**: waiting paid in **1 of 9**, the typical result is −Rs 389/maund, and interest plus storage loss come to Rs 1,29,375. Say: **"Same crop, same mandi, same day: opposite advice. The only difference is whose money he holds with."** |
| 3:00–3:30 | **Why?** (liquidity chart) | Each past year at Bahawalpur, sell in May vs October: green when holding paid (2025: +Rs 895/maund, 2022: +Rs 820), red when it didn't (2024: −Rs 289). 2026 is marked: AMIS was held at the Rs 3,500 cap while the open market climbed. |
| 3:30–4:10 | **Back to today** (Act 3: the news) | Banner: the news price differs from AMIS (AMIS Rs 3,820 on 9 Oct; **check the headline on the morning: it must be a wheat price per 40 kg, not flour**, card N1). Policy card: **support price still undecided** (Punjab Rs 4,200, Sindh Rs 5,000), and the Kissan Ittehad demand. Say: news never changes the advice; it lowers confidence and tells the farmer why. |
| 4:10–4:40 | **WhatsApp** on the phone | "گندم بہاولپور 100 من", then "رکھیں" → the same wait plan in Urdu. No smartphone app needed. |
| 4:40–5:00 | – | **Close.** "Everyone tells the farmer the price. FarmSight tells him how much to borrow, from whom, and whether he can afford to wait, in his language." Limits in one breath: AMIS mandi prices (2026 capped, and we show it); the backtest is history, not a promise; holding is worked out for wheat only for now. |

**Must work:** the loan planner, the wait plan in replay, and today's news banner. If WhatsApp fails, say so and move
on: the web shows the same numbers.

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

**"Isn't this just a calculator?"** The calculation is the point: no app in Pakistan combines the farmer's own loan, his
storage and 11 years of mandi history into one decision. Telenor and BaKhabar give prices; Zarkhez-e and the Kissan
Card give loans; PMEX offers warehouses. Nobody tells one farmer which way out is best for his 100 maund.

**"Where's the AI?"** Three places, each labelled: the hold backtest over 11 years of AMIS prices (the evidence behind
every hold or sell); the XGBoost direction call for wheat (72% of 2025's big moves right; it never sets a price); and
Gemini for Urdu answers and news tagging (it never invents a number; the app checks every one). We tried to forecast
prices with XGBoost and it didn't beat "price stays the same" (5.64% vs 5.60% error), so we don't let it drive advice.

**"Wheat is Rs 5,300; why does the app say Rs 3,820?"** AMIS reports the mandi rate, which the Punjab cap held near
Rs 3,500 through the summer (The News, 28 Apr 2026). Open-market reports are higher. We show both: AMIS for the advice,
the news banner for the gap.

**"Does holding really pay?"** Sometimes, and it depends on the money. At Bahawalpur, selling in May vs October: with own
money and a godown, waiting paid in 7 of 9 seasons; with arhti money and bags, in 1 of 9. Across our three mandis it's
the same pattern (`docs/MODEL_CARD.md`, "Decision backtest").

**"Can a small farmer really get 0% money?"** The Kissan Card (Punjab, 1–12.5 acres): Rs 30,000/acre, up to Rs 1,50,000
a season, for inputs only. PM Youth Tier 1: up to Rs 5 lakh at 0%, age 21–45. Akhuwat: small 0% loans with guarantors.
Each option in the app links its official source and says when the farmer isn't eligible.

**"Why only wheat for holding?"** Wheat is storable, and we have sourced storage-loss figures for it (FAO). Cotton and
rice storage costs aren't sourced yet, so the app says "sell" and shows the mandi comparison.

**"Is the data real?"** Yes: AMIS Punjab daily mandi prices, Jan 2015 to Oct 2026, for 3 mandis and 4 crop options; the
official API cost tables; loan terms from the government and bank pages. Old prices are shown in amber; a price AMIS
repeated for weeks says "unchanged since".

## 7. Regenerate these numbers

After the model lands (or on the morning of the demo), with the backend running:

```bash
curl "http://127.0.0.1:8000/api/wait-plan?crop=wheat&mandi=bahawalpur&quantity_maund=100&wait_months=5&offer=2900&cash_need_rs=100000&as_of=2026-05-10"
curl "http://127.0.0.1:8000/api/wait-plan?crop=wheat&mandi=bahawalpur&quantity_maund=100&wait_months=5&offer=2900&cash_need_rs=100000&as_of=2026-05-10&money=arhti&storage=bags"
curl "http://127.0.0.1:8000/api/compare-mandis?crop=wheat&mandi=bahawalpur&quantity_maund=100&as_of=2026-05-10"
curl "http://127.0.0.1:8000/api/news?crop=wheat&mandi=bahawalpur"
curl "http://127.0.0.1:8000/api/policy?crop=wheat"
curl "http://127.0.0.1:8000/api/loan-plan?crop=wheat&acres=5&planned_borrow_rs=400000&planned_lender=arhti"   # after L2a
curl "http://127.0.0.1:8000/api/advice?crop=wheat&mandi=bahawalpur&quantity_maund=100"
curl "http://127.0.0.1:8000/api/explain?crop=wheat&mandi=bahawalpur"
curl "http://127.0.0.1:8000/api/compare-mandis?crop=wheat&mandi=bahawalpur&quantity_maund=100"
curl "http://127.0.0.1:8000/api/crop-plan?mandi=bahawalpur&land_area_acres=12.5"
curl -X POST "http://127.0.0.1:8000/api/offer-check" -H "Content-Type: application/json" -d "{\"crop\":\"wheat\",\"mandi\":\"bahawalpur\",\"offer_price\":3514,\"quantity_maund\":100}"
curl "http://127.0.0.1:8000/api/advice?crop=wheat&mandi=bahawalpur&quantity_maund=100&as_of=2025-03-24"
curl "http://127.0.0.1:8000/api/advice?crop=wheat&mandi=bahawalpur&quantity_maund=100&as_of=2025-08-04"
```

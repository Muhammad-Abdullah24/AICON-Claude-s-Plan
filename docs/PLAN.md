# FarmSight: Team Build Plan (v3, follows the blueprint)

> **Team:** Team Claude's Plan · **Event:** Build With AI, AICON'26, SEECS NUST · **Domain:** Agricultural Operations
> **Our slot:** Sunday 11 October 2026, 11:27 to 11:32 AM, SEECS Lecture Hall
> **Written:** Friday 9 October 2026, 21:00.

**Two documents, two jobs:**

| Document | Answers | Changed by |
|---|---|---|
| [`docs/BLUEPRINT.md`](BLUEPRINT.md) | **What** we build: use cases, requirements, data model, API contract (section 12), screens, demo | Team agreement at a check-in |
| `docs/PLAN.md` (this file) | **Who** does **what**, **when**, and how we work together | Team agreement at a check-in. Tick your own task boxes freely |

> **Change log**
> - **9 Oct 2026, 21:00 (team decision):** the blueprint is the plan of record. The previous plan (Chronos-2, four verdicts, crisis replay, event layer) is archived at [`docs/archive/PLAN_v2_superseded.md`](archive/PLAN_v2_superseded.md) and no longer binding. Code built to it is reused where it fits (section 6).

---

## 0. Read this first (two minutes)

**What we are building.** An Urdu-first crop economics advisor for Wheat, Cotton, Super Basmati and IRRI rice at the Vehari, Bahawalpur and Rahim Yar Khan mandis. It forecasts the price 4 weeks ahead with a range, says SELL (بیچ دیں) or WAIT (رکیں) with the rupee gain after interest, explains why with SHAP, compares mandis after transport, and ranks what to grow. It runs on a React web app and WhatsApp. Full spec: `docs/BLUEPRINT.md`.

**The must-work demo path** (blueprint section 11). If any of these is missing, we do not have a demo:

1. A 4-week forecast with a range for Wheat at Bahawalpur, on real AMIS data, compared honestly against the naive baseline.
2. An Urdu SELL / WAIT signal with the net rupee impact on 100 maund.
3. "Why?" with SHAP reasons in plain Urdu.
4. Mandi comparison by net price after transport.
5. Crop ranking (What to Grow) with the best selling window.
6. A working deployed link, plus the app running on our laptop.

**How we work.** Three owners, each owning a set of folders. The interfaces between owners are fixed in section 4, and nobody's Claude session edits outside its owner's folders. `main` always runs.

---

## 1. Fixed facts: deadlines and rules

| When | What |
|---|---|
| Saturday 10 October | On-site attendance is mandatory. The submission link is handed out in person. Teamwork is observed. |
| Sunday 11 October, 11:00 AM | All three of us in SEECS Lecture Hall, laptop open, demo loaded and tested |
| Sunday 11 October, 11:27 AM | Our five minutes |
| To confirm at the venue | The official end of the build period and the submission deadline. Adjust section 5 when known |

Rules that shape the build (from the rulebook):

- The required flow is **Problem → Data → AI → Solution → Impact**. A bolted-on chatbot does not count as meaningful AI. Our AI is the forecast model, the SHAP explanations and the advisory engine; the LLM only handles language.
- **Submission needs:** a GitHub repository link, a deployed project link, and a demo presentation.
- **Falsifying results is grounds for disqualification.** Every synthetic or assumed number is labelled.
- **Plagiarism is grounds for disqualification.** Ideas from other projects, never code.
- **Pre-existing code and datasets are disclosed** in the README (the AMIS scraping was done before the event).
- **Each of us must be able to explain every AI component**: model, data, prompts, API and workflow.
- **A smaller working solution beats a large idea that cannot be demonstrated.** Use the cut list (section 7).

---

## 2. Team and ownership

| Owner | Person | Role | Owns (folders) |
|---|---|---|---|
| **A** | **Hamza** (git `muhammadhamza6002`; GitHub user to confirm) | **Data, Proof and Channels** | `data/`, `ml/features/`, `ml/ingest/`, `ml/seasonal/`, `ml/eval/`, `backend/app/channels/` (WhatsApp, SMS), `backend/app/chat/` (Gemini chat and voice), `docs/FACTS.md`, `docs/PROMPTS.md`, `docs/DATA_NOTES.md`, the slides |
| **B** | **Usman** (GitHub user to confirm) | **Models and Advisory Engine** | `ml/forecast/`, `ml/explain/`, `ml/decision/`, `artifacts/` (model files and model metadata), `docs/MODEL_CARD.md` |
| **C** | **Abd** (git "Abd"; GitHub user to confirm, likely the repo owner `Muhammad-Abdullah24`) | **Product: API, Web App, Deployment** | `backend/` (except `channels/` and `chat/`), `frontend/`, `README.md`, `CLAUDE.md`, `docs/DEMO.md`, `.github/`, deployment |

**Shared files.** `docs/BLUEPRINT.md`, `docs/PLAN.md` and `backend/app/schemas.py` change only by agreement at a check-in. When the API shape changes, C changes `schemas.py` and blueprint section 12 in the same commit and regenerates the front-end types.

**Why this split.** The data is already done, so A has capacity: A takes the channels (WhatsApp, SMS, Gemini chat and voice), which the blueprint lists as an "Integration" role. C keeps the largest surface (API and all screens), so C's tasks are kept to that. B owns everything that turns features into a decision.

**Balancing rule.** At the Saturday 13:00 check-in, if C is behind, A takes the Chat screen and the Register screen; if B is behind, A takes the seasonal crop-plan logic (B7).

---

## 3. Architecture in one picture (who owns which box)

```
OFFLINE (laptops)                                   RUNTIME (FastAPI, deployed)
───────────────────────────────────                 ─────────────────────────────────────────────────
AMIS 2015–2026 ─▶ data/processed/  [A]              React app [C] ◀── REST /api/* [C] ──▶ SQLite [C]
Open-Meteo     ─▶ features.csv     [A]                                    │       (farmers, forecasts,
economics_inputs.json              [A]                                    │        alerts, messages)
                    │                                                     ├─▶ ml/forecast/predict.py [B]
                    ├─▶ ml/forecast/train.py [B] ─▶ artifacts/models/ [B] │      (loads artifacts/models)
                    ├─▶ ml/eval/  NFR-01 gate [A]                         ├─▶ ml/decision/ engine   [B]
                    └─▶ ml/seasonal/ ─▶ data/processed/runtime/ [A]       ├─▶ weather service [C] ─▶ Open-Meteo
                                                                          │      uses ml/features [A]
                                                                          └─▶ channels/ + chat/ [A]
                                                                                 WhatsApp · SMS · Gemini
```

Only weather (and Gemini, WhatsApp, SMS) is live. Prices, tables and models are prepared offline and read at runtime (blueprint NS-10).

---

## 4. Interfaces between owners (agree in Phase 0, then freeze)

Each interface has one owner who writes it and a stub that works from the first hour, so nobody is blocked.

| ID | Interface | Owner | Used by | Stub by |
|---|---|---|---|---|
| **I1** | **Features.** `ml/features/`: `price_features(series_history, as_of) -> dict` and `weather_features(daily_weather, week_start) -> dict`, plus `FEATURE_COLUMNS`. Column names identical to `data/processed/features.csv`. One code path for training and runtime | A | B (training), C (weather service, live predict) | Sat 01:00 |
| **I2** | **Forecast.** `ml/forecast/predict.py`: `forecast(crop_option, mandi, as_of, weather) -> dict` with `current_price, predicted_price, q10, q90, trend, volatility, prices_as_of, model_version, shap=[{feature, rs_effect, direction}], data_source, is_synthetic`. Prices Rs per 40 kg | B | C (endpoints), A (WhatsApp, chat) | Fri 23:30 (returns placeholder, `is_synthetic: true`) |
| **I3** | **Advisory engine.** `ml/decision/`: `advise(...)`, `compare_mandis(...)`, `crop_plan(...)`, `selling_window(...)`, `offer_check(...)`, `margin(...)`, `alert_check(...)`. Pure Python, no third-party imports, unit-tested | B | C, A | Sat 01:00 |
| **I4** | **API contract.** Blueprint section 12, implemented in `backend/app/schemas.py`; front-end types generated from it | C | Front end, A's channels | Fri 23:30 (endpoints return placeholder data) |
| **I5** | **Runtime tables.** `data/processed/runtime/`: `crops.csv`, `mandis.csv`, `crop_calendar.csv`, `support_prices.csv`, `transport_costs.csv`, `series_coverage.csv` (per-series `prices_as_of` and `is_stale`), `frozen_stretches.csv` (A12), `data_sources.csv`, and from A6 `seasonal_index.csv`, `harvest_ratios.csv`, `post_harvest_ratios.csv`. Columns follow blueprint section 9; every value carries a source and confidence | A | C (seed SQLite), B (engine) | Sat 01:00 |
| **I6** | **Service layer.** `backend/app/services.py`: the functions the REST routes call (`get_advice`, `get_forecast`, `compare`, …). WhatsApp, SMS and chat call these same functions, so every channel gives the same answer | C | A | Sat 10:00 |

**Data facts every owner needs** (details in `docs/DATA_NOTES.md` and blueprint section 9):

- Crop options: `Wheat`, `Cotton`, `IRRI`, `SuperBasmati` (`crop_option` column). 11 series; **no IRRI at Rahim Yar Khan**. Super Basmati's latest prices are Nov 2025 to Apr 2026, so show its date in amber.
- AMIS stores Rs per 100 kg; **every API price is Rs per 40 kg** (× 0.4). Convert in one place: `ml/features/`.
- Split in `features.csv`: train = target week before 2025, val = 2025, test = 2026. Train on **real rows only** (`is_synthetic = 0`).
- Persistence baseline MAPE: 4.7% train, 5.6% val, 3.4% test. That is the bar (NFR-01). Without frozen weeks (A12) it is 6.66% on val.
- Vehari wheat's latest AMIS price is 17 Jul 2026 (stale). Bahawalpur wheat, the headline case, is current but was frozen at Rs 3,450 from Jun to Sep 2026.

### 4.1 Hand-offs: work that finished tasks created for other owners

**Keep this list current.** Whenever a change in your folders means another owner has to do something (a new
column, a changed fact, a new table to load), add a line here **in the same PR**, assigned to them. Each owner
ticks their own lines when done. Claude sessions show the owner their open lines at the start of every session
(see `CLAUDE.md`). Newest at the bottom of each list.

**For Usman (Owner B)**

- [ ] **H-B1** (from A1) In `ml/forecast/predict.py`, build model inputs with `ml.features.runtime_features(city, crop, variety, history, daily_weather, week_start)`. It returns exactly the training columns. `FEATURE_COLUMNS` lists every allowed input; choose from it.
- [ ] **H-B2** (from A1) The `action` column in `features.csv` is a legacy label (it includes a Rs 15 storage cost). Don't use it as the product rule; the blueprint's SELL/WAIT rule (5%, interest only) lives in your engine (B2).
- [ ] **H-B3** (from A2) Read costs, yields and support prices from `data/processed/runtime/` (`crops.csv`, `support_prices.csv`), not hardcoded values. Rice cost is per 40 kg of **milled-rice equivalent** while yield is in **paddy** maund: milled maund per acre = `yield_maund_per_acre × milling_yield` (0.65, an assumption).
- [ ] **H-B4** (from A2) Wheat support prices were corrected: Rs 3,900 for the 2023-24 crop (spring 2024) was **announced but not procured**; the 2024-25 crop had **no** support price; 2025-26 is Rs 3,500 (indicative). Only wheat has a support price. Use the `status` column.
- [ ] **H-B5** (from A2) If `series_coverage.csv` says `is_stale = 1` (all Super Basmati, Vehari wheat), set confidence to LOW in `advise()`.
- [ ] **H-B6** (from A5) Score every model with the gate: write predictions for **every** validation row (`series, week_start, pred_price_next_4w, q10, q90`), run `python -m ml.eval.gate --predictions <file> --model <name>`, commit the regenerated `ml/eval/report.json` and `report.md`. If it fails, ship the `persistence_band` fallback (79–81% coverage).
- [ ] **H-B7** (from A6) In `crop_plan()`, key `harvest_ratios.csv` on the **month of the latest price**, not today's month (cotton has no mandi price from March to June). Use `enough_years` and `spread_pct` for the risk badge; pick the selling window from `post_harvest_ratios.csv` after interest per month.
- [ ] **H-B8** (from A12) Never use `price_is_frozen` or `target_is_frozen` as model inputs: they look at days after the week. Try training with and without frozen rows (`is_frozen` rows are a third of val/test) and report the gate both ways in `docs/MODEL_CARD.md`.
- [ ] **H-B9** (from Super Basmati) Super Basmati has only 10 test rows (Bahawalpur) and stale prices; judge it on validation and say so in the model card.

**For Abd (Owner C)**

- [ ] **H-C1** (from A2) Seed SQLite from `data/processed/runtime/`: `crops.csv`, `mandis.csv`, `crop_calendar.csv`, `support_prices.csv`, `transport_costs.csv`, `series_coverage.csv`, `data_sources.csv`, `frozen_stretches.csv`, plus A6's three seasonal tables. Every table has source/confidence columns; show "estimate" in the UI where confidence is `assumption` or `derived`.
- [ ] **H-C2** (from A2) Mandis have two names: `amis_name` (BahawalPur, RahimYarKhan; used in every data file) and `name` (Bahawalpur, Rahim Yar Khan; for display). Crop options are `Wheat`, `Cotton`, `IRRI`, `SuperBasmati`; no IRRI at Rahim Yar Khan.
- [ ] **H-C3** (from A2) "Prices as of" is **per series**: take it from `series_coverage.csv` (`prices_as_of`, `is_stale`), never one global date. Stale → date in amber (blueprint UC-01 A3).
- [ ] **H-C4** (from A2) Margin view: support price line for wheat only, from `support_prices.csv`; label `ANNOUNCED_NOT_PROCURED` as "announced, not procured". There is no 2024-25 row on purpose (no support price that year).
- [ ] **H-C5** (from A1) Weather service: fetch Open-Meteo daily with `past_days=92` and pass records to `ml.features.weather_features(daily, week_start)` with keys `date, tmax, tmin, precip_mm, rh_mean, et0` (Open-Meteo daily `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, `relative_humidity_2m_mean`, `et0_fao_evapotranspiration`; check the names against the API).
- [ ] **H-C6** (from A6) Price history chart: the seasonal pattern comes from `seasonal_index.csv` (% of the 12-month moving average). What to Grow: for cotton from March to June, show "no mandi price this month, using <latest month>" instead of today's price.
- [ ] **H-C7** (from A12) If a series' latest price falls inside a `frozen_stretches.csv` stretch, show "price unchanged since <from_date>" and lower the confidence.
- [ ] **H-C8** (from A7) `docs/DEMO.md`: show "AMIS mandi price, as of <date>" on the headline card; backup weeks are 2025-03-24 (−19.7%, sell early) and 2025-08-04 (+48.6%, wait), and 2026-03-16 only after the final test run; avoid 2026-08-31 and 2026-09-07 (frozen artifacts); prepare the Rs 5,300 answer (open-market rate; AMIS mandis 3,475–4,700). Details: `docs/DATA_NOTES.md` section A7.
- [ ] **H-C9** (from A2/A5/A6/A12) Add the new commands to the README "Common tasks" and the data files to the acknowledgements (A4 will send the dataset lines).

**For Hamza (Owner A)** (filled by Usman and Abd when their changes need data work)

- *(none yet)*

---

## 5. Phases and tasks

Times are local. Each task has an ID, an owner, a priority and a "done when". Tick the box in your PR when it merges. Priority: **M** = must (demo path), **S** = should, **C** = could (first to cut).

### Phase 0 — Agree (Fri 21:00 to 22:00) · all three

- [ ] **P0.1** Everyone reads `docs/BLUEPRINT.md` and this file. Fill in Owner B's name in section 2 and in `CLAUDE.md` (done: Usman).
- [ ] **P0.2** Walk through interfaces I1 to I6 together. Agree the function signatures and freeze them.
- [ ] **P0.3** Each person: Python 3.11, Node 20.19+, repo cloned, `README.md` setup done, `git config user.name/email` set to your own account, Claude Code started from the repo root.
- [ ] **P0.4** Merge this plan's PR.

### Phase 1 — Setup (Fri 22:00 to Sat 01:00)

**A · Hamza**
- [x] **A1** (M) Port the feature builder to Python in `ml/features/` (I1). *Done when* regenerating `features.csv` from `farmsight_prices_clean_weekly.csv` and the weather file matches the committed file (same rows; numbers within rounding).
- [x] **A2** (M) Write the runtime tables (I5) from `economics_inputs.json` and the clean data: costs, yields, milling yield, calendar, support prices with status, transport costs, per-series `prices_as_of`. *Done when* every value has a `source` and `confidence` column.
- [ ] **A3** (S) Create the Meta WhatsApp Cloud API app and test number; register all three demo phones; get the Gemini key (as `FS_LLM_API_KEY` in `.env`); check free-tier limits (blueprint decision 14).
- [ ] **A4** (S) README data acknowledgements and AMIS terms of use (blueprint decision 22). Send the lines to C.

**B · Usman**
- [ ] **B1** (M) `ml/forecast/predict.py` stub returning placeholder values in the I2 shape, `is_synthetic: true`. *Done when* C can import it. **First task: by 23:30.**
- [ ] **B2** (M) Rewrite `ml/decision/engine.py` to the blueprint (I3): SELL / WAIT at the 5% threshold (in config), confidence from the q10 to q90 width, net rupee impact = quantity × (forecast − today) − interest (16.5% a year), optional arhti commission, fair price range, offer check, margin, mandi comparison net of transport. *Done when* unit tests cover each function, including IRRI with no Rahim Yar Khan price.
- [ ] **B3** (M) Training scaffold `ml/forecast/train.py`: XGBoost on real `features.csv` rows, target `price_change_4w_pct` (not price level, since prices rose about 3×), fixed seed, train/val split as given.

**C · Abd**
- [ ] **C1** (M) Replace the API contract in `schemas.py` with blueprint section 12 (forecast, explain, advice, compare-mandis, crop-plan, offer-check, margin, history, weather, meta, auth, farmers, chat). Stub every endpoint with placeholder data (`is_synthetic: true`). Regenerate front-end types. *Done when* CI is green and `/docs` lists every endpoint.
- [ ] **C2** (M) SQLite schema from blueprint section 9, seeded from A's runtime tables (I5) on startup. A pre-seeded demo farmer ("Ahmed", Bahawalpur, wheat and cotton, 100 maund). Login by phone returns a JWT.
- [ ] **C3** (S) Retire code built for the superseded plan: the four-verdict engine paths, replay, alerts/events and backtest endpoints and screens. Delete or move to `legacy/`; keep the Urdu, RTL, chart and verdict-card pieces that fit.

**Check-in Fri 23:30:** are the I2 and I4 stubs merged? Is anyone blocked?

### Phase 2 — Core (Sat 08:00 to 14:00) · must-work path on real models

**A · Hamza**
- [x] **A5** (M) Evaluation gate in `ml/eval/` (NFR-01): MAPE pooled and per crop option vs persistence on real validation rows; directional accuracy on moves over 3%; q10 to q90 coverage (target about 80%). Test set only once, at the end. Output `ml/eval/report.json` and a short table for the slides.
  *How Usman uses it:* write a predictions CSV for every validation row (`series, week_start, pred_price_next_4w, q10, q90`, Rs per 40 kg), then run `python -m ml.eval.gate --predictions <file> --model <name>`. It reports MAPE, MASE vs persistence, direction on moves over 3%, band coverage and width, pooled and per crop, plus the PASS/FAIL verdict. Usman may commit the regenerated `ml/eval/report.json` and `report.md`; nothing else in `ml/eval/`. The test split needs `--split test --final` and can be used once. Baseline on validation: persistence MAPE 5.60%; persistence band covers 81% at 15.8% width (the B4 fallback); seasonal naive 7.65% (worse).
- [x] **A6** (M) Seasonal tables in `ml/seasonal/` → `data/processed/runtime/seasonal.csv`: monthly index (% of each year's average) and harvest-month ratios (median, min, max, number of years) per crop option and mandi. Feeds What to Grow, the selling window and the history chart.
  *Built:* `python -m ml.seasonal.tables` writes three tables from the daily AMIS prices, each with median, min, max, `spread_pct` and `n_years` across years (`enough_years` = at least 3). `seasonal_index.csv`: each month as % of the 12-month moving average around it (removes the ~3x inflation trend). `harvest_ratios.csv`: next-harvest price / price in a reference month. `post_harvest_ratios.csv`: price k months after harvest starts / harvest-start price.
  *How Usman uses them (B7):* harvest estimate = latest price × `harvest_ratios.ratio_median` for the **month of that latest price** (cotton has no mandi price from March to June, so key on the price's month, not today's). Selling window = the `offset_months` with the best `ratio_median` after interest for that many months. Risk badge from `spread_pct`.
  *Findings:* wheat peaks before harvest (about 104–105% of trend in Feb–Mar) and dips at harvest (about 94–95% in May–Jun). After the April harvest the median wheat ratio stays within about ±2% for 5 months, below the ~1.4%/month interest, so holding rarely pays on average, with wide year-to-year spread. Cotton trades at mandis July to February; the crop calendar's cotton harvest (Sep–Dec) is an assumption that starts later than the data's July prices.
- [x] **A7** (S) Check the headline demo case in the data: Wheat at Bahawalpur now (AMIS about Rs 3,820 vs about Rs 5,300 reported), and prepare a backup historical date (spring 2024 harvest).
  *Result (docs/DATA_NOTES.md, section A7):* AMIS is not lagging across Punjab; South Punjab mandis are at the low end (Oct 2026: Bahawalpur 3,820, Rahim Yar Khan 3,475, Punjab mandi median 4,450, max 4,700). The Rs 5,300 is an open-market rate, not a mandi price. But Bahawalpur wheat was frozen at Rs 3,450 for 75 days (Jun–Sep 2026), and frozen prices are common in rice (Vehari IRRI 66% of days). Backup demo weeks, all held out: 2025-03-24 (−19.7%, sell early), 2025-08-04 (+48.6%, wait), 2026-03-16 (−21.8%, test split). **For Abd (docs/DEMO.md)** and **Usman (frozen rows inflate persistence).**
- [x] **A12** (S) Flag frozen AMIS stretches (same price on ≥ 28 reported days in a row; `ml/ingest/frozen.py`).
  *Done:* `features.csv` gains `price_is_frozen` and `target_is_frozen` as the **last two columns** (every earlier column and row unchanged). **Usman: these are evaluation-only flags, never model inputs** (spotting a 28-day stretch needs days after the week). The gate now scores every model on all rows (the official NFR-01 verdict) and excluding frozen rows: persistence MAPE on validation is 5.60% on all rows and **6.66% without frozen weeks** (108 of 328 rows), so frozen weeks flatter the baseline. New runtime table `frozen_stretches.csv` (59 stretches). **Abd:** if a series' latest price is inside a stretch, show "price unchanged since <from_date>" and set confidence LOW (like UC-01 A3).

**B · Usman**
- [ ] **B4** (M) Train the point model and the q10 and q90 quantile models. Run A's gate. If the model does not beat persistence on validation, ship the fallback: persistence as the point forecast and the range from the empirical 4-week change distribution, labelled "baseline" (blueprint NFR-01). Write the result in `docs/MODEL_CARD.md` either way.
- [ ] **B5** (M) SHAP TreeExplainer and a feature-to-sentence map in Urdu and English (top 3 to 5 factors with rupee effects). No LLM writes these reasons.
- [ ] **B6** (M) Real `predict.py`: load `artifacts/models/`, build features with I1, return the I2 shape with `is_synthetic: false`.
- [ ] **B7** (M) `crop_plan()` and `selling_window()` in the engine from A6's tables: profit per acre = harvest estimate × yield − cost per acre, risk badge from the year-to-year spread, best selling month window net of interest.

**C · Abd**
- [ ] **C4** (M) Wire `/forecast`, `/advice`, `/explain`, `/compare-mandis`, `/meta` to B's predict and engine through the service layer (I6).
- [ ] **C5** (M) Weather service: Open-Meteo with `past_days=92`, aggregated with A's `weather_features`, cached up to 1 hour in SQLite, `weather_cached` flag on fallback.
- [ ] **C6** (M) Screens: Home (big SELL/WAIT card, today → 4 weeks with range, "AMIS mandi price, as of" date), Sell advice, Why. Urdu first, RTL, 360 px.

**Check-ins Sat 10:00 and 13:00:** does the must-work path run on real models? Apply the balancing rule at 13:00.

### Phase 3 — Features (Sat 14:00 to 20:00)

**A · Hamza**
- [ ] **A8** (S) WhatsApp webhook in `backend/app/channels/whatsapp.py`: signature check; "گندم بہاولپور 100 من" style text → advice through I6; quick replies Why / Compare mandis / Stop alerts.
- [ ] **A9** (S) Gemini chat `/api/chat` in `backend/app/chat/`: context is the farmer's own forecast and advice; prompt in `docs/PROMPTS.md`; uses only the numbers given; template fallback; rate limit.
- [ ] **A10** (C) Voice notes: Gemini transcription, "Did you mean …?" confirmation, audio deleted after (web and WhatsApp).
- [ ] **A11** (C) SMS gateway webhook `backend/app/channels/sms.py` with the 160-character format and number menu.

**B · Usman**
- [ ] **B8** (S) `alert_check()`: signal change or unusual price, at most one alert per farmer per week.
- [ ] **B9** (S) History function: 52-week series and the seasonal pattern for the history chart.
- [ ] **B10** (S) `docs/MODEL_CARD.md` for judges: data, features, model, gate result vs baseline, SHAP, limits. One page.

**C · Abd**
- [ ] **C7** (M) Screens: Compare Mandis, What to Grow with the season timeline.
- [ ] **C8** (S) Screens: offer check, margin, Register/Profile (district dropdown first; map pin if time), Chat (uses A9 and A10).
- [ ] **C9** (S) APScheduler alert job: B8's check → A8's WhatsApp sender, SMS fallback.
- [ ] **C10** (M) Deploy: front end on Vercel, backend on Render or Hugging Face Spaces; environment variables set; link opens on a phone on mobile data.

**Check-ins Sat 16:00 and 19:00.**

### Phase 4 — Polish (Sat 20:00 to 23:30) · feature freeze at 23:30

- [ ] **P4.1** (C) Price history screen (C), if not cut.
- [ ] **P4.2** (all) Urdu copy review by a native speaker; fallbacks tested (LLM down, weather down, WhatsApp down).
- [ ] **P4.3** (A) Honesty checklist (section 8) and slides with real numbers from `ml/eval/report.json`.
- [ ] **P4.4** (C) `docs/DEMO.md` with real app output replacing every placeholder (blueprint decision 12). Tag `demo-v1` when the full flow works.
- [ ] **P4.5** (all) Record the backup screen capture of the whole demo.

### Phase 5 — Demo (Sun 07:30 to 10:30)

- [ ] Rehearse the five minutes at least five times with a timer. Every one of us speaks.
- [ ] Wake the server, test the deployed link on a hotspot, re-check the WhatsApp test number and demo phones.
- [ ] Load the demo locally on the laptop as a backup. Leave for the hall at 10:30.

---

## 6. What happens to the code already in the repo

| Existing piece | Fate |
|---|---|
| FastAPI app, `schemas.py` pattern, startup validation, CI, OpenAPI → TypeScript generation | **Keep.** C changes the contents to the blueprint contract |
| React shell, Urdu i18n, RTL tests, logical-class lint rule, fonts, verdict card, Forecast chart | **Keep and adapt** to SELL / WAIT and the blueprint screens |
| `ml/decision/engine.py` (four verdicts, storage, spoilage) | **Rewrite** to the blueprint rule (B2). Keep the pure-Python, tested style |
| Replay, alerts/events, backtest endpoints and screens; `ml/alarm/`, `ml/events/`, `data/events/` | **Not in the blueprint.** Retire (C3); A may reuse events later only if agreed |
| `ml/precompute.py`, placeholder `artifacts/*.json` | Replaced by `artifacts/models/` and `data/processed/runtime/`. Remove once B6 and A2 land |
| `data/processed/` cleaned data and `features.csv` | **Keep.** This is the training data |

**Stale references.** Comments in the existing code and in `README.md`, `docs/DEMO.md`, `docs/FACTS.md`, `docs/PROMPTS.md` and `docs/DATA_NOTES.md` cite "PLAN.md section N". Those numbers refer to the archived plan. Each owner updates their own files as they touch them (C: README and code; A: FACTS, PROMPTS, DATA_NOTES).

---

## 7. Cut list

If we are behind at a check-in, cut from the top. Do not debate it.

1. SMS gateway (A11)
2. Voice notes (A10)
3. Alert scheduler (C9). Show one manual WhatsApp alert instead
4. Price history screen (P4.1, B9)
5. Map pin on Register (district dropdown only)
6. Margin view (part of C8)
7. Offer check (part of C8)
8. Web chat screen (keep WhatsApp text)
9. Volatility rating
10. JWT login (use the pre-seeded profile only)

**Never cut:** real data and the honest baseline comparison, the Wheat-at-Bahawalpur forecast with range, the Urdu SELL / WAIT signal with net rupee impact, Why, Compare Mandis, What to Grow with the selling window, the deployed link.

---

## 8. Honesty and compliance checklist (run before the freeze and before submitting)

- [ ] Every number in the UI and on slides comes from data, models or `docs/FACTS.md`. None typed by hand.
- [ ] The model is shown next to the naive baseline, including any crop where the model loses.
- [ ] Assumed values are labelled "estimate": transport rate, milling yield, Super Basmati cost.
- [ ] Each screen shows the source and the "prices as of" date. Super Basmati's old dates show in amber.
- [ ] No synthetic training row reaches validation, test or any metric we show.
- [ ] The LLM never produces a number shown to users.
- [ ] Every prompt is in `docs/PROMPTS.md`.
- [ ] The README lists every dataset, library, API, model and AI coding assistant, and discloses the pre-event AMIS scraping.
- [ ] No API key is in the repo or its history. The repo is public.
- [ ] Commits exist from all three accounts.
- [ ] Each of us can explain the forecast model, SHAP, the advisory rule and the data.

---

## 9. How we work

### 9.1 Git

1. `main` always runs and is what the deployed link shows.
2. Work on a short branch `yourname/task-id`, e.g. `hamza/A1-features`. Open a pull request; merge when CI is green. Merge every one to two hours.
3. Pull `main` before starting each task.
4. Never force-push to `main`. Commit under your own GitHub account.
5. Put task IDs in commit messages and PR titles (`A1: port feature builder to Python`).
6. Keys go in the ignored `.env`, shared outside git.

### 9.2 Working with Claude Code (three Claude Pro accounts, one shared context)

The repo is the shared context: `CLAUDE.md`, `docs/BLUEPRINT.md`, this plan and the merged code are the same for all three sessions. Nothing important lives only in one person's chat.

- Start every session from the repo root so it reads `CLAUDE.md`.
- Start with the kickoff prompt below for your owner letter.
- When a session learns something the others need (a changed signature, a data quirk, a decision), it goes into the repo: this plan, the blueprint, `docs/DATA_NOTES.md` or the PR description. Never only in chat. If it creates work for another owner, it is a hand-off line in section 4.1.
- If your session wants to edit outside your folders, stop and message that owner.
- Read what Claude writes before you merge. Judges may ask any of us about any part.

**Kickoff prompts** (paste as the first message of a session):

> **Owner A (Hamza):** I am Owner A (Data, Proof and Channels) on FarmSight. Read CLAUDE.md, docs/BLUEPRINT.md and docs/PLAN.md. Then show me my open hand-offs (H-A*) in section 4.1 and my open tasks (A*) in docs/PLAN.md section 5, the interfaces I own in section 4, and start the next unticked task on a branch named hamza/<task-id>. Only edit my folders.

> **Owner B (Usman):** I am Owner B (Models and Advisory Engine) on FarmSight. Read CLAUDE.md, docs/BLUEPRINT.md and docs/PLAN.md. Then show me my open hand-offs (H-B*) in section 4.1 and my open tasks (B*) in docs/PLAN.md section 5, the interfaces I own in section 4, and start the next unticked task on a branch named usman/<task-id>. Only edit my folders.

> **Owner C (Abd):** I am Owner C (Product: API, Web App, Deployment) on FarmSight. Read CLAUDE.md, docs/BLUEPRINT.md and docs/PLAN.md. Then show me my open hand-offs (H-C*) in section 4.1 and my open tasks (C*) in docs/PLAN.md section 5, the interfaces I own in section 4, and start the next unticked task on a branch named abd/<task-id>. Only edit my folders.

### 9.3 Check-ins

Five minutes, standing up: **Fri 23:30; Sat 10:00, 13:00, 16:00, 19:00, 22:00; Sun 08:00.** Each person answers: What did I merge? What am I blocked on? Does `main` still run for me? Which hand-offs (section 4.1) did I create or close? Decisions made at a check-in go into this file the same hour.

### 9.4 Demo roles

- **Hamza:** problem and data (real AMIS data, honest baseline), then WhatsApp live.
- **Usman:** how the AI works (model, range, SHAP, the advisory rule) and the accuracy vs baseline.
- **Abd:** the app walk-through (Home → Why → Compare → What to Grow) and the close.

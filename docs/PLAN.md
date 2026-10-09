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

**Cover arrangement (10 Oct):** Abd is away, so **Hamza is doing Owner C's tasks** for now. Everything done in Owner C's folders is listed in section 4.2, so Abd can pick up exactly where it stands. Ownership itself does not change.

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

- [x] **H-B1** (from A1) In `ml/forecast/predict.py`, build model inputs with `ml.features.runtime_features(city, crop, variety, history, daily_weather, week_start)`. It returns exactly the training columns. `FEATURE_COLUMNS` lists every allowed input; choose from it.
- [x] **H-B2** (from A1) The `action` column in `features.csv` is a legacy label (it includes a Rs 15 storage cost). Don't use it as the product rule; the blueprint's SELL/WAIT rule (5%, interest only) lives in your engine (B2).
- [x] **H-B3** (from A2) Read costs, yields and support prices from `data/processed/runtime/` (`crops.csv`, `support_prices.csv`), not hardcoded values. Rice cost is per 40 kg of **milled-rice equivalent** while yield is in **paddy** maund: milled maund per acre = `yield_maund_per_acre × milling_yield` (0.65, an assumption).
- [x] **H-B4** (from A2, updated in A4) Wheat support prices, from the AMIS official table: 2021-22 Rs 2,200; 2022-23 Rs 3,900; Rs 3,900 for the 2023-24 crop (spring 2024) was **announced but not procured**; the 2024-25 crop had **no** support price; 2025-26 is Rs 3,500 (indicative). Only wheat has a support price. Use the `status` column.
- [x] **H-B5** (from A2) If `series_coverage.csv` says `is_stale = 1` (all Super Basmati, Vehari wheat), set confidence to LOW in `advise()`.
- [x] **H-B6** (from A5) Score every model with the gate: write predictions for **every** validation row (`series, week_start, pred_price_next_4w, q10, q90`), run `python -m ml.eval.gate --predictions <file> --model <name>`, commit the regenerated `ml/eval/report.json` and `report.md`. If it fails, ship the `persistence_band` fallback (79–81% coverage).
- [x] **H-B7** (from A6) In `crop_plan()`, key `harvest_ratios.csv` on the **month of the latest price**, not today's month (cotton has no mandi price from March to June). Use `enough_years` and `spread_pct` for the risk badge; pick the selling window from `post_harvest_ratios.csv` after interest per month.
- [x] **H-B8** (from A12) Never use `price_is_frozen` or `target_is_frozen` as model inputs: they look at days after the week. Try training with and without frozen rows (`is_frozen` rows are a third of val/test) and report the gate both ways in `docs/MODEL_CARD.md`.
- [x] **H-B10** (from services, 10 Oct) `backend/app/services.py` calls your `ml.forecast.predict.forecast(crop_option, mandi, as_of: date, weather)` automatically as soon as the module exists (interface I2). Return `current_price, predicted_price, q10, q90, model_version, data_source, is_synthetic, shap=[{text_ur, direction}]` in Rs per 40 kg. `weather` is `None` until the weather service (C5) lands, so handle that. Until then the app uses the labelled `baseline_persistence_band`.
- [x] **H-B11** (from services, 10 Oct) The blueprint SELL/WAIT rule (5%, interest subtracted), confidence and trend are currently computed inline in `services.get_advice`. When your `ml/decision` engine (B2) has them, say so in a hand-off for Owner C and the service will call your engine instead, so the rule lives in one place.
- [x] **H-B12** (from C1, 10 Oct) The API no longer serves `artifacts/` (the old placeholder forecasts, replay and backtest files); every endpoint now reads the real data through `services.py`. `python -m backend.app.check_artifacts` still validates the placeholders in CI. When your `predict.py` loads its own model files, delete the placeholder `artifacts/*.json`, `backend/app/artifacts.py`, `artifact_schemas.py`, `check_artifacts.py` and its CI step together (or tell Owner C and they will).
- [x] **H-B13** (from C1, 10 Oct) *(answered by B7 and H-C18: the service now calls your crop_plan and selling_window)* `crop_plan()` and `selling_window()` currently live in `backend/app/services.py`, built from A6's tables exactly as H-B7 describes (rice yield × milling yield, risk LOW < 30% spread < MEDIUM < 60% < HIGH, HIGH with fewer than 3 years). When B7 lands in `ml/decision`, keep the same outputs (`CropPlanItem` in `schemas.py`) and Owner C swaps the call. Same for `offer_check` (fair range = min/max of the last 14 days of prices) and `margin`.
- [x] **H-B14** (from C9, 10 Oct) *(answered by B8 and H-C19: alerts call your alert_check)* The alert rule lives in `backend/app/alerts.py` until your `alert_check()` (B8) exists: alert when nothing was sent before, when the signal flips, or when the price moved ≥ 10% since the last alert; at most one message per farmer per week (dates are the check's `as_of`). When B8 lands, keep that behaviour or say what changed in a hand-off, and Owner C calls yours.
- [x] **H-B15** (from H-C16–H-C19, 10 Oct) Owner C now calls your engine everywhere. Four things for you: (1) `backend/` no longer imports `ml.decision.engine`; only `ml/precompute.py` does, so the old engine, `precompute.py` and the placeholder `artifacts/*.json` can go together with H-B12. (2) `inputs.latest_price`, `crop_plan_inputs` and `alert_candidate` read only the latest data, so the service builds those inputs itself to honour `as_of` (the demo replays past weeks); an `as_of` parameter on them would let it call yours directly. (3) The service raises the crop-plan risk one level when the starting price is stale; move that into `risk_badge` if you agree. (4) With `LOW_RISK_MAX_SPREAD_PCT = 20` and `MEDIUM = 40`, every crop at Bahawalpur shows HIGH risk; check that is what you want.
- [ ] **H-B16** (from A11, 10 Oct) SMS replies are Roman Urdu, but `ml/explain` reasons come only as `text_ur` and `text_en`, so the SMS "why" uses the English sentence. Add a `text_roman` (Roman Urdu) template per reason group if we want SMS fully in Roman Urdu; `sms_reply.why_sms` would then prefer it. When the action plan (PR #4) reaches `services.get_advice`, `reply.advice_text` (WhatsApp) and `sms_reply.advice_sms` are the two places that show it.
- [x] **H-B9** (from Super Basmati) Super Basmati has only 10 test rows (Bahawalpur) and stale prices; judge it on validation and say so in the model card.

**For Abd (Owner C)**

- [x] **H-C1** *(done by Hamza, 10 Oct: the runtime tables are read-only, so `services.py` loads them straight from `data/processed/runtime/` at start-up instead of copying them into SQLite; SQLite holds only runtime records (farmers, logs, alerts). Margin shows the cost confidence)* (from A2) Seed SQLite from `data/processed/runtime/`: `crops.csv`, `mandis.csv`, `crop_calendar.csv`, `support_prices.csv`, `transport_costs.csv`, `series_coverage.csv`, `data_sources.csv`, `frozen_stretches.csv`, plus A6's three seasonal tables. Every table has source/confidence columns; show "estimate" in the UI where confidence is `assumption` or `derived`.
- [x] **H-C2** *(done by Hamza, 10 Oct: the API uses lowercase ids (`wheat`, `super_basmati`, `rahim_yar_khan`); `backend/app/ids.py` maps them to the data names)* (from A2) Mandis have two names: `amis_name` (BahawalPur, RahimYarKhan; used in every data file) and `name` (Bahawalpur, Rahim Yar Khan; for display). Crop options are `Wheat`, `Cotton`, `IRRI`, `SuperBasmati`; no IRRI at Rahim Yar Khan.
- [x] **H-C3** *(done by Hamza, 10 Oct: every price carries its own `prices_as_of` and `is_stale`; stale dates show in amber)* (from A2) "Prices as of" is **per series**: take it from `series_coverage.csv` (`prices_as_of`, `is_stale`), never one global date. Stale → date in amber (blueprint UC-01 A3).
- [x] **H-C4** *(done by Hamza, 10 Oct: Margin screen)* (from A2) Margin view: support price line for wheat only, from `support_prices.csv`; label `ANNOUNCED_NOT_PROCURED` as "announced, not procured". There is no 2024-25 row on purpose (no support price that year). A 2022-23 row (Rs 3,900) was added in A4 from the AMIS official table.
- [x] **H-C5** *(done by Hamza, 10 Oct: `backend/app/weather.py`; daily records go to the model only when one exists and never for a past `as_of`)* (from A1) Weather service: fetch Open-Meteo daily with `past_days=92` and pass records to `ml.features.weather_features(daily, week_start)` with keys `date, tmax, tmin, precip_mm, rh_mean, et0` (Open-Meteo daily `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, `relative_humidity_2m_mean`, `et0_fao_evapotranspiration`; check the names against the API).
- [x] **H-C6** *(done by Hamza, 10 Oct: History screen; What to Grow says which month's price each estimate starts from)* (from A6) Price history chart: the seasonal pattern comes from `seasonal_index.csv` (% of the 12-month moving average). What to Grow: for cotton from March to June, show "no mandi price this month, using <latest month>" instead of today's price.
- [x] **H-C7** *(done by Hamza, 10 Oct: `price_unchanged_since` in forecast/advice, confidence LOW, note under the price)* (from A12) If a series' latest price falls inside a `frozen_stretches.csv` stretch, show "price unchanged since <from_date>" and lower the confidence.
- [x] **H-C8** (from A7) *(done by Hamza, 10 Oct: `docs/DEMO.md` with real output, backup weeks replayable in the app with `?as_of=`, judge answers)* `docs/DEMO.md`: show "AMIS mandi price, as of <date>" on the headline card; backup weeks are 2025-03-24 (−19.7%, sell early) and 2025-08-04 (+48.6%, wait), and 2026-03-16 only after the final test run; avoid 2026-08-31 and 2026-09-07 (frozen artifacts); prepare the Rs 5,300 answer (open-market rate; AMIS mandis 3,475–4,700). Details: `docs/DATA_NOTES.md` section A7.
- [x] **H-C9** *(done by Hamza, 10 Oct: commands, the A4 dataset rows and tool credits are in the README; the "Pre-existing work" line now states the facts (AMIS scripts written and run on 9 Oct 2026 with Claude Code). **Team to confirm** that wording before submitting)* (from A2/A5/A6/A12, A4) Add the new commands to the README "Common tasks". Paste the ready-made dataset rows from `docs/DATA_NOTES.md` section A4 into the README acknowledgements, and fix the "Pre-existing work" wording (the AMIS scraping scripts were written and run on 9 Oct 2026; see A4).
- [x] **H-C10** *(done by Hamza, 10 Oct: on every weather line and price label, and in the README)* (from A4) Open-Meteo's CC BY 4.0 licence needs a link wherever weather data is shown: add "Weather data by Open-Meteo.com" linking to https://open-meteo.com/ on every screen with weather (and the README). Credit "Source: AMIS Punjab" on every price.
- [x] **H-C11** (from A8) *(done by Hamza, 10 Oct: routers mounted, Twilio placeholder removed, `.env.example` updated; still to do on deploy: set the `FS_WA_*` values and the Meta callback URL)* In `backend/app/main.py`, mount the WhatsApp router: `from backend.app.channels import whatsapp` and `app.include_router(whatsapp.router)` (serves `GET/POST /webhooks/whatsapp`). Retire the Twilio placeholder `POST /whatsapp`. Add the `FS_WA_*` variables (listed at the top of `backend/app/channels/whatsapp.py`) to `.env.example`, and set them on the deployed backend. The Meta app's callback URL is `<deployed backend>/webhooks/whatsapp`.
- [x] **H-C12** (from A8) *(done by Hamza, 10 Oct: `backend/app/services.py`; see 4.2)* In `backend/app/services.py` (I6), provide the functions WhatsApp calls, so web and WhatsApp give the same answer: `get_advice(crop_option, mandi, quantity_maund, phone=None)` returning the blueprint advice dict plus `crop_option`, `mandi`, `interest_cost`, `prices_as_of`, `is_synthetic`; `get_explanation(crop_option, mandi)` returning `[{text_ur, direction}]`; `compare_mandis(crop_option, mandi, quantity_maund)` returning `[{mandi, net_price, transport_cost, gain_vs_preferred, has_data}]` best first; `set_alerts(phone, enabled)`. Raise `LookupError` when a crop has no price at a mandi (e.g. IRRI at Rahim Yar Khan). Until these exist, WhatsApp replies "service not ready". Note: `pyproject.toml` now also collects tests from `backend/app/channels`.
- [x] **H-C13** (from A9) *(done by Hamza, 10 Oct: route mounted, models in `schemas.py`, optional login (the farmer's district becomes the default mandi), chat stored in `chat_messages`, Chat screen. The phone is not sent to Gemini)* Mount the chat route: `from backend.app.chat import router as chat_router` and `app.include_router(chat_router.router)` (`POST /api/chat`). Move `ChatRequest` and `ChatResponse` from `backend/app/chat/router.py` into `schemas.py` and blueprint section 12, then regenerate the front-end types. When login (C2) exists, require the farmer's JWT and pass their phone to `chat.service.answer(..., phone=...)`; store each question and answer in `chat_sessions` / `chat_messages` (blueprint section 9, `used_fallback` included). Add `FS_LLM_MODEL` (default `gemini-3.5-flash-lite`), `FS_LLM_THINKING_LEVEL` (empty), `FS_LLM_RATE_PER_MIN` (default 10) and `FS_CHAT_RATE_PER_MIN` (default 20) to `.env.example`, and set `FS_LLM_API_KEY` on the deployed backend (Hamza shares the key outside git); `FS_LLM_API_KEY` is already there. README acknowledgements: "Google Gemini API (`gemini-3.5-flash-lite`), free tier, for chat rephrasing; prompts in docs/PROMPTS.md". The Chat screen (C8) shows `answer` as plain text (never HTML) and a small note when `used_fallback` is true. `pyproject.toml` now also collects tests from `backend/app/chat`.
- [x] **H-C14** *(done by Hamza, 10 Oct: `numpy` and `xgboost` are in `backend/requirements.txt` (SciPy locked in `constraints.txt`), so CI installs them and runs `ml/forecast/test_train.py`; README credits them)* (from B3) Training needs `numpy` and `xgboost` (`ml/forecast/requirements.txt`). Add both to the README acknowledgements. CI does not install them, so `ml/forecast/test_train.py` is skipped there; add `pip install -r ml/forecast/requirements.txt` to the CI backend job to run it. When B6 lands, the runtime `predict.py` needs `xgboost` in `backend/requirements.txt` (B will say when).
- [x] **H-C15** *(done by Hamza, 10 Oct: the card says the price is the simple estimate because the model did not beat it)* (from B4) The model failed NFR-01 (validation MAPE 5.64% vs persistence 5.60%), so the deployed forecast is the persistence-band **baseline** (`artifacts/models/deployed.json`): forecast = today's price, range from past 4-week changes. Label it "baseline" on screen. The predicted change is 0%, so the signal is always SELL. Details and the open direction-signal question: `docs/MODEL_CARD.md`.
- [x] **H-C16** *(done by Hamza, 10 Oct: `direction` in forecast, advice and explain; shown on Home and Why as "likely to rise / fall" with the 72% and "not a price forecast"; SHAP reasons shown as-is. Live weather goes to the model as weather.current()'s dict, which predict accepts. **Still a team decision:** keep the direction call on (switch: `DIRECTION_CROP_OPTIONS`))* (from B6) `ml.forecast.forecast()` is real now (`is_synthetic: false`). Changes to I2: `weather` is the list of Open-Meteo **daily** records (`date, tmax, tmin, precip_mm, rh_mean, et0`, as in H-C5), not an aggregated dict; None uses the stored history. New fields: `forecast_type` ("baseline"), `direction` (`{call: UP|DOWN, validation_accuracy_pct, model_version}` for wheat only, else null) and, in each `shap` item, `features`, `text_en`, `text_ur` (show these as-is on Why). Pending team agreement on the direction call (docs/MODEL_CARD.md proposal). The direction call needs `xgboost==3.2.0` and `numpy==2.4.6` in `backend/requirements.txt`; without them it switches off (logged) and everything else still works.
- [x] **H-C17** *(done by Hamza, 10 Oct: advice, compare, offer check and margin call `ml.decision`; interest is now 4 weeks (Rs 4,848 on 100 maund at Rs 3,820). `backend/` no longer imports `ml.decision.engine`; only `ml/precompute.py` does (see H-B15))* (from B2) The blueprint engine is `ml.decision` (`advise`, `compare_mandis`, `offer_check`, `margin`, `fair_price_range`, `confidence`); read its inputs with `ml.decision.inputs` (`interest_pct_per_year`, `transport_cost`, `production_cost_per_40kg`, `support_price`, `is_stale`). Prices Rs per 40 kg, quantities in maund. Switch `/advice` and `services.get_advice` to `advise()` so the SELL/WAIT rule lives in one place (answers H-B11), and tell Usman once `backend/` and `ml/precompute.py` no longer import `ml.decision.engine`, so B can delete the old engine (part of C3). Interest is for 4 weeks (weeks / 52), so it is about 7.7% lower than the blueprint section 12 example, which used one month.
- [x] **H-C18** *(done by Hamza, 10 Oct: `services.crop_plan` builds the inputs itself so `as_of` works, then calls `crop_plan` and `selling_window`; API gains `sell_at_harvest`, `sell_window_months` and the profit range; a stale price still raises the risk one level (H-B15))* (from B7) What to Grow: `ml.decision.crop_plan(ml.decision.inputs.crop_plan_inputs(mandi), land_area_acres)` ranks the crop options by profit per acre at the next harvest, with a price range, a profit range, a risk badge and `is_estimate: true`; crops without data come last (`has_data: false`, e.g. IRRI at Rahim Yar Khan). Show `prices_as_of` and amber when `is_stale` (Super Basmati ranks first everywhere on months-old prices; say so). Selling window: `ml.decision.selling_window(ml.decision.inputs.post_harvest_ratios(crop, mandi), ml.decision.inputs.interest_pct_per_year())` gives `best_month`, `window_months` and per-month `net_pct` after interest; `sell_at_harvest: true` means holding does not pay. Sowing months: `ml.decision.inputs.crop_calendar(crop)`.
- [x] **H-C19** *(done by Hamza, 10 Oct: `backend/app/alerts.py` calls `alert_check`; candidates built in `alerts._candidate` with only data up to `as_of` (same fields as `alert_candidate`); statuses SENT / FAILED / SUPPRESSED, plus a silent BASELINE on a crop's first check so a later signal change is noticed)* (from B8) Alert job (C9): for each farmer, build one candidate per crop they follow with `ml.decision.inputs.alert_candidate(crop_option, mandi, signal, previous_signal)` (`signal` from `advise()`, `previous_signal` = the last signal that farmer was sent, None at first), then call `ml.decision.alert_check(candidates, last_alert_on, today)`. Send `alert` only when `send` is true, store `status` (CREATED or SUPPRESSED) in the alerts table, and store the new signal and `last_alert_on` per farmer. With the baseline forecast the signal is always SELL, so expect PRICE_SPIKE alerts only.
- [x] **H-C20** *(done by Hamza, 10 Oct: `/api/history` and the forecast's history come from `ml.forecast.history`; gaps are `price: null` and the charts break the line there)* (from B9) `/api/history`: `ml.forecast.history.history(crop_option, mandi, as_of=None)` returns `weeks` (52 points, `price` None for a week without an AMIS price: draw a gap, never join across it; `filled` and `frozen` flags, frozen = "price unchanged" per H-C7), `seasonal` (12 months of `index_median` with `index_min`/`index_max`, None where data is thin; this covers H-C6), `calendar` (sowing and harvest months to shade), plus `prices_as_of`, `is_stale`, `low`, `high`. Returns None for IRRI at Rahim Yar Khan.
- [ ] **H-C21** (from H-B15, 10 Oct) `ml.decision.inputs.latest_price`, `is_stale`, `crop_plan_inputs` and `alert_candidate` now take `as_of` (data on or before that day; without it, the series_coverage snapshot as before), so `services.crop_plan` and the alert job can call them directly instead of building their own inputs. `risk_badge()` now raises the badge one level for a stale starting price, so the service's own bump was removed (it would have counted twice). Risk thresholds are now LOW <= 30% and MEDIUM <= 55% spread, the thirds of the real data: Bahawalpur shows MEDIUM / MEDIUM / HIGH / HIGH instead of all HIGH.
- [x] **H-C23** *(done 10 Oct by Usman, agreed with Hamza; its own commit so it does not tangle with the action plan)* **Alerts are opt-in.** New farmers default to `alerts_enabled = false`: `FarmerIn.alerts_enabled` default (`schemas.py`, types regenerated), the `farmers` column default and `create_farmer` (`db.py`), the register form (`Profile.tsx`), and `alerts_enabled_by_phone` for unknown numbers. Ahmed (demo) is seeded with alerts on. Existing databases keep each farmer's setting. Blueprint section 9 updated.

### 4.2 Done in Owner C's folders while Abd is away (read this first, Abd)

| When | What | Where |
|---|---|---|
| 10 Oct | **Service layer (I6)** with real AMIS data: `get_advice` (latest price and date, 4-week range, SELL/WAIT, interest, confidence; stale and frozen prices lower confidence), `get_explanation` (facts until Usman's SHAP), `compare_mandis` (net of transport, best first, missing mandis flagged), `set_alerts` (in memory until C2). Uses Usman's model automatically once `ml/forecast/predict.py` exists; until then the labelled baseline | `backend/app/services.py`, `backend/tests/test_services.py` |
| 10 Oct | Mounted the WhatsApp webhook (`/webhooks/whatsapp`) and chat (`POST /api/chat`) routers; removed the Twilio placeholder `POST /whatsapp`, its constant in `phrasing.py` and its two tests | `backend/app/main.py`, `backend/app/phrasing.py`, `backend/tests/test_api.py` |
| 10 Oct | Regenerated `openapi.json` and the front-end types for the new routes; lint, typecheck, tests and build pass | `frontend/src/api/` |
| 10 Oct | `.env.example`: Gemini and WhatsApp variables; Twilio removed | `.env.example` |
| 10 Oct | **C1 contract.** `schemas.py` is now blueprint section 12 with two deliberate changes: lowercase ids (`wheat`, `irri`, `super_basmati`; `bahawalpur`, `vehari`, `rahim_yar_khan`) and plain response objects (no envelope). Endpoints: `/api/meta`, `/api/forecast`, `/api/explain`, `/api/history`, `/api/weather`, `/api/advice`, `/api/compare-mandis`, `POST /api/offer-check`, `/api/margin`, `/api/crop-plan`, `POST /api/auth/login`, `POST /api/farmers`, `GET/PUT /api/farmers/me`, `POST /api/chat`. Every price endpoint takes `as_of` (time machine for the backup demo weeks). Real AMIS data, no placeholders; the old replay/backtest/alerts endpoints are gone | `backend/app/schemas.py`, `ids.py`, `main.py`, `services.py` |
| 10 Oct | **C2 database and login.** SQLite (standard library) at `FS_DB_PATH` (default `var/farmsight.sqlite`, ignored by git): farmers, farmer crops, recommendations, alerts, messages, chat messages. Invented demo farmer Ahmed, phone `+920000000001`, Bahawalpur, wheat 100 maund then cotton 60 maund, 12.5 acres. Phone login returns a 7-day HS256 JWT signed with `FS_JWT_SECRET` | `backend/app/db.py`, `auth.py` |
| 10 Oct | **C4 wiring.** Every route goes through `services.py`; Usman's `ml.forecast.predict` is used automatically once it imports | `backend/app/main.py` |
| 10 Oct | **C5 weather.** Open-Meteo, `past_days=92`, 1-hour cache in memory, offline-file fallback with `cached: true`, CC BY 4.0 attribution | `backend/app/weather.py` |
| 10 Oct | **C3 retirement.** Deleted `phrasing.py`, the old Ask/Forecast pages and the four-verdict card; the old artifact models moved to `artifact_schemas.py` (see H-B12) | |
| 10 Oct | **C6–C8 screens.** Home (SELL/WAIT parchi, today → 4 weeks with range, interest, "as of" date, weather line, offer check), Why, Compare mandis, What to Grow (season strip, risk badge), History (52 weeks and seasonal pattern), Margin, Chat, Profile (login, register, alerts). Urdu first, RTL, checked at 375 px. A saved login the server rejects is dropped and the request retried as a guest | `frontend/src/` |
| 10 Oct | **C9 alerts.** `backend/app/alerts.py`: checks every farmer with alerts on through the service layer; FIRST / SIGNAL_CHANGE / PRICE_MOVE (≥ 10%); one WhatsApp message a week per farmer with every changed crop; FAILED recorded, SMS fallback hook. Runs every `FS_ALERTS_EVERY_HOURS` (off by default) and on demand: `POST /api/alerts/run?as_of=&dry_run=` with header `X-Admin-Token` = `FS_ADMIN_TOKEN`. The `alerts` table gained `mandi, signal, price, for_date` (migrated automatically) | `backend/app/alerts.py`, `db.py`, `main.py`, `backend/tests/test_alerts.py` |
| 10 Oct | (Usman, agreed in session) `get_explanation()` keeps the "simple estimate" baseline line after the model's SHAP reasons for wheat, since the price shown is still the baseline. Text moved to `BASELINE_NOTE` | `backend/app/services.py` |
| 10 Oct | **H-C8 demo runbook.** `docs/DEMO.md`: checklist, the five minutes with real app output, the alert text, backup weeks, failure table, judge answers, commands to regenerate the numbers once the model lands. **Replay mode:** open the app with `?as_of=2025-03-24` and every price screen replays that day, with a banner (lasts for the tab; `?as_of=` ends it). What to Grow: a stale starting price raises the risk one level; "best to sell at harvest" when holding does not beat interest; says which month's price each estimate starts from | `docs/DEMO.md`, `frontend/src/lib/replay.ts`, `components/ReplayBanner.tsx`, `services.crop_plan` |
| 10 Oct | **On Owner B's engine (H-C14–H-C20).** Advice, compare, offer check, margin, crop plan, selling window and alerts now call `ml.decision`; history comes from `ml.forecast.history`; xgboost and numpy are backend dependencies, so wheat gets the model's direction call and SHAP reasons on Home and Why. Every input honours `as_of`. Interest is 4 weeks (was one month). `docs/DEMO.md` regenerated with this output | `backend/app/services.py`, `alerts.py`, `schemas.py`, `frontend/src/components/DirectionLine.tsx`, `pages/Grow.tsx` |
| 10 Oct | **C10 deploy prepared.** `render.yaml` (API, free plan, health check, generated `FS_JWT_SECRET` and `FS_ADMIN_TOKEN`), `frontend/vercel.json` (SPA rewrites), `docs/DEPLOY.md` (Render, Vercel, CORS, Meta webhook, troubleshooting). Checked: a fresh clone of `main` serves every endpoint, the production build bakes in `VITE_API_BASE_URL`, CORS allows the Authorization header | `render.yaml`, `frontend/vercel.json`, `docs/DEPLOY.md` |
| 10 Oct | (Usman, H-B12 and H-B15) Retired the superseded placeholder chain: `backend/app/artifacts.py`, `artifact_schemas.py`, `check_artifacts.py`, `backend/tests/test_artifacts.py`, `artifacts_dir` / `FS_ARTIFACTS_DIR`, the CI step and the README/CLAUDE.md command, together with `ml/precompute.py`, the old `ml/decision/engine.py` and the placeholder `artifacts/*.json` (`artifacts/models/` stays). Removed the duplicate stale-price risk bump in `services.crop_plan` (now in `risk_badge`) | `backend/`, `.github/workflows/ci.yml`, `README.md`, `CLAUDE.md`, `.env.example` |

**Still open on Owner C's list:** C10 deploy itself (needs the accounts: follow `docs/DEPLOY.md`); P4.4 re-run `docs/DEMO.md` section 7 on the demo morning.

**For Hamza (Owner A)** (filled by Usman and Abd when their changes need data work)

- [ ] **H-A1** (from C9, 10 Oct) WhatsApp `GraphSender.send` now returns `True`/`False` (delivered or not); alerts record FAILED on `False`. With A3: Meta only delivers free text within 24 hours of the farmer's last message, so for alerts create a template (Urdu, one body parameter `{{1}}`, utility category), and put its name in `FS_WA_ALERT_TEMPLATE`. For the demo, the demo phone can simply message the bot first.
- [x] **H-A2** *(done in A11, 10 Oct: `alerts.run` uses `channels.sms.alert_sender()` by default; None, so no fallback, until an SMS vendor is configured)* (from C9, 10 Oct) When A11 (SMS) exists, pass its sender to `alerts.run(sms=...)`: a function `(phone_digits, text, one_line_summary) -> bool`. It is used when WhatsApp delivery fails.
- [ ] **H-A3** *(SMS form done in A11: `sms_reply.alert_sms`; WhatsApp text unchanged)* (from B8) WhatsApp and SMS alert text: `alert_check()` returns codes only. Phrase `{type: SELL_SIGNAL, previous_signal, signal}` as the signal change, and `{type: PRICE_SPIKE, direction: UP|DOWN, change_4w_pct, prices_as_of}` as "the <crop> price at <mandi> moved <x>% in 4 weeks, more than usual", with the "as of" date. Quick replies as in A8 (Why / Compare mandis / Stop alerts).
- [ ] **H-A4** (from A11, 10 Oct; done by Usman with Hamza's agreement) **SMS vendor.** `backend/app/channels/sms.py` is vendor-neutral and `POST /webhooks/sms` answers 503 until a vendor adapter exists. Pick the vendor (the blueprint says an Android SMS-gateway app; name which), then write its `SmsAdapter` from the vendor's official docs: `verify` (its signature or token check), `parse` (payload -> `InboundSms`, `ValueError` if malformed), `acknowledge` (the response it expects) and `sender()`; register it in `sms.ADAPTERS`, set `FS_SMS_PROVIDER`, add its keys to `.env.example` (names only), and test with real phones. Until then say "tested adapter, not live" (README, `docs/DEMO.md` 3a).
- [ ] **H-A5** (from A10 readiness, 10 Oct) **Voice notes.** `backend/app/channels/voice.py` has the `MediaFetcher` and `Transcriber` interfaces and the confirmation flow (`conversation.heard`), off by default. To turn it on: choose the speech-to-text provider, write the WhatsApp media fetcher (Graph API media URL + download with the access token, size and type limits, nothing logged) and the transcriber (confidence 0..1 or None), register both, put any prompt in `docs/PROMPTS.md`, set `FS_VOICE_NOTES=1`. The transcript must stay confirm-before-advice.
- [ ] **H-A6** (from A11, 10 Oct) Native-speaker check of the new Urdu menu strings (`reply.py`, "numbered menu") and the Roman Urdu SMS templates (`sms_reply.py`), together with P4.2.

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
  *Progress 10 Oct:* Gemini key received and working (live-tested); it is in Hamza's local `.env` only, never in git. Share it with Abd outside git for the deployed backend. Still to do: the Meta WhatsApp test number and app secret, and registering the demo phones.
- [x] **A4** (S) README data acknowledgements and AMIS terms of use (blueprint decision 22). Send the lines to C.
  *Done:* README rows ready in `docs/DATA_NOTES.md` section A4 (hand-off H-C9, H-C10). AMIS publishes no terms, only "All rights reserved"; Open-Meteo is CC BY 4.0 with a required link. **Open questions for the team:** keeping AMIS-derived series in the public repo, and the "pre-existing work" wording.

**B · Usman**
- [x] **B1** (M) `ml/forecast/predict.py` stub returning placeholder values in the I2 shape, `is_synthetic: true`. *Done when* C can import it. **First task: by 23:30.**
- [x] **B2** (M) Rewrite `ml/decision/engine.py` to the blueprint (I3): SELL / WAIT at the 5% threshold (in config), confidence from the q10 to q90 width, net rupee impact = quantity × (forecast − today) − interest (16.5% a year), optional arhti commission, fair price range, offer check, margin, mandi comparison net of transport. *Done when* unit tests cover each function, including IRRI with no Rahim Yar Khan price.
- [x] **B3** (M) Training scaffold `ml/forecast/train.py`: XGBoost on real `features.csv` rows, target `price_change_4w_pct` (not price level, since prices rose about 3×), fixed seed, train/val split as given.

**C · Abd**
- [x] **C1** (M) Replace the API contract in `schemas.py` with blueprint section 12 (forecast, explain, advice, compare-mandis, crop-plan, offer-check, margin, history, weather, meta, auth, farmers, chat). Stub every endpoint with placeholder data (`is_synthetic: true`). Regenerate front-end types. *Done when* CI is green and `/docs` lists every endpoint. *(done 10 Oct by Hamza; see 4.2)*
- [x] **C2** (M) SQLite schema from blueprint section 9, seeded from A's runtime tables (I5) on startup. A pre-seeded demo farmer ("Ahmed", Bahawalpur, wheat and cotton, 100 maund). Login by phone returns a JWT. *(done 10 Oct by Hamza; runtime tables are read from CSV, see H-C1)*
- [x] **C3** (S) Retire code built for the superseded plan: the four-verdict engine paths, replay, alerts/events and backtest endpoints and screens. Delete or move to `legacy/`; keep the Urdu, RTL, chart and verdict-card pieces that fit. *(done 10 Oct by Hamza; `artifacts/` left for Usman, see H-B12)*

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
- [x] **B4** (M) Train the point model and the q10 and q90 quantile models. Run A's gate. If the model does not beat persistence on validation, ship the fallback: persistence as the point forecast and the range from the empirical 4-week change distribution, labelled "baseline" (blueprint NFR-01). Write the result in `docs/MODEL_CARD.md` either way.
- [x] **B5** (M) SHAP TreeExplainer and a feature-to-sentence map in Urdu and English (top 3 to 5 factors with rupee effects). No LLM writes these reasons.
- [x] **B6** (M) Real `predict.py`: load `artifacts/models/`, build features with I1, return the I2 shape with `is_synthetic: false`.
- [x] **B7** (M) `crop_plan()` and `selling_window()` in the engine from A6's tables: profit per acre = harvest estimate × yield − cost per acre, risk badge from the year-to-year spread, best selling month window net of interest.

**C · Abd**
- [x] **C4** (M) Wire `/forecast`, `/advice`, `/explain`, `/compare-mandis`, `/meta` to B's predict and engine through the service layer (I6). *(done 10 Oct by Hamza; uses the baseline until B6)*
- [x] **C5** (M) Weather service: Open-Meteo with `past_days=92`, aggregated with A's `weather_features`, cached up to 1 hour in SQLite, `weather_cached` flag on fallback. *(done 10 Oct by Hamza; cache in memory, not SQLite)*
- [x] **C6** (M) Screens: Home (big SELL/WAIT card, today → 4 weeks with range, "AMIS mandi price, as of" date), Sell advice, Why. Urdu first, RTL, 360 px. *(done 10 Oct by Hamza)*

**Check-ins Sat 10:00 and 13:00:** does the must-work path run on real models? Apply the balancing rule at 13:00.

### Phase 3 — Features (Sat 14:00 to 20:00)

**A · Hamza**
- [x] **A8** (S) WhatsApp webhook in `backend/app/channels/whatsapp.py`: signature check; "گندم بہاولپور 100 من" style text → advice through I6; quick replies Why / Compare mandis / Stop alerts.
  *Done:* `backend/app/channels/` (parse, reply, whatsapp), 25 tests. Meta Cloud API webhook with the verification handshake and an `X-Hub-Signature-256` check before any parsing; Urdu, Roman Urdu and English queries with Urdu digits ("گندم بہاولپور ۱۰۰ من", "gandum vehari 50 mann"); asks for a missing crop, rice variety or mandi instead of guessing; assumes 100 maund only when no quantity is given and says so; quick-reply buttons کیوں؟ / منڈیاں / الرٹ بند; retries de-duplicated; replies sent after the 200; phone numbers never logged; voice notes answered with "coming soon" (A10). No LLM: every number comes from the advice. **Needs:** Abd's H-C11 and H-C12 to go live, and A3's keys (`FS_WA_*`) to test with Meta.
- [x] **A9** (S) Gemini chat `/api/chat` in `backend/app/chat/`: context is the farmer's own forecast and advice; prompt in `docs/PROMPTS.md`; uses only the numbers given; template fallback; rate limit.
  *Done:* `backend/app/chat/` (prompt, guard, llm, service, router), 17 tests. `POST /api/chat` answers a free question from the farmer's own advice. **Number guard:** every number in Gemini's answer must appear in the advice context or the question (Urdu and Western digits), otherwise the template reply is sent (`used_fallback: true`, with a reason). Also falls back when Gemini has no key, times out, is blocked, or passes `FS_LLM_RATE_PER_MIN`; per-caller limit `FS_CHAT_RATE_PER_MIN` returns 429. Asks for crop, rice variety or mandi before calling Gemini. No phone or personal data is sent. Synthetic data is always labelled. Prompt word for word in `docs/PROMPTS.md` (a test keeps them equal). WhatsApp: a free question after a query goes to the same chat. The shared advice adapter moved to `backend/app/channels/provider.py`. **Live-tested 10 Oct with the team's Gemini key:** `gemini-2.5-flash` is closed to new keys; `gemini-3.8-flash` cut answers off (hidden thinking used the token budget) and was overloaded; the default is now `gemini-3.5-flash-lite` (answers in 1.2–1.9 s, all passed the guard). Answers that did not finish, or that contain Hindi (Devanagari) script, now fall back too. **Needs:** H-C13 and H-C12 to go live.
- [ ] **A10** (C) Voice notes: Gemini transcription, "Did you mean …?" confirmation, audio deleted after (web and WhatsApp).
  *Readiness (10 Oct, Usman with Hamza's agreement):* `backend/app/channels/voice.py`, flag `FS_VOICE_NOTES` (off), fetcher and transcriber interfaces, confirm-before-advice flow and the honest "not available" reply; 17 tests. No transcription yet: H-A5.
- [ ] **A11** (C) SMS gateway webhook `backend/app/channels/sms.py` with the 160-character format and number menu.
  *Progress (10 Oct, Usman with Hamza's agreement):* the numbered menu for WhatsApp and SMS on one engine (`channels/conversation.py`, session in SQLite, 30 min; tables `conversations` and `seen_messages`); WhatsApp menu, numbered next steps and buttons; vendor-neutral SMS (`sms.py`, `sms_reply.py`: Roman Urdu, GSM-7, at most two parts, warnings never cut); SMS alert fallback (H-A2). `services.set_alerts` returns whether anything changed and `services.alerts_status` is new, so unregistered numbers are told nothing changed. Legacy kept: a bare "3" with no active session still stops alerts; inside a session numbers follow the step. **Not live:** no SMS vendor (H-A4).

**B · Usman**
- [x] **B8** (S) `alert_check()`: signal change or unusual price, at most one alert per farmer per week.
- [x] **B9** (S) History function: 52-week series and the seasonal pattern for the history chart.
- [x] **B10** (S) `docs/MODEL_CARD.md` for judges: data, features, model, gate result vs baseline, SHAP, limits. One page.

**C · Abd**
- [x] **C7** (M) Screens: Compare Mandis, What to Grow with the season timeline. *(done 10 Oct by Hamza)*
- [x] **C8** (S) Screens: offer check, margin, Register/Profile (district dropdown first; map pin if time), Chat (uses A9 and A10). *(done 10 Oct by Hamza; district chips instead of a dropdown, no map pin)*
- [x] **C9** (S) APScheduler alert job: B8's check → A8's WhatsApp sender, SMS fallback. *(done 10 Oct by Hamza; see 4.2. Asyncio loop instead of APScheduler, no new dependency)*
- [ ] **C10** (M) Deploy: front end on Vercel, backend on Render or Hugging Face Spaces; environment variables set; link opens on a phone on mobile data. *(prepared 10 Oct by Hamza: `render.yaml`, `frontend/vercel.json`, step-by-step `docs/DEPLOY.md`; a fresh clone serves every endpoint. Still to do: create the Render and Vercel projects with the team's accounts and set the keys)*

**Check-ins Sat 16:00 and 19:00.**

### Phase 4 — Polish (Sat 20:00 to 23:30) · feature freeze at 23:30

- [x] **P4.1** (C) Price history screen (C), if not cut. *(done 10 Oct by Hamza)*
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

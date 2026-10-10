# FarmSight

**Got a buyer's offer? Check it before you sell.** FarmSight is an independent pre-sale check for farmers in South Punjab: before accepting an offer, a farmer sees the recent reference mandi price and how fresh it is, the difference for their own quantity, and other mandis after estimated transport, in Urdu, on the web, on a WhatsApp numbered menu and (once a provider is connected) by SMS.

It is a calculation and negotiation aid, not a replacement for arhtis, mandis, buyers, transport, storage or credit. Commission agents often provide real credit, logistics and settlement; FarmSight does not judge them, and it cannot see the grade of a crop or the terms of a deal. Market forecasts are kept as clearly labelled background ("market outlook"), not as the answer.

Team Claude's Plan · Build With AI, AICON'26, SEECS NUST · Agricultural Operations

> **Status (10 Oct 2026): real data end to end; offer check first.** Every screen and endpoint runs on real AMIS mandi prices for wheat, cotton, IRRI and Super Basmati rice at Bahawalpur, Vehari and Rahim Yar Khan. The offer check compares a buyer's price with the AMIS prices reported at the mandi in the last 14 days and says how strong that reference is: a stale, frozen, one-repeated-price or thin (< 5 reported days) reference is shown as "reference data is limited", with every number still visible, never as a firm verdict. The 4-week price forecast is a labelled baseline (today's price, with the range of past 4-week swings, which held the real price 81% of the time on 2025 data), because the trained XGBoost model did not beat it on prices; for wheat, the model's direction call ("likely to rise / fall", right on 72% of 2025's big moves) and its SHAP reasons are shown alongside ([`docs/MODEL_CARD.md`](docs/MODEL_CARD.md)). The plan is in [`docs/PLAN.md`](docs/PLAN.md); the API contract is [`backend/app/schemas.py`](backend/app/schemas.py) and blueprint section 12.

## Run locally

You need **Python 3.11** and **Node 20.19 or newer**. Run every command from the repo root unless it says otherwise.

### One-time setup

Windows (PowerShell):

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
Copy-Item .env.example .env
```

macOS / Linux:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
cp .env.example .env
```

### Start the app (two terminals)

Terminal 1, the backend on http://127.0.0.1:8000 (API docs at `/docs`):

```bash
.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000
```

On macOS / Linux use `.venv/bin/python` in place of `.venv/Scripts/python`, here and below.

Terminal 2, the front end on http://localhost:5173:

```bash
npm --prefix frontend run dev
```

The front end forwards `/api` to the backend, so open http://localhost:5173 and both work together.

To put it online (Render for the API, Vercel for the web app), follow [`docs/DEPLOY.md`](docs/DEPLOY.md).

### Check everything (the same checks CI runs)

```bash
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m pytest
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

## How the pieces fit

```
data/processed/ (AMIS prices, runtime tables)  ──▶  ml/ (features, gate, seasonal, forecast model)
                         │                                         │
                         └──────────▶  backend/app/services.py  ◀──┘   one answer for every channel
                                                │
          REST API (FastAPI)  ·  WhatsApp webhook  ·  SMS adapter  ·  chat (Gemini, numbers checked)
                                                │
                                      frontend/ (React, Urdu first)
```

- **The contract is code.** `backend/app/schemas.py` defines every API request and response. The front end's TypeScript types are generated from it, and CI fails if they drift.
- **One service layer, one engine.** `backend/app/services.py` answers the web app, WhatsApp and chat, so every channel gives the same numbers. Forecasts come from `ml/forecast/predict.py` (the labelled baseline price, plus the model's wheat direction call) and every decision from the engine in `ml/decision/`.
- **Time machine.** Every price endpoint takes `as_of=YYYY-MM-DD` and never looks at a price after that date (the backup demo weeks in `docs/DEMO.md` use it).
- **Honest labels.** Every price says where it came from (`data_source`), its own "as of" date, whether it is stale (over 56 days old) and whether AMIS has repeated the same price for weeks (`price_unchanged_since`).
- **Demo login.** The invented demo farmer "Ahmed" logs in with phone `+920000000001`. Farmers, logs and alerts live in SQLite (`var/farmsight.sqlite`, not in git).

## WhatsApp, SMS and voice notes

All three use the same conversation engine (`backend/app/channels/conversation.py`) and the same service layer as the
web app, so a farmer gets the same advice, numbers, range, "as of" date and stale-price warnings everywhere. Only
the wording differs: Urdu on WhatsApp, short Roman Urdu on SMS.

| Channel | Status |
|---|---|
| WhatsApp text, numbered menu and buttons | Built and tested. Live once the Meta app is set up (below) |
| SMS | **Tested adapter only, not a live service.** No SMS vendor has been chosen, so no SMS is sent or received. `POST /webhooks/sms` answers 503 until a vendor adapter exists |
| WhatsApp voice notes | **Not available.** Off by default; no speech-to-text provider is chosen. A voice note gets a reply asking the farmer to type or use the menu |

**WhatsApp setup.** Create a Meta app with the WhatsApp product, then put its values in `.env`: `FS_WA_VERIFY_TOKEN`
(any string, also typed into Meta's webhook settings), `FS_WA_APP_SECRET`, `FS_WA_ACCESS_TOKEN`,
`FS_WA_PHONE_NUMBER_ID` (optional: `FS_WA_API_VERSION`, `FS_WA_ALERT_TEMPLATE`, `FS_WA_ALERT_TEMPLATE_LANG`). The
callback URL is `<backend>/webhooks/whatsapp`. Every request's `X-Hub-Signature-256` is checked before anything is
read. Meta only delivers free text within 24 hours of the farmer's last message; alerts outside that window need an
approved template (`FS_WA_ALERT_TEMPLATE`).

**Talking to it.** The numbered menu needs no typing beyond digits; checking a buyer's offer is 1:

```
Farmer: 0      FarmSight: 1 خریدار کی آفر چیک کریں  2 منڈیوں کا موازنہ  3 وجہ اور ڈیٹا کی تفصیل  4 الرٹ شروع کریں  5 الرٹ بند کریں  0 مینو
Farmer: 1      FarmSight: کون سی فصل؟  1 گندم  2 کپاس (پھٹی)  3 چاول  0 مینو
Farmer: 1      FarmSight: کون سی منڈی؟  1 بہاولپور  2 وہاڑی  3 رحیم یار خان  0 مینو
Farmer: 100    (after "1" for Bahawalpur and the quantity question)
Farmer: 3514   FarmSight: ⚖️ گندم، بہاولپور: حوالہ ڈیٹا محدود ہے / خریدار کی آفر: Rs 3,514 فی من /
               منڈی کا آخری رپورٹ شدہ ریٹ: Rs 3,820 (AMIS، 2026-10-09) / ... 100 من پر −Rs 30,600 /
               ⚠️ AMIS نے رپورٹ ہونے والے تمام 12 دن ایک ہی حوالہ ریٹ بتایا ... / 1 کیوں؟ · 2 منڈیاں · 3 الرٹ چالو · 0 مینو
Farmer: 2      FarmSight: (every mandi after estimated transport, against this offer, the farmer's own first)
```

Free text works too: "گندم بہاولپور 100 من آفر 3514" (or "gandum bwp 100 man offer Rs 3514") checks the offer at once.
A price counts as the offer only after an offer word; two different prices, or none, are asked for, and no
quantity is assumed for an offer. Plain "گندم بہاولپور 100 من" still answers with the market outlook as before.

Rice asks Super Basmati or IRRI. A number means something only in the step the farmer is on. With no active
session (or after 30 minutes), a bare "3" still stops alerts, as it always has, and any other bare number gets the
main menu and nothing else happens. "0" always opens the menu.
"بند" / "stop" turns alerts off and "شروع" / "shuru" turns them on; a number that is not a registered farmer is told
nothing changed.

The same menu by SMS, in Roman Urdu (at most two SMS parts; warnings are never cut to save space):

```
Farmer: 0      FarmSight: FarmSight: 1 Offer check 2 Mandiyan 3 Kyun/Data 4 Alert on 5 Alert band 0 Menu. Ya likhein: gandum bahawalpur 100 man offer 3514
...
Farmer: 3514   FarmSight: FarmSight Gandum BWP: Reference data mehdood. AMIS: sab 12 din aik hi rate, pakki range nahi.
               Offer Rs3514, reference Rs3820/man (AMIS 2026-10-09, 12/14 din). Waada nahi; grade/sharait shamil nahi.
               Farq -Rs306/man, 100 man par -Rs30600. Range Rs3820-Rs3820. 1 Kyun/Data 2 Mandiyan 3 Alert on 0 Menu
```

**SMS boundary.** `backend/app/channels/sms.py` has the vendor-neutral parts: the `SmsSender` interface (with a
`NullSmsSender` when nothing is configured and a `FakeSmsSender` for tests), the inbound route, de-duplication, a
per-number reply limit (`FS_SMS_REPLIES_PER_MIN`, default 10) and the Roman Urdu replies. To go live, the team picks a
vendor, writes its `SmsAdapter` from the vendor's official documentation (its signature or token check, payload,
acknowledgement and sender), registers it in `sms.ADAPTERS` and sets `FS_SMS_PROVIDER` to its name. Until then
`FS_SMS_PROVIDER` should stay empty.

**Alerts and SMS.** If WhatsApp fails to deliver an alert and an SMS vendor is configured, the same alert goes by SMS
in Roman Urdu. Only farmers with alerts on get alerts, at most one a week, and never a price-spike alert on a stale or
frozen price; SMS does not add alerts WhatsApp would not have sent. With no vendor configured there is no fallback.

**Voice notes.** `backend/app/channels/voice.py` defines the interfaces (fetch the audio from WhatsApp, transcribe
Urdu, a confidence score). `FS_VOICE_NOTES=1` has no effect until both are written and registered. When they are,
FarmSight replies "I heard: ..., reply 1 if right, 2 to correct" and gives advice only after 1; unclear notes go to
the menu.

### Privacy on WhatsApp and SMS

- **Kept:** the farmer's place in the menu (step, crop, mandi, quantity and the last query), keyed by channel and
  phone number (digits only), for **30 minutes** (`FS_CHANNEL_SESSION_MINUTES`); expired sessions are deleted.
  Incoming message ids are kept for 24 hours so a retried delivery is not answered twice. Alert on/off is stored on
  the farmer's profile and changed only when the farmer asks (menu 4/5, "بند", "شروع", the button, or Profile).
  **Alerts are opt-in:** a new farmer gets none until they turn them on. The invented demo farmer Ahmed is seeded
  with alerts on. Databases created earlier keep each farmer's current setting.
- **Not kept:** the text of incoming WhatsApp or SMS messages, voice audio and transcripts. Outgoing alert texts are
  logged in the `messages` table with their delivery status.
- **Not logged:** phone numbers, message text or transcripts never go to the application logs.
- **Sent to Gemini:** a free question asked on WhatsApp after an answer, with that answer's crop, mandi and numbers;
  never the phone number. SMS has no AI chat, so nothing from SMS goes to Gemini.

## What FarmSight does not solve

FarmSight gives a reference, not a deal. It does not and cannot:

- release a farmer from **tied credit** (an advance from an arhti or input dealer that comes with selling terms);
- provide **transport**: transport costs shown are estimates from road distance, not quotes or a truck;
- provide **storage** or tell a farmer that holding the crop will pay (our forecasts were tested and are not reliable
  enough for that: `docs/MODEL_CARD.md`);
- know whether a **buyer is actually there** at another mandi, or their payment terms and deductions;
- see the crop's **quality, grade or moisture**, which can move the price a buyer offers;
- **guarantee a future price**, or prove that an offer is unfair. AMIS reports can be old, frozen or repeated, and the
  app says so instead of judging the offer.

No claim is made that FarmSight raises incomes: it has not been field-tested. Replaying a past week (`?as_of=`) shows
**what reference information was available that day**, not money a farmer would have saved.

## Common tasks

**Data (Owner A).** Rebuild `features.csv`: `python -m ml.features.build`. Runtime tables: `python -m ml.ingest.runtime_tables`. Seasonal tables: `python -m ml.seasonal.tables`. Demo data checks: `python -m ml.eval.demo_check`.

**Score a model (NFR-01).** Write predictions for every validation row and run `python -m ml.eval.gate --predictions preds.csv --model <name>`. The test split (`--split test --final`) is used once, at the end.

**Change an API shape.** Edit `backend/app/schemas.py` and `docs/BLUEPRINT.md` section 12 together, then regenerate the front-end types:

```bash
.venv/Scripts/python -m backend.app.export_openapi
npm --prefix frontend run gen:api
```

Commit the regenerated `frontend/src/api/` files. CI fails if you forget.

**Add a Python dependency.** Add it, pinned, to `backend/requirements.txt` (runtime) or `requirements-dev.txt` (tests and tools), install it, then refresh the lock: `.venv/Scripts/python -m pip freeze --exclude pip > backend/constraints.txt`. Heavy ML libraries (torch, Chronos) go in a separate `ml/requirements.txt`, never in the backend's.

**Add a front-end dependency.** `npm --prefix frontend install <name>`. Versions are saved exactly (`frontend/.npmrc`).

**Add a string to the UI.** Add the key to both `frontend/src/locales/ur.json` and `en.json`. A test fails if they differ.

**Layout.** Use only logical Tailwind classes (`ms-`, `me-`, `ps-`, `pe-`, `text-start`, `text-end`) so Urdu mirrors correctly. A test fails on `ml-`, `mr-`, `text-left` and friends.

## Team workflow

The rules are in [`docs/PLAN.md`](docs/PLAN.md) sections 15 and 16 and [`CLAUDE.md`](CLAUDE.md). In short:

- `main` always runs. Work on a branch named `yourname/task`, open a pull request, and merge when CI is green.
- Only edit your owner's folders. Ask the owner before touching theirs.
- Keys go in `.env` (ignored by git) and are shared outside git. **This repository is public.**

## Acknowledgements and disclosures

Required by the competition rules. **Everyone adds their own datasets and tools here, one line each.**

### Data

| Dataset | Source | Licence / terms | Downloaded |
|---|---|---|---|
| AMIS Punjab daily mandi prices: wheat, IRRI and Super Basmati rice, seed cotton (phutti) at Bahawalpur, Vehari and Rahim Yar Khan, Jan 2015 to Oct 2026 | http://www.amis.pk (Year-Month report, CSV export) | No licence or terms published; site states "Copyright © 2006-2026 AMIS, Directorate of Agriculture (Economics & Marketing) Punjab. All rights reserved." Used with credit for a non-commercial demo; raw exports not redistributed; cleaned series in `data/processed/` | 9 Oct 2026 |
| AMIS wheat support-price table | http://www.amis.pk/Agristatistics/SupportPrice/wheat/wheat.html | As above | 9 Oct 2026 |
| Open-Meteo weather: daily history 2015 to Oct 2026, and the live forecast API | https://open-meteo.com | CC BY 4.0 (https://open-meteo.com/en/licence); free API for non-commercial use; "Weather data by [Open-Meteo.com](https://open-meteo.com/)" shown with a link wherever weather is displayed | 9 Oct 2026 (history); live at request time |
| Agriculture Policy Institute policy analyses (wheat 2023-24, rice paddy 2022-23, cotton 2022-23): cost of production and yields | https://api.gov.pk/Policies | Government of Pakistan publications; no licence stated; figures quoted with citations | 9 Oct 2026 |
| Economics inputs: support prices, SBP policy rate, CPI, diesel, USD/PKR, fertilizer prices, transport and storage assumptions | Every value's own source is in `data/processed/economics_inputs.json` (AMIS, SBP, MNFSR Fertilizer Review, Dawn, Express Tribune, Business Recorder, Profit, Radio Pakistan, The News, ARY News, USDA FAS, Al Jazeera and others) | Official publications and news reports, cited per value; assumptions labelled | 9 Oct 2026 |

Tools used for the data, outside this repo: Node.js scripts (built-in `http`) to download the AMIS exports; the `pdf-parse` npm package to extract text from the cost-of-production PDFs.

### Libraries and tools

- Backend: FastAPI, Pydantic, Uvicorn, python-dotenv, python-multipart, SQLite (Python standard library); tests with pytest and httpx2; lint with Ruff.
- Forecast model: XGBoost (with its SHAP contributions) and NumPy (SciPy comes with XGBoost), for the wheat direction call and its reasons (`ml/forecast/`, `docs/MODEL_CARD.md`).
- Live services: Open-Meteo forecast API (weather), Meta WhatsApp Cloud API (messages), Google Gemini API (`gemini-3.5-flash-lite`, free tier) for rephrasing chat answers; prompts word for word in `docs/PROMPTS.md`, and every number in an answer is checked against the farmer's own advice before it is shown.
- Front end: React, React Router, Vite, TypeScript, Tailwind CSS, Recharts, i18next / react-i18next, openapi-typescript, Vitest, oxlint, Lucide icons (`lucide-react`, ISC licence).
- Fonts (bundled with `@fontsource`, never fetched at runtime): Noto Sans Arabic (Urdu interface text) and IBM Plex Sans (English, prices, dates and numbers), both under the SIL Open Font License.

### AI assistance

- This codebase was scaffolded with **Claude Code** (Anthropic), working with the team. Commits it helped write carry a `Co-Authored-By: Claude` line. Every team member reviews and can explain what is merged.

### Pre-existing work

- An earlier v1 prototype (Streamlit, synthetic prices) existed before the event. **None of its code is used in this repository**; it was rebuilt from scratch on 9 Oct 2026.
- The AMIS data was downloaded on 9 Oct 2026 with Node.js scripts written that day with Claude Code's help; the scripts are kept outside this repo (details: `docs/DATA_NOTES.md`, section A4).

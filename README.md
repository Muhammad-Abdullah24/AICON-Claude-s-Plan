# FarmSight

**Sell now, sell at another mandi, or store and sell later.** FarmSight gives Pakistani farmers a costed decision in Urdu, on the web and on WhatsApp, built on mandi price forecasts with honest uncertainty.

Team Claude's Plan · Build With AI, AICON'26, SEECS NUST · Agricultural Operations

> **Status (10 Oct 2026): real data end to end.** Every screen and endpoint runs on real AMIS mandi prices for wheat, cotton, IRRI and Super Basmati rice at Bahawalpur, Vehari and Rahim Yar Khan. The 4-week price forecast is a labelled baseline (today's price, with the range of past 4-week swings, which held the real price 81% of the time on 2025 data), because the trained XGBoost model did not beat it on prices; for wheat, the model's direction call ("likely to rise / fall", right on 72% of 2025's big moves) and its SHAP reasons are shown alongside ([`docs/MODEL_CARD.md`](docs/MODEL_CARD.md)). The plan is in [`docs/PLAN.md`](docs/PLAN.md); the API contract is [`backend/app/schemas.py`](backend/app/schemas.py) and blueprint section 12.

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
                    REST API (FastAPI)  ·  WhatsApp webhook  ·  chat (Gemini, numbers checked)
                                                │
                                      frontend/ (React, Urdu first)
```

- **The contract is code.** `backend/app/schemas.py` defines every API request and response. The front end's TypeScript types are generated from it, and CI fails if they drift.
- **One service layer, one engine.** `backend/app/services.py` answers the web app, WhatsApp and chat, so every channel gives the same numbers. Forecasts come from `ml/forecast/predict.py` (the labelled baseline price, plus the model's wheat direction call) and every decision from the engine in `ml/decision/`.
- **Time machine.** Every price endpoint takes `as_of=YYYY-MM-DD` and never looks at a price after that date (the backup demo weeks in `docs/DEMO.md` use it).
- **Honest labels.** Every price says where it came from (`data_source`), its own "as of" date, whether it is stale (over 56 days old) and whether AMIS has repeated the same price for weeks (`price_unchanged_since`).
- **Demo login.** The invented demo farmer "Ahmed" logs in with phone `+920000000001`. Farmers, logs and alerts live in SQLite (`var/farmsight.sqlite`, not in git).

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
- Front end: React, React Router, Vite, TypeScript, Tailwind CSS, Recharts, i18next / react-i18next, openapi-typescript, Vitest, oxlint.
- Fonts (bundled): Noto Nastaliq Urdu, IBM Plex Sans, IBM Plex Mono, all under the SIL Open Font License.

### AI assistance

- This codebase was scaffolded with **Claude Code** (Anthropic), working with the team. Commits it helped write carry a `Co-Authored-By: Claude` line. Every team member reviews and can explain what is merged.

### Pre-existing work

- An earlier v1 prototype (Streamlit, synthetic prices) existed before the event. **None of its code is used in this repository**; it was rebuilt from scratch on 9 Oct 2026.
- The AMIS data was downloaded on 9 Oct 2026 with Node.js scripts written that day with Claude Code's help; the scripts are kept outside this repo (details: `docs/DATA_NOTES.md`, section A4).

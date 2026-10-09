# FarmSight

**Sell now, sell at another mandi, or store and sell later.** FarmSight gives Pakistani farmers a costed decision in Urdu, on the web and on WhatsApp, built on mandi price forecasts with honest uncertainty.

Team Claude's Plan · Build With AI, AICON'26, SEECS NUST · Agricultural Operations

> **Status: walking skeleton.** Every screen and endpoint works end to end, but the numbers come from **synthetic placeholder artifacts** (`data_source: "placeholder"`, `is_synthetic: true`), and the app shows a "synthetic data" tape on every screen. Real forecasts replace them as the models land. The plan, scope and API contract are in [`docs/PLAN.md`](docs/PLAN.md).

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

### Check everything (the same checks CI runs)

```bash
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m backend.app.check_artifacts
.venv/Scripts/python -m pytest
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

## How the pieces fit

```
data/processed/  ──▶  ml/ (models, alarm, decision engine)  ──▶  artifacts/*.json
                                                                     │
                                       backend/ (FastAPI) reads only artifacts/
                                                    │
                              frontend/ (React)  ·  /whatsapp (Twilio)
```

- **The contract is code.** `backend/app/schemas.py` defines every artifact and every API response. The backend validates artifacts against it on startup and refuses to start on a bad one. The front end's TypeScript types are generated from it.
- **One decision engine.** `ml/decision/engine.py` is plain Python, used by `/api/advice`, the WhatsApp bot and the crisis replay.
- **The time-machine rule** lives in one tested function: `ArtifactStore.forecast_at` never returns a forecast made after the requested date.

## Common tasks

**Owner B: write artifacts.** Regenerate the placeholders with `python -m ml.precompute --placeholder`. Before committing any artifact, run `python -m backend.app.check_artifacts`.

**Change an API shape.** Edit `backend/app/schemas.py` and `docs/PLAN.md` section 14 together, then regenerate the front-end types:

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
| AMIS Punjab daily mandi prices | http://www.amis.pk | **To confirm** (PLAN.md 6.1) | By a teammate, before 9 Oct 2026 |
| Open-Meteo historical weather | https://open-meteo.com | CC BY 4.0, attribution required | By a teammate, before 9 Oct 2026 |
| Punjab wheat procurement prices | To fill in | To fill in | To fill in |
| Cost-of-production and economics inputs | Sources listed inside `data/processed/economics_inputs.json` | To fill in | To fill in |

### Libraries and tools

- Backend: FastAPI, Pydantic, Uvicorn, python-dotenv, python-multipart; tests with pytest and httpx2; lint with Ruff.
- Front end: React, React Router, Vite, TypeScript, Tailwind CSS, Recharts, i18next / react-i18next, openapi-typescript, Vitest, oxlint.
- Fonts (bundled): Noto Nastaliq Urdu, IBM Plex Sans, IBM Plex Mono, all under the SIL Open Font License.

### AI assistance

- This codebase was scaffolded with **Claude Code** (Anthropic), working with the team. Commits it helped write carry a `Co-Authored-By: Claude` line. Every team member reviews and can explain what is merged.

### Pre-existing work

- An earlier v1 prototype (Streamlit, synthetic prices) existed before the event. **None of its code is used in this repository**; it was rebuilt from scratch on 9 Oct 2026.
- The AMIS data was collected by a teammate with scripts written before the event (details: `docs/DATA_NOTES.md`).

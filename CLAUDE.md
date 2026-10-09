# FarmSight: instructions for Claude sessions

Read docs/PLAN.md before doing anything. Then read README.md for how to run and check the code.

## Ownership (do not edit outside your owner's folders)
- Owner A (________): data/, ml/ingest/, ml/events/, ml/eval/
- Owner B (________): ml/forecast/, ml/alarm/, ml/decision/, ml/precompute.py, artifacts/
- Owner C (________): backend/, frontend/, README.md, docs/DEMO.md
Ask the human before touching any other path. Ask which owner the human is at the start of the session.

## Hard rules
- The API contract is docs/PLAN.md section 14 and backend/app/schemas.py. Do not change response shapes without the team's agreement; when they change, change both in the same commit and regenerate the front-end types.
- Forecasts for a date may only use data on or before that date. All as-of lookups go through backend/app/artifacts.py.
- Never hardcode a price, statistic, crop or mandi. Numbers come from data or artifacts; crops and mandis come only from artifacts/meta.json.
- Anything synthetic or simulated must be flagged is_synthetic and labelled in the UI. Unmeasured metrics are null, never invented.
- Every price in artifacts/ and in the API is Rs per 40 kg. Conversion from AMIS's Rs per 100 kg happens only in ml/precompute.py.
- The backend never imports heavy model code. ml/decision/ stays pure Python with no third-party imports.
- Do not copy code from other projects.
- Every LLM prompt goes in docs/PROMPTS.md.
- Every new dataset or library gets a line in the README acknowledgements.
- The LLM never produces numbers shown to users. It parses and rephrases only.
- Never commit secrets. .env is ignored; the repository is public. The app's LLM key is FS_LLM_API_KEY, never ANTHROPIC_API_KEY.
- Front end: every string goes in both frontend/src/locales/ur.json and en.json. Use only logical Tailwind classes (ms-/me-/ps-/pe-/text-start/text-end), never left/right ones.
- Read files as UTF-8 explicitly (encoding="utf-8"): Windows otherwise corrupts the Urdu.

## Commands (run from the repo root; on macOS/Linux use .venv/bin/python)
- Backend: .venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000
- Frontend: npm --prefix frontend run dev   (http://localhost:5173, proxies /api to the backend)
- Precompute artifacts: .venv/Scripts/python -m ml.precompute --placeholder
- Check artifacts: .venv/Scripts/python -m backend.app.check_artifacts
- Tests: .venv/Scripts/python -m pytest   and   npm --prefix frontend test
- Lint and types: .venv/Scripts/python -m ruff check .   and   npm --prefix frontend run lint && npm --prefix frontend run typecheck
- Regenerate front-end API types after a schema change: .venv/Scripts/python -m backend.app.export_openapi && npm --prefix frontend run gen:api

## Style
- Small commits with clear messages, on a branch named yourname/task, merged by pull request when CI is green.
- Explain in the pull request what changed and why.
- Match the surrounding code: comments explain why, not what.

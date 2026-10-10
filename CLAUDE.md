# FarmSight: instructions for Claude sessions

Read these before doing anything, in this order:
1. docs/BLUEPRINT.md — what we build (the spec; API contract in section 12, data model in section 9).
2. docs/PLAN.md — who does what and when (owners, interfaces I1–I6, task IDs, cut list).
3. README.md — how to run and check the code.

docs/archive/PLAN_v2_superseded.md is history only. Do not follow it.

Ask which owner the human is at the start of the session, then show:
1. their open hand-off items from docs/PLAN.md section 4.1 (work other owners' changes created for them), first;
2. their open tasks from docs/PLAN.md section 5.

When you finish a change that another owner depends on (a new or renamed column, a changed fact, a new table, a
changed function signature), add a hand-off line for that owner in docs/PLAN.md section 4.1 in the same PR, and
say so in the PR description.

## Ownership (do not edit outside your owner's folders)
- Owner A (Hamza): data/, ml/features/, ml/ingest/, ml/seasonal/, ml/eval/, backend/app/channels/, backend/app/chat/, docs/FACTS.md, docs/PROMPTS.md, docs/DATA_NOTES.md
- Owner B (Usman): ml/forecast/, ml/explain/, ml/decision/, artifacts/, docs/MODEL_CARD.md
- Owner C (Abd; Hamza is covering Owner C tasks from 10 Oct, logged in docs/PLAN.md section 4.2): backend/ (except channels/ and chat/), frontend/, README.md, CLAUDE.md, docs/DEMO.md, .github/
- Shared, change only by team agreement: docs/BLUEPRINT.md, docs/PLAN.md (owners may tick their own task boxes), backend/app/schemas.py
Ask the human before touching any other path.

## Shared context lives in the repo
- Three people use three separate Claude accounts. Anything another owner needs to know (a changed signature, a data quirk, a decision) goes into the repo: docs/PLAN.md, docs/BLUEPRINT.md, docs/DATA_NOTES.md or the PR description. Never only in chat.
- Respect the interfaces in docs/PLAN.md section 4. To change one, ask the human to agree it with its owner first.

## Hard rules
- The API contract is docs/BLUEPRINT.md section 12 and backend/app/schemas.py. Do not change response shapes without the team's agreement; when they change, change both in the same commit and regenerate the front-end types.
- Signals are SELL and WAIT only (Urdu: بیچ دیں، رکیں). WAIT when the 4-week forecast is at least 5% above today (threshold in config). The rupee impact subtracts the interest cost of waiting.
- Scope: crop options Wheat, Cotton, IRRI, SuperBasmati at BahawalPur, Vehari, RahimYarKhan. No IRRI at RahimYarKhan. Crops and mandis come only from the runtime tables (data/processed/runtime/), never hardcoded.
- Forecasts for a date may only use data on or before that date.
- Train on real rows only (is_synthetic = 0). A model is deployed only if it beats the persistence baseline on real validation data (NFR-01); otherwise use the labelled baseline fallback.
- Never hardcode a price, statistic, crop or mandi. Numbers come from data, models or runtime tables. Unmeasured metrics are null, never invented.
- Anything synthetic, assumed or simulated is flagged (is_synthetic, or "estimate") and labelled in the UI.
- Every price in the API is Rs per 40 kg with unit "40kg". AMIS stores Rs per 100 kg; convert only in ml/features/.
- Feature code is shared: training and the runtime weather service both use ml/features/, so features match exactly.
- ml/decision/ stays pure Python with no third-party imports. Only ml/forecast/predict.py imports xgboost and shap.
- The LLM (Gemini) never produces numbers shown to users. It transcribes, parses and rephrases only, using numbers it is given. Every prompt goes in docs/PROMPTS.md.
- Do not copy code from other projects.
- Every new dataset or library gets a line in the README acknowledgements.
- Never commit secrets. .env is ignored; the repository is public. The app's LLM key is FS_LLM_API_KEY, never ANTHROPIC_API_KEY.
- Front end: every string goes in both frontend/src/locales/ur.json and en.json. Use only logical Tailwind classes (ms-/me-/ps-/pe-/text-start/text-end), never left/right ones.
- Read files as UTF-8 explicitly (encoding="utf-8"): Windows otherwise corrupts the Urdu.

## Commands (run from the repo root; on macOS/Linux use .venv/bin/python)
- Backend: .venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000
- Frontend: npm --prefix frontend run dev   (http://localhost:5173, proxies /api to the backend)
- Tests: .venv/Scripts/python -m pytest   and   npm --prefix frontend test
- Lint and types: .venv/Scripts/python -m ruff check .   and   npm --prefix frontend run lint && npm --prefix frontend run typecheck
- Regenerate front-end API types after a schema change: .venv/Scripts/python -m backend.app.export_openapi && npm --prefix frontend run gen:api
- Rebuild features.csv (Owner A): .venv/Scripts/python -m ml.features.build
- Rebuild runtime tables (Owner A): .venv/Scripts/python -m ml.ingest.runtime_tables
- Rebuild seasonal tables (Owner A): .venv/Scripts/python -m ml.seasonal.tables
- Evaluation gate (NFR-01): .venv/Scripts/python -m ml.eval.gate [--predictions preds.csv --model name]   (test split: --split test --final, once)
- Demo data checks (Owner A): .venv/Scripts/python -m ml.eval.demo_check
- WhatsApp channel (Owner A): backend/app/channels/whatsapp.py; needs FS_WA_* in .env (see the module docstring); tests run with the rest of pytest
- WhatsApp/SMS conversation (Owner A): backend/app/channels/conversation.py is the numbered menu both channels share (session in SQLite, 30 min): 1 check a buyer offer, 2 compare, 3 why/data details, 4/5 alerts on/off, 0 menu; a bare number is read only against the farmer's current step (outside a session a bare 3 still stops alerts). Never add channel-specific decision logic: change the engine or the service layer
- Offer check (the product's main job): the rules live in ml/decision/offer.py (reference strength, < 5 reported days = limited); services.offer_check / reference gather the inputs; GET /api/reference and GET /api/channels/preview (rendered by the channel code, status flags only) feed the web app. Never call the AMIS reference a fair, true or guaranteed price, and never compute prices in React
- Web app shell and design system: frontend/src/components/shell/ (sidebar, bottom bar), components/ui/ (StatusBadge, Button, NumberField, Disclosure/Note/Toggle); colours and fonts only from src/index.css (Noto Sans Arabic for Urdu, IBM Plex Sans for English and figures, bundled). Status badges map only from real API fields (src/lib/status.ts)
- SMS (Owner A): backend/app/channels/sms.py (vendor-neutral; POST /webhooks/sms is 503 until a vendor adapter is registered in sms.ADAPTERS and FS_SMS_PROVIDER names it), Roman Urdu replies in sms_reply.py
- Voice notes (Owner A): backend/app/channels/voice.py, off; FS_VOICE_NOTES=1 does nothing until a fetcher and transcriber are registered. Never answer from an unconfirmed transcript
- Chat (Owner A): backend/app/chat/ (POST /api/chat); needs FS_LLM_API_KEY; the prompt lives word for word in docs/PROMPTS.md
- Service layer (Owner C): backend/app/services.py answers web, WhatsApp and chat alike; every price function takes as_of (time machine). API ids are lowercase (wheat, super_basmati, rahim_yar_khan); backend/app/ids.py maps them to the data names
- Demo login: phone +920000000001 (invented farmer "Ahmed", seeded by backend/app/db.py). The SQLite file is var/farmsight.sqlite (FS_DB_PATH); tests use ":memory:" via the root conftest.py
- Train the forecast models (Owner B; first: pip install -r ml/forecast/requirements.txt): .venv/Scripts/python -m ml.forecast.train [--quantiles] [--predictions preds.csv] [--save]
- Model search on the training years (Owner B): .venv/Scripts/python -m ml.forecast.tune
- Record the baseline fallback after a failed gate run (Owner B): .venv/Scripts/python -m ml.forecast.train --record-fallback
- Save the direction model to artifacts/models/ (Owner B): .venv/Scripts/python -m ml.forecast.train --save
(Owners add new commands here as their tasks land, e.g. training and evaluation.)

## Style
- Small commits with clear messages, on a branch named yourname/task-id, merged by pull request when CI is green. Put the task ID (A1, B2, C4…) in the commit message and PR title.
- Explain in the pull request what changed and why, and tick the task box in docs/PLAN.md.
- Match the surrounding code: comments explain why, not what.

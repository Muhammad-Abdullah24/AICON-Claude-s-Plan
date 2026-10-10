# FarmSight pivot: "Can you afford to wait?" (10 Oct 2026)

The team agreed on 10 Oct to change the core question. Instead of asking "will the price rise?", the app now asks
**"can you afford to wait, and with whose money?"** It also adds a free news feed, because in 2026 AMIS showed
wheat capped at Rs 3,450 while the open market reached about Rs 5,300.

**Reassigned 10 Oct, after U1 and U2:** Hamza builds the rest of the code (Phase H). Abd reviews, merges, deploys and
runs the demo and pitch (Phase U). Abd touches only docs and deploy config, so the two phases can't conflict.

## 1. Rules that keep us conflict-free

1. **Only edit files your phase owns** (section 2). Hamza: if you run several AI sessions at once, give each its own
   branch and its own files (the batches in section 5 are cut that way), and merge one batch before starting work that
   touches the same files. If you need a change in the other side's file, say so in the team
   chat and the owner makes it.
2. **Branch from the latest `main`**: `abd/P-<task>` or `hamza/P-<task>`. Merge through a PR. Never push to `main`.
3. **Interfaces (section 3) change only if both agree in chat.** The U1 schemas in `backend/app/schemas.py` are that contract.
4. **No new dependencies.** Read the RSS feed with the standard library (`urllib`, `xml.etree`). Use Gemini through the
   existing `backend/app/chat/llm.py` (`get_llm()`). If you really need a package, ask first.
5. **No new environment variables or keys.** The news feed needs no key. Put news settings as constants in
   `backend/app/news/config.py`.
6. **Every change comes with tests:** next to new packages (as `channels/` and `chat/` do), and in `backend/tests/` for
   the API.
7. **Run the full suite before every push:** `pytest` from the repo root, then `npm run lint`, `npm run typecheck`, `npm test` and `npm run build` in `frontend/`. CI also fails if the API
   changed and the front-end types were not regenerated.
8. **Never let a forecast or a news item flip the advice** (agreed 10 Oct). News can only add a warning or lower confidence.

## 2. Who owns which files

| Area | Phase H (Hamza): all code | Phase U (Abd): review, docs, deploy |
|---|---|---|
| Engine and backtest | `ml/decision/**`, new `ml/backtest/**` | none |
| API | `backend/app/**` (incl. `services.py`, `schemas.py`, `main.py`, the new `news/`, `channels/`), `backend/tests/**` | none |
| Front end | `frontend/**` | none |
| Docs | `FACTS.md`, `MODEL_CARD.md`, `DATA_NOTES.md`, `URDU_REVIEW.md` | `BLUEPRINT.md`, `PLAN.md`, `PIVOT.md`, `DEMO.md`, `DEPLOY.md`, `README.md`, `CLAUDE.md` |
| Config and CI | `requirements*.txt` (ask first: rule 4) | `.github/**`, `render.yaml`, `frontend/vercel.json`, `.env.example` |

`schemas.py` is now Hamza's. A change to the U1 contract still needs a word in chat first, because the front end and
WhatsApp both depend on it.

**Database:** put the news cache in its own table (`CREATE TABLE IF NOT EXISTS news_items ...`) inside
`backend/app/news/`, using `backend.app.db.connect()`.

**Rates the engine uses** (storage loss, arhti rate, bank rate) go in `ml/decision/config.py`, with their sources in
`FACTS.md` (the table in section 5).

## 3. Interfaces (fixed now)

### 3.1 Hold backtest (H1; the wait engine B1 calls it)

```python
# ml/backtest/hold.py
def hold_history(crop_option: str, mandi: str, start_month: int, wait_months: int,
                 annual_rate: float, loss_pct: float, as_of: date | None = None) -> dict | None:
    """For every past year: sell in start_month vs sell wait_months later, net of interest and storage loss.

    Prices: AMIS weekly, real (unfilled) weeks only, median of each month, per 40 kg.
    net_gain = later_price * (1 - loss_pct/100) - start_price * (1 + annual_rate/100 * wait_months/12)
    No peeking: only seasons whose later month ends on or before as_of (default: latest data).
    Returns None when fewer than 3 seasons have both prices. Wheat is the focus; other crops work the same way if data allows.
    """
    return {
        "seasons": [{"year": 2025, "start_price": 2370, "later_price": 3083,
                     "net_gain_per_maund": 512, "paid": True}],   # oldest first, values rounded to whole rupees
        "n": 9, "wins": 5,
        "median_net_per_maund": 65,
        "worst_p10_net_per_maund": -400,   # 10th percentile of net_gain (the "bad year")
        "start_month": 5, "later_month": 9,
    }
```

Check figures from Claude's quick run (`start_month=5`, later months 9 and 10, all 3 mandis, 28 mandi-years):
- 3.5% loss: waiting paid 22/28 at 0%, 11/28 at 16.5%, 4/28 at 66%.
- 10% loss: 10/28, 5/28 and 1/28.

The function uses a single later month, so its numbers will differ slightly. That's fine; just document the method.

### 3.2 News (H2, H3; services B2 and screens F3 show it)

```python
# backend/app/news/service.py
def get_news(crop_option: str | None = None, limit: int = 6) -> dict:
    """Today's Pakistan farm news. Never raises: on any failure, returns the saved snapshot."""
    return {
        "items": [{
            "title": "...", "url": "https://...", "source": "Dawn", "published": "2026-10-09",
            "tag": "SUPPORT_PRICE",   # SUPPORT_PRICE | PROCUREMENT | CAP_OR_BAN | IMPORT | PRICE_REPORT | OTHER
            "crop": "wheat",          # lowercase API id (backend/app/ids.py) or None
            "summary_ur": "...", "summary_en": "...",
            "price_rs_per_40kg": 5300,   # only when the headline or summary states a price for the crop, else None
        }],
        "fetched_at": "2026-10-10T14:00:00+05:00",
        "is_snapshot": False,     # True when served from the committed snapshot file
        "tagged_by": "llm",       # "llm" or "rules"
    }

def get_policy_events(crop_option: str, as_of: date | None = None) -> list[dict]:
    """Curated, dated, sourced policy events up to as_of (newest first). Works in replay."""
    return [{"date": "2026-04-28", "tag": "CAP_OR_BAN",
             "text_ur": "...", "text_en": "Punjab: selling wheat above Rs 3,500 declared a crime",
             "source": "The News", "url": "https://www.thenews.pk/print/1412565-..."}]
```

- **Source:** Google News RSS, Pakistan English edition: `https://news.google.com/rss/search?q=<query>+when:7d&hl=en-PK&gl=PK&ceid=PK:en`.
  Tested 10 Oct; it returns Dawn, The News, Tribune and APP. The Urdu feed is mostly YouTube spam, so don't use it. GDELT
  limits requests too tightly to rely on.
- **Cache:** in SQLite, refreshed at most every 6 hours. Send a normal browser `User-Agent` header and follow redirects.
- **Snapshot:** commit `backend/app/news/snapshot.json`, refreshed on demo morning, so the demo works offline.
- **Tagging:** Gemini returns JSON with tag, crop, Urdu and English summaries and the price. If Gemini is down, keyword
  rules fill in the tag and crop, the summary is the title, and the price comes from a regex. Never invent a price: if the
  model returns a number that isn't in the text, drop it.
- **Policy events:** in `backend/app/news/policy_events.json`, by hand, every row sourced. At minimum:
  - Jan 2026: Punjab wheat policy, Rs 3,500 through aggregators
  - Apr 2026: aggregators short of bank money
  - 28 Apr: price cap declared a "crime"
  - 22 May: Sindh movement ban
  - 24 Jul: 1 Mt import decision
  - 27 Jul: aggregator model misses target
  - Sept: Kissan Ittehad demands Rs 5,000
  - Oct: support price undecided (Punjab 4,200, Sindh 5,000)

  Starting links are in section 7.

**What news does to the advice** (B2, in `services.py`): the conflict banner (news price more than 10% away from
AMIS) and lowering confidence by one level when a SUPPORT_PRICE, CAP_OR_BAN or IMPORT item is less than 14 days old.

### 3.3 Wait plan (B1, B2; WhatsApp B3 and the home screen F1 show it)

```python
# backend/app/services.py
def wait_plan(crop_option: str, mandi: str, quantity_maund: float, cash_need_rs: float = 0,
              wait_months: int = 4, money: str = "own", annual_rate: float | None = None,
              storage: str = "godown", offer: float | None = None, phone: str | None = None,
              as_of: date | None = None) -> dict:
    # money: "own" | "bank" | "arhti"; storage: "godown" | "bags"
    return {
        "crop_option": "wheat", "mandi": "bahawalpur", "quantity_maund": 100,
        "verdict": "SPLIT",            # SELL_ALL | SPLIT | HOLD_ALL
        "sell_now_maund": 60, "hold_maund": 40,
        "best_mandi": "bahawalpur", "best_net_price": 3655,
        "exits": [                      # rupees for the whole quantity
            {"kind": "SELL_NOW", "net_total_rs": 365500},
            {"kind": "ARHTI_OFFER", "net_total_rs": 290000},      # only when an offer was entered
            {"kind": "HOLD", "expected_total_rs": 372000, "worst_total_rs": 330000},
        ],
        "history": {"wins": 22, "n": 28, "annual_rate": 0, "loss_pct": 3.5},
        "warnings": ["NEWS_PRICE_CONFLICT"],   # also STALE_PRICE, POLICY_UNCERTAIN, HOLD_WHEAT_ONLY
        "prices_as_of": "2026-10-05", "is_stale": False,
    }
```

**Landed in U1.** The exact shape is `WaitPlanResponse` in `backend/app/schemas.py`, and that schema is the source of
truth over the sketch above. Like the rest of `services.py`, the service takes and returns data names ("Wheat",
"BahawalPur"); `main.py` maps them to API ids. `services.wait_plan` already exists and returns a placeholder answer
labelled `data_source: "placeholder"`, `is_synthetic: True`, so H6 can call it today. U4 swaps in the real engine with
the same signature. `services.news()` and `services.policy_events()` are wired the same way, with placeholders until
H2/H3. U4 then calls Hamza's `get_news` / `get_policy_events` from them.

## 4. Phase U: Abd (light, saves tokens)

| # | Task | Status |
|---|---|---|
| U1 | API contract: schemas, the three routes with placeholder answers, blueprint section 0 | ✅ done 10 Oct |
| U2 | Contradiction copy: beside SELL, an UP call adds "the price may rise, but probably not by more than the interest of waiting" | ✅ done 10 Oct |
| U3 | Review and merge Hamza's PRs: pull, run the full suite (rule 7), click through the app in Urdu and English | as PRs arrive |
| U4 | `DEMO.md`: the 27 Apr 2026 replay, then today with the news banner; real numbers from the running app | after B2 and B4 |
| U5 | Deploy (Render + Vercel, `docs/DEPLOY.md`), demo-morning refresh of the news snapshot, rehearsal, pitch | demo eve and morning |
| U6 | Get one real arhti deal from a farmer (voice note) for the pitch | any time |

## 5. Phase H: Hamza (the build)

Do the batches in order. Within a batch, the tasks touch different files, so separate AI sessions can run them in
parallel. One PR per batch (or per task), named `hamza/P-<task>`.

**Batch 1: engine and data** (no front end)

| # | Task | Files |
|---|---|---|
| H1 | `hold_history` per 3.1, with tests: no peeking past `as_of`; fewer than 3 seasons returns None; the check figures in 3.1 roughly reproduce | `ml/backtest/**` |
| H2 | News: fetch, cache, Gemini tags with a rules fallback, price extraction, snapshot, `get_news` per 3.2. Tests use a saved RSS file, never the network. | `backend/app/news/**` (except the policy files) |
| H3 | Policy events JSON and `get_policy_events` (respects `as_of`), with tests | `backend/app/news/policy_events.json`, `backend/app/news/policy.py` |
| H4 | Check the rates in the table below and record them with sources in `FACTS.md` | `docs/FACTS.md` |

**Batch 2: wire it up** (needs batch 1)

| # | Task | Files |
|---|---|---|
| B1 | Wait engine, with tests. Sell-now maund = ceil(cash need / best net price), capped at the quantity. Hold the rest only for wheat, and only if `wins / n >= 0.5` and `median_net > 0` for the farmer's money and storage, else SELL_ALL. Exits: SELL_NOW, ARHTI_OFFER (if given) and HOLD (median and p10). Warnings per the `WaitWarning` list. | `ml/decision/wait.py`, `config.py`, `test_wait.py` |
| B2 | Replace the placeholders in `services.wait_plan` / `news` / `policy_events` with B1, H2 and H3. Add the news rules: `NEWS_PRICE_CONFLICT` when a price for the crop in the last 14 days is more than 10% from AMIS (fill `news_check`); `POLICY_UNCERTAIN` and confidence down one level for a SUPPORT_PRICE, CAP_OR_BAN or IMPORT item in the last 14 days. Delete `placeholders.py`. Tighten the U1 tests in `backend/tests/test_api.py` to real numbers. | `backend/app/services.py`, `backend/tests/**` |
| B3 | WhatsApp reply for the wait plan (`wait_text`), Urdu, under the message limit | `backend/app/channels/**` |
| B4 | `MODEL_CARD.md` "Decision backtest" (the new engine vs always-sell) and a `DATA_NOTES.md` note on the 2026 AMIS cap | `docs/MODEL_CARD.md`, `docs/DATA_NOTES.md` |

**Batch 3: screens** (needs B2 merged; regenerate types with
`python -m backend.app.export_openapi && npm --prefix frontend run gen:api`)

| # | Task | Files |
|---|---|---|
| F1 | New home screen: cash need, months, whose money (rate editable), storage, offer, then the split, the ways out in rupees, "waiting paid in N of M seasons with your setup" and the worst year. Keep the 18px / 48px readability rules and RTL-only logical classes (`rtl.test.ts`). Reuse `SelectionBar` / `ChipGroup`. | `frontend/src/pages/Home.tsx`, new `components/Wait*.tsx`, locales |
| F2 | Liquidity-tax chart from `history.seasons`: start price vs later price per year, 2026 marked "AMIS capped" | `frontend/src/pages/Why.tsx` (or `History.tsx`), locales |
| F3 | News banner (warnings and `news_check`, always with source, date and link) and policy card | new `components/News*.tsx`, used on Home, locales |
| F4 | Fix What to Grow (compare only within a season, a stale price never ranks first, rice water note at Bahawalpur, wheat support-price card from `/api/policy`). In Compare, a stale price can't be "best". | `services.py` (`crop_plan`, `compare_mandis`), `ml/decision/**`, `Grow.tsx`, `Compare.tsx` |

F1–F3 all add keys to `locales/*.json`: merge them one at a time, or have one session own the locale files for the batch.

**Rates for H4** (they go in `ml/decision/config.py` in B1):

| Rate | Value | Source to check |
|---|---|---|
| Storage loss, proper godown | 3.5% per about 5 months | FAO: 3.5% over 5.4 months in public godowns |
| Storage loss, bags at home | 10% | FAO 2013 via GAIN: "more than 10%" lost in stored wheat |
| Bank or warehouse-receipt loan | 16.5%/yr | already in our economics inputs; confirm source |
| Arhti money | 66%/yr | 4× the formal rate, per the SBP 2014 bulletin and PIDE ("4–5×"); look for a direct figure |
| Kissan Card | Rs 30,000/acre, up to Rs 150,000 a season, 1–12.5 acres, 6 months + 1 month grace, **inputs only** | punjab.gov.pk/node/5690 and bop.com.pk/CMPunjabKissanCard |

## 6. Merge order

1. U1 + U2 into `main` (done when this file lands), **before** Hamza branches off.
2. Batch 1 (any order), then batch 2, then batch 3. Abd reviews and merges each PR (U3).
3. Freeze on demo eve (time set by Abd), then deploy and rehearse in the morning (U5).

## 7. Research links (starting points for H3 and H4)

- Punjab wheat policy 2026, Rs 3,500: https://dunyanews.tv/en/Business/930787-punjab-announces-wheat-policy-2026-with-rs3,500-per-maund
- Aggregators short of bank money (Apr 2026): https://cropgpt.ai/funding-shortfall-jeopardizes-punjabs-3m-tonne-wheat-procurement
- Price cap declared a "crime" (28 Apr 2026): https://www.thenews.pk/print/1412565-punjab-criminalises-wheat-sales-above-rs-3-500-40kg
- Sindh movement ban (22 May 2026): https://newswav.com/article/sindh-bans-wheat-movement-as-pakistan-battles-rising-prices-A2605_QyhPaU
- 1 Mt import (24 Jul 2026): https://propakistani.pk/2026/07/24/govt-decides-to-import-of-1-million-tonnes-of-wheat/
- Aggregator model misses target (27 Jul 2026): https://propakistani.pk/2026/07/27/punjab-misses-wheat-target-as-aggregator-model-fails-and-grain-flows-to-sindh-kp/
- Kissan Ittehad demands Rs 5,000: https://www.dawn.com/news/2031938
- Support price undecided, Punjab 4,200 vs Sindh 5,000: https://bloompakistan.com/pakistan-wheat-support-price-punjab-sindh-rs5000/
- Open market Rs 5,300 (Oct 2026): https://arynews.tv/flour-price-rises-in-punjab-as-wheat-cost-surges-sharply-in-punjab
- South Punjab farmer's account, Rs 2,900 offer: https://www.thefridaytimes.com/21-May-2026/harvest-window-forty-five-days-determine-pakistan-s-food-year
- Warehouse receipts, 37 warehouses, small-farmer barriers: https://profit.pakistantoday.com.pk/2026/06/18/can-electronic-warehouses-change-how-pakistani-farmers-sell-their-crops
- Coalition's farmer warehouse-receipt proposal: https://propakistani.pk/2026/09/29/pakistan-agricultural-coalition-proposes-new-wheat-support-model-for-farmers/
- Kissan Card terms: https://punjab.gov.pk/node/5690 and https://bop.com.pk/CMPunjabKissanCard
- Storage loss: https://www.fao.org/4/X5048E/x5048E13.htm and https://nutritionconnect.org/resource-center/power-hermetic-storage-technology-reducing-food-loss-and-waste-pakistan-0
- Arhti credit cost: https://www.sbp.org.pk/research/bulletin/2014/Vol-10-1/Tete-a-TeteArhtiyas.pdf and https://pide.org.pk/research/the-role-of-arthi-in-agriculture-marketing-an-exploiter-or-facilitator-of-farmers/
- Liquidity evidence (Kenya trial, 29% return on harvest loans): https://www.atai-research.org/wp-content/uploads/2018/12/BurkeBergquistMiguel2019.pdf

# FarmSight pivot: "Can you afford to wait?" (10 Oct 2026)

The team agreed on 10 Oct to change the core question. Instead of asking "will the price rise?", the app now asks
**"can you afford to wait, and with whose money?"** It also adds a free news feed, because in 2026 AMIS showed
wheat capped at Rs 3,450 while the open market reached about Rs 5,300.

**v3, 10 Oct evening: three people, small farmers only, the loan planner added.** An agriculture expert we spoke to
(who can't give figures) said the small farmer's real problem is the **loan**:
1. They borrow more than the crop needs.
2. The whole loan falls due at harvest.
3. So they have to sell at the harvest low.

FarmSight now covers that thread through the season:
- **Sowing:** the *loan planner*. What the crop actually needs, the cheapest money first (Kissan Card 0%, PM Youth 0%,
  Akhuwat 0%), and what over-borrowing from the arhti costs.
- **During the season:** a simple *loan list* in the profile.
- **Harvest:** the *wait plan*. Loans due plus household spending minus other income (e.g. milk) gives the cash needed,
  and from that, sell X now and hold Y.

**Who:** Usman (engine), Hamza (data and API) and Abd (screens, review, demo). Each owns separate files (section 2).
Every task is sized for **one AI session** (section 1, rules 9–11).

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
9. **One task per AI session.** Open the session with: *"Read docs/PIVOT.md sections 1 and 3, then task card <id> in
   section 5. Do only that task."* Point it at the files on the card; don't paste whole files into chat. Start a fresh
   session (or compact) between tasks.
10. **Finish every session with a push**, even if the task isn't done. Use `WIP:` in the commit title, and put
    *done / left / next step* in the PR description. The next session reads that and carries on, so nothing is lost
    when a session limit hits.
11. **Small farmers only** (land of 12.5 acres or less, the Kissan Card limit). Medium and large farmers are out of scope.

## 2. Who owns which files

| Area | Usman: engine | Hamza: data and API | Abd: screens, review, demo |
|---|---|---|---|
| Python | `ml/**` (incl. new `ml/backtest/`, `ml/decision/wait.py`, `ml/decision/loan.py`) | `backend/app/**` except `news/policy*`; `backend/tests/**` | none |
| Policy events | `backend/app/news/policy.py`, `backend/app/news/policy_events.json` | none | none |
| Data | none | `data/**` (new `input_costs.json`, `loan_options.json`) | none |
| Front end | `frontend/src/pages/Grow.tsx`, `Compare.tsx`; locale blocks `"grow"`, `"compare"` | none | all other `frontend/**` |
| Docs | `MODEL_CARD.md` | `FACTS.md`, `DATA_NOTES.md`, `URDU_REVIEW.md` | `BLUEPRINT.md`, `PLAN.md`, `PIVOT.md`, `DEMO.md`, `DEPLOY.md`, `README.md`, `CLAUDE.md` |
| Config and CI | none | `requirements*.txt` (ask first: rule 4) | `.github/**`, `render.yaml`, `frontend/vercel.json`, `.env.example` |

**Locale files are shared** (`frontend/src/locales/ur.json` and `en.json`). Add keys **only inside your own top-level
block**: Usman `"grow"` and `"compare"`; Abd `"wait"`, `"loan"`, `"news"` and the rest. Git merges edits in different
blocks cleanly. `src/locales.test.ts` checks that Urdu and English have the same keys.

**Contract changes** (`schemas.py`, Hamza's) need a word in chat first: the screens, WhatsApp and the engine all depend
on them.

**Database:** new tables (news cache, `farmer_loans`) go in with `CREATE TABLE IF NOT EXISTS`. The news cache sits inside
`backend/app/news/`; `farmer_loans` sits in `db.py`.

## 3. Interfaces (fixed now)

### 3.1 Hold backtest (H1, Usman; the wait engine B1 calls it)

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

### 3.2 News (H2 Hamza, H3 Usman; B2 and F3 show it)

`get_news` lives in `backend/app/news/service.py` (Hamza). `get_policy_events` lives in `backend/app/news/policy.py` (Usman), with the same signature as below.

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

### 3.3 Wait plan (B1 Usman, B2 Hamza; B3 and F1 show it)

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

### 3.4 Loan planner and loan list (L1 engine, L2 API, L3 screens)

**Engine** (Usman, `ml/decision/loan.py`, pure function, no file reading):

```python
def loan_plan(acres: float, input_items: list[dict], savings_rs: float, options: list[dict],
              months_to_harvest: int, planned_borrow_rs: float | None = None,
              planned_rate_pct: float | None = None) -> dict:
    """input_items: [{"item": "fertilizer", "rs_per_acre": 21000}, ...] for this crop (Hamza's input_costs.json).
    options: loan options this farmer is eligible for, each {"id", "annual_rate_pct", "max_rs"}, already filtered and
    capped by the API (Kissan Card max = min(30,000 x acres, 150,000) for 1-12.5 acres, etc.).
    need = sum(rs_per_acre) x acres; borrow_needed = max(0, need - savings).
    Ladder: fill borrow_needed from the cheapest option up (ties: keep the input order).
    interest on each slice = amount x rate x months_to_harvest / 12; due at harvest = principal + interest."""
    return {
        "input_need_rs": 290000, "savings_rs": 0, "borrow_needed_rs": 290000,
        "ladder": [{"id": "kissan_card", "amount_rs": 150000, "interest_rs": 0},
                   {"id": "zarkhez_e", "amount_rs": 140000, "interest_rs": 10500}],
        "ladder_interest_rs": 10500, "harvest_due_rs": 300500,
        "planned_borrow_rs": 400000, "planned_interest_rs": 132000,   # planned x planned_rate x months / 12
        "over_borrow_rs": 110000,                                     # max(0, planned - borrow_needed)
        "extra_cost_rs": 121500,                                      # planned_interest - ladder_interest
        "uncovered_rs": 0,                                            # borrow_needed the eligible options can't cover
    }
```

**API** (Hamza):
- `GET /api/loan-plan?crop=&acres=&savings_rs=&age=&planned_borrow_rs=&planned_lender=&as_of=` returns
  `LoanPlanResponse` (`Labelled`). It holds the engine's fields plus:
  - `input_items`: `[{item, name_ur, name_en, rs_per_acre}]`, with a source note.
  - `options`: `[{id, name_ur, name_en, annual_rate_pct, max_rs, eligible, why_not_ur, why_not_en, conditions_ur,
    conditions_en, source_url, verified}]`. Ineligible options are listed too, with the reason.
  - `months_to_harvest` (from the crop calendar and `as_of`).
  - `warnings`: `OVER_BORROWING`, `NOT_SMALL_FARMER` (over 12.5 acres), `COST_ESTIMATE` (always: costs are escalated
    from the official table) and `UNCOVERED`.
- `planned_lender` is one of the option ids; its rate prices the "what you planned" line.
- `age` is optional; without it, PM Youth shows `eligible: false` with "age needed".
- Loan list: `GET /api/farmers/me/loans`, `POST /api/farmers/me/loans` with
  `{lender, amount_rs, annual_rate_pct, due_date}`, and `DELETE /api/farmers/me/loans/{id}`. Farmer auth is required.
- **Wait plan additions:**
  - New query params `household_spend_rs_month` and `other_income_rs_month` (default 0).
  - When logged in and `cash_need_rs` isn't given: `cash_need_rs` = loans due before the later sale (principal +
    interest) + max(0, household − other income) × `wait_months`.
  - The response echoes `household_spend_rs_month`, `other_income_rs_month` and `loans_due_rs`. B1 gets these as
    plain numbers.

**Loan options** (Hamza's `data/processed/loan_options.json`; verify each on its official page and set `verified`):

| id | Rate | Limit | Who | Source |
|---|---|---|---|---|
| `kissan_card` | 0% | Rs 30,000/acre, up to Rs 150,000 a season; inputs only; 6 months + 1 month grace | Punjab, 1–12.5 acres | punjab.gov.pk/node/5690, bop.com.pk/CMPunjabKissanCard |
| `pm_youth` | 0% (Tier 1) | up to Rs 500,000 | age 21–45 | ztbl.com.pk (PM Youth Business & Agriculture Loan) |
| `akhuwat` | 0% | small (sources say Rs 10,000–80,000); two guarantors; apply at a branch | anyone with a CNIC, 18–62 | akhuwat.org.pk (confirm the amount) |
| `zarkhez_e` | KIBOR + 8%, floor 18% | Rs 100,000/acre, up to Rs 1,000,000 | up to 12.5 acres in Punjab | ztbl.com.pk Zarkhez-e, sbp.org.pk/acd/2025/CL1-AnnexA.pdf |
| `bank` | 16.5% | none | anyone | our economics inputs (KIBOR + 5%) |
| `arhti` | 66% | none | anyone | 4× the formal rate (SBP 2014, PIDE) |

**Input costs** (Hamza's `data/processed/input_costs.json`, from the official API cost table already in
`data/sources/api_wheat_2023_24.*`):
- **Cash inputs only:** seed, fertiliser, sprays, land preparation, irrigation, harvesting and threshing. Leave out
  land rent and the farmer's own family labour.
- **Fertiliser** escalated by actual prices (urea 2,150 to 4,455, DAP 9,000 to 14,259, in `economics_inputs.json`);
  everything else by CPI.
- **Wheat first.** Cotton only if time allows (its API table is 2022-23).
- Each item: `{item, rs_per_acre, method, source}`.

## 4. Done so far

| # | Task | Status |
|---|---|---|
| U1 | API contract for wait plan, news and policy (placeholder answers); blueprint section 0 | ✅ merged 10 Oct |
| U2 | Beside SELL, an UP call adds "the price may rise, but probably not by more than the interest of waiting" | ✅ merged 10 Oct |

## 5. Task cards (each one session)

> **Status, 10 Oct evening.** Everything in waves 1–3 is merged: Hamza did L2a, D1, D2, H2, N1, B2 and B3; Usman did L1;
> Abd did L3 (the loan planner screen, the loan list in Profile, and household spending / other income on the wait
> screen) and E1 (hold only on at least 60% wins and a median of at least 1% of the price). Loans owed now include
> interest to the due date. Left: deploy and rehearsal (DP); D4 skipped.
>
> **Status, 10 Oct 15:30 (Abd's review of `main`).** Hamza merged batches 1–3 of the earlier plan this morning, before
> v3 was written. **Already done, don't redo:** H1, H2, H3, the D2 rates (in `FACTS.md`), B1, B2, B3, B4, F1, F2, F3, F4.
> The full suite is green on `main`.
>
> **Still open:** L2a, D1, D2 (loan options only), L1, L3, the wait-plan additions in 3.4 (household spending, other
> income, cash need from loans), the fixes below, and D4 (optional).
>
> | Card | Who | Fix found in review |
> |---|---|---|
> | **N1** | Hamza | **Demo-critical.** The news price check read a **flour** headline ("Flour price hits Rs5,...", Daily Pakistan, 10 Oct) as a wheat price of Rs 5,200, which raises a false `NEWS_PRICE_CONFLICT`. Extract a price only when the text is about wheat/gandum **and** gives it per 40 kg / maund; skip atta/flour, bags and per-kg prices. Add a test with that headline. |
> | **E1** | Usman | HOLD_ALL fires on a median of **+Rs 13/maund** (wheat, Bahawalpur, own money, today), which is noise. Proposal: hold only if `wins/n >= 0.6` **and** median net is at least 1% of today's price; otherwise SELL_ALL, with the history still shown. Team call: say yes or no in chat. |
> | **DM** | Abd | The replay date moves to **10 May 2026**. On 27 Apr the Bahawalpur backtest starts in April and says SELL_ALL. On 10 May, own money in a godown with 5 months gives HOLD (7 of 9 seasons) and arhti money in bags gives SELL, which is the contrast we want. |

Do the waves in order. Within a wave, the three people work in parallel on different files. One PR per card, named
`<name>/P-<card>`. Abd reviews and merges (rule 2).

### Wave 1: contracts and data (start now)

| Card | Who | Task | Files | Done when |
|---|---|---|---|---|
| **L2a** | Hamza | **First, and fast.** Loan contract per 3.4: `LoanPlanResponse`, `Loan`/`LoanIn`, the wait-plan additions in `schemas.py`; routes returning placeholder answers (`data_source: "placeholder"`, as U1 did); `farmer_loans` table; regenerate OpenAPI and front-end types | `schemas.py`, `main.py`, `services.py`, `placeholders.py`, `db.py`, `backend/tests/`, `frontend/src/api/*` | Merged. Abd's screens and Usman's engine build against it. |
| **D1** | Hamza | Cash input cost per acre for wheat (cotton if time) per 3.4, plus a `FACTS.md` entry | `data/processed/input_costs.json`, `docs/FACTS.md` | Each item has a method and source; the total per acre is in the PR description |
| **D2** | Hamza | `loan_options.json` per 3.4, each option checked on its official page; also the rates for H4 (table below) | `data/processed/loan_options.json`, `docs/FACTS.md` | Every row has `source_url` and `verified` |
| **H1** | Usman | `hold_history` per 3.1, with tests (no peeking past `as_of`; under 3 seasons returns None; check figures roughly reproduce) | `ml/backtest/**` | Tests pass |
| **L1** | Usman | `loan_plan` per 3.4, with tests (ladder order, the cap, over-borrowing, uncovered, zero savings) | `ml/decision/loan.py`, `test_loan.py` | Tests pass |
| **H3** | Usman | Policy events JSON (list in 3.2) and `get_policy_events(crop_option, as_of)`, with tests | `backend/app/news/policy.py`, `policy_events.json` | Every row sourced; `as_of` respected |
| **F2** | Abd | Liquidity-tax chart from the wait plan's `history.seasons` (placeholder data for now), 2026 marked "AMIS capped" | `frontend/src/pages/Why.tsx`, new component, `"wait"` locale block | Builds, readable at 360px in Urdu and English |

### Wave 2: real answers (after L2a)

| Card | Who | Task | Files | Done when |
|---|---|---|---|---|
| **H2** | Hamza | News per 3.2: fetch, cache, Gemini tags with a rules fallback, price extraction, saved snapshot. Tests use a saved RSS file. | `backend/app/news/**` except `policy*` | `get_news()` works offline from the snapshot |
| **B1** | Usman | Wait engine. Cash need comes in as a number (loans due + household − other income, computed by the API). Sell-now maund = ceil(cash need / best net price), capped at the quantity. Hold the rest only for wheat, and only if `wins/n >= 0.5` and `median_net > 0` for this money and storage. Exits and warnings per the schema. | `ml/decision/wait.py`, `config.py`, `test_wait.py` | Tests pass |
| **F1** | Abd | Wait-plan screen on Home: cash need (or "from my loans" when logged in), household spending, other income (milk, labour), months, whose money, storage, offer; then the split, ways out, "waiting paid in N of M seasons with your setup", worst year | `frontend/src/pages/Home.tsx`, new `components/Wait*.tsx`, `"wait"` locale block | Works on placeholder data; 18px / 48px rules; RTL test passes |
| **L3** | Abd | Loan planner screen (new tab): crop, acres, savings, age, what you planned to borrow and from whom; then inputs per acre, the cheapest-first ladder, harvest due, and over-borrowing in rupees. Plus a loan list in Profile. | new `frontend/src/pages/Loan.tsx`, `Profile.tsx`, `Header.tsx`, `"loan"` locale block | Works on placeholder data |

### Wave 3: wire up (after wave 2)

| Card | Who | Task | Files | Done when |
|---|---|---|---|---|
| **B2** | Hamza | Swap the placeholders for B1, L1, H1, H2 and H3. News rules: `NEWS_PRICE_CONFLICT` (a crop price within 14 days, more than 10% from AMIS; fill `news_check`), `POLICY_UNCERTAIN` plus confidence down one level. Loan options filtered and capped by eligibility; cash need from loans. Delete `placeholders.py`. Tighten the API tests to real numbers. | `backend/app/services.py`, `backend/tests/**` | No placeholder left; full suite green |
| **B3** | Hamza | WhatsApp replies: wait plan (`wait_text`) and loan plan (`loan_text`), Urdu, under the message limit | `backend/app/channels/**` | Tests pass |
| **F4** | Usman | Fix What to Grow (compare within a season only; a stale price never ranks first; rice water note at Bahawalpur; wheat support-price status from H3). In Compare, a stale price can't be "best". | `ml/decision/**`, `Grow.tsx`, `Compare.tsx`, `"grow"` / `"compare"` locale blocks | If an API field is needed, ask Hamza |
| **F3** | Abd | News banner (warnings, `news_check`, always with source, date and link) and policy card | new `components/News*.tsx`, Home, `"news"` locale block | Uses the real `/api/news` and `/api/policy` |
| **B4** | Usman | `MODEL_CARD.md` "Decision backtest": the new engine vs always-sell, and the loan-ladder method | `docs/MODEL_CARD.md` | Numbers from H1 |

### Wave 4: ship (Abd)

| Card | Task |
|---|---|
| **R** | Review and merge every PR as it arrives: pull, run the full suite (rule 7), click through in Urdu and English |
| **DM** | `DEMO.md` with real numbers. Act 1: October sowing, Ahmed with 5 acres plans Rs 4 lakh from the arhti; the loan planner shows what he really needs and the cheapest money. Act 2: replay 27 Apr 2026, where the small loan lets him hold. Act 3: today's news banner. |
| **DP** | Deploy (Render + Vercel, `docs/DEPLOY.md`), refresh the news snapshot on demo morning, rehearse, pitch |

### Optional data (only if waves 1–3 are merged before the freeze)

| Card | Who | Task |
|---|---|---|
| **D4** | Hamza | Add **Bahawalnagar** and **Lodhran** (wheat and cotton) from AMIS: about 1.08M and 0.37M acres of wheat, the biggest small-farm districts beside ours. Re-run cleaning, features and runtime tables; add transport distances. Skip it if anything is red. |

**Rates for D2** (they go in `ml/decision/config.py` in B1, with sources in `FACTS.md`):

| Rate | Value | Source to check |
|---|---|---|
| Storage loss, proper godown | 3.5% per about 5 months | FAO: 3.5% over 5.4 months in public godowns |
| Storage loss, bags at home | 10% | FAO 2013 via GAIN: "more than 10%" lost in stored wheat |
| Bank loan | 16.5%/yr | economics inputs (KIBOR + 5%) |
| Arhti money | 66%/yr | 4× the formal rate, per the SBP 2014 bulletin and PIDE ("4–5×") |

## 6. Merge order

1. **L2a first** (it unblocks everyone), then the rest of wave 1 in any order.
2. Waves 2, 3 and 4 in order. Abd merges each PR after the full suite passes.
3. Freeze on demo eve (time set by Abd), then deploy and rehearse in the morning.

## 7. Research links (starting points for H3, D1 and D2)

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
- Loan options: https://ztbl.com.pk/agri-loan/prime-ministers-youth-business-agriculture-loan-scheme/ ,
  https://ztbl.com.pk/agri-loan/zarkhez-e-assan-digital-zarai-qarza/ , https://www.sbp.org.pk/acd/2025/CL1-AnnexA.pdf ,
  https://en.wikipedia.org/wiki/Akhuwat_Foundation
- Smallholders put only about half of their credit into farming (fungibility): https://link.springer.com/article/10.1186/s40854-018-0109-x
  and https://www.researchgate.net/publication/281078636_Fungibility_of_Smallholder_Agricultural_Credit_Empirical_Evidence_from_Pakistan
- District crop areas (Crop Reporting Service): https://crs-agripunjab.punjab.gov.pk/system/files/Bahawalpur.pdf ,
  .../Bahawalnagar.pdf , .../Lodhran.pdf
- Milk (reference only): Sindh ex-farm Rs 215/L, Oct 2026: https://arynews.tv/dairy-farmers-urge-immediate-notification-of-revised-milk-prices ;
  yields 7.9 L/day buffalo, 6.1 L/day cow (PBS 2006): https://www.pbs.gov.pk/sites/default/files/agriculture/publications/pakistan-livestock-cencus2006/special_report/Write-up%20Special%20report%20on%20Milk%20Production%202006.pdf

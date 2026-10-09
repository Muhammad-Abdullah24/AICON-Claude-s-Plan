# Teammates' original project notes (9 Oct 2026)

> Kept word for word so nothing is lost. **The data sections (4, 5 item 6b, coverage table, cleaning rules) are still the reference for Owner A.** Where this file disagrees with `docs/PLAN.md` on scope, models, front end or roles, **PLAN.md wins** (decided 9 Oct, see PLAN.md change log). The "existing code" in section 5 is the v1 code, which this repo does not use.

---

## FarmSight: AI Crop Economics Advisor

AICON'26, SEECS NUST, Oct 9-11 2026. 30hr build, 5min demo.

## 1. Problem
Pakistani farmers lose money on market decisions, not farming. They sell at harvest when prices are lowest and don't know a nearby mandi pays more. FarmSight answers: what price to expect, when to sell, where to sell.

## 2. Scope (FINAL)
- **Cities:** BahawalPur, Vehari, RahimYarKhan
- **Crops:** Wheat, Rice (IRRI variety only), Cotton (Seed Cotton / Phutti)
- **Series:** 8 city-crop series. RahimYarKhan rice dropped (6% coverage).
- **Out of scope:** sugarcane (mill-priced, no mandi data), maize, vegetables, other cities.

## 3. Three AI Layers
| Layer | What | Model | Output |
|---|---|---|---|
| 1. Price Forecaster | Price 4 weeks ahead per city-crop | XGBoost regressor | Rs/100kg + range |
| 2. Sell Timing Advisor | SELL / HOLD / WAIT | Derived from Layer 1 (+ quantile or classifier) net of storage and interest cost | Action + reason (SHAP) + Urdu text |
| 3. Cross-Mandi Arbitrage | Best city to sell in | No ML. Price gap minus transport cost | Net Rs gain |

Always report a **naive baseline** (price in 4 weeks = price today). The model only counts if it beats it.

## 4. Data
| File | Content | Status |
|---|---|---|
| `data/farmsight_prices_3x3.csv` | AMIS daily prices, 3 cities x 3 crops, Jan 2022-Oct 2026, 10,380 rows. Columns: date, city, crop, variety, price_rs_per_100kg | Done, needs cleaning |
| `data/amis/amis_YYYY_MM.csv` | Raw monthly AMIS exports (58 files) | Done |
| `data/weather_daily_2015_2026.csv` | Open-Meteo daily weather, includes our 3 cities (district names: Bahawalpur, Vehari, Rahim_Yar_Khan) | Done |
| `data/procurement_prices_punjab.csv` | Govt support prices, 2011-12 on | Done |
| `data/economics_inputs.json` | Cost of production, support prices, SBP rate, diesel, USD/PKR, CPI, fertilizer, storage, transport. Each value has source, date and confidence | Done (see its `data_quality_warnings`) |
| `data/sources/` | Official API cost-of-production PDFs (wheat 2023-24, rice 2022-23, cotton 2022-23) plus extracted text | Done |

**Economics inputs, key values (details and sources in the JSON):**
- SBP policy rate 11.5% (14 Sep 2026). Holding interest assumed 16.5%/yr (policy rate + 5%, the API method).
- Wheat support price 2025-26: Rs 3,500/40kg. 2026-27 not yet announced. Punjab open market 8 Oct 2026: Rs 5,300 (up from 4,700 a week earlier).
- Cost of production per 40kg, Punjab: wheat Rs 3,700-3,761 (2026); IRRI paddy about Rs 2,058 and seed cotton about Rs 6,616 (official 2022-23 tables escalated by CPI x1.381, a lower bound).
- Diesel Rs 394.94/L, USD/PKR about 277.
- Still ASSUMPTIONS to replace with quotes: storage Rs 15/40kg/month, freight Rs 1.3/40kg/km.

**Units: AMIS prices are Rs per 100kg, not 40kg.** Check this before comparing with support prices (Rs/40kg).

### Coverage (valid prices / days listed)
| City | Wheat | Rice IRRI | Cotton |
|---|---|---|---|
| BahawalPur | 75% | 90% | 54% |
| Vehari | 76% (from Mar 2023) | 90% (from Feb 2023) | 69% |
| RahimYarKhan | 77% | 6% (drop) | 72% |

### Cleaning rules (Data owner)
1. Use variety = IRRI for rice; drop Basmati varieties.
2. Drop rows with empty price. Flag and remove outliers (e.g. > 3x rolling median).
3. Resample to weekly mean per city-crop. Forward-fill gaps of up to 2 weeks only.
4. Map weather district names to city names, aggregate to weekly (mean tmax/tmin/rh, sum precip).
5. Build features: lags 1/2/4/8/12w, momentum, rolling volatility, moving averages, month sin/cos, sowing/harvest flags (handle year wrap), weather, ratio to support price.
6. Target: price 4 weeks ahead. Output one `features.csv`, which is the contract between roles.

## 5. Known Bugs in Existing Code (`project/farmsight/`)
1. `data_pipeline.py` generates synthetic prices. Replace with real CSV.
2. `hash(crop) % 100` encoding is non-deterministic. Use a fixed mapping.
3. Harvest flag breaks for ranges that wrap the year (e.g. months 11-3).
4. `seasonal_factor` and `inflation_factor` leak the synthetic generator. Remove.
5. `config.py`: cost, support price and middleman values are unsourced and wrong (e.g. wheat support 2025 = 3900, 2026 = 4000; real 2025-26 is 3,500). Replace with `economics_inputs.json`. Remove MIDDLEMAN_CUT unless sourced.
6b. AMIS wheat may lag the real market in late 2026 (AMIS about Rs 3,820/40kg vs Rs 5,300 reported). Validate before trusting the newest weeks. AMIS rice IRRI unit (paddy vs milled) is unconfirmed.
6. All previous metrics (R2 0.92, MAPE 16.8%, 46.6% advisor accuracy) came from synthetic data. Do not quote them.

## 6. Evaluation (honest)
- Time split: train 2022-2025, test 2026. No random split.
- Metrics: MAPE per series, directional accuracy, and improvement over the naive baseline.
- Only quote what the real-data model measures. Show the baseline next to it.

## 7. Roles (merge if the team is smaller than 4)
| Role | Owns | Deliverable |
|---|---|---|
| **A. Data** | Section 4 cleaning, weather merge, features | `features.csv` + schema note, first within ~4h |
| **B. ML** | Layers 1 and 2: training, baseline, SHAP, model files | `models/*.json`, metrics table |
| **C. App** | Streamlit UI, charts, Urdu text, SELL/HOLD/WAIT screen | Working `app.py` on real models |
| **D. Economics + Pitch** | Costs, storage/interest, transport, Layer 3, deck, demo script, judge Q&A | `economics.py`, deck, 5-min script |

**Interface contract:** A publishes `features.csv`. B loads it and saves models. C loads models and `features.csv`. D provides `economics.py` (break-even, net price, arbitrage) that C imports. Agree on column names before anyone codes.

## 8. Timeline (30h)
- **0-4h:** A cleans data and ships `features.csv`. D collects cost, interest and transport inputs. C builds the UI skeleton on dummy data. B sets up the baseline.
- **4-12h:** B trains and evaluates. D builds Layer 3. C wires the real models.
- **12-20h:** Joint integration, SHAP screen, Urdu text, fix weak series.
- **20-26h:** Deck, demo rehearsal, judge Q&A.
- **26-30h:** Freeze. Bug fixes only.

## 9. Demo (5 min)
1. Problem (30s): farmer sells at harvest, loses money.
2. Wheat in Vehari (1m): forecast chart vs baseline.
3. SHAP (1m): why the model says so.
4. Sell advisor (1m): colored SELL/HOLD/WAIT with Urdu text and storage/interest-adjusted gain.
5. Cotton in RahimYarKhan (30s): volatile crop.
6. Arbitrage (30s): BahawalPur vs Vehari net of transport.
7. Close (30s): real AMIS data, honest metrics, decision support not magic.

## 10. Judge Risks
- "Is this just a price chart?" Show SHAP, an actionable signal, and Urdu.
- "Can farmers hold?" Show storage and interest cost in the HOLD calculation.
- "Does info change outcomes?" Position as decision support and state the limitation.
- "Where is the real data?" 4.8 years of daily AMIS mandi prices, shown openly with coverage gaps.

## 11. Tech
Python 3.10+, XGBoost, SHAP, Streamlit, Plotly, pandas, Open-Meteo. Data scraping was done with Node.js (`scrape_amis_focused.js`, `build_dataset.js`). Python is not installed on the scraping machine, so install it before ML work.

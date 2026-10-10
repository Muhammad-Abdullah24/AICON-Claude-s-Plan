# Model card: FarmSight's AI

> **For judges: one page.** Owner B (Usman). Every number below comes from the evaluation gate
> (`ml/eval/report.md` for 2025, `ml/eval/report_test.json` for 2026) or the technical details further down.
> The 2026 test set was scored once, on 10 October 2026, with the deployed model and nothing changed afterwards.

## What the AI does

For Wheat, Cotton, IRRI and Super Basmati rice at the Bahawalpur, Vehari and Rahim Yar Khan mandis, FarmSight
forecasts the mandi price **4 weeks ahead with a range**, says **SELL** (بیچ دیں) or **WAIT** (رکیں), and explains
**why** in Urdu. The large language model only handles language (chat, voice transcription); it never produces a
number a farmer sees.

## Data

- **Prices:** real AMIS Punjab daily mandi prices, 2015 to October 2026, cleaned to weekly series (11 series).
  Rs per 40 kg (one maund). Stretches where AMIS repeated the same price for weeks are flagged and never used as
  model inputs.
- **Weather:** Open-Meteo daily weather for each mandi district (stored history for training; live in the app).
- **Split by time, never shuffled:** train = target weeks before 2025 (2,733 rows), validation = 2025 (328),
  test = 2026 (165, held back and scored once at the end). No synthetic rows anywhere in training or scoring.

## Model

- **XGBoost** predicting the **4-week % price change** (prices tripled since 2015, so % change, not price level).
- **Inputs (26):** recent momentum and price swings, price vs its 8-week average, season (month, sowing and harvest
  flags), weather (heat, rain), and crop and mandi. No absolute price levels.
- **Settings chosen without touching validation:** 36 settings compared by rolling cross-validation on 2021–2024.

## The honest result

| | Price error (MAPE) | Direction right on moves > 3% | Range holds the real price |
|---|---|---|---|
| "Price stays the same" baseline, 2025 validation | **5.60%** | 0% (never predicts a move) | **81%** (target 80%) |
| Our XGBoost model, 2025 validation | 5.64% | **60%** overall, **72% for wheat** | 72% |
| "Price stays the same" baseline, **2026 test** | **3.44%** | 0% | **86%** |
| Our XGBoost model, **2026 test** | 3.46% | **63%** overall, **81% for wheat** | n/a |

**The model did not beat the naive baseline on price**, in 2025 or in 2026, so by our own rule (NFR-01) the price
forecast shown is the baseline, labelled "baseline". Mandi prices are sticky, and a third of the weeks touch a frozen
AMIS price. But the model **does** call the direction of real wheat moves: 72% in 2025 (50 moves, p = 0.001) and
**81% in 2026** on data it never saw (17 of 21, p = 0.004). Cotton and Super Basmati show no skill in either year.

## What we ship, and why

- **Price and range:** the baseline for every crop. It is the more accurate forecast and its range is well calibrated.
- **Direction:** the model's "likely up / likely down" for **wheat only**, where it has proven skill. Other crops say
  "no reliable direction". Wheat was chosen after seeing the 2025 results; the one-time 2026 test then confirmed it
  (81%), which is why it stays wheat only.
- **SELL / WAIT:** WAIT only if the forecast is at least 5% above today, and the rupee gain subtracts the interest
  cost of waiting (16.5% a year). With the baseline forecast the answer is SELL, which is the honest answer:
  a 5% rise in 4 weeks happens in only 14–19% of real weeks.

## How "Why?" works

The model's prediction is split exactly into each input's contribution with **SHAP** (TreeSHAP, computed by
XGBoost itself). Related inputs are summed into 8 reasons a farmer can follow (recent trend, time of year, rain,
heat...), each with its rupee effect per 40 kg, written in Urdu and English from fixed templates. No LLM writes
these. On the two backup demo weeks the wheat call was right: 24 March 2025 "likely down" (it fell 19.7%) and
4 August 2025 "likely up" (it rose 48.6%).

## Limits

- A backtest on historical AMIS prices, not a field trial. AMIS can lag the open market (Bahawalpur wheat:
  AMIS about Rs 3,820 vs about Rs 5,300 reported).
- Super Basmati's latest prices are months old; every screen shows the "prices as of" date, in amber when old.
- Costs, transport (Rs 1.3 per 40 kg per km) and the 0.65 milling yield are estimates and are labelled so.
- 2026 is a short test (165 rows, 21 wheat moves). It confirms the direction claim, but more seasons would make it
  firmer.

---

# Technical details

> Owner B (Usman). Written for task B4 on 10 October 2026. B10 turns this into the one-page version for judges.

### Decision

**Deployed: the persistence-band baseline, labelled "baseline".** The XGBoost model did not beat persistence
on pooled validation MAPE, so under NFR-01 it is not deployed. The forecast is today's AMIS price; the range
is today's price moved by the 10th and 90th percentile of past 4-week changes for that crop option (train
years only). The record is `artifacts/models/deployed.json`.

The model is not useless: it calls the direction of moves bigger than 3% right **60%** of the time on
validation (72% for wheat), where persistence by definition never predicts a move. Whether to show that as
a separate "direction" signal is a team decision (see the proposal at the end).

### Data

- AMIS Punjab daily mandi prices 2015–2026, cleaned to weekly series by Owner A (`data/processed/features.csv`),
  Rs per 40 kg. 11 series: Wheat, Cotton and Super Basmati at Bahawalpur, Vehari and Rahim Yar Khan; IRRI at
  Bahawalpur and Vehari.
- Real rows only (`is_synthetic = 0`). Split by target week: train before 2025 (2,733 rows), validation 2025
  (328 rows), test 2026 (165 rows, scored once on 10 October 2026; see "Test result" below).
- Weather from Open-Meteo, aggregated by `ml/features/` exactly as at runtime.

### Model

- XGBoost, native API, fixed seed, one thread (reproducible). Code: `ml/forecast/train.py`.
- **Target:** the 4-week % price change, not the price. Prices roughly tripled over 2015–2026, so a model on
  price levels would extrapolate. Price forecast = today's price × (1 + predicted change / 100).
- **Inputs:** `FEATURE_COLUMNS` from `ml/features/` minus absolute price levels (price, lags, moving averages):
  momentum, volatility, price vs its 8-week average, calendar (month, sowing and harvest flags), weather, and
  crop and mandi ids. The frozen-price flags are never inputs (hand-off H-B8).
- **Range:** separate q10 and q90 quantile models.

### How the settings were chosen (no validation data used)

Rolling-origin cross-validation inside the train split (`ml/forecast/tune.py`): for each year 2021–2024, fit on
earlier target weeks and score that year. 36 settings (objective × depth × rounds × with/without frozen rows),
1,053 scored rows.

| Setting | CV MAPE % | Persistence CV MAPE % |
|---|---|---|
| absolute error, depth 3, 100 rounds, all rows (**chosen**) | 6.14 | 6.05 |
| absolute error, depth 4, 100 rounds, all rows | 6.15 | 6.05 |
| absolute error, depth 4, 100 rounds, without frozen rows | 6.15 | 6.05 |
| pseudo-Huber, depth 4, 300 rounds, without frozen rows (worst shown) | 6.29 | 6.05 |

No setting beat persistence in cross-validation. Damping the predicted change toward zero (factor 0 to 1) gained
at most 0.01 points (6.04%) and not consistently across years, so it was not used.

### Validation result (`ml/eval/report.md`, scored by Owner A's gate)

| | MAPE % | MASE | Direction (moves > 3%) | Range coverage (target 80%) | Range width % |
|---|---|---|---|---|---|
| Persistence | 5.60 | 1.00 | 0% | n/a | n/a |
| **Persistence band (deployed)** | 5.60 | 1.00 | 0% | **81%** | 15.8 |
| XGBoost, all rows | 5.64 | 1.01 | 60% | 72% | 13.6 |
| XGBoost, without frozen rows | 5.68 | 1.03 | 59% | 75% | 15.8 |

Excluding the 108 of 328 validation rows that touch a frozen AMIS price: persistence 6.66%, XGBoost 6.63%
(all rows) and 6.64% (without frozen rows). The model wins there by 0.03 points, which is too small to claim.

By crop option (MAPE %, all rows):

| Crop | Validation rows | Persistence | XGBoost |
|---|---|---|---|
| Wheat | 101 | 6.23 | **6.18** |
| Cotton | 72 | 5.39 | 5.42 |
| IRRI | 96 | 6.32 | 6.40 |
| Super Basmati | 59 | 3.60 | 3.74 |

Super Basmati is judged on validation only: it has just 10 test rows (Bahawalpur) and its latest prices are
months old (hand-off H-B9).

### Limits

- A backtest on historical AMIS prices, not a field trial.
- AMIS prices are sticky: about a third of validation rows touch a stretch where the reported price did not
  change. Persistence is very hard to beat on such data.
- The range is the only uncertainty shown. The q10–q90 band covers the real price 81% of the time on
  validation; it is not adjusted per mandi.
- The 2026 test was scored once, with the deployed model (`artifacts/models/price_point.json`, trained on
  the train years only). Nothing was changed after seeing it.

### Reproduce

```bash
.venv/Scripts/python -m pip install -r ml/forecast/requirements.txt
.venv/Scripts/python -m ml.forecast.tune
.venv/Scripts/python -m ml.forecast.train --quantiles --predictions preds.csv
.venv/Scripts/python -m ml.eval.gate --predictions preds.csv --model xgb
.venv/Scripts/python -m ml.forecast.train --record-fallback
.venv/Scripts/python -m ml.forecast.train --save   # the wheat direction model
```

### Direction: where the model does have skill

Direction is scored on validation rows where the real price moved more than 3% in 4 weeks. "Right" means the
sign of the model's predicted change matched the real move. The p-value is one-sided, against a coin flip.

| Crop | Moves > 3% | Direction right | p-value |
|---|---|---|---|
| **Wheat** | 50 | **72%** | **0.001** |
| IRRI | 51 | 61% | 0.08 |
| Cotton | 39 | 49% | 0.63 |
| Super Basmati | 13 | 46% | 0.71 |
| All crops | 153 | 60% | 0.008 |

### Test result (2026, scored once; `ml/eval/report_test.json`)

Scored on 10 October 2026 with `python -m ml.eval.gate --split test --final`, using the deployed direction model
as it is (trained on the train years only; not retrained on validation). The gate allows this run only once.

| | MAPE % | MASE | Direction (moves > 3%) | Range coverage (target 80%) | Range width % |
|---|---|---|---|---|---|
| Persistence | 3.44 | 1.00 | 0% | n/a | n/a |
| **Persistence band (deployed)** | 3.44 | 1.00 | 0% | **86%** | 15.6 |
| Seasonal naive | 8.26 | 1.98 | 28% | n/a | n/a |
| XGBoost | 3.46 | 1.00 | 63% | n/a | n/a |

Excluding the 56 of 165 test rows that touch a frozen AMIS price: persistence 4.31%, XGBoost 4.31%. Verdict: the
model does not beat persistence on price (FAIL), which agrees with validation and with the deployed choice.

By crop option (MAPE %): Wheat 3.20 vs XGBoost 3.23 (59 rows), Cotton 9.80 vs 9.87 (24), IRRI 1.72 vs 1.74 (72),
Super Basmati 1.90 vs 1.85 (10 rows, too few to judge).

Direction on 2026 moves > 3% (same definition as for validation):

| Crop | Moves > 3% | Direction right | p-value |
|---|---|---|---|
| **Wheat** | 21 | **81%** (17) | **0.004** |
| IRRI | 11 | 64% (7) | 0.27 |
| Cotton | 19 | 47% (9) | 0.68 |
| Super Basmati | 3 | 33% (1) | 0.88 |
| All crops | 54 | 63% (34) | 0.04 |

The wheat-only direction call is confirmed on data the model never saw. IRRI (64%, p = 0.27) is still not enough
evidence to add it.

### Proposal for the team (B4 → B5/B6), agreed and built

1. **Price and range: the baseline, for every crop.** It is the more accurate forecast, and its range is well
   calibrated (81% coverage).
2. **Direction: the model's call, for wheat only.** Shown as "likely to rise" / "likely to fall", with no price
   number. Other crops show "no reliable direction". IRRI joins only if the final test run supports it.
3. **SELL / WAIT stays on the baseline price,** so it stays SELL. The model's price numbers failed the gate,
   so they do not drive the decision.
4. **"Why?" uses SHAP on the wheat direction call.** Other crops show recent momentum and the seasonal
   pattern instead.

Caveats to say openly:

- Wheat was picked **after** seeing validation results, a mild form of selection. The one-time 2026 test run
  then confirmed it: 81% on 21 wheat moves (see "Test result").
- Interface I2 gains a `direction` field (additive; nothing existing changes), and the blueprint needs a line
  for it. Owner C needs it for the API and the Home and Why screens.

Until the team agrees, B5 and B6 are built so that turning the direction call off is a one-line config change.

### Built (B5, B6)

- `ml/forecast/predict.py` serves the baseline price and range for every crop option, and for wheat the model's
  direction call with its SHAP reasons (`ml/explain/`). `DIRECTION_CROP_OPTIONS = ("Wheat",)` in that file is
  the switch; an empty tuple turns the direction call off.
- The model file is `artifacts/models/price_point.json`, with its settings and per-crop direction accuracy in
  `price_meta.json` (`python -m ml.forecast.train --save`).
- On the two backup demo weeks (docs/DATA_NOTES.md A7, both validation weeks) the wheat call is right: 24 March
  2025 **DOWN** (the price then fell 19.7%) and 4 August 2025 **UP** (it rose 48.6%). Two weeks are anecdotes,
  not evidence; the evidence is the 72% over 50 moves in 2025 and 81% over 21 moves in 2026.

## Decision backtest: does waiting to sell actually pay? (H5, `ml/backtest/hold.py`)

The pivot asks not "will the price rise?" but "can you afford to wait, and with whose money?" This backtest answers
it from the real record. For every past year it compares **selling wheat in May** (the post-harvest low) with
**waiting to September–October**, net of two real costs of holding: the interest on the money the unsold crop ties up,
and 3.5% grain lost in storage (see `docs/FACTS.md`; 3.5% is an assumption inside a documented 2–7% godown band).
Real AMIS weekly prices, median of each month, pooled across the three mandis and both later months — 52 mandi-years.
"Always sell at harvest" is the baseline (net 0 by definition); a season is a **win** when waiting beat it.

| Whose money (rate) | 3.5% storage loss | 10% storage loss |
|---|---|---|
| Own cash (0%) | paid **38/52 (73%)**, median +Rs 60/maund, worst-10% −Rs 97 | 18/52 (35%), median −Rs 41, worst-10% −Rs 323 |
| Bank / warehouse receipt (16.5%) | 20/52 (38%), median −Rs 22, worst-10% −Rs 287 | 10/52 (19%), median −Rs 123, worst-10% −Rs 507 |
| Arhti money (66%) | 6/52 (12%), median −Rs 292, worst-10% −Rs 870 | 3/52 (6%), median −Rs 374, worst-10% −Rs 1,082 |

**The liquidity tax, in one line:** waiting usually pays *only if the farmer can afford to wait on their own cash*
(73% of years). The moment they must borrow to hold, the odds flip — bank money wins 38% of the time, arhti money
just 12%, and the median outcome turns negative. That is exactly why the app asks *whose money* before it says hold,
and why "always sell at harvest" is a reasonable default for a farmer who needs cash now. The worst-10% column is the
bad year a farmer must be able to survive: holding on arhti money can lose Rs 870–1,082 a maund.

These are historical medians, not a promise about next season, and a single later month is used (so the figures
differ slightly from a window). Reproduce: `hold_history("Wheat", mandi, 5, wait_months, annual_rate, loss_pct)`.

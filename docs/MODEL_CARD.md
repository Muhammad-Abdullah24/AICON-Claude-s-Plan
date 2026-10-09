# Model card: FarmSight's AI

> **For judges: one page.** Owner B (Usman). Every number below comes from `ml/eval/report.md` (the evaluation
> gate) or the technical details further down. The 2026 test set has not been scored yet: it is scored once, at
> the end, and added here whatever it shows.

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
  test = 2026 (165, held back). No synthetic rows anywhere in training or scoring.

## Model

- **XGBoost** predicting the **4-week % price change** (prices tripled since 2015, so % change, not price level).
- **Inputs (26):** recent momentum and price swings, price vs its 8-week average, season (month, sowing and harvest
  flags), weather (heat, rain), and crop and mandi. No absolute price levels.
- **Settings chosen without touching validation:** 36 settings compared by rolling cross-validation on 2021–2024.

## The honest result (validation, 2025)

| | Price error (MAPE) | Direction right on moves > 3% | Range holds the real price |
|---|---|---|---|
| "Price stays the same" baseline | **5.60%** | 0% (never predicts a move) | **81%** (target 80%) |
| Our XGBoost model | 5.64% | **60%** overall, **72% for wheat** | 72% |

**The model did not beat the naive baseline on price**, so by our own rule (NFR-01) the price forecast shown is the
baseline, labelled "baseline". Mandi prices are sticky, and a third of validation weeks touch a frozen AMIS price.
But the model **does** call the direction of real moves: 72% for wheat (50 moves, p = 0.001). Cotton (49%) and
Super Basmati (46%) show no skill.

## What we ship, and why

- **Price and range:** the baseline for every crop. It is the more accurate forecast and its range is well calibrated.
- **Direction:** the model's "likely up / likely down" for **wheat only**, where it has proven skill. Other crops say
  "no reliable direction". (Built and switchable; the team confirms it at a check-in. Wheat was chosen after seeing
  validation results, so the 2026 test run confirms or rejects it.)
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
- The 2026 test set is still unscored.

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
  (328 rows), test 2026 (165 rows, not used yet; scored once at the very end).
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
- The test split (2026) has not been scored. It is scored once, at the end, with whatever is deployed.

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

### Proposal for the team (B4 → B5/B6), needs agreement at a check-in

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
  confirms or rejects it, and the result goes in this card either way.
- Interface I2 gains a `direction` field (additive; nothing existing changes), and the blueprint needs a line
  for it. Owner C needs it for the API and the Home and Why screens.

Until the team agrees, B5 and B6 are built so that turning the direction call off is a one-line config change.

### Built (B5, B6), pending the team's agreement

- `ml/forecast/predict.py` serves the baseline price and range for every crop option, and for wheat the model's
  direction call with its SHAP reasons (`ml/explain/`). `DIRECTION_CROP_OPTIONS = ("Wheat",)` in that file is
  the switch; an empty tuple turns the direction call off.
- The model file is `artifacts/models/price_point.json`, with its settings and per-crop direction accuracy in
  `price_meta.json` (`python -m ml.forecast.train --save`).
- On the two backup demo weeks (docs/DATA_NOTES.md A7, both validation weeks) the wheat call is right: 24 March
  2025 **DOWN** (the price then fell 19.7%) and 4 August 2025 **UP** (it rose 48.6%). Two weeks are anecdotes,
  not evidence; the evidence is the 72% over 50 moves above.

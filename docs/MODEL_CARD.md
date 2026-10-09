# Model card: FarmSight 4-week price forecast

> Owner B (Usman). Written for task B4 on 10 October 2026. B10 turns this into the one-page version for judges.

## Decision

**Deployed: the persistence-band baseline, labelled "baseline".** The XGBoost model did not beat persistence
on pooled validation MAPE, so under NFR-01 it is not deployed. The forecast is today's AMIS price; the range
is today's price moved by the 10th and 90th percentile of past 4-week changes for that crop option (train
years only). The record is `artifacts/models/deployed.json`.

The model is not useless: it calls the direction of moves bigger than 3% right **60%** of the time on
validation, where persistence by definition never predicts a move. Whether to show that as a separate
"direction" signal is a team decision (see Open questions).

## Data

- AMIS Punjab daily mandi prices 2015–2026, cleaned to weekly series by Owner A (`data/processed/features.csv`),
  Rs per 40 kg. 11 series: Wheat, Cotton and Super Basmati at Bahawalpur, Vehari and Rahim Yar Khan; IRRI at
  Bahawalpur and Vehari.
- Real rows only (`is_synthetic = 0`). Split by target week: train before 2025 (2,733 rows), validation 2025
  (328 rows), test 2026 (165 rows, not used yet; scored once at the very end).
- Weather from Open-Meteo, aggregated by `ml/features/` exactly as at runtime.

## Model

- XGBoost, native API, fixed seed, one thread (reproducible). Code: `ml/forecast/train.py`.
- **Target:** the 4-week % price change, not the price. Prices roughly tripled over 2015–2026, so a model on
  price levels would extrapolate. Price forecast = today's price × (1 + predicted change / 100).
- **Inputs:** `FEATURE_COLUMNS` from `ml/features/` minus absolute price levels (price, lags, moving averages):
  momentum, volatility, price vs its 8-week average, calendar (month, sowing and harvest flags), weather, and
  crop and mandi ids. The frozen-price flags are never inputs (hand-off H-B8).
- **Range:** separate q10 and q90 quantile models.

## How the settings were chosen (no validation data used)

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

## Validation result (`ml/eval/report.md`, scored by Owner A's gate)

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

## Limits

- A backtest on historical AMIS prices, not a field trial.
- AMIS prices are sticky: about a third of validation rows touch a stretch where the reported price did not
  change. Persistence is very hard to beat on such data.
- The range is the only uncertainty shown. The q10–q90 band covers the real price 81% of the time on
  validation; it is not adjusted per mandi.
- The test split (2026) has not been scored. It is scored once, at the end, with whatever is deployed.

## Reproduce

```bash
.venv/Scripts/python -m pip install -r ml/forecast/requirements.txt
.venv/Scripts/python -m ml.forecast.tune
.venv/Scripts/python -m ml.forecast.train --quantiles --predictions preds.csv
.venv/Scripts/python -m ml.eval.gate --predictions preds.csv --model xgb
.venv/Scripts/python -m ml.forecast.train --record-fallback
```

## Open questions for the team

1. **Direction signal.** Show the model's 60% direction call next to the baseline forecast (as "likely up /
   likely down", not a price)? It would give "Why?" (B5) a real model to explain. If not, "Why?" can only
   show the seasonal pattern and recent momentum, not SHAP.
2. **WAIT almost never fires.** With a persistence forecast, the predicted change is 0%, so `advise()` always
   says SELL. That is honest, but the demo should say so.

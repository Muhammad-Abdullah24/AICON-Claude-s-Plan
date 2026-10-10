# Data pack for the loan planner (10 Oct 2026)

Research by Abd and Claude while Hamza works on L2a. This is a **staging area**: it doesn't touch `data/` (Hamza's).
Hamza copies what he wants into `data/processed/` under cards D1, D2 and D4, and the sources go into `FACTS.md`.
Machine-readable copies: [`input_costs_wheat.json`](input_costs_wheat.json) and [`loan_options.json`](loan_options.json).

## 1. Wheat cash input cost per acre (card D1)

**Source:** Agriculture Policy Institute (API), *Wheat Policy Analysis for 2023-24 Crop*, Table-13, Punjab, Rs/acre
(https://api.gov.pk/SiteImage/Policy/Wheat%20Policy%20Analysis%20For%202023-24%20Crop.pdf, page 15). It's the latest
official table. The Punjab item-level annex is a scanned image; the Sindh annex (Annex-X) gives the unit basis used for
fertiliser below.

**Method, 2023-24 to 2026:**
- **Non-fertiliser items** × **1.119** (CPI FY25 1.045 × FY26 1.071, the factors already in `economics_inputs.json`).
- **Fertiliser** re-priced on the table's own basket (1 bag DAP + 2 bags urea + 0.1 bag NP + transport and application
  per acre, from Annex-X):
  - 2023-24 basket: 11,766 + 2 × 3,800 + 937 + 800 = **Rs 21,103**.
  - 2026 basket, at **DAP Rs 15,000** ("above 15,000 in May 2026") and **urea Rs 4,749** (FFC retail price, June 2026),
    both from `economics_inputs.json`: 15,000 + 2 × 4,749 + 937 × 1.119 + 800 × 1.119 = **Rs 26,442**.
  - Ratio **1.253**, applied to Punjab's Rs 21,689.

| Item (Punjab) | 2023-24 official | 2026 estimate | When it's paid |
|---|---|---|---|
| Land preparation | 10,000 | **11,190** | sowing (Oct–Nov) |
| Seed and sowing | 10,100 | **11,302** | sowing |
| Plant protection and interculture | 2,500 | **2,798** | Dec–Feb |
| Irrigation and watercourse cleaning | 9,650 | **10,799** | through the season |
| Fertiliser, FYM, transport and application | 21,689 | **27,176** | sowing + 1st/2nd irrigation |
| **Sowing-season cash inputs** | **53,939** | **≈ 63,265** | what the loan must cover |
| Harvesting and threshing | 18,525 | **20,730** | at harvest (April), often paid partly in grain |
| *Land rent (excluded: owners)* | *35,000* | *39,165* | *add it for tenants: many small farmers rent* |
| *Other (mark-up, management, land tax)* | *7,345* | *excluded* | *mark-up is the loan itself* |

**What this means:**
- Cash inputs are **about Rs 63,000 an acre**, roughly **twice** the Rs 32–38k some guides quote.
- On 5 acres that's **about Rs 3.16 lakh**. The Kissan Card (Rs 1.5 lakh) covers **about 47%**.
- The harvest cost (about **Rs 1.04 lakh** on 5 acres) falls due in April too, which adds to the pressure to sell at harvest.

**Caveats:** this is an estimate built from an official table. Label it "estimate" in the app (`COST_ESTIMATE`).
Diesel-driven items (land preparation, irrigation) may have risen faster than CPI.

## 2. Loan options (card D2)

| id | Rate to farmer | Limit | Who | Verified on an official page? |
|---|---|---|---|---|
| `kissan_card` | 0% | Rs 30,000/acre, up to **Rs 1.5 lakh a season**; card valid 6 months, then 1 month grace; inputs (seed, fertiliser) through authorised vendors | Punjab, land 1–12.5 acres | ✅ punjab.gov.pk/node/5690, read 10 Oct |
| `pm_youth_t1` | 0% (the government pays the bank KIBOR + 9%) | up to **Rs 5 lakh**; up to 3 years, equal monthly instalments; agriculture production loans eligible | age 21–45, not a defaulter | ✅ SBP scheme page sbp.org.pk/incen-others/PMYBALS.asp (Circular 12 of 2022). Bank pages differ: confirm at the bank. Tier 3 (7%, collateral) is what ZTBL's page shows. |
| `akhuwat` | 0% | **small**: Rs 15,000–50,000 a season in Akhuwat's own case studies; group-based (3–6 farmers), community-organisation membership needed; ran under Punjab's interest-free Agriculture e-Credit Scheme | small farmers, tenants | ⚠️ partly: akhuwat.org.pk case studies only, no published limit |
| `zarkhez_e` | KIBOR + 8%, floor **18%** (ZTBL) | Rs 1 lakh/acre, up to Rs 10 lakh (tenants Rs 5 lakh); cash withdrawal capped at 25% (owners) / 15% (tenants) | up to 12.5 acres in Punjab | ⚠️ ZTBL / Bank AL Habib pages; the SBP term sheet blocked our download (403) |
| `bank` | 16.5% | none | anyone | derived: policy rate 11.5% + 5% (API's KIBOR + 5% costing) |
| `arhti` | ~66% | none | anyone | derived: 4× the formal rate (SBP 2014 bulletin, PIDE: "4–5×") |

**Pitch caveat:** PM Youth Tier 1 needs a monthly instalment, which a crop farmer can struggle with before harvest. Say
so in `conditions_ur/en`.

## 3. Why over-borrowing happens (for the pitch and the planner's warning)

- **Shikarpur, Sindh:** smallholders put **51.5%** of credit into farming (medium and large farmers: 56.5%).
  https://link.springer.com/article/10.1186/s40854-018-0109-x
- **Punjab, 208 smallholders:** a significant share diverted to lean-season household costs, illness, weddings, and
  repaying informal loans.
  https://www.researchgate.net/publication/281078636_Fungibility_of_Smallholder_Agricultural_Credit_Empirical_Evidence_from_Pakistan

## 4. More mandis (card D4, optional)

AMIS lists both districts. City ids are from `ViewPrices.aspx?searchType=0&commodityId=1`, read 10 Oct; history is in
the `reports/CommodityChart.aspx?cmd=<commodity>&city=<id>` ReportViewer with a date range.

| Mandi | AMIS city id | Wheat today (Rs/100 kg) | Rs/40 kg | Note |
|---|---|---|---|---|
| **Lodhran** | **28** | 10,700–11,500, average 11,100 | **4,440** | **Rs 620/maund above Bahawalpur (3,820)**, about 90 km away. That's a strong "where to sell" story if added. |
| Chishtian (Bahawalnagar district) | listed next to Lodhran | (check) | | Bahawalnagar itself didn't report wheat today |
| Bahawalpur (for checking) | 20 | 9,500–9,600, average 9,550 | 3,820 | matches our data ✅ |

District wheat area 2024-25 (Crop Reporting Service): Bahawalnagar 1.08M acres, Bahawalpur 0.75M, Lodhran 0.37M.
https://crs-agripunjab.punjab.gov.pk/system/files/Bahawalnagar.pdf (and Bahawalpur.pdf, Lodhran.pdf).

## 5. Livestock income (reference only, for the "other income" box)

- No Punjab farm-gate milk price found. Sindh official ex-farm rate: **Rs 215/litre** (Oct 2026, ARY, quoting dairy
  farmers).
- Yield: **7.9 L/day** per buffalo and **6.1 L/day** per cow (PBS Livestock Census 2006, national averages).
- Gross, one buffalo: about Rs 1,700/day, before feed. **Don't put a net figure in the app.** Let the farmer type his
  own monthly income.

## 6. Model experiment: does "harvest price below support price" predict that holding pays?

Tested on `hold_history` (wheat, sell in May vs 5 months later, 3 mandis, 26 seasons). Only **7 seasons have a support
price** (none in 2024–2025), so there is **no usable signal**: 1 of 1 below support, 6 of 6 at or above. **Conclusion:**
with 26 seasons, a learned hold model would overfit. Keep the transparent backtest. More data (D4 mandis, more years)
helps more than a model.

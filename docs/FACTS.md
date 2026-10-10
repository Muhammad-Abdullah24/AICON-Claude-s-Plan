# Fact sheet

> Every number on a slide or in the UI that does not come from our data or artifacts must be listed here with a source (PLAN.md sections 18 and 20). Open each source and confirm the number before it is used. Seeded from PLAN.md section 19 on 9 Oct 2026; **add new facts here, not in PLAN.md.**

## Still to source

- 2022 floods: dates, affected districts, and cotton and rice impact in south Punjab (replay case `cotton_2022_floods`).
- Exact date the government halted wheat procurement in spring 2024 (replay case `wheat_2024_crash`).
- AMIS terms of use.


Open each source and confirm the number before it goes on a slide.

| Fact | Source |
|---|---|
| A National Assembly committee in February 2026 linked the potato glut to inadequate production forecasting and poor market intelligence | https://www.brecorder.com/news/40408622 |
| Potato prices fell from Rs 2,500 to Rs 200 per 62 kg bag. Punjab production rose from 9 to 12 million tonnes. | https://dailytimes.com.pk/1437716/vegetable-glut-hits-farmers-as-pakistan-lacks-processing-storage/ |
| The potato market crashed in late November 2025 as a glut met the Afghan border closure. Afghanistan had taken over 40% of Pakistan's potato exports. | https://dailytimes.com.pk/1410578/pakistan-potato-market-crashes-amid-afghan-border-closure/ |
| Tomato prices rose over 400% to about Rs 600 per kg after border crossings closed in October 2025 | https://www.dawn.com/news/1950907/pak-afghan-border-closures-push-up-prices-of-essentials |
| Wheat fell as low as Rs 2,200 per 40 kg from a peak near Rs 5,500 after procurement was halted | https://ukragroconsult.com/en/news/imf-backs-pakistans-wheat-buy-lets-govt-set-stock-target/ |
| The Wheat Policy 2025-26 set Rs 3,500 per 40 kg, described by an official as indicative and not a fixed support price | https://profit.pakistantoday.com.pk/?p=215651 |
| In a tied loan the farmer pre-sells the harvest at a discount. One worked cotton example equals about 46% annual interest. | https://criterion-quarterly.com/the-anatomy-of-agricultural-credit-in-pakistan/ |
| Commission agents charge a higher commission to farmers who borrowed from them | https://www.theigc.org/sites/default/files/2014/09/Haq-Et-Al-2013-Working-Paper.pdf |
| A randomised trial of SMS price information in India found no significant average effect on prices farmers received | https://ideas.repec.org/a/oup/wbecrv/v26y2012i3p383-414.html |
| Warehouse receipt financing in Pakistan lets farmers use stored crops as collateral. The exchange's takeover of the collateral manager was approved in November 2025. | https://www.secp.gov.pk/wp-content/uploads/2025/11/Press-Release-SECP-Greenlights-PMEXs-Strategic-Acquisition-of-NCMCL-Strengthening-Pakistans-Agricultural-Market-Infrastructure.pdf |
| The warehouse receipt scheme was launched primarily for paddy, rice and maize | https://profit.pakistantoday.com.pk/?p=111804 |
| Foundation models took the top five places among 17 methods for agricultural price forecasting. Naive ranked 6th. | https://arxiv.org/abs/2601.06371 |
| Chronos-2: pretrained, zero-shot, quantile forecasts, supports extra input variables | https://arxiv.org/abs/2510.15821 |
| India's MIEWS forecasts tomato, onion and potato prices three months ahead and raises glut alerts | https://www.business-standard.com/article/pti-stories/govt-portal-to-alert-about-price-crash-in-staple-vegetables-120022601029_1.html |
| The ALPS method and its tiers | https://documents.wfp.org/stellent/groups/public/documents/manual_guide_proced/wfp264186.pdf |
| Arya.ag: storage, loans against stored grain, and market links at scale | https://finance.yahoo.com/news/even-global-crop-prices-fall-070000157.html |
| Some Ergos farmers achieve prices 25 to 30% above the harvest price | https://rabobank.nl/en/about-us/rabofoundation/project/011098564/financial-inclusion-is-in-store-for-indian-smallholders |
| AMIS publishes prices from 135 Punjab markets | https://pitb.gov.pk/node/2960 |
| WFP food prices for Pakistan | https://data.humdata.org/dataset/wfp-food-prices-for-pakistan |
| Twilio WhatsApp sandbox rules | https://www.twilio.com/docs/whatsapp/sandbox |

## Numbers from v1 that we stop using

| v1 claim | Problem | What to do |
|---|---|---|
| "Farmers lose 15 to 30% of income" | No source | Replace with the sourced crisis figures above |
| Wheat support price of Rs 3,900 in 2024 and 2025, Rs 4,000 in 2026 | Does not match the record: the 2025-26 figure is Rs 3,500, and no support price was announced the year before | Use the sourced figures |
| Middleman cut of 15 to 35% by crop | No source | Remove. Let the farmer enter their own costs. |
| Production cost per crop | No source | Remove, or find a government source |
| "Wheat is the most stable crop" as the lead demo | Wheat had a major crash in this period | Lead with the crisis replay |
| R² of 0.92 | Measured on synthetic data | Replace with MASE on real data |
| "FarmSight raises farmer income" / "saves Rs X" | No field evidence; the Indian SMS price trial above found no average effect | Do not claim it. Replays show the reference available that day, not money saved |
| "This offer is unfair" / "exploitation" | An AMIS reference cannot see grade, buyer terms or credit ties | Say "below / within / above the recent reported reference", or "reference data is limited" |
| AMIS price as a "fair", "true" or "guaranteed" price | It is a reported mandi price, sometimes old, frozen or repeated | Call it the reference mandi price, with its date and strength |

---


## Pivot: rates the "can you afford to wait?" engine uses (H4, checked 10 Oct 2026)

These feed `ml/decision/config.py` (Abd) and the hold backtest (`ml/backtest/hold.py`). I checked each against a
source. **Differences posted to the team are marked ⚠.**

| Rate | Value used | Source checked | Status |
|---|---|---|---|
| Storage loss, proper godown | 3.5% over ~5 months | FAO, *Public sector storage of wheat in Pakistan* (http://www.fao.org/4/X5048E/x5048E13.htm); Dawn post-harvest pieces | ⚠ **Not confirmed exactly.** The FAO page gives no month-by-month rate. Documented Pakistani wheat storage losses run ~2% (metal bins) to 6.6% (jute bags, irrigated) in 1980s surveys, and 15–18% from poor handling generally (https://www.dawn.com/news/199707, https://www.dawn.com/news/966953). 3.5% is a reasonable low-to-mid godown figure but should be treated as an **assumption within a 2–7% band**, not a sourced constant. |
| Storage loss, bags at home | 10% | As above (jute bags are the lossy end; FAO/GAIN) | ⚠ Plausible (bags are worse than godowns) but not a single sourced figure; an assumption. |
| Bank / warehouse-receipt loan | 16.5% per year | `data/processed/economics_inputs.json` (`holding_interest_rate_pct_per_year`): SBP policy rate + ~5% spread | OK, matches our economics inputs. Re-check the policy-rate component near the demo. |
| Arhti (commission-agent) money | 66% per year (≈ 4× the formal rate) | Arhti charges "four to five times the rate of interest than the formal institutions" (https://www.dawn.com/news/1708457); PIDE, *The Role of Arthi…* (https://pide.org.pk/research/the-role-of-arthi-in-agriculture-marketing-an-exploiter-or-facilitator-of-farmers/) | OK as a mid-high estimate. 4–5× of 16.5% = 66–82%. A worked cotton example gives ~46% (https://criterion-quarterly.com/the-anatomy-of-agricultural-credit-in-pakistan/), so the real cost spans ~46–82%; 66% sits inside it. The arhti also takes a 2–4% sale commission on top (PIDE). |
| Kissan Card (Punjab) | Rs 30,000/acre, up to Rs 150,000/season, 1–12.5 acres, 6 months + 1 month grace, **inputs only** | CM Kissan Card, punjab.gov.pk/node/5690; Bank of Punjab (bop.com.pk/CMPunjabKissanCard); Dawn (https://www.dawn.com/news/1881918) | **Confirmed.** Up to Rs 1.5 lakh per season, Rs 30,000/acre, 1–12.5 acres, card valid 6 months + 1 month grace, interest-free, spent on fertiliser/seed/diesel through registered vendors. |

**For the team (post in chat):** the storage-loss figures (3.5% godown, 10% bags) are the one place we are using an
assumption dressed as a constant. Documented Pakistani wheat storage losses are a wide 2–18% depending on store type
and handling. Suggest we either (a) label storage loss "estimate" in the UI and the backtest, or (b) show the hold
result at two loss levels (3.5% and 10%), which the backtest already supports.

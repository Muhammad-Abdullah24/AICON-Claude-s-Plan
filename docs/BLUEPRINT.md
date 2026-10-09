# 🧠 FarmSight — Application Design & Analysis Blueprint

---

## 1. 📌 Project Overview

| Field | Description |
|-------|-------------|
| **App Name** | FarmSight |
| **Version** | 0.2.0 (Hackathon MVP, revised against the scraped AMIS data) |
| **Date** | 2026-10-09 |
| **Author(s)** | FarmSight team, AICON'26 Hackathon (SEECS, NUST) |
| **Platform** | Web (React, mobile-first) + WhatsApp + SMS, backed by a FastAPI service |
| **Status** | Design |

### Vision Statement
> Pakistani farmers lose income because they make three costly decisions without market information: what to grow, when to sell, and where to sell. Middlemen and traders have price data and seasonal knowledge that farmers lack. Crop choice is fixed months before harvest, so a wrong call there can't be fixed later. *(The often-quoted "15–30% income loss" has no source in our data; cite a source before using it in the pitch, or leave it out.)*
>
> FarmSight is an AI crop economics advisor for three major crops (Wheat, Rice and Cotton, with Rice in two varieties: Super Basmati and IRRI) in South Punjab, covering the Vehari, Bahawalpur and Rahim Yar Khan mandis. It is built on real daily AMIS mandi prices from 2015 to October 2026. It supports the whole crop cycle:
> - **What to grow:** ranks the four crop options by expected profit per acre (harvest-price estimate × yield − production cost), with the price risk shown.
> - **When to sell in the season:** shows the seasonal price pattern and the best selling window within the normal harvest period, so the farmer avoids the harvest glut.
> - **When and where to sell now:** forecasts prices 4 weeks ahead using pre-trained models and live weather, and gives a SELL (بیچ دیں) or WAIT (رکیں) signal in Urdu, with the rupee gain after the interest cost of waiting, plus which mandi pays best after transport.
>
> Every recommendation comes with a SHAP explanation of why the model expects prices to move, so farmers can trust the advice and not just follow it.

### Goals & Success Criteria
- [ ] **SC-01:** Accurate and faithful insights for farmers, with price forecasts that beat the naive "price stays the same" baseline on real held-out data, and a SHAP explanation for every recommendation.
- [ ] **SC-02:** Urdu native and user friendly, so a farmer can get an answer in under a minute on a phone.
- [ ] **SC-03:** Seamless WhatsApp and SMS integration, including voice-note questions.
- [ ] **SC-04:** Full crop-cycle coverage, answering what to grow, when in the season to sell, and when and where to sell now.
- [ ] **SC-05:** Actionable, quantified advice, shown as rupee impact on the farmer's actual harvest (e.g. 100 maund) after the interest cost of waiting, transport, and the farmer's own arhti commission if entered.
- [ ] **SC-06:** Honest uncertainty, with confidence ranges, a per-crop "prices as of" date, and clear flags.
- [ ] **SC-07:** Built on real data: daily AMIS mandi prices 2015–2026, cleaned offline into the training set, official cost-of-production tables, and live weather from Open-Meteo at request time.

### Out of Scope (What this app will NOT do)
- **NS-01:** Not an AI wrapper. Forecasts come from our own trained XGBoost models; the LLM only handles chat and language.
- **NS-02:** Not a trading or brokerage platform. It advises on when and where to sell but never buys, sells or moves money.
- **NS-03:** Not a guaranteed price oracle. Forecasts are probabilistic estimates, not promises.
- **NS-04:** Not agronomy advice. No seeds, fertilizer, pesticides, irrigation, disease diagnosis or sowing dates. Sowing follows the normal agronomic calendar; FarmSight only advises on selling.
- **NS-05:** Not a marketplace or logistics service. It does not connect buyers and sellers or arrange transport; it only uses pre-computed transport costs for comparison.
- **NS-06:** Not a replacement for government price policy. Support prices are shown as a reference only.
- **NS-07:** Not a nationwide, all-crop system. Only Wheat, Rice (Super Basmati, IRRI) and Cotton, at Vehari, Bahawalpur and Rahim Yar Khan. IRRI is not offered at Rahim Yar Khan (no usable price data).
- **NS-08:** Not financial or insurance advice. No loans, credit scoring or crop insurance.
- **NS-09:** Not for sugarcane, maize, Basmati 385 or perishable crops (potato, onion, tomato). Basmati 385 is out because AMIS stopped reporting it in June 2024.
- **NS-10:** Not a live-market system. Prices, transport costs and models are pre-processed offline; only weather is fetched in real time.
- **NS-11:** No spoken replies. Voice is input only; every reply is text.

---

## 2. 👥 Stakeholders & Actors

| Actor | Type | Description |
|-------|------|-------------|
| `Farmer` | Human (primary) | Small to mid-size farmer in Vehari, Bahawalpur or Rahim Yar Khan growing Wheat, Rice or Cotton. Often low literacy, using a basic phone or an older smartphone, mostly in Urdu through WhatsApp, SMS or the web app. |
| `Guest` | Human | A farmer who has not registered yet. Can view forecasts, mandi comparison and history, but gets no personalised rupee impact or alerts. |
| `Dev Team` | Human (admin) | Prepares data offline, trains and validates models, and deploys them. Not a runtime user of the app. |
| `Data Providers` | External system | AMIS.pk supplies daily mandi prices (scraped and cleaned offline, 2015–2026). The Agriculture Policy Institute (API) cost-of-production tables supply costs and yields. News sources supply support prices and macro rates (see `data/processed/economics_inputs.json`). Open-Meteo supplies live and historical weather. |
| `WhatsApp API` | External system | Meta WhatsApp Cloud API (free test number; Twilio sandbox as backup). Delivers alerts and receives farmer text and voice questions. |
| `SMS Gateway` | External system | An Android phone running an open-source SMS gateway app, using the SIM's SMS bundle. Sends and receives SMS for basic phones. |
| `Gemini API` | External system | Google Gemini (free tier). Transcribes Urdu voice notes and turns forecast context into plain Urdu or Roman Urdu chat replies. |
| `Map Service` | External system | OpenStreetMap (Leaflet + Nominatim). Lets the farmer set a site location pin and looks up the district. |

---

## 3. 📖 Use Cases

### Use Case List

| ID | Name | Actor | Priority |
|----|------|-------|----------|
| UC-01 | View 4-week price forecast | Farmer / Guest | High |
| UC-02 | View price explanation ("Why?") | Farmer / Guest | High |
| UC-03 | Get SELL / WAIT recommendation | Farmer | High |
| UC-04 | Compare mandis by net price | Farmer / Guest | High |
| UC-05 | Rank crops to grow by profit | Farmer | High |
| UC-06 | Get best selling window in the season | Farmer | Medium |
| UC-07 | Check a buyer's offer against a fair price | Farmer | Medium |
| UC-08 | View margin breakdown | Farmer / Guest | Medium |
| UC-09 | Ask the AI chat (text or voice note) | Farmer | Medium |
| UC-10 | Receive alerts by WhatsApp or SMS | Farmer | Medium |
| UC-11 | Register a farmer profile | Guest | High |
| UC-12 | View price history and seasonal pattern | Farmer / Guest | Low |
| UC-13 | Fetch live weather for a forecast | System (Open-Meteo) | High |
| UC-14 | Prepare data and train models offline | Dev Team | High |

### Use Case Details

```
Use Case ID  : UC-01
Name         : View 4-week price forecast
Actor(s)     : Farmer / Guest
Precondition : Pre-trained models and pre-processed price data are loaded.
Trigger      : Farmer selects a crop (and variety) and a mandi.
Main Flow    :
  1. Farmer selects crop and mandi (defaults from profile if registered).
  2. System fetches live weather for the mandi (UC-13).
  3. System runs the price model and the quantile models.
  4. System shows current price, predicted price in 4 weeks, low–high range,
     trend (UP / DOWN / STABLE), volatility, and the "prices as of" date of
     that crop and mandi (labelled "AMIS mandi price, as of <date>").
Alternative Flow (A1 - weather API down):
  1. System uses the last cached weather reading and marks it as cached.
Alternative Flow (A2 - no data for crop/mandi pair, e.g. IRRI at Rahim Yar Khan):
  1. System shows "No data for this mandi yet" and suggests another mandi.
Alternative Flow (A3 - latest price is old, e.g. Super Basmati):
  1. If the latest price is more than 8 weeks old, the system shows the date in
     amber and sets confidence to LOW.
Postcondition: A forecast record is stored and displayed.
```

```
Use Case ID  : UC-02
Name         : View price explanation ("Why?")
Actor(s)     : Farmer / Guest
Precondition : A forecast exists (UC-01).
Trigger      : Farmer taps "Why?".
Main Flow    :
  1. System computes SHAP values for the forecast.
  2. System converts the top 3–5 features into plain Urdu sentences with
     rupee effects and up/down arrows.
  3. System shows the list; a "details" toggle reveals the SHAP chart.
Alternative Flow (A1 - SHAP fails):
  1. System shows the global top factors for that crop instead.
Postcondition: The farmer sees why the price is expected to move.
```

```
Use Case ID  : UC-03
Name         : Get SELL / WAIT recommendation
Actor(s)     : Farmer
Precondition : Farmer has a profile with crop, mandi and harvest quantity.
Trigger      : Farmer opens Home or the Sell screen.
Main Flow    :
  1. System gets the forecast (UC-01).
  2. Advisory engine derives the signal: WAIT (رکیں) if the 4-week forecast is
     at least 5% above today's price, otherwise SELL (بیچ دیں). It also sets a
     confidence (high/medium/low) from the width of the 10th–90th percentile range.
  3. System calculates expected price and the rupee impact on the harvest:
     quantity × (forecast price − today's price) − interest cost of waiting
     (quantity × today's price × 1.375% per month, i.e. 16.5% per year).
     If the farmer entered an arhti commission %, it is applied to both prices.
  4. System shows the colour-coded signal in Urdu with the net rupee impact and
     a line "after Rs X interest for waiting 4 weeks".
  Note: in the real data a 5% rise in 4 weeks happens in only 14–19% of weeks
  (wheat 15.5%, rice 14.6%, cotton 27.3%), so SELL is the usual answer.
Alternative Flow (A1 - guest, no quantity):
  1. System asks for harvest quantity, or uses 100 maund as an example.
Postcondition: A recommendation record is stored for the farmer.
```

```
Use Case ID  : UC-04
Name         : Compare mandis by net price
Actor(s)     : Farmer / Guest
Precondition : Forecasts exist for the crop at two or more mandis.
Trigger      : Farmer taps "Compare Mandis".
Main Flow    :
  1. System gets current and forecast price at each mandi that has data for the
     crop (IRRI: Vehari and Bahawalpur only).
  2. System subtracts the pre-computed transport cost from the farmer's district
     (one of the three mandi districts for the MVP), labelled "estimate".
  3. System ranks mandis by net price and highlights the best one with the
     rupee gain over the farmer's preferred mandi.
Alternative Flow (A1 - no district known):
  1. System ranks by gross price and notes that transport is excluded.
Alternative Flow (A2 - crop missing at a mandi):
  1. System lists that mandi as "no price data" at the bottom.
Postcondition: The farmer knows where to sell.
```

```
Use Case ID  : UC-05
Name         : Rank crops to grow by profit
Actor(s)     : Farmer
Precondition : Farmer profile has district and land area.
Trigger      : Farmer taps "What to Grow".
Main Flow    :
  1. System computes a harvest-price estimate for Wheat, Cotton, Super
     Basmati and IRRI at the farmer's mandi: today's price × the historical
     ratio of harvest-month price to current-month price (median over the
     available years, 2015–2026). The range is the min–max of that ratio across
     years. Labelled "estimate". The 4-week model is not used here.
  2. System computes expected profit per acre = harvest-price estimate × yield
     per acre − production cost per acre, then scales to land area. Rice yields
     are in paddy and converted to milled rice with a 0.65 milling yield
     (assumption), because AMIS rice prices are milled-rice level.
  3. System shows four cards ranked by profit, each with a risk badge from the
     year-to-year spread of the ratio.
Postcondition: A crop plan record is stored.
```

```
Use Case ID  : UC-06
Name         : Get best selling window in the season
Actor(s)     : Farmer
Precondition : UC-05 shown; crop calendar data loaded.
Trigger      : Farmer taps a crop card.
Main Flow    :
  1. System reads the crop calendar (normal sowing and harvest months) and the
     seasonal price pattern, shown as percent of each year's average price.
  2. System picks the month window, from harvest to 3 months after, with the
     best median price, net of the interest cost of holding.
  3. System shows sowing (fixed, from the calendar), harvest and the best
     selling window on a month timeline.
Postcondition: The best selling window is added to the crop plan.
```

```
Use Case ID  : UC-07
Name         : Check a buyer's offer against a fair price
Actor(s)     : Farmer
Precondition : A forecast exists for the crop and mandi.
Trigger      : Farmer enters "Buyer offered Rs ___".
Main Flow    :
  1. System computes a fair selling range from the forecast range.
  2. System compares the offer and shows "Rs X below / above fair".
Alternative Flow (A1 - invalid amount):
  1. System asks for a valid number.
Postcondition: The farmer knows whether the offer is fair.
```

```
Use Case ID  : UC-08
Name         : View margin breakdown
Actor(s)     : Farmer / Guest
Precondition : Crop costs and support prices loaded.
Trigger      : Farmer opens the Margin view or checks an offer (UC-07).
Main Flow    :
  1. System splits the price into production cost, the farmer's own arhti
     commission (only if the farmer entered one) and farmer profit.
  2. For wheat only, system shows the government support price as a reference
     line. Rice and cotton have no support price. If the support price was
     announced but not procured (2023-24 crop, spring 2024 harvest), it is labelled "announced, not
     procured".
Postcondition: The farmer sees how much of the price they keep.
```

```
Use Case ID  : UC-09
Name         : Ask the AI chat (text or voice note)
Actor(s)     : Farmer, Gemini API (transcription and reply)
Precondition : Farmer is on the chat screen or messages the WhatsApp number.
Trigger      : Farmer sends a text or a voice note.
Main Flow    :
  1. (Voice) System transcribes the voice note and shows "Did you mean …?".
  2. Farmer confirms the transcript.
  3. System attaches the farmer's current forecast and recommendation as context.
  4. LLM replies in Urdu or Roman Urdu, using only the numbers provided.
  5. System sends the text reply.
Alternative Flow (A1 - transcription fails):
  1. System asks the farmer to type or record again.
Alternative Flow (A2 - LLM unavailable):
  1. System answers from a template using the forecast data.
Postcondition: The chat message and reply are stored.
```

```
Use Case ID  : UC-10
Name         : Receive alerts by WhatsApp or SMS
Actor(s)     : Farmer, Messaging APIs
Precondition : Farmer is registered and has alerts enabled.
Trigger      : The alert scheduler detects a signal change or unusual price.
Main Flow    :
  1. System builds a short Urdu text alert with quick replies.
  2. System sends it by WhatsApp.
  3. Farmer can reply "Why?", "Compare mandis", "Stop alerts", or a voice note.
Alternative Flow (A1 - WhatsApp fails or basic phone):
  1. System sends a 160-character SMS with a number menu.
Postcondition: Alert and message records are stored with delivery status.
```

```
Use Case ID  : UC-11
Name         : Register a farmer profile
Actor(s)     : Guest
Precondition : None.
Trigger      : Guest taps "Register" or messages the WhatsApp number for the first time.
Main Flow    :
  1. Guest picks a language.
  2. Guest enters phone number. On WhatsApp/SMS the sender's number is used
     directly. (OTP verification is post-MVP; the demo uses a pre-seeded profile.)
  3. Guest enters crops, preferred mandi, land area, site location (district
     or map pin on OpenStreetMap), harvest quantity, and optionally their arhti
     commission % (no default; left blank means none is applied).
  4. System saves the profile and opens Home.
Alternative Flow (A1 - phone number already registered):
  1. System loads the existing profile instead of creating a new one.
Postcondition: Guest becomes a registered Farmer.
```

```
Use Case ID  : UC-12
Name         : View price history and seasonal pattern
Actor(s)     : Farmer / Guest
Precondition : Pre-processed price history loaded.
Trigger      : Farmer opens "Price History".
Main Flow    :
  1. System shows a 52-week price chart with sowing and harvest seasons shaded.
  2. System shows a monthly seasonal pattern chart as percent of each year's
     average price (prices rose about 3x from 2015 to 2026, so raw rupees
     would hide the pattern).
Postcondition: None (read only).
```

```
Use Case ID  : UC-13
Name         : Fetch live weather for a forecast
Actor(s)     : System, Open-Meteo
Precondition : Mandi coordinates are known.
Trigger      : A forecast is requested (UC-01) and the cache is older than 1 hour.
Main Flow    :
  1. System calls Open-Meteo for the mandi's coordinates with past_days=92,
     so it gets the last 12 weeks of daily weather.
  2. System aggregates it exactly as the training pipeline does (weekly mean
     tmax, tmin and humidity; weekly rain and ET0 sums; hot days ≥ 40°C; 4-week
     and 12-week rain totals; 4-week mean tmax).
  3. System stores the aggregates and passes them to the model as features.
Alternative Flow (A1 - API down):
  1. System uses the last cached reading and flags it as cached.
Postcondition: A fresh or cached weather reading is available.
```

```
Use Case ID  : UC-14
Name         : Prepare data and train models offline
Actor(s)     : Dev Team
Precondition : Cleaned data in the repo under data/processed/ (done:
               AMIS prices 2015–2026, features.csv, weather,
               economics_inputs.json).
Trigger      : Before deployment, or when new data arrives.
Main Flow    :
  1. Team builds features (features.csv, real rows only).
  2. Team trains the 4-week price, quantile and volatility models with the
     date-based split already in features.csv (train: target before 2025,
     val: 2025, test: 2026). The harvest-price estimate is computed from
     seasonal ratios, not trained.
  3. Team checks the model beats the persistence baseline on real validation
     rows (NFR-01). The test set is used once, at the end.
  4. Team exports models, SHAP explainers and processed data to the app.
Alternative Flow (A1 - model fails accuracy check):
  1. Team does not deploy it and keeps the previous model.
Postcondition: New models and a new "prices as of" date are live.
```

### Use Case Diagram (text notation)

```
[Guest]      --> (Register Profile)
             --> (View Forecast) <<include>> (Fetch Live Weather)
             --> (View Why)
             --> (Compare Mandis)
             --> (View Price History)
             --> (View Margin)

[Farmer]     --> (all Guest use cases)
             --> (Get Sell Recommendation) <<include>> (View Forecast)
             --> (Check Buyer Offer)       <<include>> (View Margin)
             --> (Rank Crops to Grow)
             --> (Get Selling Window)      <<extend>>  (Rank Crops to Grow)
             --> (Ask AI Chat)             <<include>> (Transcribe Voice) [voice only]
             <-- (Receive Alerts)

[Dev Team]   --> (Prepare Data & Train Models)

[Open-Meteo]         <-- (Fetch Live Weather)
[WhatsApp Cloud API] <-- (Receive Alerts), (Ask AI Chat)
[SMS Gateway]        <-- (Receive Alerts), (Ask AI Chat)
[Gemini API]         <-- (Ask AI Chat), (Transcribe Voice)
[OpenStreetMap]      <-- (Register Profile)
```

---

## 4. 📋 Requirements

### Functional Requirements (FR)

| ID | Requirement | Priority | Use Case |
|----|-------------|----------|----------|
| FR-01 | 4-week price forecasts for Wheat, Cotton, Super Basmati and IRRI at the mandis that have data for them (IRRI not at Rahim Yar Khan), with confidence range, trend, volatility rating and per-series "prices as of" date | High | UC-01 |
| FR-02 | Real-time communication: alerts and advice by WhatsApp and SMS as soon as signals change | Medium | UC-10 |
| FR-03 | Sell advisory: SELL (بیچ دیں) or WAIT (رکیں) signal with expected price and net rupee impact on the farmer's harvest after the interest cost of waiting | High | UC-03 |
| FR-04 | Explainability: a SHAP-based plain-language reason for every forecast and recommendation | High | UC-02 |
| FR-05 | Crop selection: rank the four crop options by expected profit per acre, using a seasonal-ratio harvest-price estimate (4–6 months ahead), sourced yields and costs, with price risk shown | High | UC-05 |
| FR-06 | Selling window: show the seasonal price pattern and the best selling window within the harvest season (sowing dates are not advised) | Medium | UC-06 |
| FR-07 | Market comparison: compare the mandis that have data for the crop on net price after estimated transport and flag the best | High | UC-04 |
| FR-08 | Price guidance: recommend a fair selling range and compare it with a buyer's offer | Medium | UC-07 |
| FR-09 | Margin analysis: break down production cost, the farmer's own arhti commission (if entered) and profit; wheat support price as reference | Medium | UC-08 |
| FR-10 | Urdu language support: Urdu and Roman Urdu in the interface, signals and chat | High | All |
| FR-11 | AI chat: text and voice-note questions answered in text using the current forecast, with transcript confirmation and a template fallback | Medium | UC-09 |
| FR-12 | Price history and seasonality charts by crop and mandi | Low | UC-12 |
| FR-13 | Farmer profiles: crops, preferred mandi, land area, site location and harvest quantity | High | UC-11 |
| FR-14 | Real-time weather from Open-Meteo (last 92 days), aggregated the same way as the training features, fed into the forecast | High | UC-13 |
| FR-15 | Load pre-processed prices, transport costs, support prices, costs, yields and trained models from offline files | High | UC-14 |

### Non-Functional Requirements (NFR)

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Accuracy | The 4-week price forecast has lower MAPE than the persistence baseline ("price in 4 weeks = today's price") on real validation rows (2025), and is confirmed once on real test rows (2026). Reported pooled and per crop, not per crop × mandi (some series have only 1–2 test rows). Directional accuracy on moves larger than 3% is reported alongside. For reference, the baseline already scores 6.0% (val) and 3.5% (test) MAPE, so a fixed "≤ 15%" target is not meaningful. If the model does not beat the baseline, it is not deployed |
| NFR-02 | Performance | Forecast and recommendation load in under 3 s; WhatsApp/SMS replies arrive within 10 s. Live weather is the only external call on this path |
| NFR-03 | Usability | A first-time farmer reaches a sell/hold/wait answer in under 1 minute, with large text, icons and colour-coded signals. No training needed |
| NFR-04 | Localisation | All farmer-facing content in Urdu with correct right-to-left layout; Roman Urdu input accepted |
| NFR-05 | Accessibility | Works on low-end Android phones and basic phones (SMS) on low bandwidth. Minimum 18px text, 48px touch targets, high contrast for sunlight |
| NFR-06 | Reliability | Available through the demo. If the LLM, weather API or messaging fails, fall back to cached weather, templates or SMS |
| NFR-07 | Explainability | Every recommendation has a plain-language reason a less literate farmer can follow |
| NFR-08 | Transparency | Forecasts show uncertainty, the source ("AMIS mandi price") and a per-series "prices as of" date, shown in amber if older than 8 weeks. Any value derived from synthetic data is labelled "synthetic". Assumed values (transport rate, milling yield) are labelled "estimate" |
| NFR-09 | Security & Privacy | Profiles and phone numbers stored securely and never shared; API keys kept out of code; voice files deleted after transcription |
| NFR-10 | Scalability | Adding a crop or mandi needs only a config change, offline data preparation and retraining |
| NFR-11 | Maintainability | Constants in one config file, documented code, reproducible results (fixed random seeds) |
| NFR-12 | Data freshness | Weather fetched live (cached up to 1 hour). Prices, transport costs and models refreshed offline, with the update date shown |
| NFR-13 | Voice input | Urdu voice note transcribed within 10 s; transcript shown for confirmation; on failure, ask to type or retry |

---

## 5. 🗃️ Domain Model & Class Diagram

### Entities List

| Entity | Description |
|--------|-------------|
| `Farmer` | A registered user with location, land area, language and optional arhti commission % |
| `Crop` | One crop option: Wheat, Cotton, or a Rice variety (Super Basmati, IRRI), with sourced cost and yield |
| `CropCalendar` | Sowing and harvest months for a crop |
| `Mandi` | A wholesale market: Vehari, Bahawalpur or Rahim Yar Khan |
| `PriceRecord` | A pre-processed historical price for a crop at a mandi on a date |
| `SupportPrice` | Government support price for a crop in a year (wheat only), with whether it was actually procured |
| `TransportCost` | Pre-computed estimated cost to move 40 kg from a district to a mandi |
| `WeatherReading` | Live weather for a mandi, aggregated into the model's weekly features, cached |
| `FarmerCrop` | A crop the farmer grows, with preferred mandi and harvest quantity |
| `Forecast` | A model prediction for a crop at a mandi, with range and volatility |
| `Recommendation` | A sell signal for a farmer based on a forecast |
| `Explanation` | One SHAP factor behind a forecast |
| `CropPlan` | A profit ranking and best selling window for one crop for a farmer |
| `Alert` | A notification triggered by a signal change or unusual price |
| `Message` | One WhatsApp or SMS message in or out |
| `ChatSession` / `ChatMessage` | A chat conversation and its messages (text or transcribed voice) |
| `MLModel` | A trained model version with its accuracy |
| `DataSource` | Where data comes from (offline or live) and when it was refreshed |

### Class Diagram (text notation)

```
+-------------------+ 1     * +-------------------+ *     1 +-----------------+
|      Farmer       |---------|    FarmerCrop     |---------|      Crop       |
+-------------------+         +-------------------+         +-----------------+
| id: UUID          |         | harvest_qty_maund |         | id: INT         |
| name: String      |         | planting_date     |         | name: CropName  |
| phone: String     |         +-------------------+         | variety: Variety|
| language: Lang    |                  |*                   | season: Season  |
| district: String  |                  |1                   | prod_cost: Dec  |
| site_lat/lon: Dec |         +-------------------+         | yield_maund: Dec|
| land_area: Dec    |         |      Mandi        |         +-----------------+
| arhti_pct: Dec?   |         +-------------------+          |1    |1      |1
+-------------------+         | id, name          |          |     |       |
   |1     |1     |1           |                   |          |     |       |
   |      |      |            | lat, lon          |          |*    |1      |*
   |*     |*     |*           +-------------------+   PriceRecord CropCalendar SupportPrice
Recommendation Alert ChatSession   |1      |1
   |*     |1     |1                |*      |*
   |1     |*     |*           WeatherReading  Forecast *----1 MLModel
Forecast Message ChatMessage                  |1
                                              |*
                                          Explanation

Farmer 1--* CropPlan *--1 Crop
TransportCost: district --> Mandi (pre-computed)
```

### Relationships Summary

| From | Relationship | To | Cardinality |
|------|-------------|-----|-------------|
| Farmer | grows | Crop (via FarmerCrop) | Many-to-Many |
| FarmerCrop | prefers | Mandi | Many-to-One |
| Crop | has | PriceRecord | One-to-Many |
| Mandi | has | PriceRecord | One-to-Many |
| Crop | has | CropCalendar | One-to-One |
| Crop | has | SupportPrice | One-to-Many |
| Mandi | has | WeatherReading | One-to-Many |
| Forecast | is for | Crop and Mandi | Many-to-One |
| Forecast | produced by | MLModel | Many-to-One |
| Forecast | explained by | Explanation | One-to-Many |
| Recommendation | based on | Forecast | Many-to-One |
| Farmer | receives | Recommendation, Alert, CropPlan | One-to-Many |
| Alert | sent as | Message | One-to-Many |
| Farmer | has | ChatSession | One-to-Many |
| ChatSession | contains | ChatMessage | One-to-Many |
| TransportCost | from district to | Mandi | Many-to-One |

### Enumerations

```
CropName      : WHEAT | RICE | COTTON
RiceVariety   : SUPER_BASMATI | IRRI | NONE
Season        : RABI | KHARIF
Language      : UR | ROMAN_UR | EN
Signal        : SELL | WAIT          (Urdu: بیچ دیں | رکیں)
Trend         : UP | DOWN | STABLE
Volatility    : STABLE | MODERATE | VOLATILE
Confidence    : HIGH | MEDIUM | LOW
RiskLevel     : LOW | MEDIUM | HIGH
AlertType     : SELL_SIGNAL | PRICE_SPIKE | ANOMALY
AlertStatus   : CREATED | SENT | DELIVERED | FAILED | SUPPRESSED
Channel       : WHATSAPP | SMS | WEB
Direction     : INBOUND | OUTBOUND
ContentType   : TEXT | VOICE
ModelType     : PRICE | PRICE_Q10 | PRICE_Q90 | VOLATILITY
               (harvest price is a seasonal-ratio estimate, not a trained model;
                the sell-advisor classifier is dropped, see decision 9)
SourceType    : OFFLINE | LIVE
SupportStatus : PROCURED | ANNOUNCED_NOT_PROCURED
```

---

## 6. 🔄 Sequence Diagrams

### Sell advice flow (UC-01, UC-03, UC-13)

```
Farmer    React App     FastAPI      Advisory     ML Layer    Weather Svc   Open-Meteo    DB
  |           |            |          Engine          |            |            |          |
  |--open Home-->          |            |             |            |            |          |
  |           |--GET /api/advice------->|             |            |            |          |
  |           |            |--getProfile()------------------------------------------------>|
  |           |            |<--crop, mandi, qty-------------------------------------------- |
  |           |            |--getWeather(mandi)------------------->|            |          |
  |           |            |            |             |            |--(cache stale) GET past_days=92-->|
  |           |            |            |             |            |<--weather--|          |
  |           |            |<--weekly + 4w/12w weather aggregates--|            |          |
  |           |            |--predict(features)------>|            |            |          |
  |           |            |<--price, q10, q90, vol---|            |            |          |
  |           |            |--advise()->|             |            |            |          |
  |           |            |<--signal, net Rs impact (after interest), fair range       |          |
  |           |            |--save forecast + recommendation--------------------------------->|
  |           |<--200 JSON-|            |             |            |            |          |
  |<--WAIT card (Urdu)-----|            |             |            |            |          |
```

### "Why?" explanation flow (UC-02)

```
Farmer    React App     FastAPI      ML Layer (SHAP)   Urdu Text Builder
  |--tap Why?-->|          |               |                   |
  |           |--GET /api/explain-->       |                   |
  |           |            |--shap(forecast_id)-->             |
  |           |            |<--top features + values           |
  |           |            |--toSentences()------------------->|
  |           |            |<--"Price has risen 6% in 4 weeks, which usually slows" ...
  |           |<--200 JSON-|               |                   |
  |<--reason list + arrows-|               |                   |
```

### WhatsApp voice question flow (UC-09)

```
Farmer   WhatsApp Cloud API   FastAPI webhook   Gemini (transcribe)   Advisory/ML   Gemini (chat)   DB
  |--voice note-->|                 |                   |                 |              |          |
  |               |--POST /webhooks/whatsapp            |                 |              |          |
  |               |                 |--verify signature  |                 |              |          |
  |               |                 |--download media    |                 |              |          |
  |               |                 |--transcribe(audio)->|                 |              |          |
  |               |                 |<--"Gandum ka rate..."                |              |          |
  |<--"Did you mean: Gandum ka rate...? Reply 1 = Yes"---|                 |              |          |
  |--"1"--------->|---------------->|                   |                 |              |          |
  |               |                 |--getForecast + advice--------------->|              |          |
  |               |                 |<--numbers + signal-------------------|              |          |
  |               |                 |--prompt(context, question)------------------------->|          |
  |               |                 |<--Urdu text reply------------------------------------|          |
  |               |                 |--save chat + messages, delete audio------------------------------>|
  |<--text reply--|<----------------|                   |                 |              |          |
```

### Alert flow (UC-10)

```
Scheduler     Advisory Engine     DB          WhatsApp Cloud API   SMS Gateway    Farmer
   |--check signals-->|           |                  |                 |            |
   |                  |--compare with last signal--->|                 |            |
   |                  |<--changed for farmer X-------|                 |            |
   |--build Urdu alert, create Alert(CREATED)------->|                 |            |
   |--send---------------------------------------------->|             |            |
   |                  |           |                  |--deliver------------------->|
   |   (if FAILED or no WhatsApp)  |                  |                 |            |
   |--send SMS (160 chars)------------------------------------------------>|-------->|
   |--update Alert status (SENT / DELIVERED / FAILED)-->|                 |            |
```

---

## 7. 🗺️ State Diagrams

### Alert lifecycle

```
       [Signal change or anomaly detected]
                    |
                    v
                [CREATED] ---already alerted this week---> [SUPPRESSED]
                    |
               [Send WhatsApp]
                    |
                    v
                 [SENT] -----delivered-----> [DELIVERED]
                    |
                 [failed]
                    |
               [Send SMS fallback]
                    |
           +--------+--------+
           v                 v
      [DELIVERED]        [FAILED]
```

### Voice question lifecycle

```
   [Voice note received]
            |
            v
      [TRANSCRIBING] ----error----> [TRANSCRIPTION_FAILED] --> ask to type or retry
            |
            v
 [AWAITING_CONFIRMATION] ---farmer says no---> ask to type or retry
            |
         [yes]
            v
       [ANSWERING] ----LLM down----> [TEMPLATE_REPLY]
            |                              |
            v                              v
        [ANSWERED] <-----------------------+
            |
     [audio deleted]
```

### Farmer profile lifecycle

```
   [GUEST] --register (phone)--> [REGISTERED] --alerts on--> [ACTIVE]
                                    ^                          |
                                    +----"Stop alerts"---------+
                                               |
                                         [ALERTS_OFF]
```

### Recommendation signal (re-evaluated on each forecast)

```
        4-week forecast ≥ +5% above today          otherwise
   [WAIT (رکیں)] <------------------- [evaluate] -------------------> [SELL (بیچ دیں)]

   The 5% threshold lives in config. No HOLD state and no storage cost, but
   the rupee impact subtracts the interest cost of waiting (1.375% per month).
   Expect SELL in most weeks: a 5% rise in 4 weeks happens in 14–19% of real weeks.
```

---

## 8. 🏗️ System Architecture

### Architecture Pattern
Layered monolith (one FastAPI service) with a separate **offline ML pipeline**. The runtime never scrapes prices or retrains models; it only loads pre-processed files and calls live services for weather (Open-Meteo), messaging (WhatsApp Cloud API, SMS gateway) and Gemini (chat and voice transcription). All external services run on free tiers for the MVP.

```
 Farmers
   │  WhatsApp · SMS · React web app (Urdu)
   ▼
┌──────────────────────────────────────────────┐
│ 1. CHANNEL LAYER                             │
│  React web UI │ WhatsApp Cloud │ SMS gateway │
└──────────────────────┬───────────────────────┘
                       ▼  HTTPS / REST / webhooks
┌──────────────────────────────────────────────┐
│ 2. APPLICATION / API LAYER (FastAPI)         │
│  Routes · Profiles · Urdu/Roman Urdu handler │
│  Messaging webhooks · Alert scheduler        │
└───────┬──────────────┬───────────────┬───────┘
        ▼              ▼               ▼
┌──────────────┐ ┌─────────────┐ ┌──────────────┐
│ 3. ADVISORY  │ │ 4. ML LAYER │ │ 5. AI CHAT   │
│   ENGINE     │ │ (pre-trained│ │ Gemini       │
│ Sell signal  │ │  models)    │ │ Voice in,    │
│ Crop ranking │ │ 4-wk price  │ │ text out     │
│ Sell window  │ │ Quantiles   │ │ Template     │
│ Mandi compare│ │ Volatility  │ │ fallback     │
│ Fair price   │ │ SHAP        │ └──────────────┘
│ Margin calc  │ │             │
│ Harvest est. │ │             │
└──────┬───────┘ └──────┬──────┘
       └────────┬───────┘
        ┌───────┴────────┐
        ▼                ▼
┌─────────────────┐  ┌──────────────────────┐
│ 6. DATA LAYER   │  │ 7. LIVE WEATHER      │
│ Pre-processed   │  │ Open-Meteo API       │
│ prices, transport│ │ (cached ≤ 1 hour)    │
│ support prices, │  └──────────────────────┘
│ models · SQLite │
│ (farmers, alerts│
│ messages, chats)│
└────────▲────────┘
         │ export
┌────────┴─────────────────────────────────────┐
│ 8. OFFLINE PIPELINE (Dev Team, not runtime)  │
│  Raw data → clean → features → train models  │
│  + SHAP → validate (NFR-01) → export         │
└──────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| Frontend | Mobile-first Urdu UI, charts | React + TypeScript (Vite), Tailwind, shadcn/ui, Recharts, react-i18next |
| API layer | Routing, validation, profiles, webhooks | FastAPI, Pydantic |
| Auth service | Identify farmer by phone number | Sender number on WhatsApp/SMS; pre-seeded profile + JWT on web for the demo; OTP post-MVP |
| Location service | Site pin and district lookup | Leaflet + OpenStreetMap, Nominatim |
| Advisory engine | Signal with interest cost, crop ranking with seasonal-ratio harvest estimate, selling window, mandi comparison, fair price, margin | Python module |
| ML layer | 4-week price model with quantile range, volatility model; SHAP | XGBoost, SHAP |
| Weather service | Fetch the last 92 days, aggregate into training features, cache | Open-Meteo API |
| Chat service | Context-aware Urdu replies; voice transcription | Gemini API (free tier) for both |
| Notification service | Alerts, WhatsApp and SMS replies, fallback | Meta WhatsApp Cloud API, Android SMS gateway, APScheduler |
| Database | Farmers, forecasts, alerts, messages, chats | SQLite |
| Pre-processed store | Prices, transport costs, support prices, models | CSV / Parquet / model files in repo |
| Cache | Weather readings | In-process cache + SQLite table |
| Offline pipeline | Data prep, training, validation, export | Python scripts, Pandas, NumPy |

---

## 9. 🗄️ Data Model / ERD

> Pre-processed tables (marked **[offline]**) are filled by the offline pipeline and read-only at runtime.

### Entity: `farmers`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Unique identifier |
| `name` | VARCHAR(100) | | Farmer name |
| `phone` | VARCHAR(20) | UNIQUE, NOT NULL | WhatsApp/SMS number, used as identity |
| `language` | ENUM(Language) | NOT NULL, DEFAULT 'UR' | Preferred language |
| `district` | VARCHAR(50) | NOT NULL | Used for transport cost |
| `site_lat` | DECIMAL(9,6) | | Farm location |
| `site_lon` | DECIMAL(9,6) | | Farm location |
| `land_area_acres` | DECIMAL(8,2) | | Used for crop profit |
| `arhti_commission_pct` | DECIMAL(5,2) | NULL | Entered by the farmer; NULL means none applied |
| `alerts_enabled` | BOOLEAN | DEFAULT TRUE | Alert opt-in |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

### Entity: `crops` [offline]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INT | PK | |
| `name` | ENUM(CropName) | NOT NULL | WHEAT, RICE, COTTON |
| `variety` | ENUM(RiceVariety) | NOT NULL, DEFAULT 'NONE' | Rice variety or NONE |
| `season` | ENUM(Season) | NOT NULL | Rabi or Kharif |
| `production_cost_per_40kg` | DECIMAL(10,2) | NOT NULL | Rs, market level incl. land rent, in the same product unit as the AMIS price (milled-equivalent for rice) |
| `production_cost_per_acre` | DECIMAL(10,2) | | Rs, net cost of cultivation |
| `yield_maund_per_acre` | DECIMAL(6,2) | NOT NULL | Official API tables; rice in paddy |
| `milling_yield` | DECIMAL(4,2) | | Rice only; 0.65 (assumption) |
| `cost_source` / `cost_confidence` | VARCHAR | | From `economics_inputs.json` |
| | | UNIQUE(name, variety) | |

Starting values (Punjab, from `data/processed/economics_inputs.json`):

| Crop option | Cost Rs/40kg | Cost Rs/acre | Yield maund/acre | Confidence |
|---|---|---|---|---|
| Wheat | 3,761 | about 100,859 (2023-24 official) | 31 | medium (2026 farmer-group estimate; CPI check gives 3,697) |
| Cotton (seed cotton) | 6,616 | about 134,352 | 20.5 | derived (official 2022-23 × CPI 1.381) |
| IRRI | 3,166 milled-equivalent (2,058 paddy) | about 98,782 | 50 paddy | derived; milling yield 0.65 is an assumption |
| Super Basmati | about 4,130 milled-equivalent (about 2,685 paddy) | about 104,060 | 40 paddy | derived from the official 2022-23 Basmati row (Rs 1,944/40kg, Rs 75,352/acre) × CPI 1.381; to be confirmed |

No middleman cut column: there is no source for a default percentage, and AMIS prices are already wholesale mandi prices, so a default cut would double-count.

### Entity: `crop_calendars` [offline]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INT | PK | |
| `crop_id` | INT | FK → crops.id, UNIQUE | |
| `sowing_start_month` / `sowing_end_month` | TINYINT | 1–12 | |
| `harvest_start_month` / `harvest_end_month` | TINYINT | 1–12 | |

### Entity: `mandis` [offline]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INT | PK | |
| `name` | VARCHAR(50) | UNIQUE, NOT NULL | Vehari, Bahawalpur, Rahim Yar Khan |
| `amis_name` | VARCHAR(50) | NOT NULL | Name in the AMIS files: Vehari, BahawalPur, RahimYarKhan |
| `latitude` / `longitude` | DECIMAL(9,6) | NOT NULL | For weather and distance |

### Entity: `price_records` [offline]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PK | |
| `crop_id` | INT | FK → crops.id | |
| `mandi_id` | INT | FK → mandis.id | |
| `date` | DATE | NOT NULL | Week start (Monday) |
| `price_pkr` | DECIMAL(10,2) | NOT NULL | In the source unit (AMIS: Rs per 100 kg), as in repo `docs/PLAN.md` 6.5 |
| `unit` | VARCHAR(10) | NOT NULL | `100kg` for AMIS. The API converts to per 40 kg (× 0.4) and every response says `unit: "40kg"` |
| `price_type` | VARCHAR(10) | NOT NULL | `wholesale` |
| `is_filled` | BOOLEAN | DEFAULT FALSE | Short gap (≤ 2 weeks) forward-filled |
| `is_synthetic` | BOOLEAN | DEFAULT FALSE | Always false at runtime |
| `source_id` | INT | FK → data_sources.id | |
| | | UNIQUE(crop_id, mandi_id, date) | |

Coverage of the real series (2015 – Oct 2026): Wheat and Cotton at all three mandis (Vehari wheat's latest price is Jul 2026); IRRI at Vehari and Bahawalpur; Super Basmati at all three, but its latest prices are Nov 2025 (Vehari), Apr 2026 (Bahawalpur) and Dec 2025 (Rahim Yar Khan). Cotton has the most gaps.

### Entity: `support_prices` [offline]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INT | PK | |
| `crop_id` | INT | FK → crops.id | |
| `year` | SMALLINT | NOT NULL | Crop year start (2025 = 2025-26) |
| `price_per_40kg` | DECIMAL(10,2) | NOT NULL | Rs |
| `status` | ENUM(SupportStatus) | NOT NULL | The 2023-24 crop (spring 2024 harvest) was announced at 3,900 but not procured |

Wheat only (rice and cotton have no support price). Verified values, by crop year (harvest the following spring), from the AMIS official support-price table (http://www.amis.pk/Agristatistics/SupportPrice/wheat/wheat.html) plus news for 2025-26: 2020-21 Rs 1,800; 2021-22 Rs 2,200; 2022-23 Rs 3,900; 2023-24 Rs 3,900 announced, not procured (spring 2024); 2025-26 Rs 3,500, indicative (spring 2026). The 2024-25 crop (spring 2025) had no support price (IMF-linked deregulation; AMIS shows "-"). 2026-27 is not yet announced. Generated as `data/processed/runtime/support_prices.csv`.

### Entity: `transport_costs` [offline]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INT | PK | |
| `from_district` | VARCHAR(50) | NOT NULL | Farmer's district |
| `to_mandi_id` | INT | FK → mandis.id | |
| `distance_km` | DECIMAL(7,2) | NOT NULL | Road estimate = straight line × 1.3 |
| `cost_per_40kg` | DECIMAL(8,2) | NOT NULL | Rs, distance × Rs 1.3 per 40 kg per km (assumption, labelled "estimate") |
| | | UNIQUE(from_district, to_mandi_id) | |

MVP districts are the three mandi districts. Road estimates: Bahawalpur–Vehari 127 km (about Rs 165/40kg), Bahawalpur–Rahim Yar Khan 224 km (about Rs 291), Vehari–Rahim Yar Khan 349 km (about Rs 454). Replace the rate with a real freight quote when available.

### Entity: `weather_readings` [live, cached]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PK | |
| `mandi_id` | INT | FK → mandis.id | |
| `fetched_at` | TIMESTAMP | NOT NULL | Cache age check |
| `week_start` | DATE | NOT NULL | Week the aggregates describe |
| `tmax_c` / `tmin_c` / `rh_pct` | DECIMAL(5,2) | | Weekly means |
| `precip_mm_wk` / `et0_mm_wk` | DECIMAL(6,2) | | Weekly sums |
| `hot_days_wk` | TINYINT | | Days with tmax ≥ 40°C |
| `precip_mm_4w` / `precip_mm_12w` / `tmax_c_4w` | DECIMAL(6,2) | | Trailing aggregates |

Column names match `features.csv`, so the same aggregation code serves training and runtime.

### Entity: `farmer_crops`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `farmer_id` | UUID | PK, FK → farmers.id | |
| `crop_id` | INT | PK, FK → crops.id | |
| `preferred_mandi_id` | INT | FK → mandis.id | |
| `harvest_quantity_maund` | DECIMAL(10,2) | | |
| `planting_date` | DATE | | |

### Entity: `ml_models` [offline]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INT | PK | |
| `type` | ENUM(ModelType) | NOT NULL | |
| `version` | VARCHAR(20) | NOT NULL | |
| `trained_at` | TIMESTAMP | NOT NULL | |
| `mape` | DECIMAL(5,2) | | Regression models |
| `accuracy` | DECIMAL(5,2) | | Classifiers |
| `file_path` | VARCHAR(255) | NOT NULL | Model file |

### Entity: `forecasts`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `crop_id` | INT | FK → crops.id | |
| `mandi_id` | INT | FK → mandis.id | |
| `model_id` | INT | FK → ml_models.id | |
| `weather_id` | BIGINT | FK → weather_readings.id | Weather used |
| `run_date` / `target_date` | DATE | NOT NULL | target = run + 4 weeks. Crop-ranking harvest estimates are stored in `crop_plans`, not here |
| `prices_as_of` | DATE | NOT NULL | Date of the latest real price used |
| `current_price` | DECIMAL(10,2) | NOT NULL | |
| `predicted_price` | DECIMAL(10,2) | NOT NULL | |
| `lower_bound` / `upper_bound` | DECIMAL(10,2) | NOT NULL | 10th / 90th percentile |
| `trend` | ENUM(Trend) | NOT NULL | |
| `volatility_level` | ENUM(Volatility) | NOT NULL | |

### Entity: `explanations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGINT | PK | |
| `forecast_id` | UUID | FK → forecasts.id | |
| `feature_name` | VARCHAR(50) | NOT NULL | |
| `shap_value` | DECIMAL(10,2) | NOT NULL | Rs effect |
| `direction` | ENUM('UP','DOWN') | NOT NULL | |
| `text_ur` | TEXT | | Plain Urdu sentence |

### Entity: `recommendations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `farmer_id` | UUID | FK → farmers.id | |
| `forecast_id` | UUID | FK → forecasts.id | |
| `signal` | ENUM(Signal) | NOT NULL | |
| `confidence` | ENUM(Confidence) | NOT NULL | |
| `expected_price` | DECIMAL(10,2) | NOT NULL | |
| `rupee_impact` | DECIMAL(12,2) | NOT NULL | Net, on the farmer's harvest, after interest |
| `interest_cost` | DECIMAL(12,2) | NOT NULL | Interest cost of waiting 4 weeks |
| `fair_price_low` / `fair_price_high` | DECIMAL(10,2) | | Fair range to ask |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

### Entity: `crop_plans`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `farmer_id` | UUID | FK → farmers.id | |
| `crop_id` | INT | FK → crops.id | |
| `harvest_price_estimate` | DECIMAL(10,2) | NOT NULL | Rs/40kg, seasonal-ratio estimate |
| `harvest_price_low` / `harvest_price_high` | DECIMAL(10,2) | | Min–max across years |
| `expected_profit` | DECIMAL(12,2) | NOT NULL | For the farmer's land area |
| `risk_level` | ENUM(RiskLevel) | NOT NULL | From the year-to-year spread |
| `rank` | TINYINT | NOT NULL | 1–4 |
| `best_sell_start_month` / `best_sell_end_month` | TINYINT | | 1–12 |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

### Entity: `alerts`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `farmer_id` | UUID | FK → farmers.id | |
| `crop_id` | INT | FK → crops.id | |
| `type` | ENUM(AlertType) | NOT NULL | |
| `status` | ENUM(AlertStatus) | NOT NULL | |
| `message_text` | TEXT | NOT NULL | |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Used for 1-per-week rule |

### Entity: `messages`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `farmer_id` | UUID | FK → farmers.id | |
| `alert_id` | UUID | FK → alerts.id, NULL | If part of an alert |
| `channel` | ENUM(Channel) | NOT NULL | |
| `direction` | ENUM(Direction) | NOT NULL | |
| `content_type` | ENUM(ContentType) | NOT NULL | |
| `content` | TEXT | | Text or transcript |
| `provider_msg_id` | VARCHAR(128) | | WhatsApp or SMS gateway message ID |
| `status` | VARCHAR(20) | | queued / sent / delivered / failed |
| `sent_at` | TIMESTAMP | | |

### Entity: `chat_sessions` and `chat_messages`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `chat_sessions.id` | UUID | PK | |
| `chat_sessions.farmer_id` | UUID | FK → farmers.id | |
| `chat_sessions.language` | ENUM(Language) | | |
| `chat_sessions.started_at` | TIMESTAMP | | |
| `chat_messages.id` | UUID | PK | |
| `chat_messages.session_id` | UUID | FK → chat_sessions.id | |
| `chat_messages.role` | ENUM('FARMER','ASSISTANT') | NOT NULL | |
| `chat_messages.content_type` | ENUM(ContentType) | NOT NULL | Voice stored as transcript only |
| `chat_messages.text` | TEXT | NOT NULL | |
| `chat_messages.used_fallback` | BOOLEAN | DEFAULT FALSE | Template reply |
| `chat_messages.created_at` | TIMESTAMP | | |

### Entity: `data_sources`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INT | PK | |
| `name` | VARCHAR(50) | NOT NULL | AMIS.pk, Open-Meteo, API cost tables, economics_inputs.json |
| `type` | ENUM(SourceType) | NOT NULL | OFFLINE or LIVE |
| `last_refreshed` | TIMESTAMP | | Shown as "prices as of" |

---

## 10. 🔐 Security & Access Control

### Authentication Strategy
- [ ] Email & Password — not used; many farmers have no email
- [ ] OAuth (Google, GitHub, etc.) — not used
- [x] Phone number as identity. On WhatsApp/SMS, the sender's number identifies the farmer
- [x] JWT for the web app session (demo: pre-seeded farmer profile)
- [ ] OTP by SMS — post-MVP (free options only reach verified numbers)
- [ ] Two-Factor Authentication (2FA) — not needed for MVP

### Authorization Matrix (RBAC)

| Feature | Guest | Farmer | Dev Team |
|---------|-------|--------|----------|
| View forecast, Why, mandi comparison, history, margin | ✅ | ✅ | ✅ |
| Register / Login (phone number) | ✅ | ✅ | ✅ |
| Personalised sell signal with rupee impact | ❌ | ✅ | ✅ |
| Crop ranking and selling window for own land | ❌ | ✅ | ✅ |
| Buyer offer check | ✅ (example quantity) | ✅ | ✅ |
| AI chat (text and voice) | ❌ | ✅ | ✅ |
| Receive alerts | ❌ | ✅ | ❌ |
| Edit own profile, stop alerts | ❌ | ✅ | ❌ |
| Run offline pipeline, deploy models | ❌ | ❌ | ✅ (outside the app) |

### Security Checklist
- [x] Input validation & sanitization (Pydantic on every request)
- [x] SQL injection prevention (parameterized queries / ORM)
- [x] XSS prevention (React escaping; LLM output rendered as text, never HTML)
- [x] CSRF protection (JWT in Authorization header, not cookies)
- [x] HTTPS enforced on any public deployment
- [x] Rate limiting on chat and webhook endpoints (also protects the Gemini free-tier quota)
- [x] Webhook signature validation (Meta `X-Hub-Signature-256`; shared secret for the SMS gateway)
- [x] Gemini free tier may use prompts to improve Google's models: demo data only, no real farmer data until moved to a paid tier
- [x] API keys in environment variables, never in the repo
- [x] Voice files deleted after transcription; only the transcript is kept
- [x] LLM gets only the farmer's own forecast context, and is told not to invent prices
- [ ] Sensitive data encryption at rest (post-hackathon)
- [ ] Audit logging for admin actions (no runtime admin in MVP)

---

## 11. 🖥️ UI/UX Planning

### Design Principles
- **Answer first.** The decision (SELL or WAIT) is the first thing on screen.
- **Urdu first.** Default Urdu with right-to-left layout, a Roman Urdu toggle, and English for judges.
- **Low literacy.** Big text, icons, colour-coded signals, and voice-note input on WhatsApp and in the chat.
- **Phone first.** Designed for a 360px-wide Android screen.
- **Rupees, not percentages.** "Rs 12,000 more if you wait", not "+4.2%".

**Signal colours** (always with an icon and a word): SELL (بیچ دیں) green, WAIT (رکیں) amber. There are only two signals; no HOLD.

### Screen Inventory

| Screen Name | Actor | Description |
|-------------|-------|-------------|
| Language select | Guest | Urdu / Roman Urdu / English |
| Register (profile) | Guest | Phone, crops, preferred mandi, land area, site location (OpenStreetMap pin), harvest quantity, optional arhti commission % |
| Home | Farmer / Guest | Crop and mandi, large signal card, current vs 4-week forecast with range, four buttons: Sell, Grow, Compare Mandis, Ask |
| Sell advice | Farmer | Signal, expected price, net rupee impact with the interest cost line, fair price range, "Buyer offered Rs ___" check, "Why?" button |
| Why (SHAP) | Farmer / Guest | Plain Urdu reasons with arrows; SHAP chart behind a "details" toggle |
| Compare Mandis | Farmer / Guest | Mandis with data for the crop ranked by net price (transport labelled "estimate"), best highlighted, gain in rupees; mandis without data listed as "no price data" |
| What to Grow | Farmer | Four cards (Wheat, Cotton, Super Basmati, IRRI) ranked by profit per acre with risk badges and "estimate" label; tap for the season timeline (sowing, harvest, best selling window) |
| Margin check | Farmer / Guest | Production cost, own arhti commission (if entered) and farmer profit bar; support price line for wheat only |
| Price history | Farmer / Guest | 52-week chart with seasons shaded, monthly seasonal chart as % of annual average |
| Chat | Farmer | Message screen, suggested question chips, microphone button, transcript confirmation, fallback note |
| Profile / Settings | Farmer | Edit profile, language, alerts on/off |
| WhatsApp / SMS (external) | Farmer | Text alert cards with quick replies; SMS number menu; voice-note questions |

### User Flow (Critical Path)

```
[Language select]
       |
[Register: phone + profile]   (one time)
       |
     [Home] ── signal card: WAIT (رکیں) or SELL (بیچ دیں), expected price, range, Rs impact
       |
  +----+-------------+-----------------+--------------+
  |                  |                 |              |
[Sell advice]   [Compare Mandis]  [What to Grow]    [Ask (chat)]
  |    |             |                 |              |
[Why?] [Buyer offer  [Best mandi    [Crop card]     [Voice note]
        check]        + Rs gain]       |              |
         |                       [Selling window] [Confirm transcript]
    [Margin view]                                     |
                                                  [Text answer]

[Alert scheduler] --> [WhatsApp alert] --> [Why? / Compare / Stop] --> back into flow
```

### Demo Script (5 minutes)

**Persona:** Ahmed, a wheat and cotton farmer near Bahawalpur with 100 maund to sell, deciding what to plant next season.

| Time | Step | What the audience sees | Use case |
|---|---|---|---|
| 0:00–0:30 | Problem | Farmers sell at harvest into a glut, at the wrong mandi, without knowing their margin (use a sourced loss figure or none) | – |
| 0:30–1:15 | Sell now or wait? | Home with Wheat, Bahawalpur, "AMIS mandi price, as of <date>". Signal card (whatever the real model says; SELL is the most likely), expected price in 4 weeks with range, net rupee impact on 100 maund after interest, live weather shown | UC-01, UC-03, UC-13 |
| 1:15–2:00 | Why? | Plain Urdu reasons with arrows; SHAP chart for one second | UC-02 |
| 2:00–2:40 | Where and at what price? | Mandis ranked by net price (transport "estimate"); buyer's offer checked against fair range | UC-04, UC-07, UC-08 |
| 2:40–3:30 | What to grow, and when to sell it? | Four crop options ranked by profit per acre (harvest estimate, labelled); tap the top one for its best selling window | UC-05, UC-06 |
| 3:30–4:10 | Reaches the farmer | WhatsApp alert on a phone with quick replies, then the SMS version | UC-10 |
| 4:10–4:40 | Ask by voice | Voice note "Gandum ka rate agle hafte kitna hoga?", transcript confirmed, Urdu text answer | UC-09 |
| 4:40–5:00 | Close | "Same information traders have, in the farmer's language." State data and accuracy limits | – |

**Must work:** forecast with range for Wheat at Bahawalpur, Urdu sell signal with net rupee impact, "Why?", mandi comparison with net price, crop ranking with selling window.

**Known data risk for the headline case:** AMIS shows wheat at Bahawalpur at about Rs 3,820 per 40 kg in early October 2026, while news reports the Punjab open market at about Rs 5,300 and rising. A judge from Punjab may know the real price. So: (1) always show "AMIS mandi price, as of <date>"; (2) rehearse with the real AMIS number, not a placeholder; (3) keep a backup replay case from the real history, e.g. the spring 2024 wheat harvest, ready to show instead. Do not build the demo around cotton (most data gaps) or Super Basmati (latest prices are months old).

### Wireframe Notes
- **Home:** top bar with crop icon and mandi; full-width signal card (colour, icon, Urdu word, rupee impact); price row "today → in 4 weeks (range)"; 2×2 grid of large action buttons.
- **Sell advice:** signal card, fair price range, offer input with instant above/below result, "Why?" button.
- **Compare Mandis:** three stacked cards ranked by net price; the best has a green border and "+Rs X".
- **What to Grow:** four stacked crop cards with icon, profit per acre, "estimate" label and risk badge; tap opens a 12-month strip showing sowing and harvest (from the calendar) and the best selling window highlighted.
- **Chat:** WhatsApp-style bubbles, suggestion chips above the input, mic button on the input bar.
- **WhatsApp alert:** "🟡 گندم، بہاولپور: رکیں۔ 4 ہفتوں میں متوقع Rs ___ (+Rs ___ on 100 maund after interest)" with buttons: Why? / Compare mandis / Stop alerts. Fill the blanks from real app output.
- **SMS:** one line under 160 characters with "Reply 1 for why, 2 for best mandi".
- **Trust:** every forecast shows a range, the source and "prices as of" date (amber if older than 8 weeks), and "How sure are we?" (high/medium/low). Assumed inputs (transport, milling yield) carry an "estimate" tag. The data is real AMIS data, so there is no "demo data" tag by default; a "synthetic" tag appears only if a value ever comes from synthetic data.
- **Visual style:** earthy green on a light background, Noto Nastaliq Urdu headings, sans-serif numbers, 18px minimum text, 48px touch targets.

---

## 12. 🔌 API Design

### REST Endpoints

| Method | Endpoint | Auth | Description | Use Case |
|--------|----------|------|-------------|----------|
| `GET` | `/api/meta` | Public | Crops, varieties, mandis, "prices as of" date | All |
| `POST` | `/api/auth/login` | Public | Log in by phone number (demo: pre-seeded profile), return JWT. OTP post-MVP | UC-11 |
| `POST` | `/api/farmers` | Farmer (new) | Create profile | UC-11 |
| `GET` | `/api/farmers/me` | Farmer | Get own profile | UC-11 |
| `PUT` | `/api/farmers/me` | Farmer | Update profile, alerts on/off | UC-11, UC-10 |
| `GET` | `/api/forecast?crop_id=&mandi_id=` | Public | Forecast with range, trend, volatility | UC-01, UC-13 |
| `GET` | `/api/explain?forecast_id=` | Public | SHAP reasons in plain Urdu | UC-02 |
| `GET` | `/api/advice?crop_id=&mandi_id=&quantity_maund=` | Farmer | Signal, confidence, expected price, net rupee impact, interest cost, fair range | UC-03 |
| `GET` | `/api/compare-mandis?crop_id=&district=` | Public | Net price per mandi after estimated transport; mandis without data flagged | UC-04 |
| `GET` | `/api/crop-plan` | Farmer | Ranked crops with harvest estimate, profit per acre, risk and best selling window | UC-05, UC-06 |
| `POST` | `/api/offer-check` | Public | Compare a buyer's offer with the fair range | UC-07 |
| `GET` | `/api/margin?crop_id=&price=` | Public | Cost, own arhti commission (if set), profit, wheat support price | UC-08 |
| `GET` | `/api/history?crop_id=&mandi_id=` | Public | 52-week history and seasonal pattern | UC-12 |
| `GET` | `/api/weather?mandi_id=` | Public | Current weather (live or cached) | UC-13 |
| `POST` | `/api/chat` | Farmer | Text question → text answer | UC-09 |
| `POST` | `/api/chat/voice` | Farmer | Audio upload → transcript for confirmation | UC-09 |
| `GET` | `/webhooks/whatsapp` | Verify token | Meta webhook verification handshake | – |
| `POST` | `/webhooks/whatsapp` | Meta signature | Incoming WhatsApp text/voice, replies and delivery status | UC-09, UC-10 |
| `POST` | `/webhooks/sms` | Shared secret | Incoming SMS and number-menu replies from the SMS gateway phone | UC-09, UC-10 |

### API Response Format

```json
{
  "success": true,
  "data": { },
  "message": "OK",
  "error": null,
  "meta": { "prices_as_of": "2026-10-09", "data_source": "amis", "unit": "40kg", "is_synthetic": false, "weather_cached": false }
}
```

Every price in every response is Rs per 40 kg with `unit: "40kg"`; the backend converts from the stored per-100 kg AMIS unit (× 0.4). `prices_as_of` is per crop and mandi, not global.

### Example: `GET /api/advice`

```json
{
  "success": true,
  "data": {
    "crop": { "name": "WHEAT", "variety": "NONE" },
    "mandi": "Bahawalpur",
    "unit": "40kg",
    "current_price": 3820,
    "predicted_price": 4050,
    "range": { "low": 3700, "high": 4300 },
    "trend": "UP",
    "volatility": "STABLE",
    "signal": "WAIT",
    "signal_ur": "رکیں",
    "confidence": "MEDIUM",
    "quantity_maund": 100,
    "gross_gain": 23000,
    "interest_cost": 5253,
    "rupee_impact": 17747,
    "fair_price_range": { "low": 3850, "high": 4100 },
    "forecast_id": "…"
  },
  "message": "OK",
  "error": null,
  "meta": { "prices_as_of": "2026-10-09", "data_source": "amis", "unit": "40kg", "is_synthetic": false, "weather_cached": false }
}
```

> Forecast figures above are placeholders for the contract only. `current_price` 3,820 is the real AMIS level for Bahawalpur wheat in early October 2026. `interest_cost` = 100 × 3,820 × 1.375%.

---

## 13. ⚠️ Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ~~No usable price history~~ **Resolved:** real AMIS daily prices 2015–2026 are cleaned and in the repo (`data/processed/`) | – | – | Gaps remain: IRRI missing at Rahim Yar Khan, Super Basmati prices months old, cotton with long gaps. Handled by A2/A3 in UC-01 and per-series dates |
| Model does not beat the persistence baseline (prices are sticky; a simple linear check did not beat it) | High | High | NFR-01 gate on real validation data; if it fails, pitch the forecast as a direction and risk signal with the range, and say so honestly |
| AMIS lags the real market for the headline case (Bahawalpur wheat about Rs 3,820 vs about Rs 5,300 reported) | High | High | Show "AMIS mandi price, as of <date>"; rehearse with real numbers; keep a historical replay case as backup |
| The 5% threshold makes the app say SELL almost always (a 5% rise happens in 14–19% of weeks) | High | Medium | Expected and honest; plan the demo around it; check how often the model's forecast crosses 5% before tuning |
| Assumed inputs (transport Rs 1.3/40kg/km, 0.65 milling yield, Super Basmati cost) are wrong | Medium | Medium | Label as "estimate" on screen; replace with a real freight quote and a milling-yield source |
| Sell/Hold classifier accuracy is low (~47% in earlier synthetic-data work) | High | High | Derive the signal from the price forecast's % change (5% threshold) so it always agrees with the forecast shown; show confidence |
| Urdu speech-to-text is inaccurate | Medium | Medium | Show transcript for confirmation; let farmers type; pre-test demo phrases |
| LLM invents prices or gives wrong advice | Medium | High | Pass only model numbers as context; instruct it to use only those; template fallback |
| Free messaging tiers only reach verified or opted-in numbers | High | Medium | Register every demo phone in advance; Twilio sandbox as a second option; phone mockup as backup |
| Gemini free-tier rate limits hit during testing or demo | Medium | High | Cache replies for demo questions; rate-limit the chat; template fallback; keep a Groq key as a backup |
| SMS gateway phone loses signal or battery | Medium | Medium | Keep it charged and on Wi-Fi; test the night before; show SMS on a mockup if it fails |
| React build runs over time | Medium | High | Agree API contract in hour 1; build against mock JSON; limit to core screens |
| Urdu RTL and Nastaliq rendering issues | Medium | Medium | Set up RTL and font on day 1; test on a real phone early |
| Open-Meteo or Wi-Fi fails during the demo | Medium | High | 1-hour weather cache; run locally; backup demo video |
| Scope creep | High | High | Stick to the out-of-scope list; backlog everything else |
| Synthetic training rows leak into evaluation or demo numbers | Low | High | `features_augmented.csv` has flagged train-only rows and showed no gain; train on real rows only by default; never use synthetic rows in val, test or any shown metric |

---

## 14. 📅 Project Phases & Milestones (30-hour hackathon)

| Phase | Hours | Description | Deliverable |
|-------|-------|-------------|-------------|
| **Phase 0 — Design** | 0–2 | Complete this document; agree API contract | Signed-off design doc, API contract |
| **Phase 1 — Setup** | 2–5 | Repo, React + FastAPI skeletons, mock JSON, Urdu RTL and font. Offline data is already done (`data/processed/`); add Super Basmati back to the cleaned files and `features.csv` | Skeleton app on mock data |
| **Phase 2 — Core** | 5–16 | Train models on the 4 crop options and the series that have data; check against the persistence baseline (NFR-01); quantile ranges; forecast, advice and explain endpoints; live weather with 92-day aggregation; Home, Sell and Why screens | Must-work demo path running on real models |
| **Phase 3 — Features** | 16–24 | Compare Mandis, What to Grow with seasonal-ratio harvest estimate + selling window, offer check, margin; chat and voice via Gemini; WhatsApp Cloud API and SMS gateway alerts; profiles with map pin | Feature-complete MVP |
| **Phase 4 — Polish** | 24–28 | Urdu copy, mobile layout, fallbacks, price history, bug fixes | Demo-ready build |
| **Phase 5 — Demo** | 28–30 | Rehearse with fixed inputs, record backup video, replace placeholder numbers | 5-minute demo |

**Suggested team split:** ML (models, quantiles, SHAP) · Backend (FastAPI, advisory engine, SQLite, weather) · Frontend (React screens, Urdu RTL) · Integration (WhatsApp Cloud API, SMS gateway, Gemini, demo).

---

## 15. 📦 Tech Stack

| Layer | Options considered | Final Choice |
|-------|---------|--------------|
| Frontend | React, Streamlit | React + TypeScript (Vite), Tailwind CSS, shadcn/ui |
| Urdu / RTL | – | `dir="rtl"`, Noto Nastaliq Urdu, react-i18next |
| Charts | Plotly, Recharts | Recharts |
| Data fetching / routing | – | TanStack Query, React Router |
| Backend | FastAPI, Django, Node.js | FastAPI (Python 3.11) |
| ML | XGBoost, LightGBM | XGBoost, one model per task across all four crop options: 4-week price + quantiles, volatility. Trained offline on `features.csv` (real rows). Use percent-change and ratio features, not raw price level (prices rose about 3x from 2015 to 2026). Harvest price is a seasonal-ratio estimate, not a model |
| Explainability | SHAP, LIME | SHAP TreeExplainer |
| Data handling | – | Pandas, NumPy |
| Database | SQLite, PostgreSQL | SQLite (PostgreSQL later) |
| Pre-processed data | – | CSV / Parquet and model files in the repo |
| Live weather | Open-Meteo | Open-Meteo API (no key needed), `past_days=92` so runtime features match training |
| Cache | Redis, in-process | In-process cache + SQLite table |
| Auth | JWT, OTP (Twilio Verify, Firebase) | Phone number as identity + JWT; pre-seeded profile for the demo; OTP post-MVP |
| AI chat | OpenAI, Gemini, Groq | **Gemini API (free tier)** with template fallback; Groq free tier as backup |
| Voice input | Gemini, Groq Whisper, local Whisper, Google/Azure STT | **Gemini API (free tier)** transcribes Urdu audio, so one API covers chat and voice; Groq Whisper as backup |
| WhatsApp | Meta WhatsApp Cloud API, Twilio sandbox | **Meta WhatsApp Cloud API** (free test number, verified recipients); Twilio sandbox as backup |
| SMS | Twilio trial, Android SMS gateway | **Android phone running an open-source SMS gateway app** (uses the SIM's SMS bundle) |
| Maps / location | Google Maps, OpenStreetMap | **Leaflet + OpenStreetMap**, Nominatim for district lookup (≈1 request/s) |
| Price data (offline) | WFP on HDX, AMIS.pk | AMIS.pk, scraped and cleaned offline (2015–2026). WFP dropped: it covers only Multan, none of our mandis. Confirm AMIS terms of use and add it to the README acknowledgements |
| Economics inputs (offline) | – | `data/processed/economics_inputs.json`: costs, yields, support prices, interest, transport, each with source, date and confidence |
| Scheduling | APScheduler, cron | APScheduler (alert checks only) |
| File storage | – | None; voice files deleted after transcription |
| Config | – | One `config.py`; API keys in `.env` |
| Hosting | Vercel, Render, Hugging Face Spaces, VM, local | Local for the demo; **Vercel Hobby** (frontend) + **Render** or **Hugging Face Spaces** free tier (backend) for a public link |
| CI/CD | GitHub Actions | None for MVP; GitHub for version control |

> **Cost:** every external service above has a free tier that covers the demo. Free-tier limits change, so check them before the event.

---

## 16. ✅ Design Review Checklist

### Completeness
- [x] Vision statement written and agreed upon
- [x] All actors identified
- [x] All major use cases documented
- [x] Functional and non-functional requirements listed
- [x] Class diagram complete with relationships
- [x] Key sequence diagrams drawn
- [x] State diagrams for lifecycle entities done
- [x] Full data model defined (all tables/fields)

### Quality
- [x] No conflicting requirements
- [x] Each requirement is testable
- [x] Security model defined
- [x] Access control matrix filled
- [x] All screens listed in UI inventory
- [x] API endpoints mapped to use cases
- [x] Risks identified with mitigations

### Sign-off
- [ ] Reviewed by all team members
- [ ] Open questions resolved (see below)

---

## 17. ❓ Open Questions & Decisions Log

> **Status key:** ✅ Decided by the team · 🟡 Proposed (recommendation, needs team confirmation) · ⏳ Action (task with a deadline) · ⏸ Deferred (handled in a separate session)

| # | Question / Decision | Status | Owner | Resolution |
|---|---------------------|--------|-------|------------|
| 1 | Scope: which crops and mandis? | ✅ Decided (revised in v0.2.0) | Team | Wheat, Rice (Super Basmati, IRRI), Cotton at Vehari, Bahawalpur, Rahim Yar Khan. Basmati 385 dropped (AMIS stopped in June 2024). IRRI not offered at Rahim Yar Khan (9 valid prices ever) |
| 2 | Frontend framework? | ✅ Decided | Team | React + TypeScript |
| 3 | What runs live vs offline? | ✅ Decided | Team | Only weather is live; prices, transport costs, support prices and models are pre-processed |
| 4 | Voice in MVP? | ✅ Decided | Team | Yes, voice input only; all replies are text |
| 5 | Where does offline price, transport and support price data come from, and does it cover the 3 mandis and Super Basmati? | ✅ Decided | Data owner | AMIS daily prices 2015–2026, cleaned, in `data/processed/`. Wheat and Cotton at all three mandis; IRRI at Vehari and Bahawalpur; Super Basmati at all three but last prices Nov 2025 – Apr 2026. Support prices and transport in `economics_inputs.json`. No synthetic fallback needed |
| 6 | Production cost, middleman cut and yield per crop option (especially Super Basmati) | ✅ Decided (v0.2.0) | Data owner | Use `economics_inputs.json` (table in section 9, `crops`): cost Rs/40kg Wheat 3,761, Cotton 6,616, IRRI 3,166 milled-equivalent, Super Basmati about 4,130 milled-equivalent (to confirm); yields from the official tables. The old config values (1,800 / 2,200 / 1,500 / 4,000) were unsourced and are dropped. No default middleman cut: no source, and AMIS is already a wholesale price; the farmer may enter their own arhti commission |
| 7 | LLM provider: OpenAI or Gemini? | ✅ Decided | Team | Gemini API free tier; Groq free tier as backup |
| 8 | Speech-to-text provider with good Urdu support | ✅ Decided | Team | Gemini (audio input); Groq Whisper as backup. Test Urdu accuracy early |
| 9 | Sell signal from the sell-advisor classifier or from the forecast's % change? | 🟡 Proposed | Team | Derive the signal from the 4-week forecast: WAIT if ≥ 5% above today, otherwise SELL, so it always matches the forecast shown. Confidence comes from the width of the 10th–90th percentile range. The sell-advisor classifier is dropped from the MVP (already reflected in the architecture) |
| 10 | Is OTP needed for the demo, or a pre-seeded profile? | ✅ Decided | Team | No OTP in the MVP; pre-seeded profile on web, sender number on WhatsApp/SMS |
| 11 | Transport cost: per district or computed from the farmer's map pin? | 🟡 Proposed | Team | Per district, pre-computed, for the MVP, limited to the three mandi districts. Road distance = straight line × 1.3; rate Rs 1.3/40kg/km is an assumption labelled "estimate" until a real freight quote is obtained. The map pin is only used to look up the district. Distance from the exact pin is post-MVP |
| 12 | Replace placeholder rupee figures in the demo script with real app output | ⏳ Action | Team | Do it once models are trained, before rehearsal (Phase 5) |
| 13 | Messaging providers? | ✅ Decided | Team | Meta WhatsApp Cloud API (Twilio sandbox backup); Android SMS gateway for SMS |
| 14 | Which free tiers and limits apply on event day? | ⏳ Action | Team | Check Gemini, WhatsApp Cloud API and Render limits; register all demo phones in advance (Phase 1) |
| 15 | Which price do we forecast for cotton and rice? | ✅ Decided | Team | Cotton = AMIS "Seed Cotton (Phutti)". Rice = AMIS "Rice (IRRI)" and "Rice Basmati Super (New)", which look like milled-rice prices; costs are converted from paddy with a 0.65 milling yield (assumption, to confirm) |
| 16 | "What to grow" needs the price at harvest, 4–6 months away, but the 4-week model can't see that far | ✅ Decided (revised in v0.2.0) | Team | Use a seasonal-ratio estimate, not a trained model: today's price × the median historical ratio of harvest-month to current-month price, with the min–max across years as the range and risk badge. About 11 years of history gives too few harvest observations per crop for a reliable 4–6 month XGBoost model, and wheat policy changed in 2024 and 2025 |
| 17 | Urdu labels for the signals | ✅ Decided | Team | Only two signals: SELL = بیچ دیں, WAIT = رکیں |
| 18 | Storage cost or a HOLD option? | ✅ Decided (revised in v0.2.0) | Team | No HOLD signal and no storage cost. The rupee impact does subtract the interest cost of waiting (16.5% per year = policy rate 11.5% + 5%, the method used in the official cost tables; about 1.4% per month). It is one line in config and answers "can farmers afford to wait?" |
| 19 | One price model for all four crop options, or one per crop/variety? | ✅ Decided | Team | One model, with crop and variety as features. Report error pooled and per crop for NFR-01, not per crop × mandi |
| 20 | Sowing-window advice (old UC-06)? | ✅ Decided (v0.2.0) | Team | Dropped. Sowing dates are set by agronomy and shifting them changes yield (conflicts with NS-04). UC-06 now advises the best selling window within the harvest season |
| 21 | Is the "15–30% income loss" figure sourced? | ⏳ Action | Team | No source in our data. Cite one or remove it from the pitch before Phase 5 |
| 22 | AMIS terms of use and README acknowledgements | ⏳ Action | Data owner | Confirm AMIS terms; add AMIS, Open-Meteo, API cost tables and news sources to the README acknowledgements (repo `docs/PLAN.md` 6.4) |

---

## 18. 📝 Glossary

| Term | Definition |
|------|------------|
| Mandi | Wholesale agricultural market where farmers sell to traders |
| Arhti | Commission agent / middleman at the mandi |
| Maund | Unit of weight, 40 kg. The app shows prices in Rs per 40 kg; AMIS stores Rs per 100 kg (× 0.4 to convert) |
| Rabi / Kharif | Winter (sown Oct–Dec) and summer (sown Apr–Jul) crop seasons |
| Super Basmati / IRRI | Rice varieties. Super Basmati is premium aromatic rice; IRRI (IRRI-6/9) is coarse rice with lower prices |
| Support price | Government-announced minimum price for a crop. In scope, only wheat has one |
| SELL (بیچ دیں) | Price is not expected to rise at least 5% in 4 weeks: sell now |
| WAIT (رکیں) | Price expected to rise 5% or more in 4 weeks: wait and sell later; the rupee gain is shown after interest |
| Harvest-price estimate | Today's price × the historical harvest-month / current-month price ratio, used to rank which crop to grow |
| Interest cost of waiting | Today's value of the harvest × 16.5% per year for the waiting period |
| Arhti commission | The farmer's own commission paid to the commission agent, entered by the farmer; no default |
| AMIS | Punjab Agricultural Marketing Information Service, source of the daily mandi prices (Rs per 100 kg) |
| Net price | Mandi price minus estimated transport cost from the farmer's district |
| Fair price range | Price range a farmer should ask for, based on the forecast range |
| SHAP | Method that shows how much each factor pushed a prediction up or down |
| MAPE | Mean absolute percentage error; lower is better |
| Naive baseline | Predicting that the price in 4 weeks equals today's price |
| Quantile regression | Model that predicts a low and high bound (10th and 90th percentile) to give a range |
| Volatility | Expected size of price swings: STABLE (<5%), MODERATE (5–15%), VOLATILE (>15%) |
| Pre-processed data | Data cleaned and prepared offline by the team, read-only at runtime |
| Template fallback | Pre-written reply used when the LLM is unavailable |

---

*Last updated: 2026-10-09 | Version: 0.2.0 (revised against the scraped AMIS data; v0.1.0 kept as `FarmSight_Design_Blueprint.v0.1.0.backup.md`) | Status: 🟡 In Review*

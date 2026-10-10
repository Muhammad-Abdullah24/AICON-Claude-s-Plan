# FarmSight UI specification for Figma

Copy the prompt below into Figma AI / Figma Make to generate a polished, production-ready responsive interface.

---

```text
Design a polished, production-ready responsive web app UI for “FarmSight,” an Urdu-first agricultural market decision assistant for farmers in South Punjab, Pakistan.

Core product positioning:
FarmSight does not claim to predict the future or replace mandis, arthis, buyers, transport, or storage. Its primary job is to help a farmer check a buyer’s offer before selling.

Primary user moment:
A buyer offers a farmer a price for their crop. The farmer needs a quick, independent reference before accepting, negotiating, travelling to another mandi, or deciding that transport is not worth it.

Primary action:
“Check a buyer offer”

Design for both:
1. Mobile-first layout: 360–430 px wide Android phone.
2. Desktop layout: 1440 px wide web app.

Language and direction:
- Urdu is the default language and the entire primary UI must be RTL.
- Include an English language toggle, but design Urdu as the first-class experience.
- Use an elegant, highly legible Urdu font such as Noto Nastaliq Urdu or Noto Sans Arabic; use IBM Plex Sans or Inter for numbers and English.
- Prices, quantities, dates, and percentages should use tabular, highly readable numerals.
- Avoid tiny text. The target users may have limited digital literacy or use older phones.

Visual character:
- Calm, practical, trustworthy, rural-modern—not “AI sci-fi.”
- Avoid stock farmer photography, neon gradients, blockchain imagery, excessive charts, and generic chatbot visuals.
- Use warm agricultural colors:
  - deep ink/navy for text and navigation;
  - paper/cream background;
  - field green for positive / usable next step;
  - wheat/gold for caution;
  - muted madder/red only for risk or low-quality reference data;
  - slate gray for secondary information.
- Use generous spacing, rounded cards, strong contrast, large tap targets, and simple contextual icons.
- Use subtle motifs only: crop rows, grain, market tag, weighing scale, truck, phone, mandi marker.

Information architecture:
- Home / Offer Check
- Compare Mandis
- Market Outlook
- Why / Data Details
- WhatsApp / SMS Access
- Profile and Alert Settings

Most important constraint:
Never call any price a “fair price,” “true price,” or “guaranteed price.”
Use “Reference mandi price” and “Recent reported reference range.”
Always show source, date, freshness, and limitations.

────────────────────────────────────
SCREEN 1 — MOBILE HOME / OFFER CHECK
────────────────────────────────────

Create the main mobile screen with this hierarchy:

1. Top header
- FarmSight wordmark in Urdu and small English label.
- Language toggle: اردو / EN.
- Small profile/avatar icon.
- No clutter.

2. Hero
- Headline in Urdu equivalent to:
  “Buyer offer received? Check it before you sell.”
- One-line supporting text:
  “Compare it with recent mandi reference data and estimated alternatives.”
- Small trust line:
  “AMIS mandi data · Urdu · WhatsApp and SMS”

3. Primary Offer Check card
This is the largest element on the page.

Inputs:
- Crop selector chips: Wheat / Cotton / IRRI / Super Basmati
- Mandi selector chips: Bahawalpur / Vehari / Rahim Yar Khan
- Quantity input: “How many maund?”
- Buyer offer input: “What did the buyer offer per maund?”; large numeric input prefixed by “Rs”

Primary CTA:
- Large green button: “Check my offer”

Use clear labels, not placeholders only.

4. Example helper
- Small clickable example: “Example: Wheat · Bahawalpur · 100 maund · Rs 3,514”

5. Secondary Market Outlook card
This should be visually quieter than Offer Check.
- Heading: “Market outlook”
- Current reference price
- Market direction signal, if available
- Clear note: “This is context, not a guaranteed future price.”
- Link: “See details”

6. Bottom navigation
Four clear items: Offer Check, Compare, Outlook, Profile.

────────────────────────────────────
SCREEN 2 — MOBILE OFFER RESULT
────────────────────────────────────

Design the result for an offer that is materially below a current reference, but do not use alarming or accusatory wording.

Top:
- Back button
- Heading: “Your offer check”

Result status card:
- Use amber/gold, not red.
- Label: “Below recent reported reference”
- Offer: “Buyer offer: Rs 3,514 / maund”
- Reference: “Reported mandi reference: Rs 3,820 / maund”
- Source/date: “AMIS Punjab · reported 9 Oct 2026”

Impact card:
- Large number: “Rs 30,600 difference on 100 maund”
- Supporting copy: “Compared with the latest reported reference price.”

Reference range section:
- Simple horizontal visual range, not a complicated chart.
- Low / reference / high markers.
- “Reported price days: 12 of last 14 days”
- “Reference data strength: Limited”
- Use an amber info banner: “AMIS reported the same price on all available days. Use this as an independent reference, not a guaranteed sale price.”

Actions:
- Primary green CTA: “Compare nearby mandis after transport”
- Secondary outline CTA: “Show why this result is limited”
- Optional subtle action: “Set a price watch”

“What FarmSight cannot know” expandable section:
- Crop quality and moisture
- Buyer terms
- Truck availability
- Tied credit or cash pressure
- Actual buyer availability

Bottom:
- WhatsApp/share style action: “Send this summary to WhatsApp”
- Do not design social-media-style sharing. Keep it practical.

────────────────────────────────────
SCREEN 3 — MOBILE DATA-LIMITED RESULT
────────────────────────────────────

Create a second state for stale/frozen/few-day data.

Use a clear amber or muted red warning state:
- Heading: “Reference data is limited”
- Show the available reference price and date.
- Explain why: “Last reported price is 85 days old” or “Only 2 reported price days are available”.
- Do not show a strong “accept / reject / negotiate” recommendation.
- Offer safe actions: “Try another mandi”, “Check latest available date”, “Ask the mandi directly”.
- Make this screen feel honest and useful, not broken.

────────────────────────────────────
SCREEN 4 — MOBILE COMPARE MANDIS
────────────────────────────────────

Design a simple ranked list of nearby mandis.

Each mandi card includes:
- Mandi name
- Reported reference price
- Transport cost estimate
- Net estimated value
- Difference for farmer’s quantity
- Price date
- Data freshness badge

Best net option:
- Green “Best estimated net value” label only if data is fresh enough.
- If stale/frozen, show “Data limited” instead of ranking it as best.

At the bottom:
- Assumption note: “Transport is estimated. Confirm buyer availability and truck cost before travelling.”

────────────────────────────────────
SCREEN 5 — WHATSAPP / SMS ACCESS
────────────────────────────────────

Create a simple informational screen or modal showing the no-app workflow.

Show a phone mockup with WhatsApp:
- User types `0`
- FarmSight replies with numbered menu:
  1. Check buyer offer
  2. Compare mandis
  3. Why this advice?
  4. Start alerts
  5. Stop alerts

Show SMS below using Roman Urdu:
“FarmSight: Gandum BWP. Buyer offer Rs3514/man. Reference Rs3820/man. 100 man par farq Rs30600. Reply 2 for mandi compare.”

Include:
- “Works through text menus”
- “No smartphone app required for SMS”
- “Voice notes are not yet available” as a muted honest note.

────────────────────────────────────
SCREEN 6 — DESKTOP HOME
────────────────────────────────────

Desktop must not simply stretch mobile.

Layout:
- Left persistent sidebar: logo, navigation, language switch, profile.
- Main content area max-width around 1200 px.
- Two-column hero content.

Left/main column:
- Offer Check form card, large and prominent.
- Recent offer check result or empty state beneath it.

Right column:
- “Today’s market reference” summary.
- Data freshness card.
- “How FarmSight helps” mini explainer:
  1. Enter buyer offer
  2. Compare reported reference
  3. See transport-adjusted alternatives
  4. Decide with your own constraints

Below:
- Market Outlook card, visually secondary.
- Small recent activity/alert card only if relevant.

────────────────────────────────────
DESIGN SYSTEM / COMPONENTS
────────────────────────────────────

Create reusable components and variants for:
- Header
- Sidebar
- Bottom navigation
- Input field
- Numeric rupee input
- Crop chip selector
- Mandi chip selector
- Primary / secondary / text button
- Status badge: Fresh / Limited / Stale / Frozen / Estimate
- Offer Result card: Below reference / Within reference / Above reference / Data limited
- Mandi comparison row
- Limitation accordion
- Data source label
- Alert settings toggle
- WhatsApp/SMS message bubble
- Empty state
- Error state
- Loading/skeleton state

Accessibility:
- Minimum 44 px tap targets on mobile.
- High contrast.
- Do not rely on color alone; every status needs an icon and label.
- Preserve meaning in RTL layout.
- Make the primary CTA visually unmistakable.
- Use plain Urdu with minimal technical jargon.
- Ensure all fields, chips, buttons, and results have clear labels.

Deliver:
- Mobile and desktop designs for all six screens.
- Component library / variants.
- RTL-first Auto Layout structure.
- A small style guide with colors, typography, spacing, and status states.
- A clickable prototype path: Home → Enter offer → Offer result → Compare mandis → WhatsApp/SMS access.
```

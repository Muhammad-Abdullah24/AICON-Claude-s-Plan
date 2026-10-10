# Urdu review sheet (one-time native-speaker check)

**For the reviewer:** You do not need to open the code. Read the Urdu below, screen by screen; the English in
*italics* is what each line is supposed to mean. Mark anything that (a) is wrong grammar, (b) a farmer in South
Punjab with little schooling would not instantly understand, or (c) sounds unnatural. Write your fix next to it, or
send voice notes — whatever is fastest. Values in `{{…}}` are filled in by the app (price, date, %, etc.).

**Audience:** wheat/cotton/rice farmers around Bahawalpur, Vehari, Rahim Yar Khan. Plain, spoken Urdu beats formal
written Urdu. The app deliberately uses **ریٹ** (not قیمت) everywhere a farmer sees a market price.

---

## Priority items I already suspect (please decide these first)

1. **"ریٹ" vs "قیمت".** The screens say **ریٹ**. The "Why?" reasons (from the model) say **قیمت**
   ("قیمت تقریباً {{rs}} روپے فی من بڑھ سکتی ہے")۔ Should the reasons also say **ریٹ** for consistency? (Both are
   understood; this is a choice, not an error.)
2. **"What to grow" estimate note** uses maths words **ضرب** (multiply) and **منفی** (minus):
   *"اندازہ: آج کا ریٹ ضرب کٹائی تک ریٹ کی عام تبدیلی، منفی سرکاری پیداواری لاگت۔ گارنٹی نہیں۔"*
   Too technical? Suggest a plainer sentence.
3. **History seasonal note:** *"ہر مہینہ سال کے رجحان کا کتنا فیصد (برسوں کا درمیانہ)۔ 100 سے اوپر عام طور پر بیچنے کا بہتر مہینہ ہے۔"*
   Words like **رجحان** and **درمیانہ** (median) — clear enough, or simplify?
4. **"Your harvest" field** (the quantity box) is labelled **"آپ کی فصل"** (= your crop). Should it be
   **"آپ کی پیداوار"** (your produce) or **"کتنی فصل؟"** (how much crop)?

---

## Home / advice screen

- بیچ دیں  *(SELL)*
- رکیں  *(WAIT)*
- آج منڈی میں  *(today at the mandi)*
- {{weeks}} ہفتے بعد (اندازہ)  *(in {{weeks}} weeks (estimate))*
- غالباً {{low}} سے {{high}} کے بیچ  *(likely between {{low}} and {{high}})*
- اگر آپ {{weeks}} ہفتے رکیں، اپنے {{qty}} من پر  *(if you wait {{weeks}} weeks, on your {{qty}} maund)*
- انتظار کا {{interest}} سود نکال کر  *(after subtracting {{interest}} interest for waiting)*
- ہمیں کتنا یقین ہے؟  *(how sure are we?)*  →  کافی یقین / کچھ یقین / یقین نہیں  *(high / medium / low)*
- ریٹ کا اندازہ: آج کا ریٹ، پچھلے 4 ہفتوں کے اتار چڑھاؤ کی حد کے ساتھ۔ ہمارا ماڈل اس سے بہتر ریٹ نہیں بتا سکا، اس لیے یہی سادہ اندازہ دکھاتے ہیں۔
  *(Rate estimate: today's rate, with the range of past 4-week swings. Our model couldn't predict better, so we show this simple estimate.)*
- یہ اندازہ ہے، گارنٹی نہیں۔  *(this is an estimate, not a guarantee)*

### The model's direction line (wheat)
- ہمارا ماڈل: اگلے 4 ہفتوں میں ریٹ بڑھنے کا امکان ہے۔  *(our model: the rate is likely to rise in the next 4 weeks)*
- ہمارا ماڈل: اگلے 4 ہفتوں میں ریٹ گرنے کا امکان ہے۔  *(…likely to fall…)*
- (2025 کی بڑی تبدیلیوں میں سے {{pct}}% اس نے درست بتائیں۔ یہ قیمت کا اندازہ نہیں۔)
  *(it called {{pct}}% of 2025's big moves right. This is not a price estimate.)*

### Data labels (under every price)
- اصلی ڈیٹا  *(real data)*  /  مصنوعی ڈیٹا  *(synthetic data)*  /  یہ نمبر اصلی نہیں، صرف جانچ کے لیے ہیں  *(these numbers aren't real, only for testing)*
- ذریعہ: AMIS پنجاب کے منڈی ریٹ  *(source: AMIS Punjab mandi rates)*
- فی 40 کلو (ایک من)  *(per 40 kg (one maund))*
- {{date}} تک کے ریٹ  *(rates as of {{date}})*
- پرانا ریٹ: آخری بار {{date}} کو آیا  *(old rate: last came on {{date}})*
- AMIS پر {{date}} سے ایک ہی ریٹ ہے، اس لیے احتیاط کریں  *(same rate on AMIS since {{date}}, so be careful)*
- اس ہفتے کا موسم: زیادہ سے زیادہ {{tmax}}° سینٹی گریڈ، بارش {{rain}} ملی میٹر  *(this week's weather: max {{tmax}}°C, rain {{rain}} mm)*
- (محفوظ ریڈنگ)  *(cached reading)*

## Navigation / tabs
مشورہ *(advice)* · کیوں *(why)* · منڈیاں *(mandis)* · کیا اگائیں *(what to grow)* · پرانے ریٹ *(old rates)* · منافع *(profit)* · سوال *(question)* · پروفائل *(profile)*

## Selection bar
- فصل *(crop)* · منڈی *(mandi)* · آپ کی فصل *(your harvest — see priority #4)* · من *(maund)*
- صفر سے زیادہ مقدار لکھیں  *(enter an amount greater than zero)*
- مقدار زیادہ سے زیادہ {{max}} من ہو سکتی ہے  *(amount can be at most {{max}} maund)*

## Why? screen
- یہ مشورہ کیوں  *(why this advice)*
- اندازے کے ماڈل سے وجوہات (SHAP)  *(reasons from the forecast model (SHAP))*
- ڈیٹا سے وجوہات۔ ماڈل تیار ہونے پر ماڈل کی وضاحت ان کی جگہ لے گی۔  *(reasons from data. When the model is ready, its explanation replaces these.)*
- پرانے ریٹ اور 4 ہفتے کی حد  *(old rates and the 4-week range)*
- پچھلا ہفتہ وار ریٹ  *(past weekly rate)*  ·  4 ہفتے بعد کی ممکنہ حد  *(possible range in 4 weeks)*

### The "reason" sentences (model + fallback facts)
- {label} کی وجہ سے قیمت تقریباً {{rs}} روپے فی من بڑھ سکتی ہے۔  *(because of {label}, price may rise ~Rs {{rs}}/maund)*  — see priority #1 (قیمت vs ریٹ)
- {label} کی وجہ سے قیمت تقریباً {{rs}} روپے فی من کم ہو سکتی ہے۔  *(…may fall ~Rs {{rs}}/maund)*
- labels: قیمتوں کے حالیہ رجحان *(recent price trend)* · سال کے اس وقت *(the time of year)* · بوائی یا کٹائی کے موسم *(sowing/harvest season)* · بارش *(rain)* · گرمی اور موسم *(heat and weather)* · اس منڈی میں اس فصل کے عام رجحان *(usual pattern for this crop at this mandi)*
- پچھلے 4 ہفتوں میں ریٹ {{pct}}% بڑھا / گرا  *(rate rose/fell {{pct}}% in the last 4 weeks)*
- پچھلے 4 ہفتوں میں ریٹ تقریباً ایک جیسا رہا  *(rate stayed about the same over the last 4 weeks)*
- اس مہینے ریٹ عام طور پر سال کے رجحان کا {{idx}}% ہوتا ہے  *(this month the rate is usually {{idx}}% of the yearly trend)*
- AMIS پر یہ ریٹ {{date}} سے تبدیل نہیں ہوا، اس لیے اعتماد کم ہے  *(this rate hasn't changed on AMIS since {{date}}, so confidence is low)*
- آخری ریٹ {{date}} کا ہے، اس لیے اعتماد کم ہے  *(the latest rate is from {{date}}, so confidence is low)*
- یہ سادہ اندازہ ہے: ریٹ وہی رہنے کا مان کر، پچھلے برسوں کے اتار چڑھاؤ کی حد  *(this is a simple estimate: assuming the rate stays, with the range of past years' swings)*

## Compare mandis
- کہاں بیچیں: کرایہ نکال کر اصل ریٹ  *(where to sell: real rate after subtracting transport)*
- بہترین *(best)* · اصل ریٹ *(net rate)* · منڈی ریٹ *(mandi rate)* · کرایہ (اندازہ) *(transport (estimate))*
- آپ کی منڈی کے مقابلے میں، {{qty}} من پر  *(compared with your mandi, on {{qty}} maund)*
- ریٹ موجود نہیں  *(no rate available)*  ·  {{date}} کا ریٹ  *(rate of {{date}})*

## What to grow
- کیا اگائیں: کٹائی پر متوقع منافع  *(what to grow: expected profit at harvest)*
- آپ کی زمین *(your land)* · ایکڑ *(acres)*
- آپ کی زمین پر متوقع منافع  *(expected profit on your land)*
- {{amount}} فی ایکڑ  *(per acre)*  ·  (پچھلے برسوں میں: {{low}} سے {{high}})  *(in past years: {{low}} to {{high}})*
- کٹائی پر ریٹ کا اندازہ: {{price}} ({{low}} سے {{high}})  *(harvest rate estimate: …)*
- {{month}} کے منڈی ریٹ {{price}} کی بنیاد پر  *(based on {{month}}'s mandi rate {{price}})*
- ریٹ کا خطرہ *(price risk)*  →  کم / درمیانہ / زیادہ  *(low / medium / high)*
- AMIS کے {{n}} سال کے ریٹ پر مبنی  *(based on {{n}} years of AMIS rates)*
- بیچنے کا بہترین مہینہ: {{month}} (عام طور پر سود نکال کر {{gain}}%)  *(best month to sell: {{month}} (usually {{gain}}% after interest))*
- کٹائی پر ({{month}}) بیچنا بہتر: رکھنے سے عام طور پر سود جتنا فائدہ نہیں ہوتا  *(better to sell at harvest ({{month}}): holding usually doesn't beat the interest)*
- بیچنے کا مہینہ چننے کے لیے کافی برسوں کے ریٹ نہیں  *(not enough years of rates to pick a selling month)*
- بوائی *(sow)* · کٹائی *(harvest)* · بہترین فروخت *(best sale)*
- اس منڈی میں ان کا ریٹ موجود نہیں: {{crops}}  *(no rate for these at this mandi: {{crops}})*
- اندازہ: آج کا ریٹ ضرب کٹائی تک ریٹ کی عام تبدیلی، منفی سرکاری پیداواری لاگت۔ گارنٹی نہیں۔  *(see priority #2)*

## History
- پرانے ریٹ *(old rates)*
- ہفتہ وار ریٹ، پچھلے 12 مہینے  *(weekly rate, last 12 months)*
- مہینے کے حساب سے عام ریٹ  *(usual rate by month)*
- ہر مہینہ سال کے رجحان کا کتنا فیصد (برسوں کا درمیانہ)۔ 100 سے اوپر عام طور پر بیچنے کا بہتر مہینہ ہے۔  *(see priority #3)*

## Profit (margin)
- ریٹ میں سے آپ کے پاس کتنا بچتا ہے  *(how much of the rate is left with you)*
- فی من قیمت *(price per maund)* · آپ کا آڑھتی کمیشن *(your arhti commission)*
- پیداواری لاگت *(production cost)* · آڑھتی کمیشن *(arhti commission)* · آپ کے پاس بچتا ہے *(what's left with you)*
- سرکاری امدادی قیمت: {{price}} ({{year}}، {{status}})  *(government support price: …)*
  → سرکار نے اس ریٹ پر خریدا  *(govt bought at this rate)*  /  اعلان ہوا، خریداری نہیں ہوئی  *(announced, no purchase happened)*
- پیداواری لاگت: پنجاب کے سرکاری جدول، مہنگائی کے حساب سے ({{confidence}})۔  *(production cost: Punjab govt tables, inflation-adjusted ({{confidence}}))*

## Ask (chat)
- اپنی فصل کے بارے میں پوچھیں  *(ask about your crop)*
- مثلاً: کیا اگلے مہینے گندم کا ریٹ بڑھے گا؟  *(e.g. will wheat's rate rise next month?)*
- پوچھیں *(ask)* · سوچ رہے ہیں… *(thinking…)*
- یہ جواب ہمارے سانچے سے ہے، AI سے نہیں۔  *(this answer is from our template, not AI)*
- سوال {{max}} حروف سے کم رکھیں  *(keep the question under {{max}} characters)*

## Profile
- آپ کا پروفائل *(your profile)*
- آپ مہمان کے طور پر فارم سائٹ استعمال کر رہے ہیں۔  *(you're using FarmSight as a guest)*
- {{name}} کے طور پر داخل  *(logged in as {{name}})*
- اپنے فون نمبر سے داخل ہوں *(log in with your phone number)* · فون نمبر *(phone number)* · داخل ہوں *(log in)*
- ڈیمو کسان: +920000000001  *(demo farmer)*
- نئے ہیں؟ پروفائل بنائیں  *(new? create a profile)*
- نام *(name)* · آپ کا ضلع *(your district)* · زمین (ایکڑ) *(land (acres))* · آڑھتی کمیشن (%) *(arhti commission (%))*
- مجھے واٹس ایپ پر الرٹ بھیجیں  *(send me alerts on WhatsApp)*
- محفوظ کریں *(save)* · محفوظ ہو گیا *(saved)* · پروفائل بنائیں *(create profile)* · باہر نکلیں *(log out)*
- اس نمبر کا پروفائل نہیں۔ نیچے نیا بنائیں۔  *(no profile for this number. create a new one below.)*
- اس نمبر کا پروفائل پہلے سے ہے۔ داخل ہوں۔  *(a profile for this number already exists. log in.)*

## Status / errors
- لوڈ ہو رہا ہے…  *(loading…)*
- سرور سے رابطہ نہیں ہو سکا۔  *(couldn't reach the server)*  ·  انٹرنیٹ دیکھیں اور دوبارہ کوشش کریں۔  *(check internet and try again)*
- دوبارہ کوشش *(try again)*
- اس منڈی میں اس فصل کا ریٹ موجود نہیں۔  *(no rate for this crop at this mandi)*
- آپ کی لکھی ہوئی کچھ معلومات درست نہیں۔ دوبارہ دیکھیں۔  *(some info you entered isn't valid. check again.)*
- {{date}} کا منظر: ریٹ اور مشورہ ویسے ہی جیسے اس دن ایپ دکھاتی۔ موسم اور سوال جواب آج کے ہیں۔  *(view of {{date}}: rates and advice as the app would show that day. weather and Q&A are today's.)*  ·  آج پر واپس  *(back to today)*

---

## WhatsApp bot (same wording, farmers see this over chat)

- السلام علیکم! اپنی فصل، منڈی اور مقدار لکھیں۔ مثال: گندم بہاولپور 100 من  *(greeting + how to ask)*
- فصلیں: گندم، کپاس، چاول (سپر باسمتی یا اری)  *(crops list)*
- منڈیاں: بہاولپور، وہاڑی، رحیم یار خان  *(mandi list)*
- کون سی فصل؟ / کون سے چاول؟ سپر باسمتی یا اری / کون سی منڈی؟  *(which crop / which rice / which mandi)*
- معاف کیجیے، بات سمجھ نہیں آئی۔  *(sorry, didn't understand)*
- پہلے فصل اور منڈی بتائیں، مثلاً: گندم بہاولپور 100 من  *(tell crop and mandi first)*
- یہ سروس ابھی تیار ہو رہی ہے۔ تھوڑی دیر بعد دوبارہ کوشش کریں۔  *(service is getting ready, try again shortly)*
- الرٹس بند کر دیے گئے۔ دوبارہ شروع کرنے کے لیے 'شروع' لکھیں۔  *(alerts turned off. write 'shuru' to restart.)*
- الرٹس دوبارہ شروع کر دیے گئے۔  *(alerts restarted)*
- وائس نوٹ کی سہولت جلد آ رہی ہے۔ ابھی لکھ کر بھیجیں…  *(voice notes coming soon, type for now)*
- buttons: کیوں؟ / منڈیاں / الرٹ بند  *(buttons: why / mandis / stop alerts)*

### Advice reply format
- آج: {{price}} فی من (AMIS، {{date}} تک)  *(today: {{price}}/maund (AMIS, as of {{date}}))*
- 4 ہفتے بعد اندازہ: {{price}} ({{low}} سے {{high}})  *(estimate in 4 weeks: …)*
- {{qty}} من پر رکنے کا فرق: {{impact}} ({{interest}} سود نکال کر)  *(difference of waiting on {{qty}} maund: … (after {{interest}} interest))*
- اعتماد: زیادہ / درمیانہ / کم  *(confidence: high / medium / low)*
- (مقدار نہیں بتائی، اس لیے {{qty}} من مان کر حساب کیا)  *(no amount given, so calculated assuming {{qty}} maund)*
- کرایہ اندازہ ہے۔  *(transport is an estimate)*

### Alert message
- 🔔 فارم سائٹ الرٹ  *(FarmSight alert)*
- مشورہ بدل گیا ہے  *(the advice has changed)*
- ریٹ 4 ہفتوں میں {{pct}}% بڑھا / گرا، جو عام اتار چڑھاؤ سے زیادہ ہے  *(rate rose/fell {{pct}}% in 4 weeks, more than usual swings)*
- الرٹ بند کرنے کے لیے 'بند' لکھیں۔  *(write 'band' to stop alerts)*

---

*When you have the reviewer's marks, hand them back (typed, or photos of the marked-up sheet) and the fixes get
applied to `frontend/src/locales/ur.json`, `backend/app/channels/reply.py`, `backend/app/alerts.py`,
`backend/app/services.py` and `ml/explain/reasons.py` — keeping the English and Urdu locale keys in sync (a test
enforces that).*

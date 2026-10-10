"""News feed settings (task H2). Constants only, no environment variables (docs/PIVOT.md rule 5).

The feed is Google News RSS, Pakistan English edition, last 7 days. The Urdu RSS is mostly YouTube spam, so we
read the English feed and translate the one-line summary with Gemini (through backend/app/chat/llm.py).
"""

from __future__ import annotations

# q already carries "when:7d"; hl/gl/ceid pin it to the Pakistan English edition.
RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-PK&gl=PK&ceid=PK:en"

# One query per crop, plus a general one (crop_option=None). Lowercase API ids (backend/app/ids.py).
QUERIES: dict[str | None, str] = {
    None: "Pakistan wheat OR cotton OR basmati support price OR mandi OR procurement when:7d",
    "wheat": "Pakistan wheat support price OR procurement OR flour price when:7d",
    "cotton": "Pakistan cotton phutti price OR mandi OR crop when:7d",
    "irri": "Pakistan rice price OR export OR paddy mandi when:7d",
    "super_basmati": "Pakistan basmati rice price OR export when:7d",
}

CROP_IDS = ("wheat", "cotton", "irri", "super_basmati")
# Accept the data names too, so a caller that passes "Wheat"/"SuperBasmati" still works.
DATA_TO_ID = {"Wheat": "wheat", "Cotton": "cotton", "IRRI": "irri", "SuperBasmati": "super_basmati"}

# A plain browser header; Google News RSS refuses an empty or bot-looking agent.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) FarmSight/1.0"
FETCH_TIMEOUT_S = 12
CACHE_TTL_HOURS = 6
MAX_ITEMS = 6

TAGS = ("SUPPORT_PRICE", "PROCUREMENT", "CAP_OR_BAN", "IMPORT", "PRICE_REPORT", "OTHER")

# Keyword rules for the fallback tagger (checked in this order; first hit wins). Lowercased matching.
TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "SUPPORT_PRICE": ("support price", "minimum price", "indicative price", "msp"),
    "CAP_OR_BAN": ("ban", "cap ", "capped", "crime", "criminal", "movement", "deregulat", "restrict"),
    "PROCUREMENT": ("procure", "procurement", "aggregator", "wheat target", "kissan card"),
    "IMPORT": ("import", "export"),
    "PRICE_REPORT": ("price", "rate", "per maund", "per 40", "mandi", "surge", "fall", "rise", "crore"),
}

# Which word in a headline means which crop (lowercase API id).
CROP_KEYWORDS: dict[str, str] = {
    "wheat": "wheat", "gandum": "wheat", "flour": "wheat", "atta": "wheat",
    "cotton": "cotton", "phutti": "cotton", "kapas": "cotton", "lint": "cotton",
    "basmati": "super_basmati",
    "rice": "irri", "paddy": "irri", "irri": "irri",
}

# A reported per-40kg (per-maund) price outside this band is almost certainly not a mandi rate, so it is dropped.
PRICE_MIN_RS_PER_40KG = 1500
PRICE_MAX_RS_PER_40KG = 20000

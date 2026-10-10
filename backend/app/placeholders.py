"""Placeholder answers for the pivot endpoints (docs/PIVOT.md task U1), until the real ones land.

They give the front end (U5-U7) and WhatsApp (H6) the exact response shape to build against. Every value is
labelled `data_source: "placeholder"`, `is_synthetic: True`, so the app shows its "synthetic data" tape and nobody
mistakes these numbers for advice. Replaced by the wait engine (U3/U4) and Hamza's news package (H2/H3).
Names are the service layer's data names ("Wheat", "BahawalPur"), like the rest of services.py.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

PLACEHOLDER = {"data_source": "placeholder", "is_synthetic": True}
DEFAULT_RATE_PCT = {"own": 0.0, "bank": 16.5, "arhti": 66.0}
LOSS_PCT = {"godown": 3.5, "bags": 10.0}
_SEASONS = [(2022, 2292, 3120), (2023, 4038, 4582), (2024, 2847, 2660), (2025, 2370, 3083), (2026, 3450, 3695)]


def wait_plan(crop_option: str, mandi: str, quantity_maund: float, cash_need_rs: float, wait_months: int,
              money: str, annual_rate: float | None, storage: str, offer: float | None) -> dict:
    rate = DEFAULT_RATE_PCT[money] if annual_rate is None else annual_rate
    loss = LOSS_PCT[storage]
    sell_net = 3655.0
    sell_now = min(quantity_maund, -(-cash_need_rs // sell_net)) if cash_need_rs else 0.0
    exits = [{"kind": "SELL_NOW", "mandi": mandi, "per_maund": sell_net, "total_rs": round(sell_net * quantity_maund)}]
    if offer is not None:
        exits.append({"kind": "ARHTI_OFFER", "per_maund": offer, "total_rs": round(offer * quantity_maund)})
    seasons = [{"year": y, "start_price": s, "later_price": later,
                "net_gain_per_maund": round(later * (1 - loss / 100) - s * (1 + rate / 100 * wait_months / 12)),
                "paid": later * (1 - loss / 100) > s * (1 + rate / 100 * wait_months / 12)}
               for y, s, later in _SEASONS]
    wins = sum(s["paid"] for s in seasons)
    exits.append({"kind": "HOLD", "per_maund": sell_net + 65, "total_rs": round((sell_net + 65) * quantity_maund),
                  "worst_total_rs": round((sell_net - 400) * quantity_maund),
                  "cost_rs": round(sell_net * quantity_maund * (rate / 100 * wait_months / 12 + loss / 100))})
    return {
        **PLACEHOLDER, "unit": "40kg", "quantity_maund": quantity_maund, "cash_need_rs": cash_need_rs,
        "wait_months": wait_months, "money": money, "annual_rate_pct": rate, "storage": storage, "loss_pct": loss,
        "verdict": "SPLIT" if 0 < sell_now < quantity_maund else ("SELL_ALL" if sell_now else "HOLD_ALL"),
        "sell_now_maund": sell_now, "hold_maund": quantity_maund - sell_now, "exits": exits,
        "history": {"start_month": 5, "later_month": 9, "annual_rate_pct": rate, "loss_pct": loss,
                    "n": len(seasons), "wins": wins, "median_net_per_maund": 65, "worst_p10_net_per_maund": -400,
                    "seasons": seasons},
        "confidence": "LOW", "warnings": ["POLICY_UNCERTAIN"], "news_check": None,
        "prices_as_of": date(2026, 10, 5), "is_stale": False,
    }


def news() -> dict:
    today = date.today()
    return {
        **PLACEHOLDER, "is_snapshot": True, "tagged_by": "rules",
        "fetched_at": datetime.now(UTC), "price_check": None,
        "items": [{"title": "Placeholder headline: wheat support price for 2026-27 still undecided",
                   "url": "https://example.com/placeholder", "source": "Placeholder", "published": today,
                   "tag": "SUPPORT_PRICE", "crop": "Wheat",
                   "summary_ur": "نمونہ خبر: گندم کی امدادی قیمت ابھی طے نہیں ہوئی",
                   "summary_en": "Sample item: the wheat support price is not decided yet",
                   "price_rs_per_40kg": None},
                  {"title": "Placeholder headline: open-market wheat price rises",
                   "url": "https://example.com/placeholder-2", "source": "Placeholder",
                   "published": today - timedelta(days=1), "tag": "PRICE_REPORT", "crop": "Wheat",
                   "summary_ur": "نمونہ خبر: کھلی منڈی میں گندم کا ریٹ بڑھ گیا",
                   "summary_en": "Sample item: open-market wheat price rises",
                   "price_rs_per_40kg": 5300.0}],
    }


def policy_events(as_of: date | None) -> list[dict]:
    events = [{"date": date(2026, 4, 28), "tag": "CAP_OR_BAN",
               "text_ur": "نمونہ: 3,500 سے زیادہ ریٹ پر گندم بیچنا جرم قرار",
               "text_en": "Sample: selling wheat above Rs 3,500 declared a crime",
               "source": "Placeholder", "url": "https://example.com/placeholder-policy"}]
    return [e for e in events if as_of is None or e["date"] <= as_of]

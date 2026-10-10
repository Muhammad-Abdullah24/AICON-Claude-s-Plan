"""Tests for the news/policy feed (H2/H3). No network: a saved RSS file stands in for Google News."""

import datetime as dt
from pathlib import Path

import pytest

from backend.app.news import cache, fetch, service, tag

SAMPLE = (Path(__file__).parent / "testdata" / "sample_feed.xml").read_bytes()


def fake_opener(_url: str) -> bytes:
    return SAMPLE


# ---------------------------------------------------------------- fetch

def test_fetch_parses_items_and_strips_the_source_from_the_title():
    items = fetch.fetch_rss("wheat", opener=fake_opener)
    assert len(items) == 4
    first = items[0]   # newest first: 07 Oct
    assert first["title"] == "Open market wheat surges to Rs 5,300 as flour prices rise"
    assert first["source"] == "ARY News" and first["published"] == "2026-10-07"
    assert first["url"].startswith("https://news.google.com/")
    assert [i["published"] for i in items] == sorted((i["published"] for i in items), reverse=True)


# ---------------------------------------------------------------- tagging rules + price

@pytest.mark.parametrize("title, tag_, crop", [
    ("Punjab sets wheat support price at Rs 3,500 per 40 kg", "SUPPORT_PRICE", "wheat"),
    ("Punjab bans wheat movement, declares overpricing a crime", "CAP_OR_BAN", "wheat"),
    ("Government to import 1 million tonnes of wheat", "IMPORT", "wheat"),
    ("Cotton phutti arrivals pick up in mandis", "PRICE_REPORT", "cotton"),
    ("Basmati exports climb this season", "IMPORT", "super_basmati"),
    ("Monsoon update for the week", "OTHER", None),
])
def test_tag_by_rules(title, tag_, crop):
    assert tag.tag_by_rules(title) == (tag_, crop)


def test_extract_price_only_takes_a_plausible_per_maund_figure():
    assert tag.extract_price("wheat support price at Rs 3,500 per 40 kg") == 3500
    assert tag.extract_price("open market reaches Rs 5,300 a maund") == 5300
    assert tag.extract_price("prefers Rs 4,200 over Rs 5,000 per 40 kg") == 5000   # the one by the unit wins
    assert tag.extract_price("inflation rose 11.97pc") is None
    assert tag.extract_price("fine worth Rs 650 imposed") is None                  # below the mandi-price floor


def test_rules_tagging_a_whole_batch():
    items = fetch.fetch_rss("wheat", opener=fake_opener)
    tagged = tag.tag_with_rules(items)
    support = next(t for t in tagged if "support price" in t["title"].lower())
    assert support["tag"] == "SUPPORT_PRICE" and support["crop"] == "wheat" and support["price_rs_per_40kg"] == 3500
    assert all({"tag", "crop", "summary_ur", "summary_en", "price_rs_per_40kg"} <= t.keys() for t in tagged)


# ---------------------------------------------------------------- tag_items fallback (no real LLM)

def test_tag_items_falls_back_to_rules_when_the_llm_is_down():
    class Boom:
        def generate(self, system, user):
            raise RuntimeError("no key")

    items = fetch.fetch_rss("wheat", opener=fake_opener)
    tagged, tagged_by = tag.tag_items(items, lambda: Boom())
    assert tagged_by == "rules" and len(tagged) == len(items)


def test_tag_items_trusts_the_llm_only_for_a_price_in_the_text():
    import json as _json

    class Fake:
        def generate(self, system, user):
            # One object per headline in the batch; claims a price that is NOT in the text.
            n = user.count("\n") + 1
            return _json.dumps([{"tag": "PRICE_REPORT", "crop": "wheat", "summary_en": "x",
                                 "summary_ur": "ایکس", "price_rs_per_40kg": 9999} for _ in range(n)])

    items = [{"title": "Wheat support price at Rs 3,500 per 40 kg", "url": "u", "source": "s",
              "published": "2026-10-05"}]
    tagged, tagged_by = tag.tag_items(items, lambda: Fake())
    assert tagged_by == "llm"
    assert tagged[0]["price_rs_per_40kg"] == 3500   # 9999 wasn't in the headline, so it was dropped for the real one


# ---------------------------------------------------------------- service (cache + snapshot)

@pytest.fixture
def fresh_db():
    from backend.app import db
    db.reset()
    cache._READY = False
    yield
    db.reset()
    cache._READY = False


def test_get_news_caches_and_does_not_refetch_within_the_ttl(fresh_db, monkeypatch):
    calls = {"n": 0}

    def counting_opener(url):
        calls["n"] += 1
        return SAMPLE

    monkeypatch.setattr(fetch, "_default_opener", counting_opener)
    monkeypatch.setattr(service.tag, "tag_items", lambda items, _get: (service.tag.tag_with_rules(items), "rules"))

    a = service.get_news("wheat")
    b = service.get_news("wheat")
    assert calls["n"] == 1                        # second call served from cache
    assert a["is_snapshot"] is False and b["is_snapshot"] is False
    assert a["items"] and a["tagged_by"] == "rules"


def test_get_news_serves_the_snapshot_when_everything_fails(fresh_db, monkeypatch):
    def boom(url):
        raise OSError("network down")

    monkeypatch.setattr(fetch, "_default_opener", boom)
    out = service.get_news("wheat")
    assert out["is_snapshot"] is True
    assert isinstance(out["items"], list)         # the committed snapshot carries real items


def test_get_news_accepts_the_data_name_and_limits(fresh_db, monkeypatch):
    monkeypatch.setattr(fetch, "_default_opener", fake_opener)
    monkeypatch.setattr(service.tag, "tag_items", lambda items, _get: (service.tag.tag_with_rules(items), "rules"))
    out = service.get_news("Wheat", limit=2)      # data name, not the API id
    assert len(out["items"]) == 2


# ---------------------------------------------------------------- policy events (H3)

def test_policy_events_are_newest_first_and_sourced():
    events = service.get_policy_events("wheat")
    assert len(events) >= 6
    assert events == sorted(events, key=lambda e: e["date"], reverse=True)
    for e in events:
        assert e["tag"] in {"SUPPORT_PRICE", "PROCUREMENT", "CAP_OR_BAN", "IMPORT"}
        assert e["source"] and e["url"].startswith("http") and e["text_ur"] and e["text_en"]


def test_policy_events_respect_as_of_for_replay():
    early = service.get_policy_events("wheat", as_of=dt.date(2026, 5, 1))
    assert all(e["date"] <= "2026-05-01" for e in early)
    assert any(e["date"] == "2026-04-28" for e in early)       # the April cap is known
    assert not any(e["date"] == "2026-07-24" for e in early)   # the July import is not yet


def test_no_wheat_policy_events_leak_into_cotton():
    assert service.get_policy_events("cotton") == []

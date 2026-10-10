"""Tests for the news/policy feed (H2/H3). No network: a saved RSS file stands in for Google News."""

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


def test_extract_price_takes_a_crop_per_maund_figure_only():
    assert tag.extract_price("wheat support price at Rs 3,500 per 40 kg") == 3500
    assert tag.extract_price("open market wheat reaches Rs 5,300 per maund") == 5300
    assert tag.extract_price("gandum rate Rs 5,000 per 40 kg at the mandi") == 5000
    assert tag.extract_price("inflation rose 11.97pc") is None
    assert tag.extract_price("fine worth Rs 650 per 40 kg") is None                # below the mandi-price floor


def test_a_flour_price_is_not_read_as_a_wheat_price():
    # N1 (demo-critical): the flour headline that raised a false NEWS_PRICE_CONFLICT. No grain word -> no crop price.
    assert tag.extract_price("Flour price hits Rs 5,200 per 40 kg across Punjab") is None
    assert tag.extract_price("Flour Rs 5,200 per 40 kg as wheat cost surges") is None   # flour is the price's subject
    assert tag.extract_price("Onion Rs 80 per kg; wheat steady") is None                # per-kg, not wheat's price
    assert tag.extract_price("Rice exports rise, no price given") is None               # no figure
    assert tag.extract_price("Sugar Rs 3,500 per 40 kg") is None                        # not one of our crops


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


def test_tag_items_takes_the_price_from_the_rules_not_the_llms_own_number():
    # N1: the price always comes from the flour-safe extractor, never the model. The model here mis-reads a
    # flour price as wheat (5,200) and invents a number (9999); neither must become a crop price.
    import json as _json

    class Fake:
        def generate(self, system, user):
            n = user.count("\n") + 1
            prices = [9999, 5200]
            return _json.dumps([{"tag": "PRICE_REPORT", "crop": "wheat", "summary_en": "x", "summary_ur": "ایکس",
                                 "price_rs_per_40kg": prices[i % len(prices)]} for i in range(n)])

    items = [{"title": "Wheat support price at Rs 3,500 per 40 kg", "url": "u", "source": "s",
              "published": "2026-10-05"},
             {"title": "CM approves subsidy as Flour price hits Rs 5,200 per 40 kg", "url": "u2", "source": "s",
              "published": "2026-10-10"}]
    tagged, tagged_by = tag.tag_items(items, lambda: Fake())
    assert tagged_by == "llm"
    assert tagged[0]["price_rs_per_40kg"] == 3500    # real wheat price, kept
    assert tagged[1]["price_rs_per_40kg"] is None     # flour, not wheat: no false crop price


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

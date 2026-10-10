"""Tests for the curated policy timeline (H3). No network."""

import datetime as dt

from backend.app.news import policy


def test_policy_events_are_newest_first_and_sourced():
    events = policy.get_policy_events("wheat")
    assert len(events) >= 6
    assert events == sorted(events, key=lambda e: e["date"], reverse=True)
    for e in events:
        assert e["tag"] in {"SUPPORT_PRICE", "PROCUREMENT", "CAP_OR_BAN", "IMPORT"}
        assert e["source"] and e["url"].startswith("http") and e["text_ur"] and e["text_en"]


def test_policy_events_respect_as_of_for_replay():
    early = policy.get_policy_events("wheat", as_of=dt.date(2026, 5, 1))
    assert all(e["date"] <= "2026-05-01" for e in early)
    assert any(e["date"] == "2026-04-28" for e in early)       # the April cap is known
    assert not any(e["date"] == "2026-07-24" for e in early)   # the July import is not yet


def test_no_wheat_policy_events_leak_into_cotton():
    assert policy.get_policy_events("cotton") == []

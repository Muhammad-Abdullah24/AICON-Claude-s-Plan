import pytest

from backend.app import phrasing
from ml.decision.engine import Reason

# Every reason code the engine can emit, with the params it sends.
ENGINE_REASONS = [
    Reason("trend_up", {"weeks": 1, "pct": 3.2}),
    Reason("trend_down", {"weeks": 4, "pct": 6.0}),
    Reason("trend_flat", {"weeks": 1}),
    Reason("elsewhere_better", {"mandi": "vehari", "net_price": 4100, "gain": 150}),
    Reason("wait_gain", {"weeks": 1, "gain": 155}),
    Reason("downside_large", {"weeks": 2, "low": 3500}),
    Reason("band_wide", {"weeks": 1, "low": 3500, "high": 4500}),
    Reason("no_clear_gain"),
    Reason("cannot_store"),
    Reason("alert_active"),
]


def test_every_reason_has_both_languages():
    assert set(phrasing.REASONS["ur"]) == set(phrasing.REASONS["en"])
    assert {r.code for r in ENGINE_REASONS} == set(phrasing.REASONS["en"])


@pytest.mark.parametrize("lang", ["ur", "en"])
@pytest.mark.parametrize("reason", ENGINE_REASONS, ids=lambda r: r.code)
def test_every_reason_formats(reason, lang):
    [text] = phrasing.reasons_text([reason], lang, {"vehari": "Vehari"})
    assert text and "{" not in text


def test_english_week_counts_are_grammatical():
    texts = phrasing.reasons_text(ENGINE_REASONS, "en", {}) + [phrasing.risk_line(3000, 1, "en")]
    texts += [phrasing.reasons_text([r], "en", {})[0] for r in ENGINE_REASONS]
    assert not any("1 weeks" in t for t in texts)
    assert "within 1 week" in phrasing.risk_line(3000, 1, "en")
    assert "within 4 weeks" in phrasing.risk_line(3000, 4, "en")


def test_numbers_keep_western_digits_and_separators():
    [text] = phrasing.reasons_text([Reason("wait_gain", {"weeks": 4, "gain": 15484})], "ur", {})
    assert "15,484" in text


def test_mandi_ids_are_shown_as_names():
    [text] = phrasing.reasons_text(ENGINE_REASONS[3:4], "ur", {"vehari": "وہاڑی"})
    assert "وہاڑی" in text and "vehari" not in text

import pytest

from ml.explain import GROUPS, reasons
from ml.explain.reasons import LABELS
from ml.features import FEATURE_COLUMNS


def test_every_allowed_input_has_a_group_and_every_group_a_label():
    level_columns = {
        "price_rs_per_40kg", "price_lag_1w", "price_lag_2w", "price_lag_4w", "price_lag_8w", "price_lag_12w",
        "price_ma_4w", "price_ma_8w", "price_ma_12w",
    }
    assert set(FEATURE_COLUMNS) - level_columns <= set(GROUPS)
    assert set(GROUPS.values()) == set(LABELS)


def test_features_are_summed_into_groups_with_rupee_effects():
    out = reasons({"momentum_1w_pct": 1.0, "momentum_4w_pct": 1.5, "month_cos": -0.5, "bias": 9.0}, 4000)
    assert [r["feature"] for r in out] == ["recent_trend", "season"]
    trend, season = out
    assert trend["rs_effect"] == 100  # 2.5% of Rs 4,000
    assert trend["direction"] == "UP"
    assert trend["features"] == ["momentum_1w_pct", "momentum_4w_pct"]
    assert season["rs_effect"] == -20
    assert season["direction"] == "DOWN"


def test_sentences_in_both_languages():
    up, down = reasons({"momentum_4w_pct": 2.0, "precip_mm_4w": -1.0}, 5000)
    assert up["text_en"] == "Because of the recent price trend, the price may rise by about Rs 100 per 40 kg."
    assert "قیمتوں کے حالیہ رجحان" in up["text_ur"] and "100" in up["text_ur"] and "بڑھ" in up["text_ur"]
    assert down["text_en"] == "Because of rainfall, the price may fall by about Rs 50 per 40 kg."
    assert "کم ہو" in down["text_ur"]


def test_top_n_is_kept_between_one_and_five():
    contributions = {f: 1.0 + i for i, f in enumerate(GROUPS)}
    assert len(reasons(contributions, 1000)) == 3
    assert len(reasons(contributions, 1000, top_n=10)) == 5
    assert len(reasons(contributions, 1000, top_n=0)) == 1


def test_negligible_reasons_are_left_out():
    assert reasons({"momentum_4w_pct": 0.001}, 1000) == []


def test_unknown_feature_is_an_error():
    with pytest.raises(KeyError):
        reasons({"price_is_frozen": 1.0}, 1000)


def test_price_must_be_positive():
    with pytest.raises(ValueError):
        reasons({"momentum_4w_pct": 1.0}, 0)

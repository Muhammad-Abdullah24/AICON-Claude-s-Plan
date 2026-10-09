import json
import sys

import pytest

from ml.eval import gate


@pytest.fixture(scope="module")
def rows():
    return gate.load_rows()


def _perfect(rows):
    return {(r["series"], r["week_start"]): {"pred": r["actual"], "q10": r["actual"] - 1, "q90": r["actual"] + 1}
            for r in rows}


def test_committed_report_baselines_match_a_fresh_run(rows):
    """Baselines must be reproducible. A model entry, once Owner B adds one, is not rebuilt here."""
    committed = json.loads(gate.REPORT_JSON.read_text(encoding="utf-8"))
    fresh = json.loads(json.dumps(gate.build_report("val", rows=rows)))
    assert committed["features_csv_sha256"] == fresh["features_csv_sha256"]
    for name in ("persistence", "persistence_band", "seasonal_naive"):
        assert committed["models"][name] == fresh["models"][name], name


def test_persistence_is_the_reference(rows):
    val = [r for r in rows if r["split"] == "val"]
    naive = gate.persistence(val)
    m = gate.metrics(val, naive, naive)
    assert m["mase_vs_persistence"] == 1
    expected = 100 * sum(abs(r["price"] - r["actual"]) / r["actual"] for r in val) / len(val)
    assert m["mape_pct"] == pytest.approx(expected)


def test_a_perfect_model_passes(rows):
    val = [r for r in rows if r["split"] == "val"]
    report = gate.build_report("val", predictions=_perfect(val), model_name="perfect", rows=rows,
                               features_sha="x")
    v, m = report["verdict"], report["models"]["perfect"]["pooled"]
    assert v["passes_nfr01"] and m["mape_pct"] == 0
    assert m["directional_accuracy"] == 1 and m["band_coverage"] == 1


def test_a_worse_model_fails(rows):
    val = [r for r in rows if r["split"] == "val"]
    worse = {(r["series"], r["week_start"]): {"pred": r["price"] * 1.2, "q10": None, "q90": None} for r in val}
    report = gate.build_report("val", predictions=worse, model_name="worse", rows=rows, features_sha="x")
    assert not report["verdict"]["passes_nfr01"]


def test_every_row_needs_a_prediction(rows):
    val = [r for r in rows if r["split"] == "val"]
    partial = dict(list(_perfect(val).items())[:10])
    with pytest.raises(ValueError, match="have no prediction"):
        gate.build_report("val", predictions=partial, rows=rows, features_sha="x")


def test_band_quantiles_come_from_train_only(rows):
    changed = [dict(r, price_change_4w_pct="999") if r["split"] != "train" else r for r in rows]
    assert gate.change_quantiles([r for r in changed if r["split"] == "train"]) == \
        gate.change_quantiles([r for r in rows if r["split"] == "train"])


def test_seasonal_naive_only_looks_back():
    row = {"series": "S", "week_start": "2025-06-02", "target_week": "2025-06-30", "price": 100.0, "actual": 999.0}
    past = [
        {"series": "S", "week_start": "2024-06-03", "target_week": "2024-07-01", "price": 50.0, "actual": 60.0},
    ]
    preds, used = gate.seasonal_naive([row], past + [row])
    assert used == 1
    assert preds[("S", "2025-06-02")]["pred"] == pytest.approx(120.0)  # last year's +20%, not the 999 target


def test_test_split_needs_final(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["gate", "--split", "test"])
    with pytest.raises(SystemExit, match="used once"):
        gate.main()

import json
from pathlib import Path

REPORT = Path(__file__).resolve().parents[2] / "artifacts" / "models" / "policy_eval.json"


def test_policy_report_is_consistent():
    r = json.loads(REPORT.read_text(encoding="utf-8"))
    assert set(r["periods"]) == {"cv_2021_2024", "validation_2025"}  # the 2026 test split is not used
    for p in r["periods"].values():
        for s in p["scenarios"].values():
            assert sum(s["actions"].values()) == p["weeks"] == sum(s["modes"].values())
            assert set(s["actions"]) == {"SELL_NOW"}  # holding is never recommended
        assert p["scenarios"]["no_storage"]["upside_watch_by_crop"] == {}
    ev = r["hold_gate_evidence"]
    assert ev["beat_carry_pct_min"] == min(ev["beat_carry_pct_by_period"].values())
    assert ev["beat_carry_pct_min"] < ev["required_beat_carry_pct"]

"""The placeholder generator must always produce artifacts the backend accepts."""

from backend.app.artifacts import load_store
from ml.precompute import build_placeholder, write_artifacts


def test_placeholder_artifacts_pass_backend_validation(tmp_path):
    write_artifacts(build_placeholder(), tmp_path)
    store = load_store(tmp_path)
    assert store.meta.is_synthetic
    assert all(f.is_synthetic for f in (store.forecasts, store.alarms, store.replay, store.backtest))


def test_placeholder_is_deterministic():
    assert build_placeholder() == build_placeholder()


def test_committed_artifacts_match_the_generator_while_synthetic():
    """Catches hand-edited placeholder files. Delete this test when real artifacts land."""
    import json

    from backend.app.config import REPO_ROOT

    meta = json.loads((REPO_ROOT / "artifacts" / "meta.json").read_text(encoding="utf-8"))
    if meta["data_source"] != "placeholder":
        return
    for name, payload in build_placeholder().items():
        on_disk = json.loads((REPO_ROOT / "artifacts" / name).read_text(encoding="utf-8"))
        assert on_disk == payload, f"artifacts/{name} differs from `python -m ml.precompute --placeholder`"

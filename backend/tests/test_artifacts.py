"""Bad artifacts must be caught by the checker.

artifacts/ belongs to the superseded plan; the API no longer serves it (hand-off H-B12).
"""

import json
import shutil

import pytest

from backend.app.artifacts import ArtifactError, load_store
from backend.app.config import REPO_ROOT


@pytest.fixture
def artifacts(tmp_path):
    shutil.copytree(REPO_ROOT / "artifacts", tmp_path, dirs_exist_ok=True)
    return tmp_path


def edit(directory, name, change):
    path = directory / name
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def problems(directory) -> str:
    with pytest.raises(ArtifactError) as e:
        load_store(directory)
    return "\n".join(e.value.problems)


def test_committed_artifacts_are_valid():
    load_store(REPO_ROOT / "artifacts")


def test_missing_file(artifacts):
    (artifacts / "replay.json").unlink()
    assert "replay.json: file missing" in problems(artifacts)


def test_broken_json(artifacts):
    (artifacts / "backtest.json").write_text("{not json", encoding="utf-8")
    assert "backtest.json: not valid JSON" in problems(artifacts)


def test_quantiles_out_of_order(artifacts):
    def swap(d):
        b = d["series"][0]["forecasts"][0]["forecast"][0]
        b["q10"], b["q90"] = b["q90"], b["q10"]
    edit(artifacts, "forecasts.json", swap)
    assert "quantiles out of order" in problems(artifacts)


def test_misspelt_field(artifacts):
    edit(artifacts, "meta.json", lambda d: d.update(is_synthtic=True))
    assert "is_synthtic" in problems(artifacts)


def test_price_now_must_match_history(artifacts):
    def bump(d):
        d["series"][0]["forecasts"][5]["price_now"] += 100
    edit(artifacts, "forecasts.json", bump)
    assert "price_now" in problems(artifacts)


def test_series_must_be_declared_in_meta(artifacts):
    edit(artifacts, "meta.json", lambda d: d["series"].pop())
    assert "do not match meta.json" in problems(artifacts)


def test_synthetic_file_needs_synthetic_meta(artifacts):
    edit(artifacts, "meta.json", lambda d: d.update(is_synthetic=False))
    assert "meta.json says is_synthetic=false" in problems(artifacts)


def test_real_event_needs_a_source(artifacts):
    def unsource(d):
        d["events"][0]["is_synthetic"] = False
    edit(artifacts, "alarms.json", unsource)
    assert "has no source_url" in problems(artifacts)


def test_missing_storage_default(artifacts):
    edit(artifacts, "meta.json", lambda d: d["assumptions"]["storage_defaults"].pop())
    assert "no storage default" in problems(artifacts)

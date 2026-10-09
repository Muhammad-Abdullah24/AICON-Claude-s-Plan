"""Loads, validates and indexes the files in artifacts/.

Two layers of checks run on startup:

1. Each file against its schema in schemas.py (types, ranges, quantile order).
2. The files against each other: every crop, mandi and series must be declared
   in meta.json, dates must be sorted, and each forecast's price_now must match
   the history. A failure lists every problem at once and stops the server, so
   a bad artifact can never reach the demo.

All "as of" lookups live here, in one place, so the time-machine rule
(PLAN.md section 5) is enforced by a single tested function.
"""

from __future__ import annotations

import bisect
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from backend.app.schemas import (
    Alarm,
    AlarmsArtifact,
    BacktestArtifact,
    Event,
    ForecastEntry,
    ForecastsArtifact,
    Meta,
    PricePoint,
    ReplayArtifact,
    ReplayCase,
    SeriesForecasts,
    StorageDefault,
)

FILES: dict[str, type[BaseModel]] = {
    "meta.json": Meta,
    "forecasts.json": ForecastsArtifact,
    "alarms.json": AlarmsArtifact,
    "replay.json": ReplayArtifact,
    "backtest.json": BacktestArtifact,
}

PRICE_TOLERANCE = 0.5  # Rs: price_now must match the history to within rounding


class ArtifactError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Invalid artifacts:\n  - " + "\n  - ".join(problems))


@dataclass
class _Series:
    data: SeriesForecasts
    history_dates: list[dt.date]
    forecast_dates: list[dt.date]


class ArtifactStore:
    def __init__(
        self,
        meta: Meta,
        forecasts: ForecastsArtifact,
        alarms: AlarmsArtifact,
        replay: ReplayArtifact,
        backtest: BacktestArtifact,
    ):
        self.meta = meta
        self.forecasts = forecasts
        self.alarms = alarms
        self.replay = replay
        self.backtest = backtest
        _cross_check(meta, forecasts, alarms, replay, backtest)

        self._series = {
            (s.crop, s.mandi): _Series(
                data=s,
                history_dates=[p.date for p in s.history],
                forecast_dates=[f.as_of for f in s.forecasts],
            )
            for s in forecasts.series
        }
        self._alarms: dict[tuple[str, str], list[Alarm]] = {}
        for a in sorted(alarms.alarms, key=lambda a: a.date):
            self._alarms.setdefault((a.crop, a.mandi), []).append(a)
        self._alarm_dates = {k: [a.date for a in v] for k, v in self._alarms.items()}
        self._cases = {c.case_id: c for c in replay.cases}
        self._storage = {(d.crop, d.storage): d for d in meta.assumptions.storage_defaults}
        self._transport = {(t.from_mandi, t.to_mandi): t.cost_per_maund for t in meta.assumptions.transport}

    # ------------------------------------------------------------ lookups

    def has_series(self, crop: str, mandi: str) -> bool:
        return (crop, mandi) in self._series

    def mandis_for(self, crop: str) -> list[str]:
        return [m for (c, m) in self._series if c == crop]

    def forecast_at(self, crop: str, mandi: str, as_of: dt.date | None) -> ForecastEntry | None:
        """The latest forecast made on or before `as_of` (latest overall if None). Never a later one."""
        s = self._series[(crop, mandi)]
        if as_of is None:
            return s.data.forecasts[-1]
        i = bisect.bisect_right(s.forecast_dates, as_of)
        return s.data.forecasts[i - 1] if i else None

    def history_until(self, crop: str, mandi: str, as_of: dt.date, weeks: int) -> list[PricePoint]:
        """History points dated on or before `as_of`, at most `weeks` of them."""
        s = self._series[(crop, mandi)]
        end = bisect.bisect_right(s.history_dates, as_of)
        return s.data.history[max(0, end - weeks):end]

    def alarm_at(self, crop: str, mandi: str, as_of: dt.date) -> Alarm | None:
        dates = self._alarm_dates.get((crop, mandi), [])
        i = bisect.bisect_right(dates, as_of)
        return self._alarms[(crop, mandi)][i - 1] if i else None

    def events_active(self, crop: str, as_of: dt.date) -> list[Event]:
        return [e for e in self.alarms.events if crop in e.crops and e.date <= as_of <= e.active_until]

    def case(self, case_id: str) -> ReplayCase | None:
        return self._cases.get(case_id)

    def storage_default(self, crop: str, storage: str) -> StorageDefault:
        return self._storage[(crop, storage)]

    def transport_cost(self, from_mandi: str, to_mandi: str) -> float | None:
        return self._transport.get((from_mandi, to_mandi))


def load_store(artifacts_dir: Path) -> ArtifactStore:
    problems: list[str] = []
    parsed: dict[str, BaseModel] = {}
    for name, model in FILES.items():
        path = artifacts_dir / name
        if not path.is_file():
            problems.append(f"{name}: file missing in {artifacts_dir}")
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            parsed[name] = model.model_validate(raw)
        except json.JSONDecodeError as e:
            problems.append(f"{name}: not valid JSON ({e})")
        except ValidationError as e:
            for err in e.errors()[:20]:
                loc = ".".join(str(x) for x in err["loc"])
                problems.append(f"{name}: {loc}: {err['msg']}")
    if problems:
        raise ArtifactError(problems)
    return ArtifactStore(
        meta=parsed["meta.json"],
        forecasts=parsed["forecasts.json"],
        alarms=parsed["alarms.json"],
        replay=parsed["replay.json"],
        backtest=parsed["backtest.json"],
    )


def _sorted_unique(dates: list[dt.date]) -> bool:
    return all(a < b for a, b in zip(dates, dates[1:], strict=False))


def _cross_check(
    meta: Meta,
    forecasts: ForecastsArtifact,
    alarms: AlarmsArtifact,
    replay: ReplayArtifact,
    backtest: BacktestArtifact,
) -> None:
    p: list[str] = []
    crops = {c.id for c in meta.crops}
    mandis = {m.id for m in meta.mandis}
    if len(crops) != len(meta.crops):
        p.append("meta.json: duplicate crop id")
    if len(mandis) != len(meta.mandis):
        p.append("meta.json: duplicate mandi id")

    series = [(s.crop, s.mandi) for s in meta.series]
    if len(set(series)) != len(series):
        p.append("meta.json: duplicate series")
    for c, m in series:
        if c not in crops or m not in mandis:
            p.append(f"meta.json: series {c}/{m} uses an undeclared crop or mandi")
    declared = set(series)

    # Every file is labelled consistently, so the UI's synthetic badge is never wrong.
    for name, art in [("forecasts.json", forecasts), ("alarms.json", alarms),
                      ("replay.json", replay), ("backtest.json", backtest)]:
        if art.is_synthetic and not meta.is_synthetic:
            p.append(f"{name} is synthetic but meta.json says is_synthetic=false")

    # Forecasts: one entry per declared series, sorted, consistent with history.
    got = [(s.crop, s.mandi) for s in forecasts.series]
    if set(got) != declared or len(got) != len(declared):
        p.append(f"forecasts.json: series {sorted(set(got))} do not match meta.json {sorted(declared)}")
    latest = []
    for s in forecasts.series:
        key = f"forecasts.json {s.crop}/{s.mandi}"
        hist_dates = [h.date for h in s.history]
        fc_dates = [f.as_of for f in s.forecasts]
        if not _sorted_unique(hist_dates):
            p.append(f"{key}: history dates not sorted and unique")
            continue
        if not _sorted_unique(fc_dates):
            p.append(f"{key}: forecast as_of dates not sorted and unique")
            continue
        latest.append(fc_dates[-1])
        for f in s.forecasts:
            i = bisect.bisect_right(hist_dates, f.as_of)
            if i == 0:
                p.append(f"{key}: forecast as_of {f.as_of} is before any history")
                break
            if abs(s.history[i - 1].price - f.price_now) > PRICE_TOLERANCE:
                p.append(f"{key}: price_now at {f.as_of} does not match the latest history price")
                break
            horizons = [b.weeks_ahead for b in f.forecast]
            if horizons != sorted(set(horizons)):
                p.append(f"{key}: forecast horizons at {f.as_of} not sorted and unique")
                break
        if hist_dates[-1] > meta.date_range.end or hist_dates[0] < meta.date_range.start:
            p.append(f"{key}: history falls outside meta.json date_range")
    if latest and max(latest) != meta.latest_as_of:
        p.append(f"meta.json: latest_as_of {meta.latest_as_of} != latest forecast {max(latest)}")

    # Alarms and events refer only to declared things.
    for a in alarms.alarms:
        if (a.crop, a.mandi) not in declared:
            p.append(f"alarms.json: alarm for undeclared series {a.crop}/{a.mandi}")
            break
    for e in alarms.events:
        if not set(e.crops) <= crops:
            p.append(f"alarms.json: event '{e.headline[:40]}' names an undeclared crop")
        if e.source_url is None and not e.is_synthetic:
            p.append(f"alarms.json: real event '{e.headline[:40]}' has no source_url")

    # Replay cases match meta.json's list and use declared series.
    ref_ids = [r.case_id for r in meta.replay_cases]
    case_ids = [c.case_id for c in replay.cases]
    if sorted(ref_ids) != sorted(case_ids) or len(set(case_ids)) != len(case_ids):
        p.append(f"replay.json cases {case_ids} do not match meta.json replay_cases {ref_ids}")
    refs = {r.case_id: r for r in meta.replay_cases}
    for c in replay.cases:
        if (c.crop, c.mandi) not in declared:
            p.append(f"replay.json {c.case_id}: undeclared series {c.crop}/{c.mandi}")
        r = refs.get(c.case_id)
        if r and (r.crop, r.mandi, r.title_ur, r.title_en) != (c.crop, c.mandi, c.title_ur, c.title_en):
            p.append(f"replay.json {c.case_id}: crop, mandi or titles differ from meta.json")
        if not _sorted_unique([s.as_of for s in c.steps]):
            p.append(f"replay.json {c.case_id}: step dates not sorted and unique")

    for row in backtest.metrics:
        if (row.crop, row.mandi) not in declared:
            p.append(f"backtest.json: metrics for undeclared series {row.crop}/{row.mandi}")
            break

    # Defaults exist for every crop and storing option, so advice never lacks one.
    have = {(d.crop, d.storage) for d in meta.assumptions.storage_defaults}
    for c in crops:
        for s in ("home", "cold_store", "warehouse"):
            if (c, s) not in have:
                p.append(f"meta.json: no storage default for {c}/{s}")
    for t in meta.assumptions.transport:
        if t.from_mandi not in mandis or t.to_mandi not in mandis or t.from_mandi == t.to_mandi:
            p.append(f"meta.json: bad transport row {t.from_mandi} -> {t.to_mandi}")

    if p:
        raise ArtifactError(p)

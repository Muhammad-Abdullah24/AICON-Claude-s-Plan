from ml.ingest.frozen import frozen_stretches


def test_frozen_stretches_finds_long_identical_runs():
    prices = [(f"d{i:03d}", 100.0) for i in range(30)] + [("d030", 101.0)] + [(f"e{i:03d}", 90.0) for i in range(5)]
    runs = frozen_stretches(prices, min_days=28)
    assert runs == [{"from": "d000", "to": "d029", "days": 30, "price": 100.0}]


def test_a_run_at_the_end_counts():
    assert frozen_stretches([(str(i), 5.0) for i in range(3)], min_days=3)[0]["days"] == 3


def test_week_flags_need_every_reported_day_frozen():
    from datetime import date, timedelta

    from ml.ingest.frozen import week_flags

    start = date(2026, 6, 1)  # a Monday
    daily = [((start + timedelta(days=k)).isoformat(), 3450.0) for k in range(35)]
    daily += [((start + timedelta(days=35 + k)).isoformat(), 3820.0) for k in range(10)]
    flags = week_flags(daily)
    assert flags(start) == 1
    assert flags(start + timedelta(weeks=5)) == 0          # the week the price moved
    assert flags(start + timedelta(weeks=20)) == 0         # no reports, outside any stretch


def test_known_weeks_in_the_real_data():
    from datetime import date

    from ml.ingest.frozen import load_daily, week_flags

    flags = week_flags(load_daily()["BahawalPur|Wheat|none"])
    assert flags(date(2026, 7, 6)) == 1    # inside the 75-day Rs 3,450 freeze
    assert flags(date(2026, 10, 5)) == 0   # Rs 3,820 for only 12 days so far

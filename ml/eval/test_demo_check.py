from ml.eval.demo_check import frozen_stretches


def test_frozen_stretches_finds_long_identical_runs():
    prices = [(f"d{i:03d}", 100.0) for i in range(30)] + [("d030", 101.0)] + [(f"e{i:03d}", 90.0) for i in range(5)]
    runs = frozen_stretches(prices, min_days=28)
    assert runs == [{"from": "d000", "to": "d029", "days": 30, "price": 100.0}]


def test_a_run_at_the_end_counts():
    assert frozen_stretches([(str(i), 5.0) for i in range(3)], min_days=3)[0]["days"] == 3

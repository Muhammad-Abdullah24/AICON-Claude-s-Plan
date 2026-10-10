"""The API contract (docs/BLUEPRINT.md section 12), end to end on the real data files."""

import datetime as dt

import pytest

CROPS = ["wheat", "cotton", "irri", "super_basmati"]
MANDIS = ["bahawalpur", "vehari", "rahim_yar_khan"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_root_redirects_to_docs(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"


# ---------------------------------------------------------------- meta

def test_meta_is_labelled_and_complete(meta):
    assert meta["is_synthetic"] is False and meta["data_source"] == "amis" and meta["unit"] == "40kg"
    assert [c["id"] for c in meta["crops"]] and {c["id"] for c in meta["crops"]} == set(CROPS)
    assert {m["id"] for m in meta["mandis"]} == set(MANDIS)
    pairs = {(s["crop"], s["mandi"]) for s in meta["series"]}
    assert len(pairs) == 11 and ("irri", "rahim_yar_khan") not in pairs
    assert all(c["name_ur"] and c["name_en"] for c in meta["crops"] + meta["mandis"])


# ---------------------------------------------------------------- every series

def test_every_series_forecasts_and_advises(client, meta):
    for s in meta["series"]:
        f = client.get("/api/forecast", params={"crop": s["crop"], "mandi": s["mandi"]})
        assert f.status_code == 200, s
        body = f.json()
        assert body["prices_as_of"] == s["prices_as_of"] and body["current_price"] == s["latest_price"]
        assert body["range"]["low"] <= body["predicted_price"] <= body["range"]["high"]
        assert 0 < len(body["history"]) <= 52
        assert all(p["date"] <= body["prices_as_of"] for p in body["history"])
        a = client.get("/api/advice", params={"crop": s["crop"], "mandi": s["mandi"]}).json()
        assert a["signal"] in ("SELL", "WAIT") and a["rupee_impact"] == a["gross_gain"] - a["interest_cost"]
        if s["is_stale"]:
            assert a["confidence"] == "LOW"


def test_missing_series_is_404_with_a_reason(client):
    r = client.get("/api/advice", params={"crop": "irri", "mandi": "rahim_yar_khan"})
    assert r.status_code == 404 and "IRRI" in r.json()["detail"]


def test_unknown_ids_are_422(client):
    assert client.get("/api/forecast", params={"crop": "potato", "mandi": "vehari"}).status_code == 422
    assert client.get("/api/forecast", params={"crop": "wheat", "mandi": "lahore"}).status_code == 422


# ---------------------------------------------------------------- time machine

@pytest.mark.parametrize("as_of", ["2025-03-24", "2025-08-04", "2024-04-15"])
def test_as_of_never_uses_later_data(client, as_of):
    q = {"crop": "wheat", "mandi": "bahawalpur", "as_of": as_of}
    f = client.get("/api/forecast", params=q).json()
    assert f["prices_as_of"] <= as_of and all(p["date"] <= as_of for p in f["history"])
    h = client.get("/api/history", params=q).json()
    assert all(p["date"] <= as_of for p in h["weekly"])
    c = client.get("/api/compare-mandis", params=q).json()
    assert all(r["prices_as_of"] <= as_of for r in c["rows"] if r["has_data"])


def test_as_of_before_any_data_is_404(client):
    r = client.get("/api/forecast", params={"crop": "wheat", "mandi": "bahawalpur", "as_of": "2000-01-01"})
    assert r.status_code == 404


# ---------------------------------------------------------------- advice details

def test_advice_scales_with_quantity(client):
    q = {"crop": "wheat", "mandi": "bahawalpur"}
    one = client.get("/api/advice", params={**q, "quantity_maund": 1}).json()
    hundred = client.get("/api/advice", params={**q, "quantity_maund": 100}).json()
    assert abs(hundred["interest_cost"] - 100 * one["interest_cost"]) <= 100


def test_guest_gets_the_100_maund_example(client):
    assert client.get("/api/advice", params={"crop": "cotton", "mandi": "vehari"}).json()["quantity_maund"] == 100


def test_explain_gives_reasons_in_both_languages(client):
    e = client.get("/api/explain", params={"crop": "wheat", "mandi": "bahawalpur"}).json()
    assert e["source"] in ("facts", "shap") and e["reasons"]
    assert all(r["text_ur"] and r["text_en"] for r in e["reasons"])


def test_compare_best_first_and_flags_missing(client):
    c = client.get("/api/compare-mandis", params={"crop": "irri", "mandi": "vehari"}).json()
    priced = [r for r in c["rows"] if r["has_data"]]
    assert [r["net_price"] for r in priced] == sorted((r["net_price"] for r in priced), reverse=True)
    assert {"mandi": "rahim_yar_khan", "has_data": False}.items() <= next(
        r for r in c["rows"] if r["mandi"] == "rahim_yar_khan").items()
    assert c["transport_is_estimate"] is True


def test_offer_check(client):
    base = {"crop": "wheat", "mandi": "bahawalpur"}
    fair = client.post("/api/offer-check", json={**base, "offer_price": 1}).json()
    assert fair["verdict"] == "below" and fair["difference_total"] < 0
    high = client.post("/api/offer-check", json={**base, "offer_price": 999_999}).json()
    assert high["verdict"] == "above"
    assert client.post("/api/offer-check", json={**base, "offer_price": -5}).status_code == 422


def test_margin_with_support_price_for_wheat_only(client):
    w = client.get("/api/margin", params={"crop": "wheat", "price": 3820, "arhti_pct": 2}).json()
    assert w["support_price"] is not None and w["arhti_amount"] == pytest.approx(76.4)
    assert w["profit"] == pytest.approx(3820 - w["production_cost"] - 76.4)
    assert client.get("/api/margin", params={"crop": "cotton", "price": 9000}).json()["support_price"] is None


def test_wheat_carries_the_models_direction_call_and_shap_reasons(client):
    q = {"crop": "wheat", "mandi": "bahawalpur"}
    f = client.get("/api/forecast", params=q).json()
    assert f["direction"]["call"] in ("UP", "DOWN") and f["model"] == "baseline_persistence_band"
    e = client.get("/api/explain", params=q).json()
    assert e["source"] == "shap" and e["direction"] == f["direction"] and len(e["reasons"]) >= 2
    assert client.get("/api/forecast", params={"crop": "cotton", "mandi": "bahawalpur"}).json()["direction"] is None
    # The time machine reaches the model too: the 2025 crash and rally weeks get the calls that came true.
    calls = [client.get("/api/forecast", params={**q, "as_of": d}).json()["direction"]["call"]
             for d in ("2025-03-24", "2025-08-04")]
    assert calls == ["DOWN", "UP"]


def test_history_shows_gaps_and_frozen_weeks(client):
    h = client.get("/api/history", params={"crop": "wheat", "mandi": "bahawalpur", "as_of": "2026-10-09"}).json()
    assert len(h["weekly"]) == 52 and any(p["frozen"] for p in h["weekly"])   # the 2026 summer freeze
    assert all(p["price"] is None or p["price"] > 0 for p in h["weekly"])


def _plan(client, mandi, **params):
    p = client.get("/api/crop-plan", params={"mandi": mandi, "land_area_acres": 5, **params}).json()
    return p, {i["crop"]: i for i in p["items"]}, {s["season"]: s for s in p["seasons"]}


def test_crop_plan_estimates_stay_consistent(client):
    p, _, _ = _plan(client, "bahawalpur")
    assert p["is_estimate"] is True
    for i in p["items"]:
        assert i["harvest_price_low"] <= i["harvest_price_estimate"] <= i["harvest_price_high"]
        # The engine rounds profit per acre to whole rupees, so the total can differ by up to half a rupee an acre.
        assert i["expected_profit"] == pytest.approx(i["profit_per_acre"] * 5, abs=0.5 * 5)
        assert i["profit_per_acre_low"] <= i["profit_per_acre"] <= i["profit_per_acre_high"]
        assert (i["rank"] is None) or not i["evidence_issues"]      # a ranked crop always has reliable evidence


def test_crop_plan_stale_candidate_is_not_ranked(client):
    # F4 (1): at Bahawalpur, Super Basmati's last price is months old: it keeps its numbers but gets no rank.
    _, items, seasons = _plan(client, "bahawalpur")
    assert items["super_basmati"]["rank"] is None and "STALE_PRICE" in items["super_basmati"]["evidence_issues"]
    assert seasons["KHARIF"]["status"] == "RANKED"
    ranked = sorted((i for i in items.values() if i["rank"]), key=lambda i: i["rank"])
    assert [i["rank"] for i in ranked] == [1, 2] and all(i["season"] == "KHARIF" for i in ranked)
    assert ranked[0]["expected_profit"] >= ranked[1]["expected_profit"]


def test_crop_plan_never_compares_across_seasons(client):
    # F4 (3): wheat (Rabi) is never ranked against cotton or rice (Kharif); it is the only Rabi crop we track.
    for mandi in ("bahawalpur", "vehari", "rahim_yar_khan"):
        _, items, seasons = _plan(client, mandi)
        assert items["wheat"]["season"] == "RABI" and items["wheat"]["rank"] is None
        assert seasons["RABI"] == {**seasons["RABI"], "status": "TOO_FEW_CROPS", "n_crops": 1}


def test_crop_plan_too_few_comparable_crops_means_no_ranking(client):
    # F4 (2, 4): at Rahim Yar Khan only cotton has reliable Kharif evidence (no IRRI, Super Basmati stale): no winner.
    p, items, seasons = _plan(client, "rahim_yar_khan")
    assert seasons["KHARIF"]["status"] == "NOT_ENOUGH_CURRENT_EVIDENCE" and seasons["KHARIF"]["n_comparable"] == 1
    assert all(i["rank"] is None for i in items.values())
    assert "irri" in p["not_available"]


def test_crop_plan_rice_water_note_only_for_rice_at_bahawalpur(client):
    # F4 (5)
    _, bwp, _ = _plan(client, "bahawalpur")
    for crop, item in bwp.items():
        ids = [n["id"] for n in item["notes"]]
        assert ids == (["RICE_WATER_BAHAWALPUR"] if crop in ("irri", "super_basmati") else [])
    note = bwp["irri"]["notes"][0]
    assert note["url"].startswith("https://") and note["source"] and note["source_date"]
    for mandi in ("vehari", "rahim_yar_khan"):
        _, items, _ = _plan(client, mandi)
        assert all(i["notes"] == [] for i in items.values())


def test_crop_plan_wheat_support_price_context(client):
    # F4 (6): policy context from the H3 timeline, never a mandi price; out of date in a May replay.
    p, _, _ = _plan(client, "bahawalpur", as_of="2026-10-09")
    ctx = p["support_price_context"]
    assert ctx["state"] == "CURRENT" and ctx["event"]["tag"] == "SUPPORT_PRICE" and ctx["event"]["url"]
    assert ctx["age_days"] <= ctx["max_age_days"]
    assert ctx["uncertain"] is True                 # the "undecided" item is days old: flagged, not hidden
    may, _, _ = _plan(client, "bahawalpur", as_of="2026-05-10")
    assert may["support_price_context"]["state"] == "OUTDATED"
    assert may["support_price_context"]["event"]["date"] <= "2026-05-10"
    assert may["support_price_context"]["uncertain"] is True    # the 28 Apr price cap is 12 days old
    early, _, _ = _plan(client, "bahawalpur", as_of="2025-12-01")
    assert early["support_price_context"]["state"] == "UNAVAILABLE"
    assert early["support_price_context"]["event"] is None


def test_history_has_twelve_seasonal_months(client):
    h = client.get("/api/history", params={"crop": "cotton", "mandi": "vehari"}).json()
    assert [s["month"] for s in h["seasonal"]] == list(range(1, 13)) and h["weekly"]


def test_weather_falls_back_to_offline_when_live_is_down(client, monkeypatch):
    from backend.app import weather

    def down(lat, lon, timeout=8.0):
        raise TimeoutError

    monkeypatch.setattr(weather, "fetch_open_meteo", down)
    monkeypatch.setattr(weather, "_cache", {})
    w = client.get("/api/weather", params={"mandi": "vehari"}).json()["weather"]
    assert w["cached"] is True and w["source"] == "offline file" and "Open-Meteo" in w["attribution"]


# ---------------------------------------------------------------- farmers and login

def test_login_and_profile(client):
    t = client.post("/api/auth/login", json={"phone": "+92 000 0000001"}).json()
    headers = {"Authorization": f"Bearer {t['token']}"}
    me = client.get("/api/farmers/me", headers=headers).json()
    assert me["name"] == "Ahmed" and me["district"] == "bahawalpur"
    # The profile's quantity is used when none is given.
    a = client.get("/api/advice", params={"crop": "cotton", "mandi": "bahawalpur"}, headers=headers).json()
    assert a["quantity_maund"] == 60
    updated = client.put("/api/farmers/me", json={"arhti_commission_pct": 3}, headers=headers).json()
    assert updated["arhti_commission_pct"] == 3


def test_register_then_duplicate_is_409(client):
    body = {"name": "Test", "phone": "+920000000777", "district": "vehari",
            "crops": [{"crop": "irri", "preferred_mandi": "vehari", "harvest_quantity_maund": 40}]}
    first = client.post("/api/farmers", json=body)
    assert first.status_code == 201 and first.json()["token"]
    assert client.post("/api/farmers", json=body).status_code == 409


def test_auth_failures(client):
    assert client.get("/api/farmers/me").status_code == 401
    assert client.get("/api/farmers/me", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"phone": "+920000009999"}).status_code == 404


# ---------------------------------------------------------------- channels are mounted

def test_whatsapp_webhook_is_mounted_and_refuses_unsigned(client):
    assert client.post("/webhooks/whatsapp", content=b"{}").status_code in (403, 503)
    assert client.post("/whatsapp", data={"Body": "x"}).status_code == 404   # the Twilio placeholder is gone


def test_chat_route_uses_api_ids(client):
    from backend.app.chat import llm

    client.app.dependency_overrides[llm.get_llm] = lambda: type("L", (), {"generate": lambda s, a, b: "Rs 1"})()
    try:
        r = client.post("/api/chat", json={"question": "rate?", "crop": "super_basmati", "mandi": "vehari"})
    finally:
        client.app.dependency_overrides.clear()
    assert r.status_code == 200 and r.json()["crop"] == "super_basmati" and r.json()["mandi"] == "vehari"
    assert client.post("/api/chat", json={"question": "x", "crop": "Wheat"}).status_code == 422


def test_dates_in_responses_are_iso(client):
    f = client.get("/api/forecast", params={"crop": "wheat", "mandi": "vehari"}).json()
    dt.date.fromisoformat(f["prices_as_of"])


# ---------------------------------------------------------------- pivot contract (docs/PIVOT.md, U1)
# Placeholder answers for now; these tests pin the shape and the labelling, not the numbers. U4 tightens them.

def test_wait_plan_is_real_and_splits_correctly(client):
    r = client.get("/api/wait-plan", params={"crop": "wheat", "mandi": "bahawalpur", "quantity_maund": 100,
                                             "cash_need_rs": 200_000, "offer": 2900})
    assert r.status_code == 200
    p = r.json()
    assert p["crop"] == "wheat" and p["mandi"] == "bahawalpur" and p["unit"] == "40kg"
    assert p["data_source"] == "amis" and p["is_synthetic"] is False      # real data, never a placeholder
    assert p["sell_now_maund"] + p["hold_maund"] == p["quantity_maund"] == 100
    sell_now = p["exits"][0]
    assert sell_now["kind"] == "SELL_NOW" and sell_now["mandi"] in MANDIS and sell_now["per_maund"] > 0
    assert sell_now["total_rs"] == round(sell_now["per_maund"] * 100)
    assert next(e for e in p["exits"] if e["kind"] == "ARHTI_OFFER")["per_maund"] == 2900
    # wheat has years of AMIS data, so the hold history and a HOLD exit are present
    assert p["history"] is not None and p["history"]["n"] >= 3
    hold = next(e for e in p["exits"] if e["kind"] == "HOLD")
    assert hold["worst_total_rs"] <= hold["total_rs"] and hold["cost_rs"] > 0


def test_wait_plan_holds_only_wheat(client):
    p = client.get("/api/wait-plan", params={"crop": "cotton", "mandi": "bahawalpur"}).json()
    assert p["verdict"] == "SELL_ALL" and p["history"] is None and "HOLD_WHEAT_ONLY" in p["warnings"]
    assert not any(e["kind"] == "HOLD" for e in p["exits"])


def test_wait_plan_replays_a_past_week_without_live_news(client):
    p = client.get("/api/wait-plan", params={"crop": "wheat", "mandi": "bahawalpur", "as_of": "2025-08-04"}).json()
    assert p["prices_as_of"] <= "2025-08-04" and p["news_check"] is None   # news is today's, not replayed


def test_wait_plan_defaults_by_money_and_storage(client):
    p = client.get("/api/wait-plan", params={"crop": "wheat", "mandi": "vehari", "money": "arhti",
                                             "storage": "bags"}).json()
    assert p["money"] == "arhti" and p["annual_rate_pct"] == 66.0 and p["loss_pct"] == 10.0
    own = client.get("/api/wait-plan", params={"crop": "wheat", "mandi": "vehari", "annual_rate": 12}).json()
    assert own["annual_rate_pct"] == 12


@pytest.mark.parametrize("params", [{"money": "friend"}, {"storage": "roof"}, {"wait_months": 0},
                                    {"wait_months": 7}, {"cash_need_rs": -1}, {"offer": 0}])
def test_wait_plan_rejects_bad_input(client, params):
    assert client.get("/api/wait-plan", params={"crop": "wheat", "mandi": "bahawalpur", **params}).status_code == 422


def test_wait_plan_404_without_data(client):
    assert client.get("/api/wait-plan", params={"crop": "irri", "mandi": "rahim_yar_khan"}).status_code == 404


def test_news_is_offline_in_tests_with_api_ids(client):
    n = client.get("/api/news", params={"crop": "wheat", "mandi": "bahawalpur"}).json()
    assert n["is_snapshot"] is True and n["tagged_by"] in ("llm", "rules")   # offline -> committed snapshot
    assert all(i["crop"] in CROPS + [None] for i in n["items"])
    assert all({"title", "url", "source", "published", "tag", "summary_ur", "summary_en"} <= i.keys()
               for i in n["items"])


def test_policy_respects_as_of(client):
    events = client.get("/api/policy", params={"crop": "wheat", "as_of": "2026-04-01"}).json()["events"]
    assert events and all(e["date"] <= "2026-04-01" for e in events)
    assert not any(e["date"] == "2026-04-28" for e in events)   # the late-April cap is not yet known
    assert all(e["source"] and e["url"].startswith("http") and e["text_ur"] for e in events)


def test_wait_plan_derives_cash_need_from_the_household_budget(client):
    # B2: with no explicit cash_need, the need = loans due + max(0, household - other income) x months.
    p = client.get("/api/wait-plan", params={"crop": "wheat", "mandi": "bahawalpur", "wait_months": 4,
                                             "household_spend_rs_month": 30000, "other_income_rs_month": 5000}).json()
    assert p["household_spend_rs_month"] == 30000 and p["other_income_rs_month"] == 5000
    assert p["loans_due_rs"] == 0                                            # a guest has no loans
    assert p["cash_need_rs"] == (30000 - 5000) * 4                           # 100,000 derived from the budget


# ---------------------------------------------------------------- loan planner (B2: real engine + data)

def test_loan_plan_runs_on_real_tables_with_a_cheapest_first_ladder(client):
    p = client.get("/api/loan-plan", params={"crop": "wheat", "acres": 5, "savings_rs": 0}).json()
    assert p["crop"] == "wheat" and p["acres"] == 5
    assert p["data_source"] == "official_tables" and p["is_synthetic"] is False
    assert "COST_ESTIMATE" in p["warnings"]                                  # costs are escalated, always flagged
    assert p["input_need_rs"] == round(83995 * 5)                            # Rs 83,995/acre (D1) x 5 acres
    assert p["borrow_needed_rs"] == p["input_need_rs"]                       # no savings -> borrow it all
    assert p["months_to_harvest"] >= 1 and p["plan_comparison"] == "NOT_REQUESTED"
    rates = [s_rate(p, slice_["id"]) for slice_ in p["ladder"]]
    assert rates == sorted(rates)                                           # cheapest money first
    assert p["ladder"][0]["id"] == "kissan_card" and p["ladder"][0]["interest_rs"] == 0
    assert p["ladder"][0]["amount_rs"] == min(30000 * 5, 150000)            # Kissan Card capped
    assert p["harvest_due_rs"] == round(sum(s["amount_rs"] + s["interest_rs"] for s in p["ladder"]))


def test_loan_plan_eligibility_rules(client):
    small = {o["id"]: o for o in client.get("/api/loan-plan", params={"crop": "wheat", "acres": 5}).json()["options"]}
    assert small["pm_youth"]["eligible"] is False and small["pm_youth"]["why_not_en"]   # no age given
    assert small["kissan_card"]["eligible"] is True and small["kissan_card"]["verified"] is True
    with_age = {o["id"]: o for o in
                client.get("/api/loan-plan", params={"crop": "wheat", "acres": 5, "age": 30}).json()["options"]}
    assert with_age["pm_youth"]["eligible"] is True
    big = client.get("/api/loan-plan", params={"crop": "wheat", "acres": 20}).json()
    assert "NOT_SMALL_FARMER" in big["warnings"]
    big_by_id = {o["id"]: o for o in big["options"]}
    assert big_by_id["kissan_card"]["eligible"] is False                    # Kissan Card is 1-12.5 acres
    assert big_by_id["bank"]["eligible"] is True                            # a bank loan still covers it


def test_loan_plan_flags_over_borrowing(client):
    p = client.get("/api/loan-plan", params={"crop": "wheat", "acres": 5, "planned_borrow_rs": 900_000,
                                             "planned_lender": "arhti"}).json()
    assert "OVER_BORROWING" in p["warnings"] and p["over_borrow_rs"] > 0
    assert p["plan_comparison"] == "COMPARED"
    assert p["planned_interest_rs"] > p["ladder_interest_rs"] and p["extra_cost_rs"] > 0


def test_loan_plan_without_a_rate_is_insufficient_not_free(client):
    # A planned loan with no lender (so no rate) must not be priced as 0% (L1 safety rule).
    p = client.get("/api/loan-plan", params={"crop": "wheat", "acres": 5, "planned_borrow_rs": 900_000}).json()
    assert p["plan_comparison"] == "INSUFFICIENT_INFORMATION"
    assert p["planned_interest_rs"] is None and p["extra_cost_rs"] is None
    assert "planned_rate_pct" in p["missing_inputs"] and p["over_borrow_rs"] > 0   # over-borrowing still shown


def test_loan_plan_404_for_a_crop_without_a_cost_table(client):
    assert client.get("/api/loan-plan", params={"crop": "cotton", "acres": 5}).status_code == 404


def test_wait_plan_cash_need_comes_from_a_logged_in_farmers_loans(client):
    # B2: a loan due before the later sale raises the cash need, so more must be sold now.
    headers = _login(client)
    loan = client.post("/api/farmers/me/loans", headers=headers,
                       json={"lender": "arhti", "amount_rs": 150000, "annual_rate_pct": 66,
                             "due_date": "2027-01-31"}).json()   # due within the wait window of the latest data
    p = client.get("/api/wait-plan", params={"crop": "wheat", "mandi": "bahawalpur", "wait_months": 6},
                   headers=headers).json()
    # Owed at the due date = principal + simple interest from when it was recorded (66% a year here).
    days = (dt.date(2027, 1, 31) - dt.date.fromisoformat(loan["created_at"][:10])).days
    assert p["loans_due_rs"] == pytest.approx(150000 * (1 + 0.66 * days / 365), abs=1)
    assert p["cash_need_rs"] >= p["loans_due_rs"] > 150000
    assert p["sell_now_maund"] > 0                                           # the loan forces some selling now
    client.delete(f"/api/farmers/me/loans/{loan['id']}", headers=headers)   # leave the shared db clean


def s_rate(plan: dict, lender_id: str) -> float:
    return next(o["annual_rate_pct"] for o in plan["options"] if o["id"] == lender_id)


# ---------------------------------------------------------------- loan list (L2a)

def _login(client):
    t = client.post("/api/auth/login", json={"phone": "+92 000 0000001"}).json()
    return {"Authorization": f"Bearer {t['token']}"}


def test_loan_list_needs_auth(client):
    assert client.get("/api/farmers/me/loans").status_code == 401


def test_loan_list_add_list_and_delete(client):
    headers = _login(client)
    before = len(client.get("/api/farmers/me/loans", headers=headers).json())
    created = client.post("/api/farmers/me/loans", headers=headers,
                          json={"lender": "arhti", "amount_rs": 200000, "annual_rate_pct": 66,
                                "due_date": "2027-04-30"})
    assert created.status_code == 201
    loan = created.json()
    assert loan["id"] and loan["lender"] == "arhti" and loan["due_date"] == "2027-04-30"
    listed = client.get("/api/farmers/me/loans", headers=headers).json()
    assert len(listed) == before + 1 and any(x["id"] == loan["id"] for x in listed)
    assert client.delete(f"/api/farmers/me/loans/{loan['id']}", headers=headers).status_code == 204
    assert client.delete(f"/api/farmers/me/loans/{loan['id']}", headers=headers).status_code == 404
    assert len(client.get("/api/farmers/me/loans", headers=headers).json()) == before


def test_loan_rejects_bad_input(client):
    headers = _login(client)
    assert client.post("/api/farmers/me/loans", headers=headers,
                       json={"lender": "", "amount_rs": 1, "annual_rate_pct": 0,
                             "due_date": "2027-04-30"}).status_code == 422
    assert client.post("/api/farmers/me/loans", headers=headers,
                       json={"lender": "bank", "amount_rs": -5, "annual_rate_pct": 0,
                             "due_date": "2027-04-30"}).status_code == 422

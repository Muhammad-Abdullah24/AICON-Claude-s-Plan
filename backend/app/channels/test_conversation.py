from datetime import UTC, datetime, timedelta

import pytest

from backend.app.channels import conversation as conv
from backend.app.channels.conversation import State, handle
from backend.app.channels.provider import NotReady

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
PHONE = "923001234567"
OPTIONS = conv.default_options()


class FakeProvider:
    """Records every call; the engine must take all numbers from here."""

    def __init__(self, missing=(), not_ready=False):
        self.missing, self.not_ready, self.calls = set(missing), not_ready, []

    def _check(self, crop, mandi):
        if self.not_ready:
            raise NotReady("services")
        if (crop, mandi) in self.missing:
            raise LookupError

    def advice(self, crop_option, mandi, quantity_maund, phone):
        self.calls.append(("advice", crop_option, mandi, quantity_maund))
        self._check(crop_option, mandi)
        return {"crop_option": crop_option, "mandi": mandi, "quantity_maund": quantity_maund, "current_price": 3820}

    def explain(self, crop_option, mandi, phone):
        self.calls.append(("explain", crop_option, mandi))
        return [{"text_ur": "وجہ", "text_en": "reason", "direction": "UP"}]

    def compare(self, crop_option, mandi, quantity_maund, phone):
        self.calls.append(("compare", crop_option, mandi, quantity_maund))
        self._check(crop_option, mandi)
        return [{"mandi": mandi, "net_price": 3800, "has_data": True}]

    def offer(self, crop_option, mandi, quantity_maund, offer_price, phone):
        self.calls.append(("offer", crop_option, mandi, quantity_maund, offer_price))
        self._check(crop_option, mandi)
        return {"buyer_offer_price": offer_price, "reference_price": 3820, "result_status": "REFERENCE_DATA_LIMITED"}

    def set_alerts(self, phone, enabled):  # the engine never calls it: the channel applies alert_action
        raise AssertionError("engine must not write")


def say(text, state=None, provider=None, alerts=False, now=NOW):
    return handle(text, state, provider or FakeProvider(), phone=PHONE, now=now, alerts_enabled=alerts)


def chat(*texts, provider=None, alerts=False):
    """Run a conversation, carrying the state the way the store would."""
    provider, state, out = provider or FakeProvider(), None, None
    for t in texts:
        out = say(t, state, provider, alerts)
        state = out.state if out.persist == "save" else None
    return out, provider


def numbers(out):
    return [n for n, _ in out.reply.choices]


def crop_no(crop):
    return str(OPTIONS.crops.index(crop) + 1)


def mandi_no(mandi):
    return str(OPTIONS.mandis.index(mandi) + 1)


def variety_no(v):
    return str(OPTIONS.rice_varieties.index(v) + 1)


# ---------------------------------------------------------------- menus come from the id table

def test_options_group_rice_varieties_under_one_choice():
    assert set(OPTIONS.crops) == {"Wheat", "Cotton", conv.RICE}
    assert set(OPTIONS.rice_varieties) == {"SuperBasmati", "IRRI"}
    assert set(OPTIONS.mandis) == {"BahawalPur", "Vehari", "RahimYarKhan"}


@pytest.mark.parametrize("text", ["0", "۰", "hi", "مدد", "help"])
def test_zero_and_help_open_the_main_menu_from_anywhere(text):
    for state in (None, State(step=conv.MANDI, pending=conv.ADVICE, draft_crop="Wheat")):
        out = say(text, state)
        assert out.reply.kind == "menu" and out.state.step == conv.MENU
        assert numbers(out) == ["1", "2", "3", "4", "5", "0"]
        assert out.state.draft_crop is None


# ---------------------------------------------------------------- guided advice flow

def test_menu_1_is_the_offer_check_and_ends_in_the_service_layer_result():
    out, _ = chat("0", "1", crop_no("Wheat"), mandi_no("BahawalPur"), "100")
    assert out.reply.kind == "ask_offer" and out.state.step == conv.OFFER_STEP and numbers(out) == ["0"]
    out, provider = chat("0", "1", crop_no("Wheat"), mandi_no("BahawalPur"), "100", "3514")
    assert out.reply.kind == "offer"
    assert out.reply.data["result"]["reference_price"] == 3820          # straight from the provider
    assert provider.calls == [("offer", "Wheat", "BahawalPur", 100.0, 3514.0)]
    assert out.state.step == conv.POST_ADVICE and out.state.last_offer == 3514
    assert out.reply.choices == (("1", "why"), ("2", "compare"), ("3", "alerts_on"), ("0", "menu"))


def test_guided_advice_still_works_from_free_text():
    out, provider = chat("gandum", mandi_no("BahawalPur"), "100")
    assert out.reply.kind == "advice" and provider.calls == [("advice", "Wheat", "BahawalPur", 100.0)]
    assert out.reply.data["quantity_assumed"] is False and out.state.last_offer is None


def test_each_step_lists_its_numbers_and_zero():
    out, _ = chat("0", "1")
    assert out.reply.kind == "ask_crop" and numbers(out) == ["1", "2", "3", "0"]
    out, _ = chat("0", "1", crop_no("Wheat"))
    assert out.reply.kind == "ask_mandi" and numbers(out) == ["1", "2", "3", "0"]
    out, _ = chat("0", "1", crop_no("Wheat"), mandi_no("Vehari"))
    assert out.reply.kind == "ask_quantity" and numbers(out) == ["0"]


def test_rice_asks_the_variety_and_only_rice_does():
    out, _ = chat("0", "1", crop_no(conv.RICE))
    assert out.reply.kind == "ask_variety" and out.state.step == conv.RICE_VARIETY
    out, provider = chat("0", "1", crop_no(conv.RICE), variety_no("IRRI"), mandi_no("Vehari"), "40", "4500")
    assert provider.calls == [("offer", "IRRI", "Vehari", 40.0, 4500.0)]
    out, _ = chat("0", "1", crop_no("Cotton"))
    assert out.reply.kind == "ask_mandi"


@pytest.mark.parametrize("qty, expected", [("100 man", 100.0), ("2000 kg", 50.0), ("۵۰", 50.0), ("12.5", 12.5)])
def test_quantity_accepts_units_and_urdu_digits(qty, expected):
    _, provider = chat("0", "1", crop_no("Wheat"), mandi_no("Vehari"), qty, "3500")
    assert provider.calls[-1] == ("offer", "Wheat", "Vehari", expected, 3500.0)


def test_compare_flow_and_why_flow():
    out, provider = chat("0", "2", crop_no("Wheat"), mandi_no("Vehari"), "50")
    assert out.reply.kind == "compare" and provider.calls == [("compare", "Wheat", "Vehari", 50.0)]
    out, provider = chat("0", "3", crop_no("Cotton"), mandi_no("Vehari"))   # why needs no quantity
    assert out.reply.kind == "why" and ("explain", "Cotton", "Vehari") in provider.calls
    assert out.state.last_quantity is None


# ---------------------------------------------------------------- after the advice

def test_after_advice_1_is_why_2_is_compare_on_the_same_query():
    out, provider = chat("gandum bahawalpur 80 mann", "1")
    assert out.reply.kind == "why" and ("explain", "Wheat", "BahawalPur") in provider.calls
    out, provider = chat("gandum bahawalpur 80 mann", "2")
    assert out.reply.kind == "compare" and provider.calls[-1] == ("compare", "Wheat", "BahawalPur", 80.0)
    assert out.state.step == conv.POST_ADVICE


def test_compare_after_why_without_a_quantity_asks_for_it():
    out, provider = chat("0", "3", crop_no("Wheat"), mandi_no("Vehari"), "2")
    assert out.reply.kind == "ask_quantity" and out.state.pending == conv.COMPARE
    out, provider = chat("0", "3", crop_no("Wheat"), mandi_no("Vehari"), "2", "30")
    assert provider.calls[-1] == ("compare", "Wheat", "Vehari", 30.0)


@pytest.mark.parametrize("alerts_on, action, label", [(False, True, "alerts_on"), (True, False, "alerts_off")])
def test_after_advice_3_flips_alerts_and_stays(alerts_on, action, label):
    first, _ = chat("gandum vehari 10", alerts=alerts_on)
    assert first.reply.choices[2] == ("3", label)
    out = say("3", first.state, alerts=alerts_on)
    assert out.alert_action is action and out.reply.kind == "alerts"
    assert out.state.step == conv.POST_ADVICE and out.persist == "save"
    assert out.reply.choices[2][1] == ("alerts_off" if action else "alerts_on")   # label follows the change


# ---------------------------------------------------------------- alerts from the menu and words

@pytest.mark.parametrize("texts, action", [(("0", "4"), True), (("0", "5"), False), (("بند",), False),
                                           (("stop",), False), (("shuru",), True)])
def test_alert_actions_are_returned_for_the_channel_to_apply(texts, action):
    out, _ = chat(*texts)
    assert out.alert_action is action and out.reply.data["enabled"] is action
    assert out.persist == "clear" and out.state is None


def test_nothing_else_touches_alerts():
    for texts in (("0",), ("0", "1"), ("gandum bwp 5",), ("gandum bwp 5", "1"), ("0", "9")):
        out, _ = chat(*texts)
        assert out.alert_action is None


# ---------------------------------------------------------------- numbers are never guessed

@pytest.mark.parametrize("text", ["1", "2", "4", "5", "100"])
def test_bare_number_without_a_session_shows_the_menu_and_does_nothing(text):
    provider = FakeProvider()
    out = say(text, None, provider)
    assert out.reply.kind == "menu" and out.reply.data == {"note": "no_session"}
    assert out.alert_action is None and provider.calls == []
    assert out.state.step == conv.MENU   # so the next number is read against this menu


@pytest.mark.parametrize("expired", [False, True])
def test_legacy_bare_3_outside_a_session_still_stops_alerts(expired):
    old = State(step=conv.MANDI, draft_crop="Wheat", expires_at=NOW - timedelta(seconds=1)) if expired else None
    provider = FakeProvider()
    out = say("3", old, provider)
    assert out.alert_action is False and out.reply.kind == "alerts" and provider.calls == []
    assert out.persist == "clear"


@pytest.mark.parametrize("texts, kind", [(("0", "3"), "ask_crop"), (("gandum bwp 5", "3"), "alerts"),
                                         (("0", "1", "3"), "ask_variety")])
def test_inside_a_session_3_follows_the_step(texts, kind):
    out, _ = chat(*texts)
    assert out.reply.kind == kind
    if kind != "alerts":
        assert out.alert_action is None


def test_expired_session_returns_to_the_menu_and_says_why():
    live, _ = chat("0", "1", crop_no("Wheat"))
    old = conv.State(**{**live.state.__dict__, "expires_at": NOW - timedelta(seconds=1)})
    out = say(mandi_no("Vehari"), old)
    assert out.expired and out.reply.kind == "menu" and out.reply.data["note"] == "expired"
    assert out.state.draft_crop is None
    fresh = conv.State(**{**live.state.__dict__, "expires_at": NOW + timedelta(minutes=5)})
    assert say(mandi_no("Vehari"), fresh).reply.kind == "ask_quantity"


@pytest.mark.parametrize("texts, kind", [
    (("0", "7"), "menu"),
    (("0", "1", "9"), "ask_crop"),
    (("0", "1", "1.5"), "ask_crop"),
    (("0", "1", crop_no(conv.RICE), "3"), "ask_variety"),
    (("0", "1", crop_no("Wheat"), "4"), "ask_mandi"),
    (("0", "1", crop_no("Wheat"), "1", "-5"), "ask_quantity"),
    (("0", "1", crop_no("Wheat"), "1", "999999"), "ask_quantity"),
    (("0", "1", crop_no("Wheat"), "1", "bohat zyada"), "ask_quantity"),
    (("0", "1", "kal ka mausam"), "ask_crop"),
    (("gandum bwp 5", "8"), "post_menu"),
])
def test_invalid_input_repeats_the_valid_choices_and_keeps_the_step(texts, kind):
    out, provider = chat(*texts)
    assert out.reply.kind == kind and out.reply.data["invalid"] is True
    assert "0" in numbers(out) and out.persist == "save"
    _, before = chat(*texts[:-1])
    assert provider.calls == before.calls   # the invalid message itself asked the service for nothing


def test_invalid_input_keeps_what_was_already_chosen():
    out, _ = chat("0", "1", crop_no("Wheat"), mandi_no("Vehari"), "abc")
    assert (out.state.draft_crop, out.state.draft_mandi) == ("Wheat", "Vehari")


# ---------------------------------------------------------------- free text still works

@pytest.mark.parametrize("text, call", [
    ("گندم بہاولپور 100 من", ("advice", "Wheat", "BahawalPur", 100.0)),
    ("gandum vehari 50 mann", ("advice", "Wheat", "Vehari", 50.0)),
    ("Super Basmati Rahim Yar Khan 2000 kg", ("advice", "SuperBasmati", "RahimYarKhan", 50.0)),
])
def test_full_free_text_query_answers_at_once_in_or_out_of_a_session(text, call):
    for state in (None, State(step=conv.MANDI, pending=conv.COMPARE, draft_crop="Cotton")):
        provider = FakeProvider()
        out = say(text, state, provider)
        assert out.reply.kind == "advice" and provider.calls == [call]


def test_full_query_without_quantity_assumes_100_and_says_so():
    out, provider = chat("kapas ryk")
    assert provider.calls == [("advice", "Cotton", "RahimYarKhan", 100)]
    assert out.reply.data["quantity_assumed"] is True


def test_partial_text_fills_the_missing_piece():
    out, _ = chat("gandum 100 mann")                 # mandi missing: keep crop and quantity, ask mandi
    assert out.reply.kind == "ask_mandi" and out.state.draft_quantity == 100
    out, provider = chat("gandum 100 mann", "vehari")
    assert provider.calls == [("advice", "Wheat", "Vehari", 100.0)]
    out, provider = chat("gandum 100 mann", mandi_no("Vehari"))
    assert provider.calls == [("advice", "Wheat", "Vehari", 100.0)]
    out, _ = chat("chawal bahawalpur")               # rice without a variety: ask it, never guess
    assert out.reply.kind == "ask_variety" and out.state.draft_mandi == "BahawalPur"
    out, provider = chat("0", "1", "kapas")          # a word answers the crop step
    assert out.reply.kind == "ask_mandi" and out.state.draft_crop == "Cotton"


@pytest.mark.parametrize("word, kind", [("کیوں", "why"), ("why?", "why"), ("منڈیاں", "compare"),
                                        ("compare", "compare")])
def test_why_and_compare_words_use_the_last_query(word, kind):
    out, _ = chat("gandum bahawalpur 100", word)
    assert out.reply.kind == kind


def test_why_word_without_a_query_starts_the_guided_flow():
    out, provider = chat("کیوں")
    assert out.reply.kind == "ask_crop" and out.state.pending == conv.WHY and provider.calls == []


def test_unknown_text_after_advice_goes_to_chat_with_the_query_context():
    out, provider = chat("gandum bahawalpur 100", "kal ka mausam kaisa hoga")
    assert out.reply.kind == "chat"
    assert (out.reply.data["crop_option"], out.reply.data["mandi"]) == ("Wheat", "BahawalPur")
    out, _ = chat("kal ka mausam kaisa hoga")
    assert out.reply.kind == "not_understood" and numbers(out) == ["1", "2", "3", "4", "5", "0"]


# ---------------------------------------------------------------- service errors

def test_no_price_at_that_mandi_asks_for_another_mandi():
    provider = FakeProvider(missing={("IRRI", "RahimYarKhan")})
    out, _ = chat("0", "1", crop_no(conv.RICE), variety_no("IRRI"), mandi_no("RahimYarKhan"), "40", "4500",
                  provider=provider)
    assert out.reply.kind == "no_data" and out.state.step == conv.MANDI
    assert out.state.draft_crop == "IRRI" and (out.state.draft_quantity, out.state.draft_offer) == (40, 4500)
    out = say(mandi_no("Vehari"), out.state, provider)
    assert out.reply.kind == "offer" and provider.calls[-1] == ("offer", "IRRI", "Vehari", 40, 4500)


def test_service_not_ready_is_said_and_returns_to_the_menu():
    out, _ = chat("gandum bwp 10", provider=FakeProvider(not_ready=True))
    assert out.reply.kind == "not_ready" and out.state.step == conv.MENU


# ---------------------------------------------------------------- what is kept

def test_state_keeps_only_codes_and_numbers():
    out, _ = chat("gandum bahawalpur 100 man", "kuch aur poochna hai")
    for value in out.state.__dict__.values():
        assert value is None or isinstance(value, (int, float, datetime)) or value in (
            *conv.STEPS, conv.ADVICE, conv.COMPARE, conv.WHY, conv.RICE, "Wheat", "BahawalPur")


def test_unknown_step_is_rejected():
    with pytest.raises(ValueError):
        State(step="anything")


# ---------------------------------------------------------------- the buyer offer check

@pytest.mark.parametrize("text, call", [
    ("گندم بہاولپور 100 من آفر 3514", ("offer", "Wheat", "BahawalPur", 100.0, 3514.0)),
    ("gandum bwp 100 man offer Rs 3514", ("offer", "Wheat", "BahawalPur", 100.0, 3514.0)),
    ("offer 3514 gandum vehari 50", ("offer", "Wheat", "Vehari", 50.0, 3514.0)),
    ("گندم آفر ۳۵۱۴ روپے فی من بہاولپور 80 من", ("offer", "Wheat", "BahawalPur", 80.0, 3514.0)),
])
def test_free_text_offer_checks_at_once(text, call):
    out, provider = chat(text)
    assert out.reply.kind == "offer" and provider.calls == [call]


def test_an_offer_word_never_assumes_a_quantity_or_guesses_a_price():
    out, provider = chat("gandum bahawalpur offer 3514")          # no quantity: ask, do not assume 100
    assert out.reply.kind == "ask_quantity" and out.state.draft_offer == 3514 and provider.calls == []
    out, provider = chat("gandum bahawalpur 100 man offer 3500 offer 3600")   # two prices: ask
    assert out.reply.kind == "ask_offer" and out.state.draft_offer is None and provider.calls == []
    out, provider = chat("gandum bahawalpur 100 man aafar")       # an offer word without a price: ask
    assert out.reply.kind == "ask_offer" and provider.calls == []
    out, _ = chat("آفر")                                          # the word alone starts the flow
    assert out.reply.kind == "ask_crop" and out.state.pending == conv.OFFER


def test_a_bare_price_is_never_read_as_an_offer_without_the_offer_step():
    out, provider = chat("gandum bahawalpur 3514")   # a plain number is a quantity, as it always was
    assert out.reply.kind == "advice" and provider.calls == [("advice", "Wheat", "BahawalPur", 3514.0)]


@pytest.mark.parametrize("bad", ["0.0", "abc", "-5", "1000001", "3514 100"])
def test_invalid_offer_value_keeps_the_offer_step(bad):
    out, provider = chat("0", "1", crop_no("Wheat"), mandi_no("Vehari"), "100", bad)   # "0.0" is a price, not "0"
    assert out.reply.kind == "ask_offer" and out.reply.data["invalid"] is True
    assert out.state.step == conv.OFFER_STEP and provider.calls == []


@pytest.mark.parametrize("price", ["Rs 3514", "3514 روپے", "۳۵۱۴"])
def test_offer_step_accepts_currency_words_and_urdu_digits(price):
    _, provider = chat("0", "1", crop_no("Wheat"), mandi_no("Vehari"), "100", price)
    assert provider.calls == [("offer", "Wheat", "Vehari", 100.0, 3514.0)]


def test_after_an_offer_2_compares_against_that_offer_and_1_explains():
    out, provider = chat("gandum bwp 100 man offer 3514", "2")
    assert out.reply.kind == "offer_compare" and provider.calls[-1] == ("offer", "Wheat", "BahawalPur", 100.0, 3514.0)
    out, provider = chat("gandum bwp 100 man offer 3514", "1")
    assert out.reply.kind == "why" and ("explain", "Wheat", "BahawalPur") in provider.calls


def test_plain_advice_after_an_offer_forgets_the_offer():
    out, provider = chat("gandum bwp 100 man offer 3514", "kapas vehari 20", "2")
    assert out.reply.kind == "compare" and provider.calls[-1] == ("compare", "Cotton", "Vehari", 20.0)


def test_root_menu_order_is_offer_first():
    out, _ = chat("0")
    assert out.reply.choices == (("1", "offer"), ("2", "compare"), ("3", "why"), ("4", "alerts_on"),
                                 ("5", "alerts_off"), ("0", "menu"))


def test_legacy_3_still_stops_alerts_and_menu_3_is_why():
    out, _ = chat("3")
    assert out.alert_action is False
    out, _ = chat("0", "3")
    assert out.reply.kind == "ask_crop" and out.state.pending == conv.WHY and out.alert_action is None

"""Price alerts (task C9, blueprint UC-10): tell a farmer on WhatsApp when something changes for one of their crops.

A check looks at every farmer with alerts on and every crop in their profile. The advice comes from the same
service layer as the web app, and the decision is Owner B's `ml.decision.alert_check` (B8):

    SELL_SIGNAL  the signal changed (SELL <-> WAIT) since the last one the farmer was told
    PRICE_SPIKE  the latest price moved more in 4 weeks than the forecast band allows (not for frozen or stale
                 prices, where a jump is a reporting artifact or old news)

At most one alert per farmer every 7 days, across all their crops; the most important event is sent and the rest
are recorded as SUPPRESSED. The first check for a crop records its signal silently (BASELINE), so a later change
can be noticed. Dates are the check's as-of date, so replaying past weeks with `as_of` (the demo time machine)
behaves as those weeks did; the candidates are built here for that reason, with only data up to `as_of`.

SMS fallback (task A11): only for farmers with alerts on, only when WhatsApp delivery failed, and only when an SMS
provider is configured (backend/app/channels/sms.py; none is yet, so today there is no fallback). The SMS carries
the same alert in short Roman Urdu (sms_reply.alert_sms). The weekly limit, opt-out and the no-spike-on-stale-or-
frozen-price rules apply before any channel is chosen, so SMS adds no alert WhatsApp would not have sent.

Scheduling: FS_ALERTS_EVERY_HOURS > 0 runs the check in the background while the server is up (off by default).
`POST /api/alerts/run` runs it on demand (needs FS_ADMIN_TOKEN), with `dry_run` to see the result without sending.

WhatsApp only delivers free text within 24 hours of the farmer's last message. Outside that window Meta requires an
approved template: set FS_WA_ALERT_TEMPLATE to its name (one body parameter, filled with a one-line summary).
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from datetime import date

from backend.app import db, services
from backend.app.channels import reply, sms_reply
from backend.app.ids import CROP_FROM_DATA, CROP_TO_DATA, MANDI_FROM_DATA, MANDI_TO_DATA
from ml import decision

log = logging.getLogger("farmsight.alerts")

HEADER = "🔔 فارم سائٹ الرٹ"
FOOTER = "الرٹ بند کرنے کے لیے 'بند' لکھیں۔"
SIGNAL_CHANGED = "مشورہ بدل گیا ہے"

SendFn = Callable[[str, str, str], bool]   # (phone digits, full text, one-line summary) -> delivered?


def recent_change(crop_option: str, mandi: str, as_of: date | None) -> tuple[float | None, bool]:
    """(% change of the latest observed weekly price vs exactly 4 weeks earlier, either week frozen), using only
    weeks on or before `as_of`. The change is None when the earlier week has no real price."""
    from ml.forecast.history import history  # noqa: PLC0415 (Owner B; loads the weekly table once)
    h = history(crop_option, mandi, as_of, weeks=5)
    if h is None or len(h["weeks"]) < 5:
        return None, False
    earlier, latest = h["weeks"][0], h["weeks"][-1]
    frozen = earlier["frozen"] or latest["frozen"]
    if earlier["price"] is None or earlier["filled"] or latest["price"] is None:
        return None, frozen
    return round((latest["price"] / earlier["price"] - 1) * 100, 2), frozen


def _candidate(advice: dict, previous_signal: str | None, as_of: date | None) -> dict:
    """alert_check's input for one crop, like ml.decision.inputs.alert_candidate but honouring as_of."""
    change, frozen = recent_change(advice["crop_option"], advice["mandi"], as_of)
    now = advice["current_price"]
    return {
        "crop_option": advice["crop_option"], "mandi": advice["mandi"], "signal": advice["signal"],
        "previous_signal": previous_signal, "prices_as_of": advice["prices_as_of"], "change_4w_pct": change,
        "band_q10_pct": (advice["range"]["low"] / now - 1) * 100,
        "band_q90_pct": (advice["range"]["high"] / now - 1) * 100,
        "is_frozen": frozen, "is_stale": advice["is_stale"],
    }


def _why_ur(event: dict) -> str:
    if event["type"] == "SELL_SIGNAL":
        return SIGNAL_CHANGED
    moved = "بڑھا" if event["direction"] == "UP" else "گرا"
    return f"ریٹ 4 ہفتوں میں {abs(event['change_4w_pct']):.0f}% {moved}، جو عام اتار چڑھاؤ سے زیادہ ہے"


def message_for(event: dict, advice: dict) -> tuple[str, str]:
    """(full WhatsApp text, one-line summary for a template parameter: Meta rejects newlines there)."""
    text = reply.clip("\n\n".join([HEADER, f"{_why_ur(event)}:\n{reply.advice_text(advice)}", FOOTER]), 4096)
    crop = reply.CROP_UR.get(advice["crop_option"], advice["crop_option"])
    mandi = reply.MANDI_UR.get(advice["mandi"], advice["mandi"])
    summary = (f"{crop} {mandi}: {_why_ur(event)}۔ {reply.SIGNAL[advice['signal']][1]}، "
               f"آج {reply.rs(advice['current_price'])} فی من")
    return text, summary


def check_farmer(farmer: dict, today: date, as_of: date | None) -> dict:
    """What a check would do for this farmer today. Reads the database, never writes."""
    advice, candidates, baseline = {}, [], []
    for c in farmer["crops"]:
        crop, mandi = CROP_TO_DATA.get(c["crop"]), MANDI_TO_DATA.get(c["preferred_mandi"])
        if crop is None or mandi is None:
            continue
        try:
            a = services.get_advice(crop, mandi, c["harvest_quantity_maund"], as_of=as_of)
        except LookupError:
            continue   # no price for this crop at this mandi (e.g. IRRI at Rahim Yar Khan)
        advice[crop] = a
        last = db.last_alert(farmer["id"], c["crop"])
        if last is None:
            baseline.append(a)
        candidates.append(_candidate(a, last["signal"] if last else None, as_of))
    last_sent = db.last_sent_date(farmer["id"])
    result = decision.alert_check(candidates, date.fromisoformat(last_sent) if last_sent else None, today)
    return {"farmer_id": farmer["id"], "result": result, "advice": advice, "baseline": baseline}


def _item(event: dict, advice: dict) -> dict:
    return {"crop": CROP_FROM_DATA[event["crop_option"]], "mandi": MANDI_FROM_DATA[event["mandi"]],
            "kind": event["type"], "signal": advice["signal"], "current_price": advice["current_price"],
            "prices_as_of": advice["prices_as_of"], "change_4w_pct": event.get("change_4w_pct")}


def _record(farmer_id: str, event: dict, advice: dict, today: date, status: str, text: str) -> str:
    return db.add_alert(farmer_id, CROP_FROM_DATA[event["crop_option"]], MANDI_FROM_DATA[event["mandi"]],
                        event["type"], advice["signal"], advice["current_price"], today.isoformat(), status, text)


def run(send: SendFn | None = None, as_of: date | None = None, dry_run: bool = False,
        sms: SendFn | None = None) -> list[dict]:
    """One alert check for every farmer with alerts on. Returns what was (or, with dry_run, would be) sent."""
    today = as_of or date.today()
    send = send or whatsapp_send
    if sms is None and not dry_run:
        from backend.app.channels import sms as sms_channel  # noqa: PLC0415
        sms = sms_channel.alert_sender()   # None unless an SMS provider is configured
    results = []
    for farmer in db.list_alert_farmers():
        c = check_farmer(farmer, today, as_of)
        res = c["result"]
        out = {"farmer_id": farmer["id"], "items": [], "suppressed": len(res["suppressed"]),
               "skipped": {"NO_EVENT": "no_event", "ALERTED_THIS_WEEK": "weekly_limit"}.get(res["reason"])}
        if res["send"]:
            event = res["alert"]
            a = c["advice"][event["crop_option"]]
            text, summary = message_for(event, a)
            out["items"], out["message"] = [_item(event, a)], text
            if not dry_run:
                channel, ok = "whatsapp", bool(send(farmer["phone"], text, summary))
                if not ok and sms is not None:
                    text = sms_reply.alert_sms(event, a)
                    channel, ok = "sms", bool(sms(farmer["phone"], text, summary))
                status = "SENT" if ok else "FAILED"
                alert_id = _record(farmer["id"], event, a, today, status, text)
                db.log_message(farmer["id"], channel, "out", text, status, alert_id)
                out["status"], out["channel"] = status, channel
        if not dry_run:
            for e in res["suppressed"]:
                _record(farmer["id"], e, c["advice"][e["crop_option"]], today, "SUPPRESSED", "")
            sent_crop = res["alert"]["crop_option"] if res["send"] else None
            for a in c["baseline"]:
                if a["crop_option"] != sent_crop:
                    _record(farmer["id"], {"type": "BASELINE", "crop_option": a["crop_option"], "mandi": a["mandi"]},
                            a, today, "BASELINE", "")
        results.append(out)
    sent = sum(1 for r in results if r.get("status") == "SENT")
    log.info("alert check %s: %d farmers, %d sent%s", today, len(results), sent, " (dry run)" if dry_run else "")
    return results


def whatsapp_send(phone: str, text: str, summary: str) -> bool:
    from backend.app.channels import whatsapp  # noqa: PLC0415 (keeps the import graph one-way at start-up)
    settings = whatsapp.get_wa_settings()
    template = os.environ.get("FS_WA_ALERT_TEMPLATE", "")
    if template:
        message = {"type": "template", "template": {
            "name": template, "language": {"code": os.environ.get("FS_WA_ALERT_TEMPLATE_LANG", "ur")},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": summary[:1000]}]}]}}
    else:
        message = whatsapp.text_message(text)
    return whatsapp.GraphSender(settings).send(phone, message) is not False


async def loop(every_hours: float) -> None:
    """Background schedule while the server runs. A failed check is logged and retried next time."""
    while True:
        try:
            await asyncio.to_thread(run)
        except Exception:  # noqa: BLE001 (one bad check must not stop the schedule)
            log.exception("alert check failed")
        await asyncio.sleep(every_hours * 3600)

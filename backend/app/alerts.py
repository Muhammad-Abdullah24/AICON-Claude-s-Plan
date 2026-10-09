"""Price alerts (task C9, blueprint UC-10): tell a farmer on WhatsApp when the advice for one of their crops changes.

A check looks at every farmer with alerts on and every crop in their profile, through the same service layer as the
web app, so an alert always matches what the app says. A crop raises an alert when:

    FIRST         nothing was sent for it before
    SIGNAL_CHANGE the signal flipped (SELL <-> WAIT) since the last alert
    PRICE_MOVE    today's price moved at least PRICE_MOVE_PCT since the last alert

At most one message per farmer per week (all changed crops go in that one message). Dates are the check's as-of
date, so replaying past weeks with `as_of` (the demo time machine) behaves like the real weeks did.

The rule lives here until Owner B's `alert_check()` (task B8) exists in ml/decision; then this calls it instead.
SMS fallback: when WhatsApp fails and an SMS sender is given (task A11), the same text goes by SMS.

Scheduling: FS_ALERTS_EVERY_HOURS > 0 runs the check in the background while the server is up (off by default).
`POST /api/alerts/run` runs it on demand (needs FS_ADMIN_TOKEN), with `dry_run` to see the messages without sending.

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
from backend.app.channels import reply
from backend.app.ids import CROP_TO_DATA, MANDI_TO_DATA

log = logging.getLogger("farmsight.alerts")

PRICE_MOVE_PCT = 10.0
MIN_DAYS_BETWEEN = 7
HEADER = "🔔 فارم سائٹ الرٹ"
FOOTER = "الرٹ بند کرنے کے لیے 'بند' لکھیں۔"
WHY_UR = {
    "FIRST": "آپ کی فصل کا تازہ مشورہ",
    "SIGNAL_CHANGE": "مشورہ بدل گیا ہے",
    "PRICE_MOVE": "ریٹ میں بڑی تبدیلی",
}

SendFn = Callable[[str, str, str], bool]   # (phone digits, full text, one-line summary) -> delivered?


def _kind(last: dict | None, advice: dict) -> str | None:
    if last is None:
        return "FIRST"
    if last["signal"] != advice["signal"]:
        return "SIGNAL_CHANGE"
    if last["price"] and abs(advice["current_price"] / last["price"] - 1) * 100 >= PRICE_MOVE_PCT:
        return "PRICE_MOVE"
    return None


def _summary(items: list[dict]) -> str:
    """One line per alert for the WhatsApp template parameter (Meta rejects newlines there)."""
    parts = []
    for i in items:
        a = i["advice"]
        crop = reply.CROP_UR.get(a["crop_option"], a["crop_option"])
        mandi = reply.MANDI_UR.get(a["mandi"], a["mandi"])
        parts.append(f"{crop} {mandi}: {reply.SIGNAL[a['signal']][1]}، آج {reply.rs(a['current_price'])} فی من")
    return " | ".join(parts)


def message_for(items: list[dict]) -> str:
    blocks = [f"{WHY_UR[i['kind']]}:\n{reply.advice_text(i['advice'])}" for i in items]
    return reply.clip("\n\n".join([HEADER, *blocks, FOOTER]), 4096)


def check_farmer(farmer: dict, today: date, as_of: date | None) -> dict:
    """What an alert check would send this farmer today. Reads the database, never writes."""
    last_sent = db.last_sent_date(farmer["id"])
    if last_sent and 0 <= (today - date.fromisoformat(last_sent)).days < MIN_DAYS_BETWEEN:
        return {"farmer_id": farmer["id"], "items": [], "skipped": "weekly_limit"}
    items = []
    for c in farmer["crops"]:
        crop, mandi = CROP_TO_DATA.get(c["crop"]), MANDI_TO_DATA.get(c["preferred_mandi"])
        if crop is None or mandi is None:
            continue
        try:
            advice = services.get_advice(crop, mandi, c["harvest_quantity_maund"], as_of=as_of)
        except LookupError:
            continue   # no price for this crop at this mandi (e.g. IRRI at Rahim Yar Khan)
        kind = _kind(db.last_alert(farmer["id"], c["crop"]), advice)
        if kind:
            items.append({"crop": c["crop"], "mandi": c["preferred_mandi"], "kind": kind, "advice": advice})
    return {"farmer_id": farmer["id"], "items": items, "skipped": None if items else "no_change"}


def run(send: SendFn | None = None, as_of: date | None = None, dry_run: bool = False,
        sms: SendFn | None = None) -> list[dict]:
    """One alert check for every farmer with alerts on. Returns what was (or, with dry_run, would be) sent."""
    today = as_of or date.today()
    send = send or whatsapp_send
    results = []
    for farmer in db.list_alert_farmers():
        r = check_farmer(farmer, today, as_of)
        if r["items"]:
            text, summary = message_for(r["items"]), _summary(r["items"])
            r["message"] = text
            if not dry_run:
                channel, ok = "whatsapp", bool(send(farmer["phone"], text, summary))
                if not ok and sms is not None:
                    channel, ok = "sms", bool(sms(farmer["phone"], text, summary))
                status = "SENT" if ok else "FAILED"
                alert_id = None
                for i in r["items"]:
                    alert_id = db.add_alert(farmer["id"], i["crop"], i["mandi"], i["kind"], i["advice"]["signal"],
                                            i["advice"]["current_price"], today.isoformat(), status, text)
                db.log_message(farmer["id"], channel, "out", text, status, alert_id)
                r["status"], r["channel"] = status, channel
        results.append(r)
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

"""What WhatsApp and SMS would send, for the web app's "WhatsApp and SMS" page (GET /api/channels/preview).

Rendered by the channels' own code (the conversation engine's menu, reply.py, sms_reply.py) and the same
services.offer_check, so the page can never drift from the real messages. Nothing is sent and nothing is stored.
The status flags say only whether each piece is set up; no number, token or setting value is returned.
"""

from __future__ import annotations

from datetime import date

from backend.app.channels import conversation as conv
from backend.app.channels import sms, sms_reply, voice, whatsapp


def _body(message: dict) -> str:
    return message["text"]["body"] if message["type"] == "text" else message["interactive"]["body"]["text"]


def _buttons(message: dict) -> list[str]:
    if message["type"] != "interactive":
        return []
    return [b["reply"]["title"] for b in message["interactive"]["action"]["buttons"]]


def status() -> dict:
    s = whatsapp.get_wa_settings()
    return {
        "whatsapp_configured": bool(s.app_secret and s.access_token and s.phone_number_id),
        "sms_provider_configured": sms.configured(),
        "voice_notes_enabled": voice.pipeline() is not None,
    }


def preview(crop_option: str, mandi: str, quantity_maund: float, offer_price: float | None,
            as_of: date | None = None) -> dict:
    """The main menu on both channels, and, given an offer, the offer-check reply each would send."""
    from backend.app import services  # noqa: PLC0415 (the same answer as the web)

    menu = conv.Reply("menu", {}, conv.MAIN_CHOICES)
    out = {
        "whatsapp_menu": _body(whatsapp.render(menu, None, "")),
        "sms_menu": sms_reply.render(menu),
        "menu_choices": [code for _, code in conv.MAIN_CHOICES],
        "whatsapp_offer": None, "whatsapp_offer_buttons": [], "sms_offer": None, "sms_offer_parts": None,
        "status": status(),
    }
    if offer_price is not None:
        r = services.offer_check(crop_option, mandi, offer_price, quantity_maund, as_of)
        reply = conv.Reply("offer", {"crop_option": crop_option, "mandi": mandi, "result": r}, conv.post_choices(False))
        wa = whatsapp.render(reply, None, "")
        text = sms_reply.render(reply)
        out.update(whatsapp_offer=_body(wa), whatsapp_offer_buttons=_buttons(wa), sms_offer=text,
                   sms_offer_parts=sms_reply.parts(text), prices_as_of=r["reference_price_as_of"])
    return out

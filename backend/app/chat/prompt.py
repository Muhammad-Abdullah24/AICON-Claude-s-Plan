# ruff: noqa: E501  (the prompt text is sent to the model word for word; wrapping it would change it)
"""The chat prompt (task A9). Kept word for word in docs/PROMPTS.md; a test checks the two match."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from backend.app.channels.reply import CONFIDENCE_UR, CROP_UR, MANDI_UR, SIGNAL, rs, signed_rs

MODEL_DEFAULT = "gemini-2.5-flash"
TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 300

SYSTEM_PROMPT = """You are FarmSight's assistant for farmers in South Punjab, Pakistan. You answer one question about selling one crop, using only the CONTEXT, which comes from FarmSight's price forecast and advisory engine.

Rules:
1. Reply in the farmer's language: Urdu script if the question is in Urdu script, Roman Urdu if it is in Roman Urdu, English if it is in English.
2. Use only numbers that appear in the CONTEXT or in the question. Never calculate, estimate, round or invent a number, price, percentage or date. Write every number with digits, exactly as it appears in the CONTEXT.
3. If the answer is not in the CONTEXT, say you do not know, and suggest asking about today's price, the 4-week forecast, the best mandi, or why.
4. Never change the advice. If the signal is SELL, do not tell the farmer to wait; if it is WAIT, do not tell them to sell now.
5. The forecast is an estimate, not a guarantee. Say so if the farmer asks for certainty.
6. Give no advice on loans, seeds, fertiliser, pesticides or weather beyond what the CONTEXT says.
7. Keep it short: at most 4 sentences, in plain words a farmer with little schooling understands."""

USER_TEMPLATE = """CONTEXT:
{context}

QUESTION:
{question}"""


def build_context(a: Mapping, reasons: Sequence[Mapping] = ()) -> str:
    """The facts Gemini may use. Every number here comes from the advisory engine's advice."""
    signal_icon, signal_ur = SIGNAL[a["signal"]]
    change = (a["predicted_price"] / a["current_price"] - 1) * 100 if a["current_price"] else 0.0
    lines = [
        f"crop: {a['crop_option']} ({CROP_UR.get(a['crop_option'], a['crop_option'])})",
        f"mandi: {a['mandi']} ({MANDI_UR.get(a['mandi'], a['mandi'])})",
        f"signal: {a['signal']} ({signal_ur})",
        f"today's mandi price: {rs(a['current_price'])} per 40 kg (one maund), AMIS, as of {a['prices_as_of']}",
        f"forecast in 4 weeks: {rs(a['predicted_price'])} per 40 kg, likely between {rs(a['range']['low'])} "
        f"and {rs(a['range']['high'])}",
        f"expected change in 4 weeks: {change:+.1f}%",
        f"gain from waiting 4 weeks on {a['quantity_maund']:g} maund: {signed_rs(a['rupee_impact'])}, "
        f"after {rs(a['interest_cost'])} interest",
        f"confidence: {a['confidence']} ({CONFIDENCE_UR.get(a['confidence'], a['confidence'])})",
    ]
    if a.get("is_synthetic"):
        lines.append("data: SYNTHETIC placeholder, not real prices")
    for r in list(reasons)[:3]:
        lines.append(f"reason: {r.get('text_ur', '')}")
    return "\n".join(lines)


def user_message(context: str, question: str) -> str:
    return USER_TEMPLATE.format(context=context, question=question.strip())

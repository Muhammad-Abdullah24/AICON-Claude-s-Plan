# ruff: noqa: E501  (the prompt text is sent to the model word for word; wrapping it would change it)
"""The chat prompt (task A9). Kept word for word in docs/PROMPTS.md; a test checks the two match."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from backend.app.channels.reply import CONFIDENCE_UR, CROP_UR, MANDI_UR, SIGNAL, rs, signed_rs

MODEL_DEFAULT = "gemini-3.5-flash-lite"   # gemini-2.5-flash is closed to new keys; lite answers in ~1.3 s
TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 400

SYSTEM_PROMPT = """You are KASHT's farm assistant for small farmers in South Punjab, Pakistan. You answer the farmer's question about selling, waiting, borrowing or which crop to sow, using only the CONTEXT, which comes from KASHT's price, crop-plan, wait-plan and loan engines.

Rules:
1. Reply in the farmer's language: Urdu script if the question is in Urdu script, Roman Urdu if it is in Roman Urdu, English if it is in English. Never use Hindi (Devanagari) script.
2. Use only numbers that appear in the CONTEXT or in the question. Never calculate, estimate, round or invent a number, price, percentage or date. Write every number with digits, exactly as it appears in the CONTEXT.
3. Answer first, in one clear sentence (for example which crop to sow, sell now or wait, how much to borrow), then at most 2 short reasons from the CONTEXT.
4. For "what to sow", use the crop plan: match the month the farmer asks about to the crops' sowing months, and name the best crop of that season. If no tracked crop is sown in that month, say which tracked crop is sown next and when.
5. If the answer is not in the CONTEXT, say so in one sentence and suggest asking about selling, waiting, loans or which crop to sow.
6. Never change the advice: if the signal or plan says sell, do not tell the farmer to wait, and the reverse.
7. These are estimates, not guarantees; say so in a few words.
8. Keep it short: at most 4 sentences, in plain words a farmer with little schooling understands."""

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
        f"net gain from waiting 4 weeks on {a['quantity_maund']:g} maund: {signed_rs(a['rupee_impact'])} "
        f"(the interest cost of waiting, {rs(a['interest_cost'])}, has already been subtracted)",
        f"confidence: {a['confidence']} ({CONFIDENCE_UR.get(a['confidence'], a['confidence'])})",
    ]
    if a.get("is_synthetic"):
        lines.append("data: SYNTHETIC placeholder, not real prices")
    for r in list(reasons)[:3]:
        lines.append(f"reason: {r.get('text_ur', '')}")
    return "\n".join(lines)


MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")


def _months(span) -> str:
    a, b = span
    return MONTHS[a - 1] if a == b else f"{MONTHS[a - 1]} to {MONTHS[b - 1]}"


def extra_context(crop_plan: Mapping | None, wait: Mapping | None, loan: Mapping | None,
                  policy: str | None) -> str:
    """More facts from the app's engines, so the assistant can answer beyond today's sell signal."""
    lines = []
    if crop_plan:
        for s in crop_plan.get("seasons", []):
            crops = [i for i in crop_plan["items"] if i.get("season") == s["season"]]
            ranked = s["status"] == "RANKED"
            lines.append(f"crop plan, {s['season']} season: "
                         + ("crops ranked by estimated profit" if ranked else "too few tracked crops to rank"))
            for i in crops:
                lines.append(f"  {i['crop_option']}: sow {_months(i['sowing_months'])}, harvest {_months(i['harvest_months'])}, "
                             f"estimated profit {rs(i['profit_per_acre'])} per acre, price risk {i['risk_level']}"
                             + (f", rank {i['rank']}" if ranked and i.get('rank') else "")
                             + (", price data old" if i.get("is_stale") else ""))
    if wait:
        h = wait.get("history") or {}
        lines.append(f"wait plan for {wait.get('quantity_maund', 0):g} maund (own money, proper store): {wait['verdict']}"
                     + (f"; waiting paid in {h['wins']} of {h['n']} past years" if h else ""))
    if loan:
        lines.append(f"loan plan for wheat, per acre: cash needed before selling {rs(loan['input_need_rs'] / loan['acres'])}; "
                     "cheapest money first: Kissan Card (0% interest, up to Rs 30,000 per acre, up to Rs 150,000), "
                     "PM Youth loan (0%, age 21 to 45), Akhuwat (0%, small), bank about 16.5% a year, arhti about 66% a year")
    if policy:
        lines.append(f"wheat policy: {policy}")
    return "\n".join(lines)


def user_message(context: str, question: str) -> str:
    return USER_TEMPLATE.format(context=context, question=question.strip())

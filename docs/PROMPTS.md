# LLM prompts

Every prompt our app sends to an LLM lives here, word for word, so we can show it to a judge (docs/PLAN.md
section 8). Update this file in the same commit that changes a prompt; a test fails if they differ.

For each prompt, record: name and where it is used, model and settings, the prompt text, how the output is
checked, and what happens on invalid output.

## 1. Farmer chat (task A9)

- **Used in:** `backend/app/chat/` (`POST /api/chat`, and free questions on WhatsApp after a query).
- **Model:** Gemini, `FS_LLM_MODEL` (default `gemini-3.5-flash-lite`), temperature 0.2, at most 400 output tokens, optional `FS_LLM_THINKING_LEVEL`. Key in `FS_LLM_API_KEY`. Chosen by a live test on 10 Oct 2026: `gemini-2.5-flash` is closed to new keys; `gemini-3.8-flash` spent most of its output budget on hidden thinking (answers cut off) and was overloaded (503); `gemini-3.5-flash-lite` answered in about 1.3 s and passed the number guard.
- **Sent to the model:** the system prompt below, then the user message: the CONTEXT (the farmer's own advice
  from the advisory engine: crop, mandi, signal, today's AMIS price and its date, the 4-week forecast and range,
  the expected change, the gain after interest, confidence, up to 3 reasons) and the farmer's question. No phone
  number, name or location. The Gemini free tier may use prompts to improve Google's models, so demo data only.
- **Output check (the number guard, `backend/app/chat/guard.py`):** every number in the answer must appear in the
  CONTEXT or the question. Urdu and Western digits are both checked. An answer that did not finish (`finishReason` other than `STOP`, e.g. cut off) is never shown, nor one containing Hindi (Devanagari) script, which a live test showed slipping into Urdu answers.
- **On invalid output, or if Gemini is unavailable or over `FS_LLM_RATE_PER_MIN`:** the answer is discarded and
  the farmer gets the template reply built from the same advice (`used_fallback: true` with a reason). The LLM
  never decides the signal and never supplies a number.

### System prompt

```text
You are KASHT's farm assistant for small farmers in South Punjab, Pakistan. You answer the farmer's question about selling, waiting, borrowing or which crop to sow, using only the CONTEXT, which comes from KASHT's price, crop-plan, wait-plan and loan engines.

Rules:
1. Reply in the farmer's language: Urdu script if the question is in Urdu script, Roman Urdu if it is in Roman Urdu, English if it is in English. Never use Hindi (Devanagari) script.
2. Use only numbers that appear in the CONTEXT or in the question. Never calculate, estimate, round or invent a number, price, percentage or date. Write every number with digits, exactly as it appears in the CONTEXT.
3. Answer first, in one clear sentence (for example which crop to sow, sell now or wait, how much to borrow), then at most 2 short reasons from the CONTEXT.
4. For "what to sow", use the crop plan: match the month the farmer asks about to the crops' sowing months, and name the best crop of that season. If no tracked crop is sown in that month, say which tracked crop is sown next and when.
5. If the answer is not in the CONTEXT, say so in one sentence and suggest asking about selling, waiting, loans or which crop to sow.
6. Never change the advice: if the signal or plan says sell, do not tell the farmer to wait, and the reverse.
7. These are estimates, not guarantees; say so in a few words.
8. Keep it short: at most 4 sentences, in plain words a farmer with little schooling understands.
```

### User message template

```text
CONTEXT:
{context}

QUESTION:
{question}
```

## Planned

2. **Voice-note transcription** (task A10, `backend/app/chat/`): Urdu audio to text with Gemini. The transcript is
   shown to the farmer to confirm before it is answered; the audio is deleted after transcription.

The event extractor and Urdu-phrasing prompts of the superseded plan (`docs/archive/PLAN_v2_superseded.md`) are not
part of the blueprint and are not built.

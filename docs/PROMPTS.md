# LLM prompts

Every prompt our app sends to an LLM lives here, word for word, so we can show it to a judge (PLAN.md sections 9.5 and 20). Update this file in the same commit that changes a prompt.

For each prompt, record:

- **Name and where it is used** (file path)
- **Model and settings** (temperature, JSON mode)
- **The prompt text**
- **The output schema** it is checked against
- **What happens on invalid output**

## Prompts

None yet. The walking skeleton makes no LLM calls.

Planned:

1. **Event extractor** (`ml/events/`): headline → structured event (PLAN.md 9.2 and 9.5). Owner A.
2. **WhatsApp message parser fallback** (`backend/`): free text → crop, mandi, quantity, used only when keyword matching fails (PLAN.md 12.3). Owner C.
3. **Urdu phrasing** (`backend/`): smooths template reasons. Never changes a number (PLAN.md 7.8 and 13). Owner C.

# SMS through TextBee: operator setup

TextBee turns an Android phone with a Pakistani SIM into our SMS gateway. The phone sends our replies from its own
SIM and forwards the SMS it receives to the backend's webhook. Code: `backend/app/channels/textbee.py` (gateway),
`backend/app/channels/sms.py` (phone numbers, SMS form of a reply). An SMS gets the same conversation as WhatsApp:
the same parser, commands and Urdu replies.

**This is a pilot gateway, not a carrier-grade service.** One phone, one SIM, the SIM's own SMS limits and charges,
and nothing works while the phone is off, offline or out of signal. TextBee's "sent" only means the phone and the
carrier accepted the message; delivery reports are not always available. Never promise a farmer delivery.

No secret goes in this file, in git or in chat. Real values live only in the TextBee dashboard and in the backend
host's environment settings (Render).

## 1. The phone

1. Use an Android phone with an active Pakistani SIM that has SMS balance. Install the TextBee app from
   [textbee.dev](https://textbee.dev).
2. Sign in to the TextBee dashboard, register (pair) the phone from the app, and leave it plugged in and online.
3. In the app, turn on **Receive SMS**. Grant the SMS permission when Android asks.
4. In Android settings, exempt TextBee from **battery optimisation**, otherwise Android stops it in the background.

## 2. API key and environment

1. In the TextBee dashboard, create an **API key**. Note the phone's **device ID** (Devices list).
2. Make a webhook signing secret of 20+ characters, e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. Set these on the backend host (Render: Environment), never in the repo:

   | Variable | Value |
   |---|---|
   | `SMS_PROVIDER` | `textbee` (empty = SMS off) |
   | `TEXTBEE_API_KEY` | the API key |
   | `TEXTBEE_DEVICE_ID` | the phone's device ID (events from any other device are refused) |
   | `TEXTBEE_BASE_URL` | `https://api.textbee.dev/api/v1` (the default) |
   | `TEXTBEE_WEBHOOK_SECRET` | the signing secret from step 2 |

4. **Deploy the backend first**, so the webhook exists before TextBee calls it. Without the secret it answers 503
   and without `SMS_PROVIDER`/`TEXTBEE_API_KEY` it answers 503 too; TextBee then retries later.

## 3. The webhook

In the TextBee dashboard, **Webhooks → Add webhook**:

- Delivery URL: `https://<backend host>/api/channels/sms/textbee/webhook`
  (today: `https://farmsight-api-auat.onrender.com/api/channels/sms/textbee/webhook`)
- Signing secret: the same value as `TEXTBEE_WEBHOOK_SECRET`
- Events: **only `MESSAGE_RECEIVED`** to start with. Sent/delivered/failed reports are acknowledged and ignored.

How the backend treats each call:

| Situation | Answer | Reply SMS |
|---|---|---|
| Missing or wrong `X-Signature` | 401 | none |
| Secret or sending not configured | 503 (TextBee retries) | none |
| Not `MESSAGE_RECEIVED` | 200 `ignored` | none |
| Malformed event | 422 | none |
| Another device ID | 403 | none |
| Sender not a Pakistani mobile (short codes, banks, carriers) | 200 `ignored` | none |
| A new event | 200 `accepted` | exactly one |
| The same `idempotencyKey` again (a retry) | 200 `duplicate` | none |

A reply is never re-sent, even after a timeout, because a second SMS is worse than none.

## 4. Test from a second phone

From any other Pakistani mobile, text the gateway phone's number:

1. `hi` (or `مدد`): the help message (how to ask, the crops and mandis).
2. `گندم بہاولپور 100 من` (or `gandum bahawalpur 100 mann`): the advice, ending with
   `1 کیوں؟ | 2 منڈیاں | 3 الرٹ بند`.
3. `1`: the reasons. Check that **one** SMS arrives for each message sent.
4. `2`: the mandi comparison. (`3` turns alerts off; `شروع` turns them back on.)
5. Retry: in the TextBee dashboard's webhook delivery log, resend one delivered event. The backend answers
   `duplicate`, and no second SMS arrives.
6. On Render's log, check that only the last three digits of a number appear, and no message text.

## Limits to know

- **Replies are de-duplicated in the SQLite database.** On a host without a persistent disk (Render's free plan),
  a restart forgets the keys; a TextBee retry of an older event after a restart could then be answered again.
  Put `FS_DB_PATH` on a persistent disk for anything beyond a demo.
- The conversation memory (what "1" refers to) is in memory, as for WhatsApp: a restart forgets it, and the farmer
  sends the query again.
- Long replies are clipped at 670 characters (10 SMS parts in Urdu). Each part costs the SIM one SMS.
- After a query, a free question (not a command, crop or mandi) goes to the same guarded chat as WhatsApp, which
  needs `FS_LLM_API_KEY`. Before any query, it gets the help message.

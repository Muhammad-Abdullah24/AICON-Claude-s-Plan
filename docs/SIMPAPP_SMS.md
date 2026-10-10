# SMS through the "SMS Gateway API" Android app (Simpapp): operator setup

The app turns an Android phone with a Pakistani SIM into our SMS gateway: it forwards each SMS the phone receives to
our webhook, and sends our reply from the same SIM. Code: `backend/app/channels/simpapp.py`. An SMS gets the same
conversation as WhatsApp (same parser, commands and Urdu replies); `backend/app/channels/sms.py` turns a reply into
SMS text, with the WhatsApp buttons as `1 کیوں؟ | 2 منڈیاں | 3 الرٹ بند`.

**Pilot gateway, not carrier-grade.** One phone and one SIM: nothing works while it is off, offline or out of
signal, and the SIM's own limits and charges apply. The app's "queued"/"sent" is not "delivered".

No key or token goes in git, in this file or in chat: only in the app and in Render's Environment settings.

## 1. Backend (Render → farmsight-api → Environment)

| Variable | Value |
|---|---|
| `SMS_PROVIDER` | `simpapp` (empty = SMS off) |
| `SIMPAPP_SMS_API_URL` | `https://europe-west1-sms-gateway-api-simpapp.cloudfunctions.net/api_sms_send` (V1, `X-API-Key`). The V2 URL `…/api_v2_sms_send` also works (Bearer token). |
| `SIMPAPP_SMS_API_KEY` | the key from the app: **API Gateway → Generate API Key** |
| `SIMPAPP_WEBHOOK_SECRET` | 20+ random characters, e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

Save (Render redeploys), then check `https://farmsight-api-auat.onrender.com/health` says `{"status":"ok"}`.
Without these the webhook answers 503 and sends nothing.

## 2. The webhook URL

```
https://farmsight-api-auat.onrender.com/api/channels/sms/simpapp/webhook?token=<SIMPAPP_WEBHOOK_SECRET>
```

The vendor documents no webhook signature, so this token in the URL is the only check that a call comes from our
phone. Keep the full URL secret. Our server blanks the token out of its own logs; Render's request logs are outside
our control.

## 3. The phone

1. Install **SMS Gateway API** on an Android phone with an active Pakistani SIM, mobile data or Wi-Fi, and SMS
   balance. Grant the SMS permissions; exempt the app from battery optimisation; keep it plugged in.
2. **API Gateway → Generate API Key**: put it in Render as `SIMPAPP_SMS_API_KEY` (step 1), nowhere else.
3. **Incoming SMS Forwarding**: paste the webhook URL from step 2 as the endpoint URL and turn forwarding on.
4. **API Gateway → Webhook URL** (delivery status): optional. The same URL works; we acknowledge the reports and
   do nothing with them.

Our webhook never returns `sms_text`, so the app's own auto-reply never sends a second SMS: the one reply goes
through the send API.

## 4. Test from a second phone

Text the gateway phone's number from another Pakistani mobile and expect **one SMS per message**:

| Send | Expected reply |
|---|---|
| `0` or `hi` (first message) | the help text: how to write crop, mandi and quantity (`0` is not a command; after a query it is treated as a question) |
| `گندم بہاولپور 100 من` | today's advice, ending with `1 کیوں؟ \| 2 منڈیاں \| 3 الرٹ بند` |
| `1` | why: the reasons for the advice |
| `2` | the mandi comparison |
| `3` | alerts off (`شروع` turns them on again) |

Duplicate check: the app identifies a message only by sender, timestamp and text, so a resend of the same event
(same `timestamp`) is answered `duplicate` and gets no reply. To test it without the phone, post the same
`incoming_sms` body twice to the webhook URL: the second answer is `{"status":"duplicate"}`.

## Limits

- No message id from the vendor: two identical texts from one number in the same second count as one.
- De-duplication lives in SQLite; on Render's free plan a restart forgets it (and the demo farmer is re-seeded).
- Replies are clipped at 670 characters (10 SMS parts in Urdu). Every part costs the SIM one SMS.

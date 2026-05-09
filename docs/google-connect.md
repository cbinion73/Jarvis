# Google Connect

JARVIS can now connect directly to personal Gmail and Google Calendar in read-only mode.

## What This Enables

- unread Gmail visibility inside the `Catalyst` packet
- upcoming Google Calendar events inside the same packet
- local OAuth token storage for the JARVIS runtime

This first pass is intentionally read-only. JARVIS can see email and calendar context, but it does not send mail or edit events yet.

## One-Time Setup

1. Create a Google Cloud OAuth client.
2. Use an OAuth client that allows this redirect URI:

```text
http://127.0.0.1:8787/google/callback
```

3. Download the client secret JSON.
4. Place it at:

```text
config/google_client_secret.json
```

You can override the paths with environment variables:

```text
JARVIS_GOOGLE_CLIENT_SECRET
JARVIS_GOOGLE_TOKEN_PATH
```

## Connect Flow

1. Start JARVIS:

```bash
source /Users/chris/Desktop/CODE/JARVIS/.venv/bin/activate
python -m jarvis serve --host 127.0.0.1 --port 8787
```

2. Open the local shell at [http://127.0.0.1:8787](http://127.0.0.1:8787).
3. Open the `Catalyst` packet.
4. Click `Connect Google`.
5. Complete Google sign-in and consent.

JARVIS stores the resulting local token at:

```text
data/google/google_token.json
```

## CLI Checks

```bash
python -m jarvis google-status
python -m jarvis google-summary
```

## Current Scope

The current OAuth scopes are:

- Gmail read-only
- Calendar read-only

That means the integration is safe to wire now while we keep approvals and writes for a later pass.

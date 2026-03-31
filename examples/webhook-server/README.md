# Aira Webhook Server

Minimal Flask server that receives and verifies Aira webhook events.

## Setup

```bash
pip install aira-sdk flask
```

## Environment

Set your webhook secret (from the Aira dashboard webhook configuration):

```python
WEBHOOK_SECRET = "whsec_xxx"
```

## Run

```bash
python server.py
```

The server listens on `http://localhost:5000/webhook`.

## Supported Events

- **action.notarized** -- Fired when an action receives a cryptographic receipt
- **case.complete** -- Fired when a case is fully resolved

## Testing Locally

Use a tunnel (e.g., ngrok) to expose your local server:

```bash
ngrok http 5000
```

Then configure the public URL as your webhook endpoint in the Aira dashboard.

## Signature Verification

Every incoming request is verified using `X-Aira-Signature` header and your webhook secret. Requests with invalid signatures are rejected with 401.

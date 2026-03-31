"""Minimal webhook receiver that verifies Aira webhook signatures."""
# pip install aira-sdk flask
from flask import Flask, request, jsonify
from aira.extras.webhooks import verify_signature, parse_event

app = Flask(__name__)
WEBHOOK_SECRET = "whsec_xxx"  # From your Aira webhook config


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    signature = request.headers.get("X-Aira-Signature", "")
    if not verify_signature(request.data, signature, WEBHOOK_SECRET):
        return jsonify({"error": "Invalid signature"}), 401

    event = parse_event(request.data)
    print(f"Received: {event.event_type}")
    print(f"Data: {event.data}")

    # Handle specific events
    if event.event_type == "action.notarized":
        print(f"Action notarized: {event.data.get('action_id')}")
    elif event.event_type == "case.complete":
        print(f"Case completed: {event.data.get('case_id')}")

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(port=5000)

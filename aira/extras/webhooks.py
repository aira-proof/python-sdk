"""Webhook signature verification and event parsing for Aira webhooks."""

import hashlib
import hmac
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class WebhookEventType(str, Enum):
    """Known Aira webhook event types."""
    CASE_COMPLETE = "case.complete"
    CASE_REQUIRES_REVIEW = "case.requires_human_review"
    ACTION_NOTARIZED = "action.notarized"
    ACTION_AUTHORIZED = "action.authorized"
    AGENT_REGISTERED = "agent.registered"
    AGENT_DECOMMISSIONED = "agent.decommissioned"
    EVIDENCE_SEALED = "evidence.sealed"
    ESCROW_DEPOSITED = "escrow.deposited"
    ESCROW_RELEASED = "escrow.released"
    ESCROW_DISPUTED = "escrow.disputed"
    COMPLIANCE_SNAPSHOT = "compliance.snapshot_created"


@dataclass
class WebhookEvent:
    """Parsed webhook event."""
    event_type: str
    data: dict[str, Any]
    timestamp: str | None = None
    delivery_id: str | None = None


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature. Signature format: sha256={hex_digest}"""
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def parse_event(payload: bytes) -> WebhookEvent:
    """Parse raw webhook payload into a WebhookEvent."""
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Invalid webhook payload: {e}") from e

    return WebhookEvent(
        event_type=data.get("event", "unknown"),
        data=data.get("data", data),
        timestamp=data.get("timestamp"),
        delivery_id=data.get("delivery_id"),
    )

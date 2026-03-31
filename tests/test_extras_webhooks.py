"""Tests for aira.extras.webhooks — signature verification and event parsing."""

import hashlib
import hmac
import inspect
import json

import pytest

from aira.extras.webhooks import (
    WebhookEvent,
    WebhookEventType,
    parse_event,
    verify_signature,
)


SECRET = "test-webhook-secret"


def _sign(payload: bytes, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ── verify_signature ────────────────────────────────────────────────


def test_verify_valid_signature():
    payload = b'{"event":"case.complete","data":{}}'
    sig = _sign(payload)
    assert verify_signature(payload, sig, SECRET) is True


def test_verify_invalid_signature():
    payload = b'{"event":"case.complete","data":{}}'
    sig = _sign(payload, secret="wrong-secret")
    assert verify_signature(payload, sig, SECRET) is False


def test_verify_tampered_payload():
    original = b'{"event":"case.complete","data":{}}'
    sig = _sign(original)
    tampered = b'{"event":"case.complete","data":{"injected":true}}'
    assert verify_signature(tampered, sig, SECRET) is False


def test_verify_missing_prefix():
    payload = b'{"event":"case.complete","data":{}}'
    digest = hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()
    # No "sha256=" prefix — should be rejected
    assert verify_signature(payload, digest, SECRET) is False


# ── parse_event ─────────────────────────────────────────────────────


def test_parse_event_valid():
    payload = json.dumps({
        "event": "action.notarized",
        "data": {"action_id": "a-1"},
        "timestamp": "2026-03-31T00:00:00Z",
        "delivery_id": "d-42",
    }).encode()
    evt = parse_event(payload)
    assert isinstance(evt, WebhookEvent)
    assert evt.event_type == "action.notarized"
    assert evt.data == {"action_id": "a-1"}
    assert evt.timestamp == "2026-03-31T00:00:00Z"
    assert evt.delivery_id == "d-42"


def test_parse_event_invalid_json():
    with pytest.raises(ValueError, match="Invalid webhook payload"):
        parse_event(b"not-json{{{")


# ── WebhookEventType enum ──────────────────────────────────────────


def test_event_type_enum_values():
    expected = {
        "CASE_COMPLETE": "case.complete",
        "CASE_REQUIRES_REVIEW": "case.requires_human_review",
        "ACTION_NOTARIZED": "action.notarized",
        "ACTION_AUTHORIZED": "action.authorized",
        "AGENT_REGISTERED": "agent.registered",
        "AGENT_DECOMMISSIONED": "agent.decommissioned",
        "EVIDENCE_SEALED": "evidence.sealed",
        "ESCROW_DEPOSITED": "escrow.deposited",
        "ESCROW_RELEASED": "escrow.released",
        "ESCROW_DISPUTED": "escrow.disputed",
        "COMPLIANCE_SNAPSHOT": "compliance.snapshot_created",
    }
    for name, value in expected.items():
        assert WebhookEventType[name].value == value
    assert len(WebhookEventType) == len(expected)


# ── timing-safe comparison ──────────────────────────────────────────


def test_timing_safe_comparison():
    """verify_signature must use hmac.compare_digest, not == ."""
    src = inspect.getsource(verify_signature)
    assert "compare_digest" in src, "verify_signature should use hmac.compare_digest"

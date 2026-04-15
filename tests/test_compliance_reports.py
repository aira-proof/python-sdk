"""Tests for the Phase 1 compliance report SDK methods."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from aira import (
    ActionExplanation,
    Aira,
    AsyncAira,
    ComplianceReport,
    ComplianceReportVerification,
    ExplanationVerification,
    FRAMEWORK_ANNEX_IV,
    FRAMEWORK_ART6,
    FRAMEWORK_ART9,
    FRAMEWORK_ART12,
)
from aira.client import AiraError


def _resp(data, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=data,
        request=httpx.Request("GET", "http://test"),
    )


def _binary_resp(data: bytes, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        content=data,
        request=httpx.Request("GET", "http://test"),
    )


REPORT_OK = {
    "id": "rep-1",
    "framework": "eu_ai_act_art12",
    "status": "ready",
    "org_uuid": "org-1",
    "period_start": "2026-04-01T00:00:00",
    "period_end": "2026-04-30T00:00:00",
    "action_uuid": None,
    "agent_filter": None,
    "receipt_count": 2,
    "pdf_size_bytes": 1234,
    "content_hash": "sha256:abc",
    "signature": "ed25519:sig",
    "signing_key_id": "k1",
    "timestamp_token": "ts-token",
    "timestamp_token_present": True,
    "report_metadata": {"article": "12", "total_actions": 2},
    "error_message": None,
    "generated_at": "2026-04-30T01:00:00Z",
    "created_at": "2026-04-30T00:59:00Z",
    "request_id": "req-1",
}


def _client() -> Aira:
    return Aira(api_key="aira_live_" + "x" * 32, base_url="http://test")


def _async_client() -> AsyncAira:
    return AsyncAira(api_key="aira_live_" + "x" * 32, base_url="http://test")


# ─── sync ────────────────────────────────────────────────────────────


class TestSyncComplianceReports:
    def test_create_report(self):
        aira = _client()
        with patch.object(aira._client, "post", return_value=_resp(REPORT_OK)):
            report = aira.create_compliance_report(
                framework="eu_ai_act_art12",
                period_start="2026-04-01T00:00:00",
                period_end="2026-04-30T00:00:00",
            )
        assert isinstance(report, ComplianceReport)
        assert report.framework == "eu_ai_act_art12"
        assert report.status == "ready"
        assert report.receipt_count == 2

    def test_get_report(self):
        aira = _client()
        with patch.object(aira._client, "get", return_value=_resp(REPORT_OK)):
            report = aira.get_compliance_report("rep-1")
        assert report.id == "rep-1"

    def test_list_reports(self):
        aira = _client()
        listing = {
            "items": [REPORT_OK],
            "total": 1,
            "limit": 50,
            "offset": 0,
            "request_id": "req-2",
        }
        with patch.object(aira._client, "get", return_value=_resp(listing)):
            result = aira.list_compliance_reports()
        assert result["total"] == 1
        assert len(result["items"]) == 1

    def test_download_report(self):
        aira = _client()
        with patch.object(
            aira._client, "get", return_value=_binary_resp(b"%PDF-1.4 fake")
        ):
            content = aira.download_compliance_report("rep-1")
        assert content.startswith(b"%PDF")

    def test_verify_report(self):
        aira = _client()
        body = {
            "report_uuid": "rep-1",
            "valid": True,
            "checks": {"content_hash_matches": True, "signature_valid": True},
            "descriptor": {"framework": "eu_ai_act_art12"},
            "request_id": "req-3",
        }
        with patch.object(aira._client, "get", return_value=_resp(body)):
            result = aira.verify_compliance_report("rep-1")
        assert isinstance(result, ComplianceReportVerification)
        assert result.valid is True

    def test_get_action_explanation(self):
        aira = _client()
        body = {
            "action": {"id": "act-1"},
            "policy_chain": [],
            "approval_chain": [],
            "receipt": {"receipt_uuid": "rec-1"},
            "regulation": {"framework": "eu_ai_act"},
            "_envelope": {
                "alg": "Ed25519",
                "signing_key_id": "aira-signing-key-v1",
                "content_hash": "sha256:abc",
                "signature": "ed25519:sig",
                "generated_at": "2026-04-12T00:00:00Z",
            },
            "request_id": "req-4",
        }
        with patch.object(aira._client, "get", return_value=_resp(body)):
            explanation = aira.get_action_explanation("act-1")
        assert isinstance(explanation, ActionExplanation)
        assert explanation.action["id"] == "act-1"
        # The underscore-prefixed wire key is surfaced as ``envelope``
        # on the dataclass.
        assert explanation.envelope is not None
        assert explanation.envelope["signature"] == "ed25519:sig"

    def test_verify_action_explanation_roundtrips_wire_key(self):
        aira = _client()
        # Fake explanation shaped like what get_action_explanation would
        # return to the caller (with ``envelope`` attribute).
        exp = ActionExplanation(
            action={"id": "act-1"},
            policy_chain=[],
            approval_chain=[],
            regulation={"framework": "eu_ai_act"},
            request_id="req-4",
            receipt=None,
            envelope={
                "alg": "Ed25519",
                "signing_key_id": "aira-signing-key-v1",
                "content_hash": "sha256:abc",
                "signature": "ed25519:sig",
                "generated_at": "2026-04-12T00:00:00Z",
            },
        )
        verify_body = {
            "valid": True,
            "checks": {
                "key_known": True,
                "content_hash_matches": True,
                "signature_valid": True,
            },
            "signing_key_id": "aira-signing-key-v1",
            "request_id": "req-v",
        }
        captured: dict = {}

        def _post(url, json=None, **_kw):
            captured["url"] = url
            captured["json"] = json
            return _resp(verify_body)

        with patch.object(aira._public_client, "post", side_effect=_post):
            result = aira.verify_action_explanation(exp)

        assert isinstance(result, ExplanationVerification)
        assert result.valid is True
        assert result.signing_key_id == "aira-signing-key-v1"
        assert captured["url"] == "/verify/explanation"
        # The client must post back ``_envelope`` (the signed-canonical
        # key), not the Pythonic ``envelope`` — otherwise the server's
        # hash recomputation fails.
        sent = captured["json"]["explanation"]
        assert "_envelope" in sent
        assert "envelope" not in sent
        assert "request_id" not in sent

    def test_create_annex_iv_report(self):
        """Annex IV framework must POST through the same endpoint and
        round-trip the constant into the returned report."""
        aira = _client()
        annex_iv_report = {
            **REPORT_OK,
            "id": "rep-annex",
            "framework": FRAMEWORK_ANNEX_IV,
            "report_metadata": {
                "annex": "IV",
                "article_reference": "11",
                "total_actions": 0,
                "sections": {"section_1_general": {"provider_name": "Acme"}},
            },
        }
        captured: dict = {}

        def _post(url, json=None, **_kw):
            captured["url"] = url
            captured["json"] = json
            return _resp(annex_iv_report)

        with patch.object(aira._client, "post", side_effect=_post):
            report = aira.create_compliance_report(
                framework=FRAMEWORK_ANNEX_IV,
                period_start="2026-04-01T00:00:00",
                period_end="2026-04-30T00:00:00",
            )
        assert isinstance(report, ComplianceReport)
        assert report.framework == "eu_ai_act_annex_iv"
        assert report.report_metadata is not None
        assert report.report_metadata["annex"] == "IV"
        # The constant the caller passed is forwarded as the body value.
        assert captured["json"]["framework"] == "eu_ai_act_annex_iv"

    def test_framework_constants_values(self):
        """Pin the wire values so a backend rename wouldn't silently
        succeed in CI."""
        assert FRAMEWORK_ART12 == "eu_ai_act_art12"
        assert FRAMEWORK_ART9 == "eu_ai_act_art9"
        assert FRAMEWORK_ART6 == "eu_ai_act_art6"
        assert FRAMEWORK_ANNEX_IV == "eu_ai_act_annex_iv"

    def test_verify_action_explanation_accepts_dict(self):
        """Raw dict input path — callers can load a saved JSON file
        directly without constructing the dataclass first."""
        aira = _client()
        raw = {
            "action": {"id": "act-1"},
            "policy_chain": [],
            "approval_chain": [],
            "regulation": {},
            "receipt": None,
            "_envelope": {"signature": "ed25519:sig"},
            "request_id": "should-be-stripped",
        }
        captured: dict = {}

        def _post(url, json=None, **_kw):
            captured["json"] = json
            return _resp(
                {"valid": False, "checks": {"envelope_present": "bad"},
                 "request_id": "r"}
            )

        with patch.object(aira._public_client, "post", side_effect=_post):
            aira.verify_action_explanation(raw)
        sent = captured["json"]["explanation"]
        assert "_envelope" in sent
        assert "request_id" not in sent

    def test_download_explanation_pdf(self):
        aira = _client()
        with patch.object(
            aira._client, "get", return_value=_binary_resp(b"%PDF-1.4")
        ):
            content = aira.download_action_explanation_pdf("act-1")
        assert content.startswith(b"%PDF")

    def test_download_report_blocks_in_offline_mode(self):
        aira = Aira(
            api_key="aira_live_" + "x" * 32,
            base_url="http://test",
            offline=True,
        )
        with pytest.raises(AiraError):
            aira.download_compliance_report("rep-1")


# ─── async ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAsyncComplianceReports:
    async def test_create_report(self):
        aira = _async_client()
        with patch.object(
            aira._client,
            "post",
            return_value=_resp(REPORT_OK),
        ):
            report = await aira.create_compliance_report(
                framework="eu_ai_act_art12",
                period_start="2026-04-01T00:00:00",
                period_end="2026-04-30T00:00:00",
            )
        assert report.framework == "eu_ai_act_art12"

    async def test_get_report(self):
        aira = _async_client()
        with patch.object(
            aira._client, "get", return_value=_resp(REPORT_OK)
        ):
            report = await aira.get_compliance_report("rep-1")
        assert report.id == "rep-1"

    async def test_download_report(self):
        aira = _async_client()
        with patch.object(
            aira._client, "get", return_value=_binary_resp(b"%PDF-1.4")
        ):
            content = await aira.download_compliance_report("rep-1")
        assert content.startswith(b"%PDF")

    async def test_get_action_explanation(self):
        aira = _async_client()
        body = {
            "action": {"id": "act-1"},
            "policy_chain": [],
            "approval_chain": [],
            "receipt": None,
            "regulation": {"framework": "eu_ai_act"},
            "_envelope": {"signature": "ed25519:sig"},
            "request_id": "req-5",
        }
        with patch.object(aira._client, "get", return_value=_resp(body)):
            explanation = await aira.get_action_explanation("act-1")
        assert explanation.action["id"] == "act-1"
        assert explanation.receipt is None
        assert explanation.envelope == {"signature": "ed25519:sig"}

    async def test_verify_action_explanation(self):
        aira = _async_client()
        exp = ActionExplanation(
            action={"id": "act-1"},
            policy_chain=[],
            approval_chain=[],
            regulation={},
            request_id="req-5",
            receipt=None,
            envelope={"signature": "ed25519:sig"},
        )
        verify_body = {
            "valid": True,
            "checks": {"signature_valid": True},
            "signing_key_id": "k1",
            "request_id": "req-v",
        }
        with patch.object(
            aira._public_client, "post", return_value=_resp(verify_body)
        ):
            result = await aira.verify_action_explanation(exp)
        assert isinstance(result, ExplanationVerification)
        assert result.valid is True


# ─── Retry behavior ────────────────────────────────────────────────


class TestDownloadRetry:
    def test_download_retries_on_5xx_then_succeeds(self):
        """Three attempts: two 503s, one 200. The bytes from the third
        attempt are returned. Retries must NOT raise on intermediate
        5xx — they should sleep + retry transparently."""
        from unittest.mock import MagicMock, patch

        aira = _client()
        responses = [
            _binary_resp(b"first-fail", status=503),
            _binary_resp(b"second-fail", status=503),
            _binary_resp(b"%PDF-1.4 success"),
        ]
        # patch sleep to keep the test fast
        with (
            patch.object(aira._client, "get", side_effect=responses),
            patch("aira.client.time.sleep") if False else patch("time.sleep"),
        ):
            data = aira.download_compliance_report("rep-1")
        assert data == b"%PDF-1.4 success"

    def test_download_does_not_retry_on_4xx(self):
        """A 404 must be raised, not retried — it's a real error."""
        from unittest.mock import patch

        aira = _client()
        with patch.object(
            aira._client,
            "get",
            return_value=_resp({"code": "REPORT_NOT_FOUND", "message": "not found"}, status=404),
        ) as get_mock:
            with pytest.raises(AiraError):
                aira.download_compliance_report("rep-bad")
        # Called exactly once — no retry.
        assert get_mock.call_count == 1

    def test_download_retries_then_gives_up(self):
        """After _DOWNLOAD_MAX_ATTEMPTS the last 5xx is propagated."""
        from unittest.mock import patch

        from aira.client import _DOWNLOAD_MAX_ATTEMPTS

        aira = _client()
        responses = [
            _binary_resp(b"x", status=502) for _ in range(_DOWNLOAD_MAX_ATTEMPTS)
        ]
        with (
            patch.object(aira._client, "get", side_effect=responses) as get_mock,
            patch("time.sleep"),
        ):
            with pytest.raises(AiraError):
                aira.download_compliance_report("rep-1")
        assert get_mock.call_count == _DOWNLOAD_MAX_ATTEMPTS

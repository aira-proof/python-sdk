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
    "org_id": "org-1",
    "period_start": "2026-04-01T00:00:00",
    "period_end": "2026-04-30T00:00:00",
    "action_id": None,
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
            "report_id": "rep-1",
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
            "receipt": {"receipt_id": "rec-1"},
            "regulation": {"framework": "eu_ai_act"},
            "request_id": "req-4",
        }
        with patch.object(aira._client, "get", return_value=_resp(body)):
            explanation = aira.get_action_explanation("act-1")
        assert isinstance(explanation, ActionExplanation)
        assert explanation.action["id"] == "act-1"

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
            "request_id": "req-5",
        }
        with patch.object(aira._client, "get", return_value=_resp(body)):
            explanation = await aira.get_action_explanation("act-1")
        assert explanation.action["id"] == "act-1"
        assert explanation.receipt is None


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

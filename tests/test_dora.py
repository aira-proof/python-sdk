"""Tests for the DORA SDK methods."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from aira import Aira, AsyncAira, DoraIncident, DoraTest, IctThirdParty


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


def _client() -> Aira:
    return Aira(api_key="aira_live_" + "x" * 32, base_url="http://test")


def _async_client() -> AsyncAira:
    return AsyncAira(api_key="aira_live_" + "x" * 32, base_url="http://test")


INCIDENT_OK = {
    "uuid": "i-1",
    "title": "Outage",
    "status": "detected",
    "severity": None,
    "category": None,
    "is_major": False,
    "detected_at": "2026-04-15T10:00:00Z",
    "classified_at": None,
    "resolved_at": None,
    "reported_at": None,
    "clients_affected_count": 1500,
    "has_report": False,
    "created_at": "2026-04-15T10:00:00Z",
    "org_uuid": "org-1",
    "description": "DB down",
    "affected_services": ["api"],
    "geographic_scope": None,
    "root_cause_summary": None,
    "root_cause_classification": None,
    "third_party_uuid": None,
    "resolution_summary": None,
    "lessons_learned": None,
    "related_action_uuids": None,
    "report_content_hash": None,
    "report_signature": None,
    "report_signing_key_id": None,
    "report_signed_at": None,
    "report_pdf_size_bytes": None,
    "request_id": "req-1",
}

THIRD_PARTY_OK = {
    "uuid": "tp-1",
    "org_uuid": "org-1",
    "vendor_name": "AWS",
    "service_description": "Cloud compute",
    "service_type": "cloud_compute",
    "criticality": "critical",
    "contract_start_date": "2026-01-01",
    "contract_end_date": None,
    "exit_strategy_summary": "12-month exit plan",
    "subcontractors": None,
    "data_categories": None,
    "jurisdiction": "US-EAST",
    "is_active": True,
    "created_at": "2026-01-01T00:00:00Z",
    "request_id": "req-2",
}


# ─── Sync ────────────────────────────────────────────────────────────


class TestSyncDora:
    def test_create_incident(self):
        aira = _client()
        with patch.object(aira._client, "post", return_value=_resp(INCIDENT_OK)):
            incident = aira.create_dora_incident(
                title="Outage", description="DB down",
                detected_at="2026-04-15T10:00:00Z",
                clients_affected_count=1500,
            )
        assert isinstance(incident, DoraIncident)
        assert incident.status == "detected"

    def test_classify_incident(self):
        aira = _client()
        body = {**INCIDENT_OK, "status": "classified", "severity": "critical",
                "category": "cyber_attack", "is_major": True}
        captured: dict = {}

        def _put(url, json=None, **_kw):
            captured["url"] = url
            captured["json"] = json
            return _resp(body)

        with patch.object(aira._client, "put", side_effect=_put):
            incident = aira.classify_dora_incident(
                "i-1", severity="critical", category="cyber_attack",
            )
        assert incident.is_major is True
        assert captured["url"] == "/dora/incidents/i-1/classify"
        assert captured["json"] == {
            "severity": "critical", "category": "cyber_attack",
        }

    def test_download_report_returns_pdf_bytes(self):
        aira = _client()
        fake = b"%PDF-1.4 fake"
        with patch.object(aira._client, "get", return_value=_binary_resp(fake)):
            data = aira.download_dora_incident_report("i-1")
        assert data.startswith(b"%PDF")

    def test_create_third_party(self):
        aira = _client()
        captured: dict = {}

        def _post(url, json=None, **_kw):
            captured["url"] = url
            captured["json"] = json
            return _resp(THIRD_PARTY_OK)

        with patch.object(aira._client, "post", side_effect=_post):
            tp = aira.create_ict_third_party(
                vendor_name="AWS", service_description="Cloud compute",
                service_type="cloud_compute", criticality="critical",
                exit_strategy_summary="12-month exit plan",
            )
        assert isinstance(tp, IctThirdParty)
        assert tp.criticality == "critical"
        assert captured["url"] == "/dora/third-parties"
        assert captured["json"]["vendor_name"] == "AWS"

    def test_list_incidents_filters(self):
        aira = _client()
        captured: dict = {}

        def _get(url, params=None, **_kw):
            captured["url"] = url
            captured["params"] = params
            return _resp({"items": [], "total": 0, "limit": 50,
                          "offset": 0, "request_id": "r"})

        with patch.object(aira._client, "get", side_effect=_get):
            aira.list_dora_incidents(severity="critical", is_major=True)
        assert captured["params"]["severity"] == "critical"
        assert captured["params"]["is_major"] is True

    def test_create_dora_test(self):
        aira = _client()
        body = {"uuid": "t-1", "test_type": "tlpt", "title": "Q1",
                "conducted_at": "2026-03-15", "conducted_by": "Recurity",
                "status": "passed"}
        with patch.object(aira._client, "post", return_value=_resp(body)):
            t = aira.create_dora_test(
                test_type="tlpt", title="Q1", scope="API",
                conducted_at="2026-03-15", conducted_by="Recurity",
                status="passed",
            )
        assert isinstance(t, DoraTest)
        assert t.test_type == "tlpt"


# ─── Async mirror ───────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAsyncDora:
    async def test_create_incident(self):
        aira = _async_client()
        with patch.object(aira._client, "post", return_value=_resp(INCIDENT_OK)):
            incident = await aira.create_dora_incident(
                title="x", description="y",
                detected_at="2026-04-15T10:00:00Z",
            )
        assert incident.status == "detected"

    async def test_create_third_party(self):
        aira = _async_client()
        with patch.object(
            aira._client, "post", return_value=_resp(THIRD_PARTY_OK)
        ):
            tp = await aira.create_ict_third_party(
                vendor_name="AWS", service_description="x",
                service_type="cloud_compute", criticality="critical",
            )
        assert tp.vendor_name == "AWS"

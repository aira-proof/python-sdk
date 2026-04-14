"""Tests for the output content-scan policy SDK methods."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from aira import Aira, AsyncAira, OutputPolicy


def _resp(data, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        json=data,
        request=httpx.Request("GET", "http://test"),
    )


def _client() -> Aira:
    return Aira(api_key="aira_live_" + "x" * 32, base_url="http://test")


def _async_client() -> AsyncAira:
    return AsyncAira(api_key="aira_live_" + "x" * 32, base_url="http://test")


POLICY_OK = {
    "enabled": True,
    "mode": "flag",
    "libraries": ["pii", "credentials", "prompt_injection"],
    "deny_severity_threshold": "critical",
    "redact_severity_threshold": "warning",
    "request_id": "req-1",
}


class TestSyncOutputPolicy:
    def test_get_output_policy(self):
        aira = _client()
        with patch.object(aira._client, "get", return_value=_resp(POLICY_OK)):
            policy = aira.get_output_policy()
        assert isinstance(policy, OutputPolicy)
        assert policy.mode == "flag"
        assert policy.enabled is True

    def test_update_output_policy_patches_body(self):
        aira = _client()
        captured: dict = {}

        def _patch(path, json=None, **_kw):
            captured["path"] = path
            captured["json"] = json
            return _resp({**POLICY_OK, "mode": "deny"})

        with patch.object(aira._client, "patch", side_effect=_patch):
            policy = aira.update_output_policy(mode="deny")
        assert policy.mode == "deny"
        assert captured["path"] == "/output-policies"
        # Only the fields the caller supplied are in the body — omitted
        # fields must not flow through as ``null`` (that would reset
        # them server-side).
        assert captured["json"] == {"mode": "deny"}

    def test_update_output_policy_filters_none_fields(self):
        aira = _client()
        captured: dict = {}

        def _patch(path, json=None, **_kw):
            captured["json"] = json
            return _resp(POLICY_OK)

        with patch.object(aira._client, "patch", side_effect=_patch):
            aira.update_output_policy(enabled=False, libraries=["pii"])
        assert captured["json"] == {"enabled": False, "libraries": ["pii"]}


@pytest.mark.asyncio
class TestAsyncOutputPolicy:
    async def test_get_output_policy(self):
        aira = _async_client()
        with patch.object(aira._client, "get", return_value=_resp(POLICY_OK)):
            policy = await aira.get_output_policy()
        assert policy.mode == "flag"

    async def test_update_output_policy(self):
        aira = _async_client()
        with patch.object(
            aira._client, "patch", return_value=_resp({**POLICY_OK, "mode": "redact"})
        ):
            policy = await aira.update_output_policy(mode="redact")
        assert policy.mode == "redact"

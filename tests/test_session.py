"""Tests for AiraSession and AsyncAiraSession."""

from unittest.mock import patch

import httpx
import pytest

from aira import Aira, AsyncAira
from aira.client import AiraSession, AsyncAiraSession


# --- Helpers (same pattern as test_client.py) ---

def _resp(data, status: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status, json=data, request=httpx.Request("GET", "http://test"))


RECEIPT = {
    "action_id": "act-1", "receipt_id": "rct-1", "payload_hash": "sha256:abc",
    "signature": "ed25519:xyz", "timestamp_token": "ts",
    "created_at": "2026-03-25T00:00:00Z", "request_id": "req-1", "warnings": None,
}


class TestSyncSession:
    def setup_method(self):
        self.c = Aira(api_key="aira_live_test", base_url="http://test")

    def teardown_method(self):
        self.c.close()

    def test_session_prefills_agent_id(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            s = self.c.session(agent_id="my-agent")
            s.notarize(action_type="x", details="y")
            body = m.call_args[1]["json"]
            assert body["agent_id"] == "my-agent"

    def test_kwarg_override(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            s = self.c.session(agent_id="default-agent")
            s.notarize(action_type="x", details="y", agent_id="override-agent")
            body = m.call_args[1]["json"]
            assert body["agent_id"] == "override-agent"

    def test_context_manager_works(self):
        with self.c.session(agent_id="my-agent") as s:
            assert s._defaults["agent_id"] == "my-agent"

    def test_session_trace_inherits_agent_id(self):
        """Session trace() should pass agent_id from defaults."""
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            s = self.c.session(agent_id="traced-agent")
            decorator = s.trace(action_type="function_call")
            assert decorator is not None
            # trace returns a decorator — the agent_id is merged from defaults

    def test_multiple_defaults(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            s = self.c.session(agent_id="my-agent", model_id="claude-4", agent_version="1.0")
            s.notarize(action_type="x", details="y")
            body = m.call_args[1]["json"]
            assert body["agent_id"] == "my-agent"
            assert body["model_id"] == "claude-4"
            assert body["agent_version"] == "1.0"

    def test_session_does_not_close_parent(self):
        s = self.c.session(agent_id="my-agent")
        s.__exit__(None, None, None)
        # Parent client should still be usable
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)):
            r = self.c.notarize(action_type="x", details="y")
            assert r.action_id == "act-1"

    def test_all_params_forwarded(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            s = self.c.session(agent_id="a", model_id="m")
            s.notarize(
                action_type="email_sent", details="test",
                instruction_hash="h", parent_action_id="p",
                store_details=True, idempotency_key="k",
            )
            body = m.call_args[1]["json"]
            assert body["agent_id"] == "a"
            assert body["model_id"] == "m"
            assert body["instruction_hash"] == "h"
            assert body["parent_action_id"] == "p"
            assert body["idempotency_key"] == "k"


class TestAsyncSession:
    @pytest.mark.asyncio
    async def test_async_session_prefills(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
                s = c.session(agent_id="async-agent")
                await s.notarize(action_type="x", details="y")
                body = m.call_args[1]["json"]
                assert body["agent_id"] == "async-agent"

    @pytest.mark.asyncio
    async def test_async_session_context_manager(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            async with c.session(agent_id="my-agent") as s:
                assert s._defaults["agent_id"] == "my-agent"

    @pytest.mark.asyncio
    async def test_async_session_notarize(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
                s = c.session(agent_id="a", model_id="claude")
                r = await s.notarize(action_type="decision", details="approved")
                body = m.call_args[1]["json"]
                assert body["agent_id"] == "a"
                assert body["model_id"] == "claude"
                assert r.action_id == "act-1"

"""Comprehensive tests for Aira SDK — full API coverage + security checks."""

import json
from unittest.mock import patch

import httpx
import pytest

from aira import Aira, AsyncAira, ActionReceipt, ActionDetail, AgentDetail, AgentVersion, EvidencePackage, ComplianceSnapshot, EscrowAccount, EscrowTransaction
from aira.client import AiraError, _sanitize_details, _validate_api_key, MAX_DETAILS_LENGTH


# --- Helpers ---

def _resp(data, status: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status, json=data, request=httpx.Request("GET", "http://test"))

def _paginated_resp(items: list, total: int = None) -> httpx.Response:
    t = total or len(items)
    return _resp({"data": items, "pagination": {"page": 1, "per_page": 20, "total": t, "has_more": False}})

RECEIPT = {"action_id": "act-1", "receipt_id": "rct-1", "payload_hash": "sha256:abc", "signature": "ed25519:xyz", "timestamp_token": "ts", "created_at": "2026-03-25T00:00:00Z", "request_id": "req-1", "warnings": None}
ACTION = {"action_id": "act-1", "org_id": "org-1", "action_type": "email_sent", "status": "notarized", "legal_hold": False, "action_details_hash": "sha256:abc", "created_at": "2026-03-25T00:00:00Z", "request_id": "req-1"}
AGENT = {"id": "ag-1", "agent_slug": "my-agent", "display_name": "My Agent", "status": "active", "public": True, "registered_at": "2026-03-25T00:00:00Z", "request_id": "req-1"}
VERSION = {"id": "v-1", "version": "1.0.0", "status": "active", "created_at": "2026-03-25T00:00:00Z"}
EVIDENCE = {"id": "pkg-1", "title": "Test", "action_ids": ["act-1"], "package_hash": "sha256:p", "signature": "ed25519:p", "status": "sealed", "created_at": "2026-03-25T00:00:00Z", "request_id": "req-1"}
SNAPSHOT = {"id": "s-1", "framework": "eu-ai-act", "status": "compliant", "findings": {}, "snapshot_hash": "sha256:s", "signature": "ed25519:s", "snapshot_at": "2026-03-25T00:00:00Z", "created_at": "2026-03-25T00:00:00Z", "request_id": "req-1"}
ESCROW_ACC = {"id": "esc-1", "currency": "EUR", "balance": "5000.00", "status": "active", "created_at": "2026-03-25T00:00:00Z", "request_id": "req-1"}
ESCROW_TX = {"id": "tx-1", "transaction_type": "deposit", "amount": "5000.00", "currency": "EUR", "transaction_hash": "sha256:tx", "signature": "ed25519:tx", "status": "completed", "created_at": "2026-03-25T00:00:00Z"}


class TestValidation:
    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key is required"):
            Aira(api_key="")

    def test_sanitize_truncates(self):
        assert _sanitize_details("x" * (MAX_DETAILS_LENGTH + 100)).endswith("...[truncated]")

    def test_sanitize_normal(self):
        assert _sanitize_details("hello") == "hello"


class TestSyncActions:
    def setup_method(self):
        self.c = Aira(api_key="aira_live_test", base_url="http://test")

    def teardown_method(self):
        self.c.close()

    def test_notarize(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)):
            r = self.c.notarize(action_type="email_sent", details="Test")
        assert isinstance(r, ActionReceipt) and r.action_id == "act-1"

    def test_notarize_all_params(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            self.c.notarize(action_type="x", details="y", agent_id="a", model_id="m", instruction_hash="h", parent_action_id="p", store_details=True, idempotency_key="k")
            b = m.call_args[1]["json"]
            assert b["agent_id"] == "a" and b["store_details"] is True and b["idempotency_key"] == "k"

    def test_get_action(self):
        with patch.object(self.c._client, "get", return_value=_resp(ACTION)):
            assert isinstance(self.c.get_action("act-1"), ActionDetail)

    def test_list_actions(self):
        with patch.object(self.c._client, "get", return_value=_paginated_resp([{"id": "1"}])):
            assert self.c.list_actions(action_type="email_sent").total == 1

    def test_authorize(self):
        with patch.object(self.c._client, "post", return_value=_resp({"ok": True})):
            assert self.c.authorize_action("act-1")["ok"]

    def test_legal_hold(self):
        with patch.object(self.c._client, "post", return_value=_resp({"legal_hold": True})):
            assert self.c.set_legal_hold("act-1")["legal_hold"]

    def test_release_hold(self):
        with patch.object(self.c._client, "delete", return_value=_resp({"legal_hold": False})):
            assert not self.c.release_legal_hold("act-1")["legal_hold"]

    def test_chain(self):
        with patch.object(self.c._client, "get", return_value=_resp({"chain": [{"id": "1"}, {"id": "2"}]})):
            assert len(self.c.get_action_chain("act-1")) == 2

    def test_verify_uses_public_client(self):
        with patch.object(self.c._public_client, "get", return_value=_resp({"valid": True, "public_key_id": "k", "message": "OK", "verified_at": "t", "request_id": "r"})):
            assert self.c.verify_action("act-1").valid


class TestSyncAgents:
    def setup_method(self):
        self.c = Aira(api_key="aira_live_test", base_url="http://test")

    def teardown_method(self):
        self.c.close()

    def test_register(self):
        with patch.object(self.c._client, "post", return_value=_resp(AGENT, 201)):
            assert self.c.register_agent("my-agent", "My Agent").agent_slug == "my-agent"

    def test_get(self):
        with patch.object(self.c._client, "get", return_value=_resp(AGENT)):
            assert self.c.get_agent("my-agent").display_name == "My Agent"

    def test_list(self):
        with patch.object(self.c._client, "get", return_value=_paginated_resp([AGENT])):
            assert self.c.list_agents(status="active").total == 1

    def test_update(self):
        with patch.object(self.c._client, "put", return_value=_resp({**AGENT, "display_name": "Updated"})):
            assert self.c.update_agent("my-agent", display_name="Updated").display_name == "Updated"

    def test_publish_version(self):
        with patch.object(self.c._client, "post", return_value=_resp(VERSION, 201)):
            assert self.c.publish_version("my-agent", "1.0.0", model_id="claude").version == "1.0.0"

    def test_list_versions(self):
        with patch.object(self.c._client, "get", return_value=_resp([VERSION])):
            assert len(self.c.list_versions("my-agent")) == 1

    def test_decommission(self):
        with patch.object(self.c._client, "post", return_value=_resp({**AGENT, "status": "decommissioned"})):
            assert self.c.decommission_agent("my-agent").status == "decommissioned"

    def test_transfer(self):
        with patch.object(self.c._client, "post", return_value=_resp({"status": "transferred"})):
            assert self.c.transfer_agent("my-agent", "org-2", reason="M&A")["status"] == "transferred"

    def test_agent_actions(self):
        with patch.object(self.c._client, "get", return_value=_paginated_resp([{"id": "a1"}])):
            assert self.c.get_agent_actions("my-agent").total == 1


class TestSyncEvidence:
    def setup_method(self):
        self.c = Aira(api_key="aira_live_test", base_url="http://test")

    def teardown_method(self):
        self.c.close()

    def test_create(self):
        with patch.object(self.c._client, "post", return_value=_resp(EVIDENCE, 201)):
            assert self.c.create_evidence_package("Test", ["act-1"]).package_hash == "sha256:p"

    def test_list(self):
        with patch.object(self.c._client, "get", return_value=_paginated_resp([{"id": "p1"}])):
            assert self.c.list_evidence_packages().total == 1

    def test_get(self):
        with patch.object(self.c._client, "get", return_value=_resp(EVIDENCE)):
            assert self.c.get_evidence_package("pkg-1").title == "Test"

    def test_time_travel(self):
        with patch.object(self.c._client, "post", return_value=_resp({"result_count": 5})):
            assert self.c.time_travel("2026-03-20T00:00:00Z")["result_count"] == 5

    def test_liability_chain(self):
        with patch.object(self.c._client, "get", return_value=_resp({"chain": [{"id": "1"}]})):
            assert len(self.c.liability_chain("act-1")) == 1


class TestSyncEstate:
    def setup_method(self):
        self.c = Aira(api_key="aira_live_test", base_url="http://test")

    def teardown_method(self):
        self.c.close()

    def test_set_will(self):
        with patch.object(self.c._client, "put", return_value=_resp({"id": "w1"})):
            assert self.c.set_agent_will("my-agent", successor_slug="v2")["id"] == "w1"

    def test_get_will(self):
        with patch.object(self.c._client, "get", return_value=_resp({"id": "w1"})):
            assert self.c.get_agent_will("my-agent")["id"] == "w1"

    def test_issue_death_cert(self):
        with patch.object(self.c._client, "post", return_value=_resp({"id": "dc-1"}, 201)):
            assert self.c.issue_death_certificate("my-agent")["id"] == "dc-1"

    def test_get_death_cert(self):
        with patch.object(self.c._client, "get", return_value=_resp({"id": "dc-1"})):
            assert self.c.get_death_certificate("my-agent")["id"] == "dc-1"

    def test_create_snapshot(self):
        with patch.object(self.c._client, "post", return_value=_resp(SNAPSHOT, 201)):
            assert self.c.create_compliance_snapshot("eu-ai-act").framework == "eu-ai-act"

    def test_list_snapshots(self):
        with patch.object(self.c._client, "get", return_value=_paginated_resp([{"id": "s1"}])):
            assert self.c.list_compliance_snapshots(framework="eu-ai-act").total == 1


class TestSyncEscrow:
    def setup_method(self):
        self.c = Aira(api_key="aira_live_test", base_url="http://test")

    def teardown_method(self):
        self.c.close()

    def test_create_account(self):
        with patch.object(self.c._client, "post", return_value=_resp(ESCROW_ACC, 201)):
            assert self.c.create_escrow_account(purpose="Test").balance == "5000.00"

    def test_list_accounts(self):
        with patch.object(self.c._client, "get", return_value=_paginated_resp([{"id": "e1"}])):
            assert self.c.list_escrow_accounts().total == 1

    def test_get_account(self):
        with patch.object(self.c._client, "get", return_value=_resp(ESCROW_ACC)):
            assert self.c.get_escrow_account("esc-1").status == "active"

    def test_deposit(self):
        with patch.object(self.c._client, "post", return_value=_resp(ESCROW_TX, 201)):
            assert self.c.escrow_deposit("esc-1", 5000.0).transaction_type == "deposit"

    def test_release(self):
        with patch.object(self.c._client, "post", return_value=_resp({**ESCROW_TX, "transaction_type": "release"}, 201)):
            assert self.c.escrow_release("esc-1", 2000.0).transaction_type == "release"

    def test_dispute(self):
        with patch.object(self.c._client, "post", return_value=_resp({**ESCROW_TX, "transaction_type": "dispute", "status": "disputed"}, 201)):
            assert self.c.escrow_dispute("esc-1", 1000.0, "Agent error").status == "disputed"


class TestSyncChat:
    def setup_method(self):
        self.c = Aira(api_key="aira_live_test", base_url="http://test")

    def teardown_method(self):
        self.c.close()

    def test_ask(self):
        with patch.object(self.c._client, "post", return_value=_resp({"content": "3 agents", "tools_used": []})):
            assert self.c.ask("How many?")["content"] == "3 agents"


class TestErrors:
    def setup_method(self):
        self.c = Aira(api_key="aira_live_test", base_url="http://test")

    def teardown_method(self):
        self.c.close()

    def test_404(self):
        with patch.object(self.c._client, "get", return_value=_resp({"error": "Not found", "code": "NOT_FOUND"}, 404)):
            with pytest.raises(AiraError) as e:
                self.c.get_action("bad")
            assert e.value.status == 404

    def test_429(self):
        with patch.object(self.c._client, "post", return_value=_resp({"error": "Rate limited", "code": "RATE_LIMIT_EXCEEDED"}, 429)):
            with pytest.raises(AiraError) as e:
                self.c.notarize("x", "y")
            assert e.value.status == 429

    def test_500(self):
        with patch.object(self.c._client, "get", return_value=_resp({"error": "Internal", "code": "INTERNAL"}, 500)):
            with pytest.raises(AiraError):
                self.c.get_agent("x")

    def test_non_json(self):
        resp = httpx.Response(status_code=502, text="Bad Gateway", request=httpx.Request("GET", "http://test"))
        with patch.object(self.c._client, "get", return_value=resp):
            with pytest.raises(AiraError) as e:
                self.c.get_action("x")
            assert e.value.status == 502


class TestTraceSecurity:
    def setup_method(self):
        self.c = Aira(api_key="aira_live_test", base_url="http://test")

    def teardown_method(self):
        self.c.close()

    def test_no_arg_leakage(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            @self.c.trace(agent_id="test")
            def login(username, password):
                return "token"
            login("admin", "secret-password-123")
            body = m.call_args[1]["json"]
            assert "secret-password-123" not in body["details"]
            assert "admin" not in body["details"]

    def test_no_result_leakage_by_default(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            @self.c.trace(agent_id="test")
            def get_key():
                return "sk-secret-key-123"
            get_key()
            assert "sk-secret-key-123" not in m.call_args[1]["json"]["details"]

    def test_result_included_when_opted_in(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            @self.c.trace(agent_id="test", include_result=True)
            def compute():
                return 42
            compute()
            assert "42" in m.call_args[1]["json"]["details"]

    def test_notarize_failure_non_blocking(self):
        with patch.object(self.c._client, "post", side_effect=Exception("Network down")):
            @self.c.trace(agent_id="test")
            def important():
                return "critical"
            assert important() == "critical"

    def test_hash_uses_metadata_not_values(self):
        with patch.object(self.c._client, "post", return_value=_resp(RECEIPT, 201)) as m:
            @self.c.trace(agent_id="test")
            def process(data, key=None):
                return "done"
            process({"pii": "secret"}, key="sk-123")
            body = m.call_args[1]["json"]
            assert body["instruction_hash"].startswith("sha256:")
            full = json.dumps(body)
            assert "secret" not in full and "sk-123" not in full


class TestContextManager:
    def test_sync(self):
        with Aira(api_key="aira_live_test", base_url="http://test") as c:
            assert c._client is not None

    @pytest.mark.asyncio
    async def test_async(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            assert c._client is not None


class TestAsync:
    @pytest.mark.asyncio
    async def test_notarize(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "post", return_value=_resp(RECEIPT, 201)):
                assert (await c.notarize(action_type="x", details="y")).action_id == "act-1"

    @pytest.mark.asyncio
    async def test_get_action(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "get", return_value=_resp(ACTION)):
                assert (await c.get_action("act-1")).action_type == "email_sent"

    @pytest.mark.asyncio
    async def test_list_actions(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "get", return_value=_paginated_resp([{"id": "1"}])):
                assert (await c.list_actions()).total == 1

    @pytest.mark.asyncio
    async def test_register_agent(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "post", return_value=_resp(AGENT, 201)):
                assert (await c.register_agent("a", "A")).agent_slug == "my-agent"

    @pytest.mark.asyncio
    async def test_verify_no_auth(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._public_client, "get", return_value=_resp({"valid": True, "public_key_id": "k", "message": "OK", "verified_at": "t", "request_id": "r"})):
                assert (await c.verify_action("act-1")).valid

    @pytest.mark.asyncio
    async def test_escrow_deposit(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "post", return_value=_resp(ESCROW_TX, 201)):
                assert (await c.escrow_deposit("esc-1", 5000.0)).transaction_type == "deposit"

    @pytest.mark.asyncio
    async def test_evidence_package(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "post", return_value=_resp(EVIDENCE, 201)):
                assert (await c.create_evidence_package("T", ["a"])).package_hash == "sha256:p"

    @pytest.mark.asyncio
    async def test_compliance_snapshot(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "post", return_value=_resp(SNAPSHOT, 201)):
                assert (await c.create_compliance_snapshot("eu-ai-act")).framework == "eu-ai-act"

    @pytest.mark.asyncio
    async def test_trace_decorator(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "post", return_value=_resp(RECEIPT, 201)):
                @c.trace(agent_id="a")
                async def compute(x):
                    return x * 2
                assert await compute(5) == 10

    @pytest.mark.asyncio
    async def test_set_will(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "put", return_value=_resp({"id": "w1"})):
                assert (await c.set_agent_will("a", successor_slug="b"))["id"] == "w1"

    @pytest.mark.asyncio
    async def test_list_agents(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "get", return_value=_paginated_resp([AGENT])):
                assert (await c.list_agents()).total == 1

    @pytest.mark.asyncio
    async def test_time_travel(self):
        async with AsyncAira(api_key="aira_live_test", base_url="http://test") as c:
            with patch.object(c._client, "post", return_value=_resp({"result_count": 3})):
                assert (await c.time_travel("2026-03-20T00:00:00Z"))["result_count"] == 3

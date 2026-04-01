"""Tests for OpenAI Agents SDK integration — aira.extras.openai_agents."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from aira.extras.openai_agents import AiraGuardrail


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.notarize = MagicMock()
    return client


class TestAiraGuardrail:
    def test_on_tool_call_notarizes(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1")
        g.on_tool_call("search", {"query": "test"})
        call_kwargs = mock_client.notarize.call_args[1]
        assert call_kwargs["action_type"] == "tool_call"
        assert "'search'" in call_kwargs["details"]
        assert "query" in call_kwargs["details"]

    def test_on_tool_result_notarizes(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1")
        g.on_tool_result("search", result="found 5 items")
        call_kwargs = mock_client.notarize.call_args[1]
        assert call_kwargs["action_type"] == "tool_completed"
        assert "Result length:" in call_kwargs["details"]

    def test_agent_id_forwarded(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="my-agent")
        g.on_tool_call("t")
        assert mock_client.notarize.call_args[1]["agent_id"] == "my-agent"

    def test_model_id_forwarded_when_set(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1", model_id="gpt-4o")
        g.on_tool_call("t")
        assert mock_client.notarize.call_args[1]["model_id"] == "gpt-4o"

    def test_model_id_omitted_when_none(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1")
        g.on_tool_call("t")
        assert "model_id" not in mock_client.notarize.call_args[1]

    def test_non_blocking_on_notarize_failure(self, mock_client):
        mock_client.notarize.side_effect = RuntimeError("API down")
        g = AiraGuardrail(mock_client, agent_id="a1")
        g.on_tool_call("t")  # Should not raise

    def test_details_truncated_to_5000(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1")
        g.on_tool_result("t", result="x" * 10000)
        details = mock_client.notarize.call_args[1]["details"]
        assert len(details) <= 5000

    def test_wrap_tool_calls_and_notarizes(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1")

        def my_tool(x: int) -> str:
            return f"result-{x}"

        wrapped = g.wrap_tool(my_tool)
        result = wrapped(42)
        assert result == "result-42"
        assert mock_client.notarize.call_count == 2  # on_tool_call + on_tool_result

    def test_trust_policy_enriches_details(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1", trust_policy={
            "verify_counterparty": True,
            "min_reputation": 60,
        })
        mock_client.get_agent_did.return_value = {"did": "did:web:airaproof.com:agents:search"}
        mock_client.get_reputation.return_value = {"score": 85, "tier": "gold"}
        g.on_tool_call("search", {"query": "test"})
        call_kwargs = mock_client.notarize.call_args[1]
        assert "trust:" in call_kwargs["details"]
        assert '"did_resolved": true' in call_kwargs["details"]
        assert '"reputation_score": 85' in call_kwargs["details"]

    def test_trust_policy_blocks_revoked_vc(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1", trust_policy={
            "verify_counterparty": True,
            "require_valid_vc": True,
            "block_revoked_vc": True,
        })
        mock_client.get_agent_did.return_value = {"did": "did:web:bad"}
        mock_client.get_agent_credential.return_value = {"id": "vc_1"}
        mock_client.verify_credential.return_value = {"valid": False}
        g.on_tool_call("bad", {"query": "test"})
        mock_client.notarize.assert_not_called()

    def test_trust_policy_doesnt_block_unregistered(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1", trust_policy={
            "verify_counterparty": True,
            "block_unregistered": False,
        })
        mock_client.get_agent_did.side_effect = Exception("Not found")
        g.on_tool_call("unknown", {"query": "test"})
        mock_client.notarize.assert_called_once()
        details = mock_client.notarize.call_args[1]["details"]
        assert '"did_resolved": false' in details

    def test_trust_policy_includes_reputation(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1", trust_policy={
            "verify_counterparty": True,
            "min_reputation": 80,
        })
        mock_client.get_agent_did.return_value = {"did": "did:web:low"}
        mock_client.get_reputation.return_value = {"score": 45, "tier": "bronze"}
        g.on_tool_call("low", {"q": "x"})
        details = mock_client.notarize.call_args[1]["details"]
        assert "reputation_warning" in details
        assert "Below minimum" in details

    def test_no_trust_policy_no_checks(self, mock_client):
        g = AiraGuardrail(mock_client, agent_id="a1")
        g.on_tool_call("search", {"query": "test"})
        mock_client.notarize.assert_called_once()
        details = mock_client.notarize.call_args[1]["details"]
        assert "trust:" not in details
        mock_client.get_agent_did.assert_not_called()

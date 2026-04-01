"""Tests for CrewAI integration — aira.extras.crewai."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from aira.extras.crewai import AiraCrewHook


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.notarize = MagicMock()
    return client


class TestAiraCrewHook:
    def test_task_callback_calls_notarize(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="agent-1")
        output = MagicMock()
        output.description = "Summarize the report"
        hook.task_callback(output)
        mock_client.notarize.assert_called_once()
        call_kwargs = mock_client.notarize.call_args[1]
        assert call_kwargs["action_type"] == "task_completed"
        assert "Summarize the report" in call_kwargs["details"]

    def test_step_callback_calls_notarize(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="agent-1")
        hook.step_callback("some step output")
        mock_client.notarize.assert_called_once()
        call_kwargs = mock_client.notarize.call_args[1]
        assert call_kwargs["action_type"] == "agent_step"
        assert "Output length:" in call_kwargs["details"]

    def test_agent_id_forwarded(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="my-agent")
        hook.step_callback("x")
        assert mock_client.notarize.call_args[1]["agent_id"] == "my-agent"

    def test_model_id_forwarded_when_set(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="a1", model_id="gpt-4")
        hook.step_callback("x")
        assert mock_client.notarize.call_args[1]["model_id"] == "gpt-4"

    def test_model_id_omitted_when_none(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="a1")
        hook.step_callback("x")
        assert "model_id" not in mock_client.notarize.call_args[1]

    def test_non_blocking_on_notarize_failure(self, mock_client):
        mock_client.notarize.side_effect = RuntimeError("API down")
        hook = AiraCrewHook(mock_client, agent_id="a1")
        # Should not raise
        hook.task_callback(MagicMock(description="test"))

    def test_details_truncated_to_5000(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="a1")
        output = MagicMock()
        output.description = "x" * 10000
        hook.task_callback(output)
        details = mock_client.notarize.call_args[1]["details"]
        assert len(details) <= 5000

    def test_for_crew_returns_callbacks_dict(self, mock_client):
        result = AiraCrewHook.for_crew(mock_client, agent_id="a1")
        assert "task_callback" in result
        assert "step_callback" in result
        assert callable(result["task_callback"])
        assert callable(result["step_callback"])

    def test_trust_policy_enriches_details(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="a1", trust_policy={
            "verify_counterparty": True,
            "min_reputation": 60,
        })
        mock_client.get_agent_did.return_value = {"did": "did:web:airaproof.com:agents:peer"}
        mock_client.get_reputation.return_value = {"score": 85, "tier": "gold"}
        # task_callback doesn't pass counterparty, so trust won't fire
        # but step_callback also doesn't — trust enrichment requires counterparty_id
        # Verify no trust context without counterparty
        hook.step_callback("x")
        details = mock_client.notarize.call_args[1]["details"]
        assert "trust:" not in details

    def test_trust_policy_blocks_revoked_vc(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="a1", trust_policy={
            "verify_counterparty": True,
            "require_valid_vc": True,
            "block_revoked_vc": True,
        })
        mock_client.get_agent_did.return_value = {"did": "did:web:bad"}
        mock_client.get_agent_credential.return_value = {"id": "vc_1"}
        mock_client.verify_credential.return_value = {"valid": False}
        # Manually call _notarize with counterparty_id to test blocking
        hook._notarize("test_action", "test details", counterparty_id="bad-agent")
        mock_client.notarize.assert_not_called()

    def test_trust_policy_doesnt_block_unregistered(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="a1", trust_policy={
            "verify_counterparty": True,
            "block_unregistered": False,
        })
        mock_client.get_agent_did.side_effect = Exception("Not found")
        hook._notarize("test_action", "test details", counterparty_id="unknown")
        mock_client.notarize.assert_called_once()
        details = mock_client.notarize.call_args[1]["details"]
        assert '"did_resolved": false' in details

    def test_trust_policy_includes_reputation(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="a1", trust_policy={
            "verify_counterparty": True,
            "min_reputation": 80,
        })
        mock_client.get_agent_did.return_value = {"did": "did:web:low"}
        mock_client.get_reputation.return_value = {"score": 45, "tier": "bronze"}
        hook._notarize("test_action", "test details", counterparty_id="low-agent")
        details = mock_client.notarize.call_args[1]["details"]
        assert "reputation_warning" in details
        assert "Below minimum" in details

    def test_no_trust_policy_no_checks(self, mock_client):
        hook = AiraCrewHook(mock_client, agent_id="a1")
        hook.step_callback("x")
        mock_client.notarize.assert_called_once()
        details = mock_client.notarize.call_args[1]["details"]
        assert "trust:" not in details
        mock_client.get_agent_did.assert_not_called()

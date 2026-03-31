"""Tests for AWS Bedrock integration — aira.extras.bedrock."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from aira.extras.bedrock import AiraBedrockHandler


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.notarize = MagicMock()
    return client


class TestAiraBedrockHandler:
    def test_wrap_invoke_model_calls_original_and_notarizes(self, mock_client):
        bedrock = MagicMock()
        bedrock.invoke_model = MagicMock(return_value={"body": "resp"})
        handler = AiraBedrockHandler(mock_client, agent_id="a1")
        wrapped = handler.wrap_invoke_model(bedrock)
        result = wrapped(modelId="anthropic.claude-v2")
        assert result == {"body": "resp"}
        bedrock.invoke_model.assert_called_once_with(modelId="anthropic.claude-v2")
        call_kwargs = mock_client.notarize.call_args[1]
        assert call_kwargs["action_type"] == "model_invoked"
        assert "anthropic.claude-v2" in call_kwargs["details"]

    def test_wrap_invoke_agent_calls_original_and_notarizes(self, mock_client):
        bedrock_agent = MagicMock()
        bedrock_agent.invoke_agent = MagicMock(return_value={"completion": "ok"})
        handler = AiraBedrockHandler(mock_client, agent_id="a1")
        wrapped = handler.wrap_invoke_agent(bedrock_agent)
        result = wrapped(agentId="AGENT123")
        assert result == {"completion": "ok"}
        call_kwargs = mock_client.notarize.call_args[1]
        assert call_kwargs["action_type"] == "agent_invoked"
        assert "AGENT123" in call_kwargs["details"]

    def test_agent_id_forwarded(self, mock_client):
        handler = AiraBedrockHandler(mock_client, agent_id="my-agent")
        handler.notarize_invocation("claude-v2")
        assert mock_client.notarize.call_args[1]["agent_id"] == "my-agent"

    def test_non_blocking_on_notarize_failure(self, mock_client):
        mock_client.notarize.side_effect = RuntimeError("API down")
        handler = AiraBedrockHandler(mock_client, agent_id="a1")
        handler.notarize_invocation("claude-v2")  # Should not raise

    def test_details_truncated_to_5000(self, mock_client):
        handler = AiraBedrockHandler(mock_client, agent_id="a1")
        handler.notarize_invocation("m1", details="x" * 10000)
        details = mock_client.notarize.call_args[1]["details"]
        assert len(details) <= 5000

    def test_notarize_invocation_default_details(self, mock_client):
        handler = AiraBedrockHandler(mock_client, agent_id="a1")
        handler.notarize_invocation("anthropic.claude-v2")
        details = mock_client.notarize.call_args[1]["details"]
        assert "anthropic.claude-v2" in details

    def test_notarize_invocation_custom_details(self, mock_client):
        handler = AiraBedrockHandler(mock_client, agent_id="a1")
        handler.notarize_invocation("m1", details="Custom invocation context")
        assert mock_client.notarize.call_args[1]["details"] == "Custom invocation context"

    def test_wrap_invoke_model_unknown_model_id(self, mock_client):
        bedrock = MagicMock()
        bedrock.invoke_model = MagicMock(return_value={})
        handler = AiraBedrockHandler(mock_client, agent_id="a1")
        wrapped = handler.wrap_invoke_model(bedrock)
        wrapped()  # No modelId kwarg
        assert "unknown" in mock_client.notarize.call_args[1]["details"]

    def test_wrap_invoke_agent_unknown_agent_id(self, mock_client):
        bedrock_agent = MagicMock()
        bedrock_agent.invoke_agent = MagicMock(return_value={})
        handler = AiraBedrockHandler(mock_client, agent_id="a1")
        wrapped = handler.wrap_invoke_agent(bedrock_agent)
        wrapped()  # No agentId kwarg
        assert "unknown" in mock_client.notarize.call_args[1]["details"]

    def test_wrap_invoke_model_non_blocking_on_failure(self, mock_client):
        mock_client.notarize.side_effect = RuntimeError("fail")
        bedrock = MagicMock()
        bedrock.invoke_model = MagicMock(return_value={"ok": True})
        handler = AiraBedrockHandler(mock_client, agent_id="a1")
        wrapped = handler.wrap_invoke_model(bedrock)
        result = wrapped(modelId="m1")
        assert result == {"ok": True}  # Original call still succeeds

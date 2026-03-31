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

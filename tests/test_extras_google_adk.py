"""Tests for Google ADK integration — aira.extras.google_adk."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest

from aira.extras.google_adk import AiraPlugin


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.notarize = MagicMock()
    return client


class TestAiraPlugin:
    def test_before_tool_call_notarizes(self, mock_client):
        p = AiraPlugin(mock_client, agent_id="a1")
        p.before_tool_call("search", {"query": "hello"})
        call_kwargs = mock_client.notarize.call_args[1]
        assert call_kwargs["action_type"] == "tool_invoked"
        assert "'search'" in call_kwargs["details"]
        assert "query" in call_kwargs["details"]

    def test_after_tool_call_notarizes(self, mock_client):
        p = AiraPlugin(mock_client, agent_id="a1")
        p.after_tool_call("search", result="5 results")
        call_kwargs = mock_client.notarize.call_args[1]
        assert call_kwargs["action_type"] == "tool_completed"
        assert "Result length:" in call_kwargs["details"]

    def test_agent_id_forwarded(self, mock_client):
        p = AiraPlugin(mock_client, agent_id="my-agent")
        p.before_tool_call("t")
        assert mock_client.notarize.call_args[1]["agent_id"] == "my-agent"

    def test_model_id_forwarded_when_set(self, mock_client):
        p = AiraPlugin(mock_client, agent_id="a1", model_id="gemini-pro")
        p.before_tool_call("t")
        assert mock_client.notarize.call_args[1]["model_id"] == "gemini-pro"

    def test_model_id_omitted_when_none(self, mock_client):
        p = AiraPlugin(mock_client, agent_id="a1")
        p.before_tool_call("t")
        assert "model_id" not in mock_client.notarize.call_args[1]

    def test_non_blocking_on_notarize_failure(self, mock_client):
        mock_client.notarize.side_effect = RuntimeError("API down")
        p = AiraPlugin(mock_client, agent_id="a1")
        p.before_tool_call("t")  # Should not raise

    def test_details_truncated_to_5000(self, mock_client):
        p = AiraPlugin(mock_client, agent_id="a1")
        p.after_tool_call("t", result="x" * 10000)
        details = mock_client.notarize.call_args[1]["details"]
        assert len(details) <= 5000

    def test_before_tool_call_no_args(self, mock_client):
        p = AiraPlugin(mock_client, agent_id="a1")
        p.before_tool_call("my_tool")
        call_kwargs = mock_client.notarize.call_args[1]
        assert "Arg keys: []" in call_kwargs["details"]

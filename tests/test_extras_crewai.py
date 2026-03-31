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

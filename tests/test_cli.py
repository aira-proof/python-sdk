"""Tests for Aira CLI."""
from __future__ import annotations

import os
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from typer.testing import CliRunner

from aira.cli import app
from aira.types import (
    AgentDetail,
    ComplianceSnapshot,
    EvidencePackage,
    PaginatedList,
    VerifyResult,
)

runner = CliRunner()

FAKE_KEY = "aira_test_cli000000"


def _make_verify_result(valid: bool = True) -> VerifyResult:
    return VerifyResult(
        valid=valid,
        public_key_id="pk-1",
        message="OK" if valid else "INVALID",
        verified_at="2026-01-01T00:00:00Z",
        request_id="req-1",
        receipt_id="rct-1",
        action_id="act-1",
    )


def _make_paginated(data: list | None = None) -> PaginatedList:
    data = data or []
    return PaginatedList(data=data, total=len(data), page=1, per_page=20, has_more=False)


def _mock_client():
    """Return a MagicMock that behaves like an Aira client."""
    return MagicMock()


# ---- test_version ----

def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "aira-sdk" in result.output


# ---- test_verify_success ----

@patch("aira.cli.Aira")
def test_verify_success(mock_aira_cls):
    client = _mock_client()
    client.verify_action.return_value = _make_verify_result(valid=True)
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["verify", "act-123", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    assert "Action verified" in result.output
    client.verify_action.assert_called_once_with("act-123")


# ---- test_verify_invalid ----

@patch("aira.cli.Aira")
def test_verify_invalid(mock_aira_cls):
    client = _mock_client()
    client.verify_action.return_value = _make_verify_result(valid=False)
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["verify", "act-bad", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    assert "Verification failed" in result.output


# ---- test_verify_not_found ----

@patch("aira.cli.Aira")
def test_verify_not_found(mock_aira_cls):
    client = _mock_client()
    client.verify_action.side_effect = Exception("Not found")
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["verify", "act-gone", "--api-key", FAKE_KEY])
    assert result.exit_code == 1
    assert "Not found" in result.output


# ---- test_actions_list ----

@patch("aira.cli.Aira")
def test_actions_list(mock_aira_cls):
    client = _mock_client()
    client.list_actions.return_value = _make_paginated([
        {"action_id": "act-001", "action_type": "email_sent", "agent_id": "bot-1", "status": "notarized", "created_at": "2026-01-01T00:00:00Z"},
    ])
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["actions", "list", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    assert "act-001" in result.output
    client.list_actions.assert_called_once_with(per_page=10)


# ---- test_actions_list_with_agent ----

@patch("aira.cli.Aira")
def test_actions_list_with_agent(mock_aira_cls):
    client = _mock_client()
    client.get_agent_actions.return_value = _make_paginated([
        {"action_id": "act-002", "action_type": "loan_decision", "agent_id": "lending-bot", "status": "notarized", "created_at": "2026-02-01T00:00:00Z"},
    ])
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["actions", "list", "--agent", "lending-bot", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    assert "act-002" in result.output
    client.get_agent_actions.assert_called_once_with("lending-bot")


# ---- test_actions_list_with_limit ----

@patch("aira.cli.Aira")
def test_actions_list_with_limit(mock_aira_cls):
    client = _mock_client()
    client.list_actions.return_value = _make_paginated([])
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["actions", "list", "--limit", "5", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    client.list_actions.assert_called_once_with(per_page=5)


# ---- test_agents_list ----

@patch("aira.cli.Aira")
def test_agents_list(mock_aira_cls):
    client = _mock_client()
    client.list_agents.return_value = _make_paginated([
        {"agent_slug": "my-bot", "display_name": "My Bot", "status": "active", "public": False},
    ])
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["agents", "list", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    assert "my-bot" in result.output
    client.list_agents.assert_called_once()


# ---- test_agents_create ----

@patch("aira.cli.Aira")
def test_agents_create(mock_aira_cls):
    client = _mock_client()
    client.register_agent.return_value = AgentDetail(
        id="ag-1", agent_slug="new-bot", display_name="New Bot",
        status="active", public=False, registered_at="2026-01-01T00:00:00Z", request_id="req-1",
    )
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["agents", "create", "new-bot", "--name", "New Bot", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    assert "Agent registered" in result.output
    assert "new-bot" in result.output
    client.register_agent.assert_called_once_with(agent_slug="new-bot", display_name="New Bot")


# ---- test_snapshot_create ----

@patch("aira.cli.Aira")
def test_snapshot_create(mock_aira_cls):
    client = _mock_client()
    client.create_compliance_snapshot.return_value = ComplianceSnapshot(
        id="snap-1", framework="eu-ai-act", status="complete",
        findings={}, snapshot_hash="abc", signature="sig",
        snapshot_at="2026-01-01T00:00:00Z", created_at="2026-01-01T00:00:00Z", request_id="req-1",
    )
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["snapshot", "create", "eu-ai-act", "my-agent", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    assert "Snapshot created" in result.output
    assert "snap-1" in result.output
    client.create_compliance_snapshot.assert_called_once_with(framework="eu-ai-act", agent_slug="my-agent")


# ---- test_package_create ----

@patch("aira.cli.Aira")
def test_package_create(mock_aira_cls):
    client = _mock_client()
    client.create_evidence_package.return_value = EvidencePackage(
        id="pkg-1", title="Audit Q1", action_ids=["a1", "a2"],
        package_hash="hash", signature="sig", status="sealed",
        created_at="2026-01-01T00:00:00Z", request_id="req-1",
    )
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["package", "create", "--title", "Audit Q1", "--actions", "a1,a2", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    assert "Evidence package created" in result.output
    assert "pkg-1" in result.output
    client.create_evidence_package.assert_called_once_with(title="Audit Q1", action_ids=["a1", "a2"])


# ---- test_missing_api_key ----

@patch.dict(os.environ, {}, clear=True)
@patch("aira.cli.Aira")
def test_missing_api_key(mock_aira_cls):
    # Ensure AIRA_API_KEY is not set
    env = os.environ.copy()
    env.pop("AIRA_API_KEY", None)
    with patch.dict(os.environ, env, clear=True):
        result = runner.invoke(app, ["agents", "list"])
        assert result.exit_code == 1
        assert "No API key" in result.output


# ---- test_api_key_from_env ----

@patch("aira.cli.Aira")
def test_api_key_from_env(mock_aira_cls):
    client = _mock_client()
    client.list_agents.return_value = _make_paginated([])
    mock_aira_cls.return_value = client

    with patch.dict(os.environ, {"AIRA_API_KEY": FAKE_KEY}):
        result = runner.invoke(app, ["agents", "list"])
        assert result.exit_code == 0
        mock_aira_cls.assert_called_once_with(api_key=FAKE_KEY)


# ---- test_api_key_from_flag ----

@patch("aira.cli.Aira")
def test_api_key_from_flag(mock_aira_cls):
    client = _mock_client()
    client.list_agents.return_value = _make_paginated([])
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["agents", "list", "--api-key", FAKE_KEY])
    assert result.exit_code == 0
    mock_aira_cls.assert_called_once_with(api_key=FAKE_KEY)


# ---- Error branch tests ----

@patch("aira.cli.Aira")
def test_verify_exception(mock_aira_cls):
    client = _mock_client()
    client.verify_action.side_effect = RuntimeError("connection refused")
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["verify", "act-err", "--api-key", FAKE_KEY])
    assert result.exit_code == 1
    assert "connection refused" in result.output


@patch("aira.cli.Aira")
def test_actions_list_exception(mock_aira_cls):
    client = _mock_client()
    client.list_actions.side_effect = RuntimeError("timeout")
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["actions", "list", "--api-key", FAKE_KEY])
    assert result.exit_code == 1
    assert "timeout" in result.output


@patch("aira.cli.Aira")
def test_agents_list_exception(mock_aira_cls):
    client = _mock_client()
    client.list_agents.side_effect = RuntimeError("unauthorized")
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["agents", "list", "--api-key", FAKE_KEY])
    assert result.exit_code == 1
    assert "unauthorized" in result.output


@patch("aira.cli.Aira")
def test_agents_create_exception(mock_aira_cls):
    client = _mock_client()
    client.register_agent.side_effect = RuntimeError("slug taken")
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["agents", "create", "dup-bot", "--name", "Dup", "--api-key", FAKE_KEY])
    assert result.exit_code == 1
    assert "slug taken" in result.output


@patch("aira.cli.Aira")
def test_snapshot_create_exception(mock_aira_cls):
    client = _mock_client()
    client.create_compliance_snapshot.side_effect = RuntimeError("framework invalid")
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["snapshot", "create", "bad-framework", "my-agent", "--api-key", FAKE_KEY])
    assert result.exit_code == 1
    assert "framework invalid" in result.output


@patch("aira.cli.Aira")
def test_package_create_exception(mock_aira_cls):
    client = _mock_client()
    client.create_evidence_package.side_effect = RuntimeError("action not found")
    mock_aira_cls.return_value = client

    result = runner.invoke(app, ["package", "create", "--title", "Fail", "--actions", "bad-id", "--api-key", FAKE_KEY])
    assert result.exit_code == 1
    assert "action not found" in result.output

"""Tests for aira.extras lazy __getattr__ imports."""
from __future__ import annotations

import pytest


class TestExtrasLazyImports:
    """Test that aira.extras exposes the correct names via lazy imports."""

    def test_import_verify_signature(self):
        from aira.extras.webhooks import verify_signature
        from aira.extras import verify_signature as Imported
        assert Imported is verify_signature

    def test_import_parse_event(self):
        from aira.extras.webhooks import parse_event
        from aira.extras import parse_event as Imported
        assert Imported is parse_event

    def test_import_webhook_event(self):
        from aira.extras.webhooks import WebhookEvent
        from aira.extras import WebhookEvent as Imported
        assert Imported is WebhookEvent

    def test_import_aira_callback_handler(self):
        from aira.extras.langchain import AiraCallbackHandler
        from aira.extras import AiraCallbackHandler as Imported
        assert Imported is AiraCallbackHandler

    def test_import_aira_crew_hook(self):
        from aira.extras.crewai import AiraCrewHook
        from aira.extras import AiraCrewHook as Imported
        assert Imported is AiraCrewHook

    def test_import_aira_guardrail(self):
        from aira.extras.openai_agents import AiraGuardrail
        from aira.extras import AiraGuardrail as Imported
        assert Imported is AiraGuardrail

    def test_import_aira_plugin(self):
        from aira.extras.google_adk import AiraPlugin
        from aira.extras import AiraPlugin as Imported
        assert Imported is AiraPlugin

    def test_import_aira_bedrock_handler(self):
        from aira.extras.bedrock import AiraBedrockHandler
        from aira.extras import AiraBedrockHandler as Imported
        assert Imported is AiraBedrockHandler

    def test_nonexistent_name_raises_attribute_error(self):
        import aira.extras
        with pytest.raises(AttributeError, match="has no attribute 'DoesNotExist'"):
            _ = aira.extras.DoesNotExist

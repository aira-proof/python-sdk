"""Tests for aira.gateway helpers."""

from aira.gateway import (
    DEFAULT_GATEWAY_URL,
    gateway_anthropic_kwargs,
    gateway_openai_kwargs,
)


class TestGatewayOpenaiKwargs:
    def test_default_url(self):
        kw = gateway_openai_kwargs(aira_api_key="aira_live_test")
        assert kw["base_url"] == f"{DEFAULT_GATEWAY_URL}/gateway/openai/v1"
        assert kw["default_headers"]["X-Aira-Api-Key"] == "aira_live_test"

    def test_custom_url(self):
        kw = gateway_openai_kwargs(
            aira_api_key="aira_live_test",
            gateway_url="https://custom.example.com",
        )
        assert kw["base_url"] == "https://custom.example.com/gateway/openai/v1"

    def test_trailing_slash_stripped(self):
        kw = gateway_openai_kwargs(
            aira_api_key="k",
            gateway_url="https://example.com/",
        )
        assert kw["base_url"] == "https://example.com/gateway/openai/v1"


class TestGatewayAnthropicKwargs:
    def test_default_url(self):
        kw = gateway_anthropic_kwargs(aira_api_key="aira_live_test")
        assert kw["base_url"] == f"{DEFAULT_GATEWAY_URL}/gateway/anthropic/v1"
        assert kw["default_headers"]["X-Aira-Api-Key"] == "aira_live_test"

    def test_custom_url(self):
        kw = gateway_anthropic_kwargs(
            aira_api_key="aira_live_test",
            gateway_url="https://custom.example.com",
        )
        assert kw["base_url"] == "https://custom.example.com/gateway/anthropic/v1"

    def test_trailing_slash_stripped(self):
        kw = gateway_anthropic_kwargs(
            aira_api_key="k",
            gateway_url="https://example.com/",
        )
        assert kw["base_url"] == "https://example.com/gateway/anthropic/v1"

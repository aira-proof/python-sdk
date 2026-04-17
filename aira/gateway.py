"""Helpers for routing LLM SDK calls through Aira Gateway.

Usage:
    from aira.gateway import gateway_openai_kwargs, gateway_anthropic_kwargs

    # OpenAI
    import openai
    client = openai.OpenAI(**gateway_openai_kwargs(aira_api_key="aira_live_..."))

    # Anthropic
    import anthropic
    client = anthropic.Anthropic(**gateway_anthropic_kwargs(aira_api_key="aira_live_..."))
"""

DEFAULT_GATEWAY_URL = "https://api.airaproof.com"


def gateway_openai_kwargs(
    aira_api_key: str,
    gateway_url: str = DEFAULT_GATEWAY_URL,
) -> dict:
    """Return kwargs for ``openai.OpenAI()`` to route through Aira Gateway."""
    return {
        "base_url": f"{gateway_url.rstrip('/')}/gateway/openai/v1",
        "default_headers": {"X-Aira-Api-Key": aira_api_key},
    }


def gateway_anthropic_kwargs(
    aira_api_key: str,
    gateway_url: str = DEFAULT_GATEWAY_URL,
) -> dict:
    """Return kwargs for ``anthropic.Anthropic()`` to route through Aira Gateway."""
    return {
        "base_url": f"{gateway_url.rstrip('/')}/gateway/anthropic/v1",
        "default_headers": {"X-Aira-Api-Key": aira_api_key},
    }

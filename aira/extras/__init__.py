"""Aira SDK framework integrations — lazy imports to avoid pulling in optional deps."""

def __getattr__(name: str):
    _imports = {
        "AiraCallbackHandler": "aira.extras.langchain",
        "AiraCrewHook": "aira.extras.crewai",
        "AiraGuardrail": "aira.extras.openai_agents",
        "AiraPlugin": "aira.extras.google_adk",
        "AiraBedrockHandler": "aira.extras.bedrock",
        "verify_signature": "aira.extras.webhooks",
        "parse_event": "aira.extras.webhooks",
        "WebhookEvent": "aira.extras.webhooks",
    }
    if name in _imports:
        import importlib
        module = importlib.import_module(_imports[name])
        return getattr(module, name)
    raise AttributeError(f"module 'aira.extras' has no attribute {name!r}")

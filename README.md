# Aira Python SDK

[![PyPI](https://img.shields.io/pypi/v/aira-sdk)](https://pypi.org/project/aira-sdk/)
[![License](https://img.shields.io/pypi/l/aira-sdk)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/aira-sdk)](https://pypi.org/project/aira-sdk/)

Authorize every AI agent action before it runs. Sign every outcome with Ed25519.

## Table of contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Core methods](#core-methods)
- [Async support](#async-support)
- [Gateway](#gateway)
- [Framework integrations](#framework-integrations)
- [Content scanning](#content-scanning)
- [Compliance and DORA](#compliance-and-dora)
- [Self-hosted](#self-hosted)
- [Links](#links)

## Installation

```bash
pip install aira-sdk
```

Requires Python 3.9+.

## Quick start

Three steps: **authorize** the action, **execute** it, **notarize** the outcome.

```python
from aira import Aira

aira = Aira(api_key="aira_live_xxx")

# 1. Authorize — policies evaluate, denied actions raise AiraError
auth = aira.authorize(
    action_type="wire_transfer",
    details="Send EUR 75,000 to vendor-x",
    agent_id="payments-agent",
    model_id="claude-sonnet-4-6",
)

# 2. Execute
ref = send_wire(75000, to="vendor-x")

# 3. Notarize — mints an Ed25519 + RFC 3161 receipt
receipt = aira.notarize(
    action_id=auth.action_id,
    outcome="completed",
    outcome_details=f"Wire sent, ref={ref}",
)
print(receipt.signature)  # ed25519:base64url...
```

If the action requires human approval, `auth.status` returns `"pending_approval"` and you can enqueue it for review.

> **Universal receipts** — Every action — authorized, denied, or failed — produces an Ed25519 receipt. The audit trail has zero gaps.

## Core methods

| Method | Description |
|---|---|
| `authorize()` | Gate before execution. Returns `Authorization` (`authorized` or `pending_approval`). Raises `AiraError` if denied. |
| `notarize()` | Sign after execution. Mints Ed25519 + RFC 3161 receipt. |
| `verify_action()` | Public receipt verification -- no auth required. |
| `get_action()` | Retrieve action details and receipt. |
| `list_actions()` | List actions with filters. |
| `cosign_action()` | Human co-signature on an action. |
| `get_replay_context()` | Reproducibility metadata (prompt hash, tool inputs, model params). |

## Async support

`AsyncAira` mirrors every method on `Aira`. Use `await` and an async context manager.

```python
from aira import AsyncAira

async with AsyncAira(api_key="aira_live_xxx") as aira:
    auth = await aira.authorize(
        action_type="contract_signed",
        details="Signed vendor agreement #1234",
        agent_id="procurement-agent",
    )
    if auth.status == "authorized":
        ref = await sign_contract(1234)
        await aira.notarize(
            action_id=auth.action_id,
            outcome="completed",
            outcome_details=f"signed, ref={ref}",
        )
```

## Gateway

Route existing OpenAI or Anthropic calls through Aira. Every request is policy-checked and receipted with zero prompt changes.

```python
from aira import gateway_openai_kwargs

client = openai.OpenAI(api_key="sk-...", **gateway_openai_kwargs(aira_api_key="aira_live_xxx"))
```

The Anthropic equivalent:

```python
from aira import gateway_anthropic_kwargs

client = anthropic.Anthropic(**gateway_anthropic_kwargs(aira_api_key="aira_live_xxx"))
```

Both helpers return `base_url` and `default_headers` dicts. Self-hosted deployments can pass `gateway_url` to point at your own instance.

## Framework integrations

| Integration | Install | Type |
|---|---|---|
| **LangChain** | `pip install aira-sdk[langchain]` | gate |
| **OpenAI Agents** | `pip install aira-sdk[openai-agents]` | gate |
| **Google ADK** | `pip install aira-sdk[google-adk]` | gate |
| **AWS Bedrock** | `pip install aira-sdk[bedrock]` | gate |
| **CrewAI** | `pip install aira-sdk[crewai]` | audit |
| **MCP** | `pip install aira-sdk[mcp]` | adapter |
| **Webhooks** | `pip install aira-sdk[webhooks]` | adapter |

**gate** intercepts before execution and can deny. **audit** records after execution. **adapter** exposes Aira as tools the host framework can call.

```python
# LangChain
from aira.extras.langchain import AiraCallbackHandler
handler = AiraCallbackHandler(client=aira, agent_id="research-agent")
result = chain.invoke({"input": "Analyze Q1"}, config={"callbacks": [handler]})

# OpenAI Agents
from aira.extras.openai_agents import AiraGuardrail
guardrail = AiraGuardrail(client=aira, agent_id="assistant-agent")
search = guardrail.wrap_tool(search_tool, tool_name="web_search")
```

## Content scanning

Verify agent outputs against your organization's endpoint whitelist. Configure allowed domains and content policies in the [dashboard](https://app.airaproof.com), enforce them at `authorize()` time.

## Compliance and DORA

Aira provides built-in support for regulatory compliance:

- **Compliance bundles** -- sealed, Merkle-rooted evidence packets (EU AI Act Art 12, ISO 42001, SOC 2 CC7)
- **DORA compliance** -- ICT incident reporting, resilience testing, third-party risk management
- **Public verification** -- anyone can verify a receipt with `verify_action()`, no auth required

## Self-hosted

Point the SDK at your own deployment:

```python
aira = Aira(api_key="aira_live_xxx", base_url="https://aira.your-infra.com")
```

All features -- policies, receipts, settlements -- work identically on self-hosted.

## Links

- [Documentation](https://docs.airaproof.com)
- [API Reference](https://docs.airaproof.com/docs/api-reference)
- [Gateway Guide](https://docs.airaproof.com/docs/guides/gateway)
- [Dashboard](https://app.airaproof.com)
- [GitHub](https://github.com/aira-proof/python-sdk)

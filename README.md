# Aira Python SDK

The authorization and audit layer for AI agents. Every action authorized before it runs, every outcome signed with Ed25519.

[![PyPI](https://img.shields.io/pypi/v/aira-sdk)](https://pypi.org/project/aira-sdk/)
[![License](https://img.shields.io/pypi/l/aira-sdk)](LICENSE)

## Install

```bash
pip install aira-sdk
```

## Quick start

### Option A: Gateway (zero code change)

Route your existing OpenAI or Anthropic calls through the Aira Gateway. Every request is policy-checked and receipted -- no SDK integration needed.

```python
import openai
from aira import gateway_openai_kwargs

client = openai.OpenAI(
    api_key="sk-...",
    **gateway_openai_kwargs(aira_api_key="aira_live_xxx"),
)

# Every call now flows through Aira. Policies evaluate, receipts mint.
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Summarize Q1 revenue"}],
)
```

### Option B: SDK integration

Full control with the two-step flow: **authorize** before execution, **notarize** after.

```python
from aira import Aira, AiraError

aira = Aira(api_key="aira_live_xxx")

# 1. Gate the action -- policies run here, denied calls raise AiraError
auth = aira.authorize(
    action_type="wire_transfer",
    details="Send EUR 75,000 to vendor-x",
    agent_id="payments-agent",
    model_id="claude-sonnet-4-6",
)

# 2. Execute only if authorized
if auth.status == "authorized":
    ref = send_wire(75000, to="vendor-x")
    receipt = aira.notarize(
        action_id=auth.action_id,
        outcome="completed",
        outcome_details=f"Wire sent, ref={ref}",
    )
    print(receipt.signature)  # ed25519:base64url...

elif auth.status == "pending_approval":
    queue.enqueue(auth.action_id)  # wait for action.approved webhook
```

## Gateway helpers

Route LLM SDK traffic through Aira with zero code changes to your prompts or tools.

```python
from aira import gateway_openai_kwargs, gateway_anthropic_kwargs

# OpenAI / Azure OpenAI
client = openai.OpenAI(**gateway_openai_kwargs(aira_api_key="aira_live_xxx"))

# Anthropic
client = anthropic.Anthropic(**gateway_anthropic_kwargs(aira_api_key="aira_live_xxx"))
```

Both return `base_url` and `default_headers` dicts that plug into the respective SDK constructors.

## Core API

| Method | Purpose |
|---|---|
| `authorize()` | Gate before execution. Returns `Authorization` with status `authorized` or `pending_approval`. Raises `AiraError("POLICY_DENIED")` if denied. |
| `notarize()` | Sign after execution. Mints the Ed25519 + RFC 3161 receipt. |
| `verify_action()` | Public receipt verification -- no auth required. Returns signature, public key, signed payload, RFC 3161 token. |
| `get_action()` | Retrieve action details + receipt. |
| `list_actions()` | List actions with filters. |
| `cosign_action()` | Human co-signature on an action. |
| `get_replay_context()` | Reproducibility metadata (prompt hash, tool inputs, model params). |

## Async support

`AsyncAira` mirrors every method on `Aira`. The only difference is `await`.

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

## Framework integrations

| Integration | Install | Type | Pre-exec gate? |
|---|---|---|---|
| **LangChain** | `pip install aira-sdk[langchain]` | gate | Yes (tools) |
| **OpenAI Agents** | `pip install aira-sdk[openai-agents]` | gate | Yes |
| **Google ADK** | `pip install aira-sdk[google-adk]` | gate | Yes |
| **AWS Bedrock** | `pip install aira-sdk[bedrock]` | gate | Yes |
| **CrewAI** | `pip install aira-sdk[crewai]` | audit | No |
| **MCP** | `pip install aira-sdk[mcp]` | adapter | N/A |

**gate** -- intercepts before execution and can deny. **audit** -- records after execution (no pre-exec hook in the host framework). **adapter** -- exposes Aira as tools the host framework can call.

```python
# LangChain example
from aira.extras.langchain import AiraCallbackHandler

handler = AiraCallbackHandler(client=aira, agent_id="research-agent")
result = chain.invoke({"input": "Analyze Q1"}, config={"callbacks": [handler]})

# OpenAI Agents example
from aira.extras.openai_agents import AiraGuardrail

guardrail = AiraGuardrail(client=aira, agent_id="assistant-agent")
search = guardrail.wrap_tool(search_tool, tool_name="web_search")
```

## Features

- **Policy engine** -- rules, AI evaluation, or multi-model consensus. Configured in dashboard, enforced at `authorize()` time.
- **Human approval** -- hold high-stakes actions for human review. Pass `require_approval=True`.
- **Content scanning** -- endpoint verification against org whitelist.
- **Ed25519 receipts** -- every completed action gets a cryptographic receipt.
- **RFC 3161 timestamps** -- third-party timestamping authority proof.
- **Compliance bundles** -- sealed, Merkle-rooted evidence packets (EU AI Act Art 12, ISO 42001, SOC 2 CC7).
- **DORA compliance** -- ICT incident reporting, resilience testing, third-party risk.
- **Public verification** -- anyone can verify a receipt with `verify_action()`, no auth required.
- **Drift detection** -- per-agent behavioral baselines, KL divergence scoring, automatic alerts.
- **Agent identity** -- W3C DID (`did:web`), Verifiable Credentials, key rotation.
- **Mutual notarization** -- two-party co-signing for high-stakes cross-agent actions.
- **Reputation scoring** -- agent trust scores and tiers.
- **Escrow** -- liability commitment ledgers with deposit/release/dispute flow.
- **Merkle settlements** -- periodic anchoring of all receipts into signed batches.
- **Offline mode** -- queue actions locally, flush with `sync()` when back online.
- **Session context** -- `aira.session(agent_id=..., model_id=...)` pre-fills defaults for a block of calls.

## Self-hosted

Point the SDK at your own deployment by passing `base_url`:

```python
aira = Aira(api_key="aira_live_xxx", base_url="https://aira.your-infra.com")
```

Gateway helpers accept the same `gateway_url` parameter. All features -- policy engine, receipts, settlements -- work identically on self-hosted.

## Links

- [Docs](https://docs.airaproof.com)
- [API Reference](https://docs.airaproof.com/docs/api-reference)
- [Gateway Guide](https://docs.airaproof.com/docs/guides/gateway)
- [Dashboard](https://app.airaproof.com)
- [GitHub](https://github.com/aira-proof/python-sdk)

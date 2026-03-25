# Aira Python SDK

Legal infrastructure for AI agents. Notarize actions, register agents, build evidence packages, manage lifecycle, escrow liability.

```bash
pip install aira-sdk
```

## Quick Start

```python
from aira import Aira

aira = Aira(api_key="aira_live_xxx")

# Notarize an agent action
receipt = aira.notarize(
    action_type="email_sent",
    details="Sent onboarding email to customer@example.com",
    agent_id="support-agent",
    model_id="claude-sonnet-4-6",
    instruction_hash="sha256:a1b2c3...",
)

print(receipt.payload_hash)   # sha256:e5f6a7b8...
print(receipt.signature)       # ed25519:base64url...
print(receipt.action_id)       # uuid
```

## Decorator — Auto-Notarize Functions

```python
@aira.trace(agent_id="lending-agent", action_type="loan_decision")
def approve_loan(application):
    decision = model.predict(application)
    return decision

# Every call to approve_loan() is automatically notarized
result = approve_loan({"credit_score": 742, "income": 45000})
```

## Async Support

```python
from aira import AsyncAira

async with AsyncAira(api_key="aira_live_xxx") as aira:
    receipt = await aira.notarize(
        action_type="contract_signed",
        details="Agent signed vendor agreement #1234",
        agent_id="procurement-agent",
    )

    # Async decorator
    @aira.trace(agent_id="my-agent")
    async def process_order(order):
        return await execute(order)
```

## Agent Registry

```python
# Register an agent
agent = aira.register_agent(
    agent_slug="support-agent-v2",
    display_name="Customer Support Agent",
    capabilities=["email", "chat", "tickets"],
    public=True,
)

# Publish a version
version = aira.publish_version(
    slug="support-agent-v2",
    version="1.0.0",
    model_id="claude-sonnet-4-6",
    changelog="Initial release",
)

# Decommission
aira.decommission_agent("old-agent")
```

## Evidence Packages

```python
# Bundle actions into a sealed evidence package
package = aira.create_evidence_package(
    title="Q1 2026 Audit Trail — Lending Agent",
    action_ids=["act-uuid-1", "act-uuid-2", "act-uuid-3"],
    description="All lending decisions for regulatory review",
)

print(package.package_hash)  # Cryptographically sealed
print(package.signature)     # Ed25519 signed
```

## Compliance Snapshots

```python
snapshot = aira.create_compliance_snapshot(
    framework="eu-ai-act",
    agent_slug="lending-agent",
    findings={"art_12_logging": "pass", "art_14_oversight": "pass"},
)
```

## Agent Will & Estate

```python
# Set succession plan
aira.set_agent_will(
    slug="support-agent-v2",
    successor_slug="support-agent-v3",
    succession_policy="transfer_to_successor",
    data_retention_days=2555,
    notify_emails=["compliance@acme.com"],
)
```

## Escrow

```python
# Create escrow account
account = aira.create_escrow_account(purpose="Vendor contract #4521")

# Deposit before agent acts
tx = aira.escrow_deposit(account.id, amount=5000.00, description="10% liability deposit")

# Release after successful completion
aira.escrow_release(account.id, amount=5000.00)
```

## Ask Aira (Chat)

```python
response = aira.ask("How many email actions were notarized this week?")
print(response["content"])
```

## Public Verification

```python
# Anyone can verify — no auth needed
result = aira.verify_action("action-uuid")
print(result.valid)     # True
print(result.message)   # "Action receipt exists and signing key is valid."
```

## Error Handling

```python
from aira import Aira, AiraError

try:
    receipt = aira.notarize(action_type="email_sent", details="test")
except AiraError as e:
    print(e.status)   # 429
    print(e.code)     # PLAN_LIMIT_EXCEEDED
    print(e.message)  # Monthly operation limit reached
```

## Configuration

```python
aira = Aira(
    api_key="aira_live_xxx",
    base_url="https://your-self-hosted.com",  # Self-hosted
    timeout=60.0,                               # Request timeout
)
```

## Links

- [Documentation](https://docs.airaproof.com)
- [API Reference](https://docs.airaproof.com/docs/api-reference)
- [Dashboard](https://app.airaproof.com)

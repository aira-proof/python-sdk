# Lending Agent — Complete Aira SDK Example

A real AI lending agent that evaluates loan applications using Claude and demonstrates **every feature** of the `aira-sdk`.

## Features Covered

| # | Feature | SDK Methods Used |
|---|---------|-----------------|
| 1 | **Agent Registry** | `register_agent`, `publish_version`, `update_agent`, `list_agents`, `get_agent`, `list_versions` |
| 2 | **Notarization** | `notarize` (with idempotency), chain of custody (`parent_action_id`), `get_action`, `get_action_chain`, `list_actions`, `@aira.trace` decorator |
| 3 | **Multi-Model Consensus** | `run_case`, `list_cases` |
| 4 | **Evidence** | `create_evidence_package`, `list_evidence_packages`, `get_evidence_package`, `time_travel` |
| 5 | **Estate & Compliance** | `set_agent_will`, `get_agent_will`, `create_compliance_snapshot`, `list_compliance_snapshots` |
| 6 | **Escrow** | `create_escrow_account`, `escrow_deposit`, `escrow_release`, `list_escrow_accounts` |
| 7 | **Chat** | `ask` |
| 8 | **Verification** | `verify_action` (public, no auth) |
| 9 | **Error Handling** | `AiraError` with status, code, message |

## Setup

```bash
pip install aira-sdk anthropic
export AIRA_API_KEY="aira_live_xxx"      # https://app.airaproof.com/dashboard/api-keys
export ANTHROPIC_API_KEY="sk-ant-..."     # For Claude AI model
python agent.py
```

## Output

```
============================================================
  Aira Lending Agent — Complete SDK Demo
============================================================

1. Agent Registry
----------------------------------------
   ✓ Registered: lending-agent
   ✓ Version: 1.0.0
   ✓ Updated description
   ✓ 6 agent(s) in registry
   ✓ Status: active
   ✓ 1 version(s)

2. Action Notarization
----------------------------------------
   AI decision: APPROVED (confidence: 0.91)
   ✓ Notarized: act_01J8X...
   ✓ Signature: ed25519:Mzx0xEB...
   ✓ Chained: act_01J8Y...
   ✓ Type: loan_decision
   ✓ Chain: 2 action(s)
   ✓ Loan decisions: 5
   ✓ @trace: credit=good (auto-notarized)

3. Multi-Model Consensus
----------------------------------------
   ✓ Decision: APPROVE
   ✓ Confidence: 0.89
   ✓ Human review: no
   ✓ Total cases: 12

4. Evidence & Discovery
----------------------------------------
   ✓ Sealed: "Loan Decision — Maria Schmidt"
   ✓ Hash: sha256:c6f4a2b8e91b...
   ✓ Total packages: 8
   ✓ Retrieved: Loan Decision — Maria Schmidt
   ✓ Time-travel: queried

5. Agent Estate & Compliance
----------------------------------------
   ✓ Will set: 2555-day retention
   ✓ Policy: transfer_to_successor
   ✓ EU AI Act: compliant
   ✓ Snapshots: 3

6. Escrow & Liability
----------------------------------------
   ✓ Account: esc_01J8Z...
   ✓ Deposited: €1,500
   ✓ Released: €1,500
   ✓ Accounts: 2

7. Ask Aira
----------------------------------------
   ✓ Today you notarized 5 loan decisions across...

8. Public Verification
----------------------------------------
   ✓ Valid: True
   ✓ Key: aira-signing-key-v1
   ✓ Action receipt exists and signing key is valid...

9. Error Handling
----------------------------------------
   ✓ Caught: [NOT_FOUND] Action receipt not found

============================================================
  All 9 feature areas demonstrated.
  Dashboard: https://app.airaproof.com
  Docs:      https://docs.airaproof.com
  SDK:       pip install aira-sdk
============================================================
```

## Links

- [SDK Documentation](https://docs.airaproof.com/docs/getting-started/sdk)
- [API Reference](https://docs.airaproof.com/docs/api-reference)
- [GitHub — aira-sdk](https://github.com/aira-verify/python-sdk)
- [PyPI — aira-sdk](https://pypi.org/project/aira-sdk/)

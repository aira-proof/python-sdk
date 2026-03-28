"""Aira SDK — legal infrastructure for AI agents.

Usage:
    from aira import Aira

    aira = Aira(api_key="aira_live_xxx")

    # Notarize an action
    receipt = aira.notarize(
        action_type="email_sent",
        details="Sent onboarding email to customer@example.com",
        agent_id="support-agent",
    )

    # Decorator
    @aira.trace(agent_id="lending-agent", action_type="loan_decision")
    def approve_loan(application):
        return model.predict(application)
"""

from aira.client import Aira, AsyncAira, AiraError
from aira.types import (
    ActionReceipt,
    ActionDetail,
    AgentDetail,
    AgentVersion,
    EvidencePackage,
    ComplianceSnapshot,
    EscrowAccount,
    EscrowTransaction,
)

__version__ = "0.1.1"

__all__ = [
    "Aira",
    "AsyncAira",
    "AiraError",
    "ActionReceipt",
    "ActionDetail",
    "AgentDetail",
    "AgentVersion",
    "EvidencePackage",
    "ComplianceSnapshot",
    "EscrowAccount",
    "EscrowTransaction",
]

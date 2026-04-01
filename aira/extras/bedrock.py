"""AWS Bedrock integration — notarize model invocations."""
from __future__ import annotations
import functools
import json
import logging
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from aira import Aira

logger = logging.getLogger(__name__)


class AiraBedrockHandler:
    """Wraps Bedrock invoke_model/invoke_agent to notarize each call."""

    def __init__(self, client: "Aira", agent_id: str, trust_policy: dict | None = None):
        self.client = client
        self.agent_id = agent_id
        self._trust_policy = trust_policy

    def _check_trust(self, counterparty_id: str | None = None) -> dict:
        """Check counterparty trust. Returns trust_context dict for receipt enrichment."""
        if not self._trust_policy or not counterparty_id:
            return {}

        trust_context: dict[str, Any] = {"counterparty_id": counterparty_id}

        try:
            if self._trust_policy.get("verify_counterparty"):
                try:
                    did_info = self.client.get_agent_did(counterparty_id)
                    trust_context["did_resolved"] = True
                    trust_context["did"] = did_info.get("did")
                except Exception:
                    trust_context["did_resolved"] = False
                    trust_context["recommendation"] = "Counterparty not registered in Aira"

            if self._trust_policy.get("require_valid_vc") and trust_context.get("did_resolved"):
                try:
                    vc = self.client.get_agent_credential(counterparty_id)
                    result = self.client.verify_credential(vc)
                    trust_context["vc_valid"] = result.get("valid", False)
                    if not trust_context["vc_valid"] and self._trust_policy.get("block_revoked_vc"):
                        trust_context["blocked"] = True
                        trust_context["block_reason"] = "Counterparty VC revoked or invalid"
                except Exception:
                    trust_context["vc_valid"] = None

            min_rep = self._trust_policy.get("min_reputation")
            if min_rep and trust_context.get("did_resolved"):
                try:
                    rep = self.client.get_reputation(counterparty_id)
                    trust_context["reputation_score"] = rep.get("score")
                    trust_context["reputation_tier"] = rep.get("tier")
                    if rep.get("score", 0) < min_rep:
                        trust_context["reputation_warning"] = f"Below minimum ({rep.get('score')} < {min_rep})"
                except Exception:
                    trust_context["reputation_score"] = None
        except Exception:
            pass  # trust checks are non-blocking

        return trust_context

    def _notarize(self, action_type: str, details: str, counterparty_id: str | None = None) -> None:
        try:
            trust_ctx = self._check_trust(counterparty_id)
            if trust_ctx.get("blocked"):
                logger.warning("Action blocked by trust policy: %s", trust_ctx.get("block_reason"))
                return

            full_details = details
            if trust_ctx:
                full_details += f" | trust: {json.dumps(trust_ctx)}"

            self.client.notarize(action_type=action_type, details=full_details[:5000], agent_id=self.agent_id)
        except Exception as e:
            logger.warning("Aira notarize failed (non-blocking): %s", e)

    def wrap_invoke_model(self, bedrock_client: Any) -> Callable:
        """Return a wrapped invoke_model that notarizes each call."""
        original = bedrock_client.invoke_model

        @functools.wraps(original)
        def wrapped(**kwargs: Any) -> Any:
            model_id = kwargs.get("modelId", "unknown")
            trust_ctx = self._check_trust(model_id)
            if trust_ctx.get("blocked"):
                logger.warning("Action blocked by trust policy: %s", trust_ctx.get("block_reason"))
                return None
            response = original(**kwargs)
            self._notarize("model_invoked", f"Bedrock invoke_model: {model_id}", counterparty_id=model_id)
            return response

        return wrapped

    def wrap_invoke_agent(self, bedrock_agent_client: Any) -> Callable:
        """Return a wrapped invoke_agent that notarizes each call."""
        original = bedrock_agent_client.invoke_agent

        @functools.wraps(original)
        def wrapped(**kwargs: Any) -> Any:
            agent_id = kwargs.get("agentId", "unknown")
            response = original(**kwargs)
            self._notarize("agent_invoked", f"Bedrock invoke_agent: {agent_id}", counterparty_id=agent_id)
            return response

        return wrapped

    def notarize_invocation(self, model_id: str, details: str | None = None) -> None:
        """Manual hook for custom Bedrock invocations."""
        self._notarize("model_invoked", details or f"Bedrock model invoked: {model_id}", counterparty_id=model_id)

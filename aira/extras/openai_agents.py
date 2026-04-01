"""OpenAI Agents SDK integration — notarize tool calls as guardrail."""
from __future__ import annotations
import json
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aira import Aira

logger = logging.getLogger(__name__)


class AiraGuardrail:
    """Guardrail that notarizes tool calls in OpenAI Agents SDK."""

    def __init__(self, client: "Aira", agent_id: str, model_id: str | None = None, trust_policy: dict | None = None):
        self.client = client
        self.agent_id = agent_id
        self.model_id = model_id
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

            kwargs: dict[str, Any] = {"action_type": action_type, "details": full_details[:5000], "agent_id": self.agent_id}
            if self.model_id:
                kwargs["model_id"] = self.model_id
            self.client.notarize(**kwargs)
        except Exception as e:
            logger.warning("Aira notarize failed (non-blocking): %s", e)

    def on_tool_call(self, tool_name: str, arguments: dict | None = None) -> None:
        """Call after a tool execution to notarize it."""
        arg_keys = list((arguments or {}).keys())
        self._notarize("tool_call", f"Tool '{tool_name}' called. Arg keys: {arg_keys}", counterparty_id=tool_name)

    def on_tool_result(self, tool_name: str, result: Any = None) -> None:
        """Call after a tool returns to notarize the completion."""
        self._notarize("tool_completed", f"Tool '{tool_name}' completed. Result length: {len(str(result))} chars", counterparty_id=tool_name)

    def wrap_tool(self, tool_fn: Any, tool_name: str | None = None) -> Any:
        """Wrap a tool function to auto-notarize calls."""
        import functools
        name = tool_name or getattr(tool_fn, "__name__", "unknown")

        @functools.wraps(tool_fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            trust_ctx = self._check_trust(name)
            if trust_ctx.get("blocked"):
                logger.warning("Action blocked by trust policy: %s", trust_ctx.get("block_reason"))
                return None
            self.on_tool_call(name, kwargs)
            result = tool_fn(*args, **kwargs)
            self.on_tool_result(name, result)
            return result

        return wrapper

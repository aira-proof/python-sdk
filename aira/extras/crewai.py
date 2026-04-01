"""CrewAI integration — notarize task and step completions."""
from __future__ import annotations
import json
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aira import Aira

logger = logging.getLogger(__name__)


class AiraCrewHook:
    """CrewAI hook that notarizes task completions via Aira."""

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

    def task_callback(self, output: Any) -> None:
        """Called by CrewAI when a task completes."""
        desc = str(getattr(output, "description", ""))[:200]
        self._notarize("task_completed", f"Task completed: {desc}")

    def step_callback(self, step_output: Any) -> None:
        """Called by CrewAI on each agent step."""
        self._notarize("agent_step", f"Agent step completed. Output length: {len(str(step_output))} chars")

    @classmethod
    def for_crew(cls, client: "Aira", agent_id: str, **kwargs) -> dict[str, Any]:
        """Return callbacks dict compatible with CrewAI's Crew() constructor."""
        hook = cls(client, agent_id, **kwargs)
        return {
            "task_callback": hook.task_callback,
            "step_callback": hook.step_callback,
        }

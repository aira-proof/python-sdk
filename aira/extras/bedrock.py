"""AWS Bedrock integration — notarize model invocations."""
from __future__ import annotations
import functools
import logging
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from aira import Aira

logger = logging.getLogger(__name__)


class AiraBedrockHandler:
    """Wraps Bedrock invoke_model/invoke_agent to notarize each call."""

    def __init__(self, client: "Aira", agent_id: str):
        self.client = client
        self.agent_id = agent_id

    def _notarize(self, action_type: str, details: str) -> None:
        try:
            self.client.notarize(action_type=action_type, details=details[:5000], agent_id=self.agent_id)
        except Exception as e:
            logger.warning("Aira notarize failed (non-blocking): %s", e)

    def wrap_invoke_model(self, bedrock_client: Any) -> Callable:
        """Return a wrapped invoke_model that notarizes each call."""
        original = bedrock_client.invoke_model

        @functools.wraps(original)
        def wrapped(**kwargs: Any) -> Any:
            model_id = kwargs.get("modelId", "unknown")
            response = original(**kwargs)
            self._notarize("model_invoked", f"Bedrock invoke_model: {model_id}")
            return response

        return wrapped

    def wrap_invoke_agent(self, bedrock_agent_client: Any) -> Callable:
        """Return a wrapped invoke_agent that notarizes each call."""
        original = bedrock_agent_client.invoke_agent

        @functools.wraps(original)
        def wrapped(**kwargs: Any) -> Any:
            agent_id = kwargs.get("agentId", "unknown")
            response = original(**kwargs)
            self._notarize("agent_invoked", f"Bedrock invoke_agent: {agent_id}")
            return response

        return wrapped

    def notarize_invocation(self, model_id: str, details: str | None = None) -> None:
        """Manual hook for custom Bedrock invocations."""
        self._notarize("model_invoked", details or f"Bedrock model invoked: {model_id}")

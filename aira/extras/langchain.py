"""LangChain integration — auto-notarize tool and chain completions."""
from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aira import Aira, AsyncAira

logger = logging.getLogger(__name__)

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
except ImportError:
    raise ImportError(
        "langchain-core is required for the LangChain integration. "
        "Install with: pip install aira-sdk[langchain]"
    )


class AiraCallbackHandler(BaseCallbackHandler):
    """LangChain callback that notarizes tool and chain completions via Aira."""

    def __init__(
        self,
        client: "Aira | AsyncAira",
        agent_id: str,
        model_id: str | None = None,
        action_types: dict[str, str] | None = None,
    ):
        self.client = client
        self.agent_id = agent_id
        self.model_id = model_id
        self._action_types = {
            "tool_end": "tool_call",
            "chain_end": "chain_completed",
            "llm_end": "llm_completion",
            **(action_types or {}),
        }

    def _notarize(self, action_type: str, details: str) -> None:
        """Non-blocking notarize — failures logged, never raised."""
        try:
            kwargs = {"action_type": action_type, "details": details[:5000], "agent_id": self.agent_id}
            if self.model_id:
                kwargs["model_id"] = self.model_id
            self.client.notarize(**kwargs)
        except Exception as e:
            logger.warning("Aira notarize failed (non-blocking): %s", e)

    def on_tool_end(self, output: str, *, name: str = "unknown", **kwargs: Any) -> None:
        self._notarize(
            self._action_types["tool_end"],
            f"Tool '{name}' completed. Output length: {len(str(output))} chars",
        )

    def on_chain_end(self, outputs: dict, **kwargs: Any) -> None:
        keys = list(outputs.keys()) if isinstance(outputs, dict) else []
        self._notarize(
            self._action_types["chain_end"],
            f"Chain completed. Output keys: {keys}",
        )

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        gen_count = len(response.generations) if hasattr(response, "generations") else 0
        self._notarize(
            self._action_types["llm_end"],
            f"LLM completed. Generations: {gen_count}",
        )

"""OpenAI Agents SDK integration — notarize tool calls as guardrail."""
from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aira import Aira

logger = logging.getLogger(__name__)


class AiraGuardrail:
    """Guardrail that notarizes tool calls in OpenAI Agents SDK."""

    def __init__(self, client: "Aira", agent_id: str, model_id: str | None = None):
        self.client = client
        self.agent_id = agent_id
        self.model_id = model_id

    def _notarize(self, action_type: str, details: str) -> None:
        try:
            kwargs: dict[str, Any] = {"action_type": action_type, "details": details[:5000], "agent_id": self.agent_id}
            if self.model_id:
                kwargs["model_id"] = self.model_id
            self.client.notarize(**kwargs)
        except Exception as e:
            logger.warning("Aira notarize failed (non-blocking): %s", e)

    def on_tool_call(self, tool_name: str, arguments: dict | None = None) -> None:
        """Call after a tool execution to notarize it."""
        arg_keys = list((arguments or {}).keys())
        self._notarize("tool_call", f"Tool '{tool_name}' called. Arg keys: {arg_keys}")

    def on_tool_result(self, tool_name: str, result: Any = None) -> None:
        """Call after a tool returns to notarize the completion."""
        self._notarize("tool_completed", f"Tool '{tool_name}' completed. Result length: {len(str(result))} chars")

    def wrap_tool(self, tool_fn: Any, tool_name: str | None = None) -> Any:
        """Wrap a tool function to auto-notarize calls."""
        import functools
        name = tool_name or getattr(tool_fn, "__name__", "unknown")

        @functools.wraps(tool_fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.on_tool_call(name, kwargs)
            result = tool_fn(*args, **kwargs)
            self.on_tool_result(name, result)
            return result

        return wrapper
